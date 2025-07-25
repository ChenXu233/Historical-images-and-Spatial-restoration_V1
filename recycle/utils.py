import math
import cv2
import csv
import numpy as np

from scipy.interpolate import RegularGridInterpolator
from osgeo import gdal

from typing import List

##
from logger import logging
from geo_transformer import geo_transformer
from schema import Feature, DEMData, CameraLocation, PointData


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


def load_and_prepare_image(image_path):
    """
    加载并准备图像,将 OpenCV 加载的 BGR 格式图像转换为 Matplotlib 所需的 RGB 格式。
    """
    im = cv2.imread(image_path)
    im2 = np.copy(im)
    im[:, :, 0] = im2[:, :, 2]
    im[:, :, 1] = im2[:, :, 1]
    im[:, :, 2] = im2[:, :, 0]
    return im


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
            logging.error(f"转换 DEM 坐标 {lon},{lat} 到 UTM 时出错: {e}")
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
    logging.debug(f"DEM 范围: 经度 {dem_data.x_range}, 纬度 {dem_data.y_range}")
    logging.debug(
        f"DEM UTM 范围: 东距 {dem_data.utm_x_range}, 北距 {dem_data.utm_y_range}"
    )
    return dem_data


def get_features(feature_path: str) -> List[Feature]:
    """
    从 CSV 文件加载特征数据，并返回一个包含特征信息的列表。
    """
    features = []
    with open(feature_path, "r", encoding="GBK") as f:
        reader = csv.DictReader(f)
        for row in reader:
            feature = {
                "object_id": int(row["Objectid"]),
                "pixel_x": float(row["Pixel_x"]),
                "pixel_y": float(row["Pixel_y"]),
                "symbol": row["Symbol"],
                "name": row["Name"],
                "height": float(row["Height"]),
                "longitude": float(row["Longitude"]),
                "latitude": float(row["Latitude"]),
                "elevation": float(row["Elevation"]),
            }
            feature = Feature(**feature)  # 验证数据格式
            features.append(feature)
    return features


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


def read_camera_locations(
    camera_locations_path: str, dem_data: DEMData
) -> List[CameraLocation]:
    updated_rows = []
    recs = []
    with open(camera_locations_path, encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        fieldnames = reader.fieldnames
        updated_rows.append(fieldnames)  # 保留标题行
        line_count = 0
        for row in reader:
            line_count += 1
            try:
                grid_code = int(row["Grid_code"])  # 假设列名为 grid_code
                longitude = float(row["Longitude"])  # 假设列名为 longitude
                latitude = float(row["Latitude"])  # 假设列名为 latitude
                elevation = (
                    get_dem_elevation(
                        dem_data, (longitude, latitude), coord_type="wgs84"
                    )
                    + 1.5
                )
                row["Elevation"] = str(elevation)  # 更新Elevation列
                updated_rows.append(list(row.values()))  # 保存更新后的行

                logging.debug(
                    f"Processing row {line_count}: lat={latitude}, lon={longitude}"
                )
                easting, northing = geo_transformer.wgs84_to_utm(longitude, latitude)
                pos3d = np.array([float(easting), float(northing), float(elevation)])

                rec = CameraLocation(grid_code=grid_code, pos3d=pos3d)  # 验证数据格式

                recs.append(rec)
            except ValueError as e:
                logging.error(f"Error processing row {line_count}: {e}")
                continue

    # 将更新后的数据写回文件
    with open(camera_locations_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file, delimiter=",")
        writer.writerows(updated_rows)

    logging.debug(f"Processed {line_count} lines.")
    return recs


def read_points_data(
    features: List[Feature], scale: float, dem_data: DEMData
) -> List[PointData]:
    recs = []
    line_count = 0
    for feature in features:
        pixel = np.array([int(feature.pixel_x), int(feature.pixel_y)]) / scale
        longitude = float(feature.longitude)
        latitude = float(feature.latitude)
        elevation = get_dem_elevation(
            dem_data, (longitude, latitude), coord_type="wgs84"
        )
        # 跳过当前处理照片中像素坐标为0,0的点
        if int(feature.pixel_x) == 0 and int(feature.pixel_y) == 0:
            continue

        # 添加坐标转换
        try:
            logging.debug(
                f"Processing row {line_count}: lat={latitude}, lon={longitude}"
            )
            easting, northing = geo_transformer.wgs84_to_utm(
                longitude, latitude
            )  # 注意顺序
            pos3d = np.array([easting, northing, elevation])
            print(
                f"Processed Point - Symbol: {feature.symbol}, Name: {feature.name}, Pixel: {pixel}, Lon: {longitude}, Lat: {latitude}, Easting: {easting}, Northing: {northing}, Elevation: {elevation}"
            )
        except ValueError as e:
            logging.error(f"Error processing row {line_count}: {e}")
            continue

        rec = PointData(
            pixel=pixel, symbol=feature.symbol, name=feature.name, pos3d=pos3d
        )  # 验证数据格式
        recs.append(rec)

    logging.debug(f"Processed {line_count} lines.")
    return recs


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
