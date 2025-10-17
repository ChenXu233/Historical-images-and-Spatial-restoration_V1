import numpy as np
import cv2

from typing import List, Tuple
from scipy.optimize import minimize


## 本身

from service.recycle.geo_transformer import geo_transformer
from service.recycle.schema import PointData


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


# 计算重投影误差
def compute_reprojection_error(pos3d, pixels, K, dist_coeffs, rvec, tvec):
    projected_points, _ = cv2.projectPoints(pos3d, rvec, tvec, K, dist_coeffs)
    projected_points = projected_points.squeeze()
    errors = np.linalg.norm(pixels - projected_points, axis=1)
    return errors


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


# EPNP算法计算相机位置 - 多次计算并选择重投影误差最小的解
def EPNP_calculate(
    point_data: List[PointData],
) -> Tuple[
    Tuple[float, float, float], int, Tuple[int, int], float
]:  # 相机位置（经度，纬度，高程），焦距，传感器尺寸，重投影误差
    # 从point_data中提取3D点和2D像素点
    pos3d = np.array([rec.pos3d for rec in point_data], dtype=np.float64).reshape(-1, 3)
    pixels = np.array([rec.pixel for rec in point_data], dtype=np.float64).reshape(
        -1, 2
    )

    # 过滤掉像素坐标为0,0的点
    valid_indices = np.logical_or(pixels[:, 0] != 0, pixels[:, 1] != 0)
    pos3d = pos3d[valid_indices]
    pixels = pixels[valid_indices]

    if len(pos3d) < 4:
        raise ValueError("点数量不足，无法进行EPNP计算")

    # 定义图像尺寸
    image_width = np.max(pixels[:, 0]) if len(pixels) > 0 else 1920
    image_height = np.max(pixels[:, 1]) if len(pixels) > 0 else 1080

    # 可选的相机参数列表
    focal_lengths = [90, 100, 120, 150, 180, 210, 240, 300, 360]
    sensor_sizes = [(102, 127), (127, 178), (203, 254)]

    # 初始化最优结果变量
    best_mean_error = np.inf
    best_camera_origin = None
    best_params = None

    # 初始化畸变系数为0
    dist_coeffs = np.zeros((4, 1), dtype=np.float64)

    # 存储所有成功的计算结果
    all_results = []

    # 遍历所有焦距和传感器尺寸的组合
    total_combinations = len(focal_lengths) * len(sensor_sizes)
    print(f"开始EPNP多次计算，总共有 {total_combinations} 种参数组合\n")

    for focal_length in focal_lengths:
        for sensor_width, sensor_height in sensor_sizes:
            try:
                # 计算像素大小
                pixel_size_width = sensor_width / image_width
                pixel_size_height = sensor_height / image_height

                # 构建相机内参矩阵K
                fx = focal_length / pixel_size_width
                fy = focal_length / pixel_size_height

                K = np.array(
                    [[fx, 0, image_width / 2], [0, fy, image_height / 2], [0, 0, 1]],
                    dtype=np.float32,
                )

                # 使用EPNP算法进行相机姿态估计
                success, initial_rotation_vector, initial_translation_vector = (
                    cv2.solvePnP(pos3d, pixels, K, dist_coeffs, flags=cv2.SOLVEPNP_EPNP)
                )

                if not success:
                    print(
                        f"焦距 {focal_length}mm, 传感器尺寸 {sensor_width}x{sensor_height}mm: EPNP求解失败，跳过此组合"
                    )
                    continue

                # 优化旋转向量和平移向量
                optimized_rotation_vector, optimized_translation_vector = (
                    cv2.solvePnPRefineLM(
                        pos3d,
                        pixels,
                        K,
                        dist_coeffs,
                        initial_rotation_vector,
                        initial_translation_vector,
                    )
                )

                # 计算重投影误差
                errors_optimized = compute_reprojection_error(
                    pos3d,
                    pixels,
                    K,
                    dist_coeffs,
                    optimized_rotation_vector,
                    optimized_translation_vector,
                )
                mean_error_optimized = np.mean(errors_optimized)

                # 计算相机原点位置
                R_matrix, _ = cv2.Rodrigues(optimized_rotation_vector)
                camera_origin = -R_matrix.T @ optimized_translation_vector.flatten()

                # 记录结果
                all_results.append(
                    {
                        "mean_error": mean_error_optimized,
                        "camera_origin": camera_origin,
                        "focal_length": focal_length,
                        "sensor_width": sensor_width,
                        "sensor_height": sensor_height,
                        "K": K,
                    }
                )

                # 更新最优结果
                if mean_error_optimized < best_mean_error:
                    best_mean_error = mean_error_optimized
                    best_camera_origin = camera_origin
                    best_params = {
                        "focal_length": focal_length,
                        "sensor_width": sensor_width,
                        "sensor_height": sensor_height,
                        "K": K,
                    }

            except Exception as e:
                print(
                    f"焦距 {focal_length}mm, 传感器尺寸 {sensor_width}x{sensor_height}mm: 计算出错 - {str(e)}"
                )
                continue

    # 检查是否有成功的计算结果
    if not all_results:
        raise RuntimeError("所有EPNP计算组合均失败")

    # 按重投影误差排序结果
    all_results.sort(key=lambda x: x["mean_error"])

    # 输出前5个最优结果
    print(f"\nEPNP计算完成，共成功 {len(all_results)} 种组合")
    print("\n前5个最优结果（按重投影误差排序）：")

    for i, result in enumerate(all_results[:5]):
        lon, lat = geo_transformer.utm_to_wgs84(
            result["camera_origin"][0], result["camera_origin"][1]
        )
        print(f"\n排名 {i + 1}：")
        print(f"焦距: {result['focal_length']}mm")
        print(f"传感器尺寸: {result['sensor_width']}x{result['sensor_height']}mm")
        print(f"重投影误差: {result['mean_error']:.2f} pixels")
        print(f"相机原点（UTM）: {result['camera_origin']}")
        print(f"相机原点（WGS84）: ({lon}, {lat}, {result['camera_origin'][2]})")

    # 使用最优结果
    best_result = all_results[0]
    camera_origin = best_result["camera_origin"]

    # 将相机原点位置从UTM坐标系转换为WGS84坐标系
    lon, lat = geo_transformer.utm_to_wgs84(camera_origin[0], camera_origin[1])
    height = camera_origin[2]

    print(f"\n最优解选择：")
    print(f"焦距: {best_result['focal_length']}mm")
    print(f"传感器尺寸: {best_result['sensor_width']}x{best_result['sensor_height']}mm")
    print(f"重投影误差: {best_result['mean_error']:.2f} pixels")
    print(f"相机原点（WGS84）: ({lon}, {lat}, {height})")

    return (
        (lon, lat, float(height)),
        best_result["focal_length"],
        (
            best_result["sensor_width"],
            best_result["sensor_height"],
        ),
        best_result["mean_error"],
    )


def calculate(
    point_data: List[PointData],
) -> Tuple[float, float, float]:
    initial_pos = point_data[2].pos3d + 1

    # ---------------- 新增优化逻辑 ----------------

    # 替换原随机采样为拉丁超立方采样
    from scipy.stats import qmc  # 新增导入

    # 设置10公里搜索范围（10000米）
    search_radius = 10000

    num_initial_points = 5  # 可根据计算资源调整

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
            maxiter=2000,  # 最大迭代次数
            popsize=20,  # 种群大小（影响搜索广度）
            tol=0.0001,  # 收敛阈值
            mutation=(0.5, 1),  # 变异参数
            recombination=0.7,  # 重组概率
            workers=1,  # 使用所有可用CPU核心
            polish=False,  # 暂不启用局部细化（后续用局部优化器处理）
            updating="deferred",  # 延迟更新策略
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
    if best_result is not None and hasattr(best_result, "x"):
        optimized_pos = best_result.x  # 优化后的相机位置
    else:
        raise RuntimeError(
            "优化未找到有效结果，best_result为None。请检查优化过程或参数设置。"
        )

    M, _, _, _ = find_homography(
        pixels=np.array([r.pixel for r in point_data]),
        pos3ds=np.array([r.pos3d for r in point_data]),
        camera_location=optimized_pos,
        ransacbound=RANSACBOUND,
    )
    print("优化后位置误差:", best_error)
    print(f"优化后相机位置: {optimized_pos}")

    position = geo_transformer.utm_to_wgs84(optimized_pos[0], optimized_pos[1])
    height = optimized_pos[2]

    return (position[0], position[1], height)
