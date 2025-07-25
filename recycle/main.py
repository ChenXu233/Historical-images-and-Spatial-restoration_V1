import numpy as np
import cv2
import matplotlib.pyplot as plt
from matplotlib import font_manager
import os

from scipy.optimize import minimize

## 类型
from typing import List

## 本身
from logger import logging
from utils import (
    load_and_prepare_image,
    load_dem_data,
    get_features,
    read_camera_locations,
    read_points_data,
    get_dem_elevation,
    reprojection_to_pixel,
    reprojection_to_lon_lat,
)
from schema import CameraLocation, PointData
from geo_transformer import geo_transformer

# 设置字体
plt.rcParams["font.sans-serif"] = ["SimHei"]  # 使用黑体
plt.rcParams["axes.unicode_minus"] = False  # 解决负号 '-' 显示
# 验证字体是否存在
font_path = font_manager.findSystemFonts(fontpaths=None, fontext="ttf")


RANSACBOUND = 50.0


# **********
# Find homography function
# **********
def find_homography(
    pixels,
    pos3ds,
    camera_location,
    ransacbound,
):
    pixels = np.array(pixels)
    pos2 = np.zeros((len(pixels), 2))
    good = np.zeros(len(pixels))
    for i in range(len(pixels)):
        good[i] = pixels[i][0] != 0 or pixels[i][1] != 0
        p = pos3ds[i, :] - camera_location
        p = np.array([p[2], p[1], p[0]])
        p = p / p[2]
        pos2[i, :] = p[0:2]
    M, mask = cv2.findHomography(
        pos2[good == 1], np.array(pixels)[good == 1], cv2.RANSAC, ransacbound
    )

    M = np.linalg.inv(np.array(M, dtype=np.float64))
    err1 = 0
    err2 = 0
    # 新增：计算图像对角线长度用于归一化（假设图像尺寸已知）
    img_diagonal = np.linalg.norm([pixels[:, 0].max(), pixels[:, 1].max()])
    huber_delta = 0.1 * img_diagonal  # Huber损失阈值设为图像对角线的10%

    for i in range(pos2[good == 1].shape[0]):
        p1 = np.array(pixels)[good == 1][i, :]
        pp = np.array([pos2[good == 1][i, 0], pos2[good == 1][i, 1], 1.0])
        pp2 = np.matmul(np.linalg.inv(M), pp)
        pp2 = pp2 / pp2[2]
        P1 = np.array([p1[0], p1[1], 1.0])
        PP2 = np.matmul(M, P1)
        PP2 = PP2 / PP2[2]
        P2 = pos2[good == 1][i, :]

        # 计算Huber损失（替代原L2范数）
        error1 = np.linalg.norm(p1 - pp2[0:2])
        error2 = np.linalg.norm(P2 - PP2[0:2])

        # 归一化误差（除以图像对角线长度）
        error1_normalized = error1 / img_diagonal
        error2_normalized = error2 / img_diagonal

        # Huber损失计算
        huber_err1 = (
            0.5 * error1_normalized**2
            if error1_normalized <= huber_delta
            else huber_delta * (error1_normalized - 0.5 * huber_delta)
        )
        huber_err2 = (
            0.5 * error2_normalized**2
            if error2_normalized <= huber_delta
            else huber_delta * (error2_normalized - 0.5 * huber_delta)
        )

        if mask[i] == 1:
            err1 += huber_err1  # 内点使用Huber损失
            err2 += huber_err2
        else:
            # 外点使用实际误差的Huber损失（替代原固定值惩罚）
            err1 += huber_err1
            err2 += huber_err2

    return M, err1, err2, mask


def find_homographies(
    point_data: List[PointData],
    camera_locations: List[CameraLocation],
):
    pixels = []
    pos3ds = []
    symbols = []

    for r in point_data:
        pixels.append(r.pixel)
        pos3ds.append(r.pos3d)
        symbols.append(r.symbol)

    pixels = np.array(pixels)
    pos3ds = np.array(pos3ds)
    symbols = np.array(symbols)

    loc3ds = []
    grids = []
    for cl in camera_locations:
        grids.append(cl.grid_code)
        loc3ds.append(cl.pos3d)
    grids = np.array(grids)
    loc3ds = np.array(loc3ds)

    num_matches = np.zeros((loc3ds.shape[0], 2))
    scores = []
    homographies = []
    for i in range(0, grids.shape[0], 1):
        grid_code_min = 0
        if grids[i] >= grid_code_min:
            M, err1, err2, mask = find_homography(
                pixels,
                pos3ds,
                loc3ds[i],
                RANSACBOUND,
            )
            num_matches[i, 0], num_matches[i, 1] = err1, err2
            homographies.append((M, mask))
        else:
            num_matches[i, :] = 0
        score = [
            i + 1,
            num_matches[i, 0],
            num_matches[i, 1],
            grids[i],
            loc3ds[i][0],
            loc3ds[i][1],
            loc3ds[i][2],
        ]
        scores.append(score)

        print(
            f"Camera Location {i}: Grid Code={grids[i]}, Position={loc3ds[i]}, Matches={num_matches[i]}"
        )

    # print(f"Scores: {scores}")

    return num_matches, homographies


def error_function(camera_pos, point_data):
    """输入相机3D坐标，输出err2（目标函数）"""
    # 调用find_homography计算当前位置的误差（需调整参数适配）
    _, err1, err2, _ = find_homography(
        pixels=np.array([r.pixel for r in point_data]),
        pos3ds=np.array([r.pos3d for r in point_data]),
        camera_location=camera_pos,
        ransacbound=RANSACBOUND,
    )
    return err1 * 10000 + err2 * 10000  # 调整权重以平衡err1和err2


def main(image_path: str, dem_path: str, feature_path: str, camera_locations_path: str):
    """
    主函数，处理图像和DEM数据，并生成CSV文件
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # 检查图像文件是否存在
    image_path = os.path.join("historical photos", image_path)
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    # 加载图像
    im = load_and_prepare_image(image_path)

    # 加载DEM数据
    dem_data = load_dem_data(dem_path)

    # 获取特征数据
    features = get_features(feature_path)

    # 读取点数据
    point_data = read_points_data(features, scale=1.0, dem_data=dem_data)

    # # 读取相机位置数据
    # camera_locations = read_camera_locations(camera_locations_path, dem_data)

    # num_matches12, homographies = find_homographies(point_data, camera_locations)

    # num_matches2 = num_matches12[:, 1]
    # num_matches2[num_matches2 == 0] = 1000000
    # min_idx = np.argmin(num_matches2)
    # print("Minimum average reprojection error:", np.min(num_matches2))
    # print("err1:", num_matches12[min_idx, 0])
    # print("err2:", num_matches12[min_idx, 1])
    # print(
    #     f"推测相机位置: {camera_locations[min_idx].pos3d}, point_id: {min_idx + 1}, grid_code: {camera_locations[min_idx].grid_code}"
    # )

    # position = geo_transformer.utm_to_wgs84(
    #     camera_locations[min_idx].pos3d[0], camera_locations[min_idx].pos3d[1]
    # )

    # print(f"推测相机位置: {position}")

    img_height, img_width, _ = im.shape  # 获取图像的宽度和高度
    plt.figure(figsize=(4, 2))
    plt.imshow(im)

    for rec in point_data:
        symbol = rec.symbol
        pixel = rec.pixel
        if pixel[0] != 0 or pixel[1] != 0:
            plt.text(pixel[0] + 7, pixel[1] - 4, symbol, color="red", fontsize=32)
            plt.plot(pixel[0], pixel[1], marker="s", markersize=8, color="red")

    # for i in features:
    #     if i.pixel_x == 0:
    #         continue
    #     pixel = reprojection(
    #         dem_data,
    #         i.longitude,
    #         i.latitude,
    #         camera_locations[min_idx].pos3d,
    #         homographies[min_idx][0],
    #     )
    #     plt.plot(pixel[0], pixel[1], marker="s", markersize=8, color="yellow")

    initial_pos = point_data[2].pos3d + 1

    # ---------------- 新增优化逻辑 ----------------

    # ---------------- 优化初始点生成 ----------------
    # 替换原随机采样为拉丁超立方采样
    from scipy.stats import qmc  # 新增导入

    # 设置10公里搜索范围（10000米）
    search_radius = 10000

    num_initial_points = 30  # 可根据计算资源调整

    # 定义搜索空间边界
    bounds = [
        (initial_pos[0] - search_radius, initial_pos[0] + search_radius),
        (initial_pos[1] - search_radius, initial_pos[1] + search_radius),
        (initial_pos[2] - search_radius / 10, initial_pos[2] + search_radius / 10),
    ]

    # 拉丁超立方采样生成初始点（包含原始点）
    sampler = qmc.LatinHypercube(d=3)
    sample = sampler.random(n=num_initial_points - 1)  # 生成n-1个随机点
    initial_points = [initial_pos]  # 第一个点保留原始位置

    # 将采样点映射到实际搜索空间
    l_bounds = [b[0] for b in bounds]
    u_bounds = [b[1] for b in bounds]
    scaled_samples = qmc.scale(sample, l_bounds, u_bounds)  # shape: (n-1, 3)
    for i in range(num_initial_points - 1):
        initial_points.append(np.array(scaled_samples[i]))

    # 多初始点优化搜索
    best_result = None
    best_error = np.inf
    bounds = [
        (initial_pos[0] - search_radius, initial_pos[0] + search_radius),
        (initial_pos[1] - search_radius, initial_pos[1] + search_radius),
        (
            (
                initial_pos[2] - search_radius / 10
                if initial_pos[2] - search_radius / 10 > 0
                else 0
            ),
            initial_pos[2] + search_radius / 10,
        ),
    ]

    best_result = None
    best_error = np.inf

    for idx, start_pos in enumerate(initial_points):
        print(f"\n===== 正在优化第 {idx + 1}/{num_initial_points} 个初始点 =====")
        print(f"初始点坐标: {start_pos}")

        # ---------------- 替换为全局+局部优化组合 ----------------
        from scipy.optimize import differential_evolution  # 新增导入

        # 第一阶段：全局优化（差分进化算法）
        print("===== 正在执行全局优化（差分进化） =====")
        global_result = differential_evolution(
            func=error_function,
            args=(point_data,),
            bounds=bounds,
            strategy="best1bin",  # 经典策略
            maxiter=200,  # 最大迭代次数
            popsize=20,  # 种群大小（影响搜索广度）
            tol=0.0001,  # 收敛阈值
            mutation=(0.5, 1),  # 变异参数
            recombination=0.7,  # 重组概率
            workers=-1,  # 使用所有可用CPU核心
            polish=False,  # 暂不启用局部细化（后续用局部优化器处理）
        )

        # 第二阶段：局部优化细化（使用全局优化结果作为初始点）
        print("\n===== 正在执行局部优化细化 =====")
        local_result = minimize(
            fun=error_function,
            args=(point_data,),
            x0=global_result.x,
            method="BFGS",  # 也可替换为L-BFGS-B等梯度优化器
            options={"disp": True, "maxiter": 3000},
        )

        # 更新最优结果
        if local_result.fun < best_error:
            best_error = local_result.fun
            best_result = local_result
            print(f"找到更优解！当前最小误差: {best_error}")
            print(f"当前最优位置: {best_result.x}")

    # 最终优化结果
    optimized_pos = best_result.x  # 优化后的相机位置
    M, _, _, _ = find_homography(
        pixels=np.array([r.pixel for r in point_data]),
        pos3ds=np.array([r.pos3d for r in point_data]),
        camera_location=optimized_pos,
        ransacbound=RANSACBOUND,
    )

    # print("原最优位置误差:", np.min(num_matches2))
    print("优化后位置误差:", best_error)
    print(f"优化后相机位置: {optimized_pos}")

    for i in features:
        pixel = reprojection_to_pixel(
            dem_data,
            i.longitude,
            i.latitude,
            optimized_pos,
            M,
        )
        plt.plot(pixel[0], pixel[1], marker="s", markersize=8, color="blue")

    position = geo_transformer.utm_to_wgs84(optimized_pos[0], optimized_pos[1])

    print(f"推测相机位置: {position}")

    plt.show()


if __name__ == "__main__":
    main(
        image_path="1910.jpg",
        dem_path="DEM1.tif",
        feature_path="feature_points_with_annotations1.csv",
        camera_locations_path="potential_camera_locations.csv",
    )
