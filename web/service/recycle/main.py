import numpy as np
import cv2

from typing import List, Tuple, Dict, Any


## 本身

from service.recycle.geo_transformer import geo_transformer
from service.recycle.schema import PointData


# 计算重投影误差
def compute_reprojection_error(pos3d, pixels, K, dist_coeffs, rvec, tvec):
    projected_points, _ = cv2.projectPoints(pos3d, rvec, tvec, K, dist_coeffs)
    projected_points = projected_points.squeeze()
    errors = np.linalg.norm(pixels - projected_points, axis=1)
    return errors


def reprojection_point(
    pos3d: np.ndarray,
    K: np.ndarray,
    dist_coeffs: np.ndarray,
    rvec: np.ndarray,
    tvec: np.ndarray,
) -> List[Tuple[float, float]]:
    projected_points, _ = cv2.projectPoints(pos3d, rvec, tvec, K, dist_coeffs)
    projected_points = projected_points.squeeze()
    return [(p[0][0], p[0][1]) for p in projected_points]


# EPNP算法计算相机位置 - 多次计算并选择重投影误差最小的解
def EPNP_calculate(
    point_data: List[PointData],
) -> Tuple[
    Tuple[float, float, float], float, Tuple[int, int], float, Dict[str, Any]
]:  # 相机位置（经度，纬度，高程），焦距，传感器尺寸，重投影误差，相机参数
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

    # 相机参数 - 使用单个值而非列表
    focal_length = 180.0
    sensor_width, sensor_height = 102, 127

    # 初始化畸变系数为0
    dist_coeffs = np.zeros((4, 1), dtype=np.float64)

    print("开始EPNP计算")

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
        success, initial_rotation_vector, initial_translation_vector = cv2.solvePnP(
            pos3d, pixels, K, dist_coeffs, flags=cv2.SOLVEPNP_EPNP
        )

        if not success:
            raise RuntimeError("EPNP求解失败")

        # 优化旋转向量和平移向量
        optimized_rotation_vector, optimized_translation_vector = cv2.solvePnPRefineLM(
            pos3d,
            pixels,
            K,
            dist_coeffs,
            initial_rotation_vector,
            initial_translation_vector,
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

        # 准备参数
        best_params = {
            "focal_length": focal_length,
            "sensor_width": sensor_width,
            "sensor_height": sensor_height,
            "K": K,
            "R": R_matrix,
            "dist_coeffs": dist_coeffs,
            "optimized_rotation_vector": optimized_rotation_vector,
            "optimized_translation_vector": optimized_translation_vector,
        }

        # 将相机原点位置从UTM坐标系转换为WGS84坐标系
        lon, lat = geo_transformer.utm_to_wgs84(camera_origin[0], camera_origin[1])
        height = camera_origin[2]

        print("EPNP计算完成")
        print(f"焦距: {focal_length}mm")
        print(f"传感器尺寸: {sensor_width}x{sensor_height}mm")
        print(f"重投影误差: {mean_error_optimized:.2f} pixels")
        print(f"相机原点（WGS84）: ({lon}, {lat}, {height})")

        return (
            (lon, lat, float(height)),
            focal_length,
            (
                sensor_width,
                sensor_height,
            ),
            mean_error_optimized,
            best_params,
        )

    except Exception as e:
        raise RuntimeError(f"EPNP计算出错: {str(e)}")
