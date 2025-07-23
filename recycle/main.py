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
)
from schema import CameraLocation, PointData
from geo_transformer import geo_transformer

# 设置字体
plt.rcParams["font.sans-serif"] = ["SimHei"]  # 使用黑体
plt.rcParams["axes.unicode_minus"] = False  # 解决负号 '-' 显示
# 验证字体是否存在
font_path = font_manager.findSystemFonts(fontpaths=None, fontext="ttf")


RANSACBOUND = 70.0


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
    # print(f"Homography Matrix M: {M}")
    # print(f"Mask: {mask}")
    err1 = 0
    err2 = 0
    for i in range(pos2[good == 1].shape[0]):
        p1 = np.array(pixels)[good == 1][i, :]
        pp = np.array([pos2[good == 1][i, 0], pos2[good == 1][i, 1], 1.0])
        pp2 = np.matmul(np.linalg.inv(M), pp)
        pp2 = pp2 / pp2[2]
        P1 = np.array([p1[0], p1[1], 1.0])
        PP2 = np.matmul(M, P1)
        PP2 = PP2 / PP2[2]
        P2 = pos2[good == 1][i, :]
        logging.debug(
            f"Feature {i}: mask={mask[i]}, p1={p1}, pp2={pp2[0:2]}, distance={np.linalg.norm(p1 - pp2[0:2])}"
        )
        if mask[i] == 1:
            err1 += np.linalg.norm(p1 - pp2[0:2])
            err2 += np.linalg.norm(P2 - PP2[0:2])

    err2 += np.sum(1 - mask) * ransacbound
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

    # 读取相机位置数据
    camera_locations = read_camera_locations(camera_locations_path, dem_data)

    num_matches12, homographies = find_homographies(point_data, camera_locations)

    num_matches2 = num_matches12[:, 1]
    num_matches2[num_matches2 == 0] = 1000000
    min_idx = np.argmin(num_matches2)
    print("Minimum average reprojection error:", np.min(num_matches2))
    print("err1:", num_matches12[min_idx, 0])
    print("err2:", num_matches12[min_idx, 1])
    print(
        f"推测相机位置: {camera_locations[min_idx].pos3d}, point_id: {min_idx + 1}, grid_code: {camera_locations[min_idx].grid_code}"
    )

    position = geo_transformer.utm_to_wgs84(
        camera_locations[min_idx].pos3d[0], camera_locations[min_idx].pos3d[1]
    )

    print(f"推测相机位置: {position}")

    img_height, img_width, _ = im.shape  # 获取图像的宽度和高度
    plt.figure(figsize=(40, 20))
    plt.imshow(im)

    for rec in point_data:
        symbol = rec.symbol
        pixel = rec.pixel
        if pixel[0] != 0 or pixel[1] != 0:
            plt.text(pixel[0] + 7, pixel[1] - 4, symbol, color="red", fontsize=32)
            plt.plot(pixel[0], pixel[1], marker="s", markersize=8, color="red")

    plt.show()

    initial_pos = camera_locations[3000].pos3d  # 初始最优位置

    # ---------------- 新增优化逻辑 ----------------
    def error_function(camera_pos):
        """输入相机3D坐标，输出err2（目标函数）"""
        # 调用find_homography计算当前位置的误差（需调整参数适配）
        _, err1, err2, _ = find_homography(
            pixels=np.array([r.pixel for r in point_data]),
            pos3ds=np.array([r.pos3d for r in point_data]),
            camera_location=camera_pos,
            ransacbound=RANSACBOUND,
        )
        return err1 + err2

    # 使用L-BFGS算法优化（可根据需求替换为其他优化器）
    result = minimize(
        fun=error_function,
        x0=initial_pos,  # 初始值为原最优位置
        method="Powell",  # 适用于连续可导问题，无导数可用Nelder-Mead
        bounds=None,  # 可选：添加相机位置的物理约束（如z≥DEM高度）
        options={"disp": True, "maxiter": 9000, "miniter": 3000},
    )
    optimized_pos = result.x  # 优化后的相机位置
    print("原最优位置误差:", np.min(num_matches2))
    print("优化后位置误差:", result.fun)
    print(f"优化后相机位置: {optimized_pos}")

    position = geo_transformer.utm_to_wgs84(optimized_pos[0], optimized_pos[1])

    print(f"推测相机位置: {position}")


if __name__ == "__main__":
    main(
        image_path="1898.jpg",
        dem_path="dem_dx.tif",
        feature_path="feature_points_with_annotations.csv",
        camera_locations_path="potential_camera_locations.csv",
    )
