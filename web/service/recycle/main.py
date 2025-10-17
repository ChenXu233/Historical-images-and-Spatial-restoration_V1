import numpy as np
import cv2

from typing import List, Tuple


## 本身

from service.recycle.geo_transformer import geo_transformer
from service.recycle.schema import PointData


# 计算重投影误差
def compute_reprojection_error(pos3d, pixels, K, dist_coeffs, rvec, tvec):
    projected_points, _ = cv2.projectPoints(pos3d, rvec, tvec, K, dist_coeffs)
    projected_points = projected_points.squeeze()
    errors = np.linalg.norm(pixels - projected_points, axis=1)
    return errors


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

    print("\n最优解选择：")
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
