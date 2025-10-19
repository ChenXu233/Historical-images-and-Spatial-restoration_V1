import math
import numpy as np

from scipy.interpolate import RegularGridInterpolator
from osgeo import gdal

from sqlalchemy.orm import Session

from typing import List

##
from service.recycle.geo_transformer import geo_transformer
from service.recycle.schema import Feature, DEMData, PointData

from model.feature import Feature as ORMFeature


def calc_bearing(x1: float, y1: float, x2: float, y2: float) -> float:
    """
    计算从点1到点2的方位角
    """
    if x1 == 0 or x2 == 0 or y1 == 0 or y2 == 0:
        degrees_final = 0
    else:
        deltaX = x2 - x1
        deltaY = y2 - y1

        degrees_temp = math.atan2(deltaX, deltaY) / math.pi * 180

        if degrees_temp < 0:
            degrees_final = 360 + degrees_temp
        else:
            degrees_final = degrees_temp

        if degrees_final < 180:
            degrees_final = 180 - degrees_final
        else:
            degrees_final = 360 + 180 - degrees_final

    return degrees_final


# 加载DEM数据
def load_dem_data(dem_file_path: str) -> DEMData:
    """
    加载 DEM 文件，并返回一个包含 DEM 数据和地理变换信息的字典。
    """
    dem_dataset = gdal.Open(dem_file_path)
    if dem_dataset is None:
        raise RuntimeError(f"无法加载 DEM 文件: {dem_file_path}")

    dem_array = dem_dataset.ReadAsArray()
    gt = dem_dataset.GetGeoTransform()
    dem_x = np.arange(dem_array.shape[1]) * gt[1] + gt[0]
    dem_y = np.arange(dem_array.shape[0]) * gt[5] + gt[3]

    # 新增部分：计算 DEM 四角点在 UTM 下的坐标范围
    corners = [
        (dem_x.min(), dem_y.min()),
        (dem_x.min(), dem_y.max()),
        (dem_x.max(), dem_y.min()),
        (dem_x.max(), dem_y.max()),
    ]
    utm_x_list = []
    utm_y_list = []
    for lon, lat in corners:
        try:
            easting, northing = geo_transformer.wgs84_to_utm(lon, lat)
            utm_x_list.append(easting)
            utm_y_list.append(northing)
        except Exception as e:
            print(f"转换 DEM 坐标 {lon},{lat} 到 UTM 时出错: {e}")

    dem_utm_x_range = (min(utm_x_list), max(utm_x_list)) if utm_x_list else (None, None)
    dem_utm_y_range = (min(utm_y_list), max(utm_y_list)) if utm_y_list else (None, None)

    dem_interpolator = RegularGridInterpolator((dem_y, dem_x), dem_array)

    dem_data = DEMData(
        interpolator=dem_interpolator,
        x_range=(dem_x.min(), dem_x.max()),
        y_range=(dem_y.min(), dem_y.max()),
        utm_x_range=dem_utm_x_range,
        utm_y_range=dem_utm_y_range,
        data=dem_array,
    )  # 验证数据格式
    print(f"DEM 范围: 经度 {dem_data.x_range}, 纬度 {dem_data.y_range}")
    print(f"DEM UTM 范围: 东距 {dem_data.utm_x_range}, 北距 {dem_data.utm_y_range}")
    return dem_data


def load_features_from_orm(img_id: int, db: Session) -> List[Feature]:
    """
    从 ORM 中加载特征数据，并返回一个包含特征信息的列表。
    """

    features = db.query(ORMFeature).filter(ORMFeature.image_id == img_id).all()

    if not features:
        raise ValueError(f"没有找到与图片 ID {img_id} 相关的特征点。")

    r_feature = []
    for feature in features:
        r_feature.append(
            Feature(
                object_id=feature.id,
                pixel_x=feature.pixel_x,
                pixel_y=feature.pixel_y,
                symbol=feature.building_point.name,
                name=feature.building_point.name,
                height=4,
                longitude=feature.building_point.longitude,
                latitude=feature.building_point.latitude,
                elevation=None,
            )
        )

    return r_feature


def load_points_data_from_orm(
    features: List[Feature], dem_data: DEMData
) -> List[PointData]:
    """
    从 ORM 中加载点数据，并返回一个包含点信息的列表。
    """
    recs = []
    for feature in features:
        pixel = np.array([int(feature.pixel_x), int(feature.pixel_y)])
        longitude = float(feature.longitude)
        latitude = float(feature.latitude)
        elevation = get_dem_elevation(
            dem_data, (longitude, latitude), coord_type="wgs84"
        )
        # 跳过当前处理照片中像素坐标为0,0的点
        if int(feature.pixel_x) == 0 and int(feature.pixel_y) == 0:
            continue

        easting, northing = geo_transformer.wgs84_to_utm(longitude, latitude)
        pos3d = np.array([easting, northing, elevation])
        rec = PointData(
            pixel=pixel, symbol=feature.symbol, name=feature.name, pos3d=pos3d
        )  # 验证数据格式
        recs.append(rec)

    return recs


def get_dem_elevation(dem_data: DEMData, coord, coord_type="utm"):
    """
    根据坐标类型获取 DEM 高程。
    :param dem_data: DEM 数据
    :param coord: 坐标 (easting, northing) 或 (lon, lat)
    :param coord_type: 坐标类型，'utm' 或 'wgs84'
    :return: 海拔高度
    """
    if coord_type == "utm":
        lon, lat = geo_transformer.utm_to_wgs84(coord[0], coord[1])
    elif coord_type == "wgs84":
        lon, lat = coord
    else:
        raise ValueError("Invalid coord_type. Must be 'utm' or 'wgs84'.")

    # 插值器构造时使用的坐标顺序为 (lat, lon)
    dem_elev = dem_data.interpolator((lat, lon))
    return dem_elev


def reprojection_to_pixel(
    dem_data: DEMData,
    longitude,
    latitude,
    camera_location,
    M,
):
    elevation = get_dem_elevation(dem_data, (longitude, latitude), coord_type="wgs84")
    easting, northing = geo_transformer.wgs84_to_utm(longitude, latitude)
    camera_easting, camera_northing, camera_elevation = camera_location
    relative_easting = easting - camera_easting
    relative_northing = northing - camera_northing
    relative_elevation = elevation - camera_elevation
    p = np.array([relative_elevation, relative_northing, relative_easting])
    p = p / p[2]
    pp2 = np.matmul(np.linalg.inv(M), p)
    pp2 = pp2 / pp2[2]
    return pp2


def pixel_to_ray(pixel_x, pixel_y, K, R, ray_origin):
    """
    将像素坐标 (pixel_x, pixel_y) 转换为射线方向.

    参数:
      pixel_x, pixel_y -- 像素坐标
      K -- 根据物理参数换算到像素单位的内参矩阵
      R -- 旋转矩阵，要求转换后可将相机坐标转换至UTM坐标系
      ray_origin -- 相机在UTM坐标系下的位置

    返回:
      (ray_origin, ray_direction) 其中 ray_direction 为UTM坐标系下的单位向量
    """
    # 构建齐次像素向量
    pixel_homogeneous = np.array([pixel_x, pixel_y, 1.0], dtype=np.float64)
    print("【DEBUG】像素齐次向量:", pixel_homogeneous)

    # 计算相机坐标下的射线方向（未归一化）
    camera_ray = np.linalg.inv(K) @ pixel_homogeneous
    camera_ray /= np.linalg.norm(camera_ray)
    print("【DEBUG】相机坐标下的射线方向:", camera_ray)

    # 将相机坐标下的射线方向转换到UTM坐标系
    # 如果你的流程中 R 已为从物体到相机坐标的转换，应使用 R.T 进行转换
    utm_ray = R.T @ camera_ray
    utm_ray /= np.linalg.norm(utm_ray)

    return ray_origin, utm_ray


def compute_optimization_factors(control_points, K, R, ray_origin):
    optimization_factors = []
    for cp in control_points:
        true_geo = np.array(cp["pos3d"], dtype=np.float64)
        ideal_direction = true_geo - np.array(ray_origin, dtype=np.float64)
        print(f"【DEBUG】归一化前的理想UTM射线方向: {ideal_direction}")
        norm_ideal = np.linalg.norm(ideal_direction)
        if norm_ideal == 0:
            continue
        ideal_direction /= norm_ideal
        _, computed_ray = pixel_to_ray(cp["pixel"][0], cp["pixel"][1], K, R, ray_origin)
        computed_ray /= np.linalg.norm(computed_ray)
        optimization_factor_x = ideal_direction[0] / computed_ray[0]
        optimization_factor_y = ideal_direction[1] / computed_ray[1]
        optimization_factor_z = ideal_direction[2] / computed_ray[2]

        optimization_factors.append(
            (optimization_factor_x, optimization_factor_y, optimization_factor_z)
        )
        print(f"【DEBUG】控制点 {cp['symbol']} 的理想UTM射线方向: {ideal_direction}")
        print(f"【DEBUG】像素射线方向: {computed_ray}")
        print(
            f"【DEBUG】控制点 {cp['symbol']} 的优化因子: ({optimization_factor_x}, {optimization_factor_y}, {optimization_factor_z})"
        )
    return optimization_factors


def calculate_weights(input_pixel, control_points, max_weight=1, knn_weight=30):
    weights = []
    input_pixel = np.array(
        input_pixel, dtype=np.float64
    )  # 确保 input_pixel 是浮点数类型
    distances = []
    for cp in control_points:
        pixel = np.array(cp["pixel"], dtype=np.float64)  # 确保 pixel 是浮点数类型
        distance = np.linalg.norm(input_pixel - pixel)
        distances.append(distance)
        weight = min(
            1.0 / distance if distance != 0 else 1.0, max_weight
        )  # 限制权重最大值
        weights.append(weight)

    # 找到距离最近的控制点并提升其权重
    min_distance_index = np.argmin(distances)
    weights[min_distance_index] *= knn_weight

    # 输出每个控制点的距离和权重信息
    for i, cp in enumerate(control_points):
        print(
            f"【DEBUG】控制点 {cp['symbol']} 的距离: {distances[i]}, 权重: {weights[i]}"
        )

    return np.array(weights)


def weighted_average_optimization_factors(factors, weights):
    # 将权重归一化
    normalized_weights = weights / np.sum(weights)
    print(f"【DEBUG】归一化权重: {normalized_weights}")
    weighted_factors = np.average(factors, axis=0, weights=normalized_weights)
    return weighted_factors


def ray_intersect_dem(
    ray_origin, ray_direction, dem_data, max_search_dist=5000, step=1
):
    current_pos = np.array(ray_origin, dtype=np.float64)
    step_count = 0  # 初始化步进计数器
    for _ in range(int(max_search_dist / step)):
        print(f"【DEBUG】当前UTM坐标: {current_pos}, 当前射线方向: {ray_direction}")
        current_easting = current_pos[0]
        current_northing = current_pos[1]
        lon, lat = geo_transformer.utm_to_wgs84(current_easting, current_northing)

        # 添加坐标边界检查，避免在DEM数据范围外进行插值
        if not (
            dem_data.x_range[0] <= lon <= dem_data.x_range[1]
            and dem_data.y_range[0] <= lat <= dem_data.y_range[1]
        ):
            print(f"【警告】坐标超出DEM范围: 经度={lon}, 纬度={lat}")
            return None, step_count

        try:
            # 修复：使用点号访问属性而不是字典下标
            dem_elev = dem_data.interpolator((lat, lon))
        except Exception as e:
            print(f"【错误】插值时出错: {e}")
            return None, step_count
        print(f"【DEBUG】DEM海拔: {dem_elev}, 当前高度: {current_pos[2]}")

        if step_count >= 50 and current_pos[2] <= dem_elev + 0.5:
            return np.array(
                [current_easting, current_northing, current_pos[2]]
            ), step_count

        current_pos[0] += step * ray_direction[0]
        current_pos[1] += step * ray_direction[1]
        current_pos[2] += step * ray_direction[2]
        step_count += 1  # 增加步进计数器

    return None, step_count


def pixel_to_geo(pixel_coord, K, R, ray_origin, dem_data, control_points):
    optimization_factors = compute_optimization_factors(
        control_points, K, R, ray_origin
    )
    # 计算权重
    weights = calculate_weights(pixel_coord, control_points)
    # 计算加权优化因子
    weighted_optimization_factors = weighted_average_optimization_factors(
        optimization_factors, weights
    )
    print(f"【DEBUG】加权优化因子: {weighted_optimization_factors}")
    # 计算射线方向
    ray_origin, ray_direction = pixel_to_ray(
        pixel_coord[0], pixel_coord[1], K, R, ray_origin
    )
    print(f"【DEBUG】初始射线方向: {ray_direction}")
    # 应用优化因子校正射线方向的Z分量
    optimized_ray_direction = np.array(
        [
            ray_direction[0] * weighted_optimization_factors[0],
            ray_direction[1] * weighted_optimization_factors[1],
            ray_direction[2] * weighted_optimization_factors[2],
        ]
    )
    print(f"【DEBUG】优化射线方向: {optimized_ray_direction}")
    # 归一化校正后的射线方向
    final_ray_direction = optimized_ray_direction / np.linalg.norm(
        optimized_ray_direction
    )
    print(f"【DEBUG】最终射线方向: {final_ray_direction}")
    # 计算射线与DEM的交点
    geo_coord, total_steps = ray_intersect_dem(
        ray_origin, final_ray_direction, dem_data
    )
    print(f"【DEBUG】地理坐标: {geo_coord}")
    print(f"【DEBUG】射线步进总步数: {total_steps}")

    return geo_coord, total_steps
