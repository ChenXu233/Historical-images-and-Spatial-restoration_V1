# -*- coding: utf-8 -*-

import numpy as np
import cv2
import matplotlib.pyplot as plt
from matplotlib import font_manager
import csv
import math
import logging
from pyproj import Transformer
from scipy.interpolate import RegularGridInterpolator
from osgeo import gdal
import os

# 设置字体
plt.rcParams["font.sans-serif"] = ["SimHei"]  # 使用黑体
plt.rcParams["axes.unicode_minus"] = False  # 解决负号 '-' 显示为方块的问题

# 验证字体是否存在
font_path = font_manager.findSystemFonts(fontpaths=None, fontext="ttf")

# 设置日志记录
logging.basicConfig(
    level=logging.DEBUG,
    filename="debug.log",
    filemode="w",
    format="%(asctime)s - %(levelname)s - %(message)s",
)


# 坐标系统统一化
class GeoCoordTransformer:
    def __init__(self):
        self.to_utm = Transformer.from_crs("epsg:4326", "epsg:32650", always_xy=True)
        self.to_wgs84 = Transformer.from_crs("epsg:32650", "epsg:4326", always_xy=True)

    def wgs84_to_utm(self, lon, lat):  # 注意顺序：先经度，后纬度
        try:
            easting, northing = self.to_utm.transform(lon, lat)
            if np.isinf(easting) or np.isinf(northing):
                raise ValueError("Invalid UTM coordinates")
            return easting, northing
        except Exception as e:
            raise

    def utm_to_wgs84(self, easting, northing):
        try:
            lon, lat = self.to_wgs84.transform(
                easting, northing
            )  # 注意顺序：先经度，后纬度
            if np.isinf(lat) or np.isinf(lon):
                raise ValueError("Invalid WGS84 coordinates")
            return lon, lat
        except Exception as e:
            raise


geo_transformer = GeoCoordTransformer()


# **********
"""
计算特征之间的真实距离和像素距离
"""


# Calculate true and pixel distances between features
# **********
def correlate_features(features, depth_val):
    result = [
        "id",
        "sym_s",
        "x_s",
        "y_s",
        "pixel_x_s",
        "pixel_y_s",
        "calc_pixel_x_s",
        "calc_pixel_y_s",
        "sym_t",
        "x_t",
        "y_t",
        "pixel_x_t",
        "pixel_y_t",
        "calc_pixel_x_t",
        "calc_pixel_y_t",
        "dis_m_x",
        "dis_m_y",
        "dis_m",
        "dis_pix_x",
        "dis_pix_y",
        "dis_pix",
        "dis_c_pix_x",
        "dis_c_pix_y",
        "dis_c_pix",
        "bear_pix",
        "dis_depth_pix",
        "bear_c_pix",
        "dis_depth_c_pix",
    ]

    results = []
    results.append(result)
    count = 1
    i = 0
    j = 0
    features.remove(features[0])  # remove the headers
    features.sort()  # sort alphabethically
    for f1 in features:
        i = j
        while i < len(features):
            if f1[1] != features[i][1]:
                dis_m_x = int(features[i][3]) - int(f1[3])
                dis_m_y = int(features[i][4]) - int(f1[4])
                dis_m = math.sqrt(math.pow(dis_m_x, 2) + math.pow(dis_m_y, 2))

                if f1[5] != 0 and features[i][5] != 0:
                    dis_pix_x = int(features[i][5]) - int(f1[5])
                    dis_pix_y = int(features[i][6]) - int(f1[6])
                else:
                    dis_pix_x = 0
                    dis_pix_y = 0
                dis_pix = math.sqrt(math.pow(dis_pix_x, 2) + math.pow(dis_pix_y, 2))

                if features[i][7] != 0 and f1[7] != 0:
                    dis_c_pix_x = int(features[i][7]) - int(f1[7])
                    dis_c_pix_y = int(features[i][8]) - int(f1[8])
                else:
                    dis_c_pix_x = 0
                    dis_c_pix_y = 0
                dis_c_pix = math.sqrt(
                    math.pow(dis_c_pix_x, 2) + math.pow(dis_c_pix_y, 2)
                )

                bear_pix = calc_bearing(f1[5], f1[6], features[i][5], features[i][6])
                if bear_pix != 0 and bear_pix <= 180:
                    dis_depth_pix = (abs(bear_pix - 90) / 90 + depth_val) * dis_pix
                elif bear_pix != 0 and bear_pix > 180:
                    dis_depth_pix = (abs(bear_pix - 270) / 90 + depth_val) * dis_pix
                else:
                    dis_depth_pix = 0

                bear_c_pix = calc_bearing(f1[7], f1[8], features[i][7], features[i][8])
                if bear_c_pix != 0 and bear_c_pix <= 180:
                    dis_depth_c_pix = (
                        abs(bear_c_pix - 90) / 90 + depth_val
                    ) * dis_c_pix
                elif bear_c_pix != 0 and bear_c_pix > 180:
                    dis_depth_c_pix = (
                        abs(bear_c_pix - 270) / 90 + depth_val
                    ) * dis_c_pix
                else:
                    dis_depth_c_pix = 0

                result = [
                    str(count),
                    f1[1],
                    f1[3],
                    f1[4],
                    f1[5],
                    f1[6],
                    f1[7],
                    f1[8],
                    features[i][1],
                    features[i][3],
                    features[i][4],
                    features[i][5],
                    features[i][6],
                    features[i][7],
                    features[i][8],
                    dis_m_x,
                    dis_m_y,
                    dis_m,
                    dis_pix_x,
                    dis_pix_y,
                    dis_pix,
                    dis_c_pix_x,
                    dis_c_pix_y,
                    dis_c_pix,
                    bear_pix,
                    dis_depth_pix,
                    bear_c_pix,
                    dis_depth_c_pix,
                ]

                results.append(result)
                count += 1
            i += 1
        j += 1
    return results


# **********
# Calculation of the bearing from point 1 to point 2
# **********
def calc_bearing(x1, y1, x2, y2):
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


# **********
# Find homographies function
# **********
def find_homographies(
    recs,
    camera_locations,
    im,
    show,
    ransacbound,
    output,
    pixel_x,
    pixel_y,
    dem_data,
):
    pixels = []
    pos3ds = []
    symbols = []
    for r in recs:
        pixels.append(r["pixel"])
        pos3ds.append(r["pos3d"])
        symbols.append(r["symbol"])
    pixels = np.array(pixels)
    pos3ds = np.array(pos3ds)
    symbols = np.array(symbols)
    loc3ds = []
    grids = []
    for cl in camera_locations:
        grids.append(cl["grid_code"])
        loc3ds.append(cl["pos3d"])
    grids = np.array(grids)
    loc3ds = np.array(loc3ds)
    num_matches = np.zeros((loc3ds.shape[0], 2))
    scores = []
    homographies = []
    for i in range(0, grids.shape[0], 1):
        grid_code_min = 0
        if grids[i] >= grid_code_min:
            if show:
                print(i, grids[i], loc3ds[i])
            M, err1, err2, mask = find_homography(
                recs,
                pixels,
                pos3ds,
                symbols,
                loc3ds[i],
                im,
                show,
                ransacbound,
                output,
                pixel_x,
                pixel_y,
                dem_data,
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

    if show is False:
        outputCsv = output.replace(".jpg", "_location.csv")
        csvFile = open(outputCsv, "w", newline="", encoding="utf-8")
        csvWriter = csv.writer(csvFile)
        csvWriter.writerow(
            ["location_id", "min_score", "max_score", "grid_code", "Z", "X", "Y"]
        )
        for s in scores:
            csvWriter.writerow(s)

    return num_matches, homographies


# **********
# Find homography function
# **********
def find_homography(
    recs,
    pixels,
    pos3ds,
    symbols,
    camera_location,
    im,
    show,
    ransacbound,
    outputfile,
    pixel_x,
    pixel_y,
    dem_data,
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

    M = np.linalg.inv(M)
    logging.debug(f"Homography Matrix M: {M}")
    logging.debug(f"Mask: {mask}")
    if show:
        print("M", M, np.sum(mask))
    if show:
        plt.figure(figsize=(40, 20))
        plt.imshow(im)
        for rec in recs:
            symbol = rec["symbol"]
            pixel = rec["pixel"]
            if pixel[0] != 0 or pixel[1] != 0:
                plt.text(
                    pixel[0] + 10,
                    pixel[1] - 5,
                    symbol,
                    color="red",
                    fontsize=32,
                    weight="bold",
                )
    err1 = 0
    err2 = 0
    feature = [
        "id",
        "symbol",
        "name",
        "x",
        "y",
        "pixel_x",
        "pixel_y",
        "calc_pixel_x",
        "calc_pixel_y",
    ]
    features = []
    features.append(feature)
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
        if show and good[i]:
            print(i)
            print(mask[i] == 1, p1, pp2[0:2], np.linalg.norm(p1 - pp2[0:2]))
            print(mask[i] == 1, P2, PP2[0:2], np.linalg.norm(P2 - PP2[0:2]))
        if mask[i] == 1:
            err1 += np.linalg.norm(p1 - pp2[0:2])
            err2 += np.linalg.norm(P2 - PP2[0:2])
        if show:
            color = "green" if mask[i] == 1 else "purple"
            plt.plot(
                [p1[0], pp2[0]], [p1[1], pp2[1]], color="red", linewidth=4, zorder=3
            )
            plt.plot(p1[0], p1[1], marker="X", color=color, markersize=18, zorder=2)
            plt.plot(pp2[0], pp2[1], marker="o", color=color, markersize=18, zorder=2)
            sym = ""
            name = ""
            for r in recs:
                px = r["pixel"].tolist()
                if px[0] == p1[0] and px[1] == p1[1]:
                    sym = r["symbol"]
                    name = r["name"]
                    x = r["pos3d"][0]
                    y = r["pos3d"][1]
                    break
            feature = [i, sym, name, x, y, p1[0], p1[1], pp2[0], pp2[1]]
            features.append(feature)

    if show:
        outputCsv = outputfile.replace(".jpg", "_accuracies.csv")
        with open(outputCsv, "w", newline="", encoding="utf-8-sig") as csvFile:
            csvWriter = csv.writer(csvFile)
            for f in features:
                csvWriter.writerow(f)

        # 发送特征到相关函数
        results = correlate_features(features, 1)
        outputCsv = outputfile.replace(".jpg", "_correlations.csv")
        with open(outputCsv, "w", newline="", encoding="utf-8") as csvFile:
            csvWriter = csv.writer(csvFile)
            for r in results:
                csvWriter.writerow(r)

        print("Output image file: ", outputfile)
        plt.savefig(
            outputfile.replace(".jpg", "_1_output.png"), dpi=300, bbox_inches="tight"
        )
        plt.subplots_adjust(left=0.05, right=0.98, top=0.98, bottom=0.05)  # 移除边距
        plt.tight_layout(pad=1.0)  # 冗余保险
        plt.show()

    err2 += np.sum(1 - mask) * ransacbound
    if show:
        print("err", err1, err1 / np.sum(mask), err2, err2 / np.sum(mask))
    return M, err1, err2, mask


# 加载DEM数据
def load_dem_data(dem_file):
    dem_dataset = gdal.Open(dem_file)
    if dem_dataset is None:
        raise RuntimeError(f"无法加载 DEM 文件: {dem_file}")

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
    dem_data = {
        "interpolator": dem_interpolator,
        "x_range": (dem_x.min(), dem_x.max()),
        "y_range": (dem_y.min(), dem_y.max()),
        "utm_x_range": dem_utm_x_range,
        "utm_y_range": dem_utm_y_range,
        "data": dem_array,
    }
    logging.debug(f"DEM 范围: 经度 {dem_data['x_range']}, 纬度 {dem_data['y_range']}")
    logging.debug(
        f"DEM UTM 范围: 东距 {dem_data['utm_x_range']}, 北距 {dem_data['utm_y_range']}"
    )
    return dem_data


# 获取DEM数据中的海拔值
def get_dem_elevation(dem_data, coord, coord_type="utm"):
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
    dem_elev = dem_data["interpolator"]((lat, lon))
    return dem_elev


# **********
# read data from the features file
# **********
def read_points_data(filename, pixel_x, pixel_y, scale, dem_data):
    updated_rows = []
    with open(filename, encoding="utf-8") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=",")
        line_count = 0
        recs = []
        pixels = []
        for row in csv_reader:
            if line_count == 0:
                updated_rows.append(row)  # 保留标题行
                line_count += 1
                names = row
                indx = names.index(pixel_x)
                indy = names.index(pixel_y)
            else:
                symbol = row[1]
                name = row[2]
                pixel = np.array([int(row[indx]), int(row[indy])]) / scale
                longitude = float(row[4])
                latitude = float(row[5])
                elevation = get_dem_elevation(
                    dem_data, (longitude, latitude), coord_type="wgs84"
                )
                row[6] = str(elevation)  # 更新Elevation列
                updated_rows.append(row)  # 保存更新后的行
                # 跳过当前处理照片中像素坐标为0,0的点
                if int(row[indx]) == 0 and int(row[indy]) == 0:
                    continue
                pixels.append(pixel)
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
                        f"Processed Point - Symbol: {symbol}, Name: {name}, Pixel: {pixel}, Lon: {longitude}, Lat: {latitude}, Easting: {easting}, Northing: {northing}, Elevation: {elevation}"
                    )
                except ValueError as e:
                    logging.error(f"Error processing row {line_count}: {e}")
                    continue

                rec = {"symbol": symbol, "pixel": pixel, "pos3d": pos3d, "name": name}
                recs.append(rec)
                line_count += 1

    # 将更新后的数据写回文件
    with open(filename, "w", newline="", encoding="utf-8") as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=",")
        csv_writer.writerows(updated_rows)

    logging.debug(f"Processed {line_count} lines.")
    return recs


# **********
# read data from the potential camera locations file
# **********
def read_camera_locations(camera_locations, dem_data):
    updated_rows = []
    with open(camera_locations, encoding="utf-8") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=",")
        line_count = 0
        recs = []
        for row in csv_reader:
            if line_count == 0:
                updated_rows.append(row)  # 保留标题行
                line_count += 1
                names = row
            else:
                grid_code = int(row[1])
                longitude = float(row[2])
                latitude = float(row[3])
                elevation = (
                    get_dem_elevation(
                        dem_data, (longitude, latitude), coord_type="wgs84"
                    )
                    + 1.5
                )
                row[4] = str(elevation)  # 更新Elevation列
                updated_rows.append(row)  # 保存更新后的行
                # 添加坐标转换
                try:
                    logging.debug(
                        f"Processing row {line_count}: lat={latitude}, lon={longitude}"
                    )
                    easting, northing = geo_transformer.wgs84_to_utm(
                        longitude, latitude
                    )  # 注意顺序
                    pos3d = np.array([easting, northing, elevation])
                except ValueError as e:
                    logging.error(f"Error processing row {line_count}: {e}")
                    continue

                rec = {"grid_code": grid_code, "pos3d": pos3d}
                recs.append(rec)
                line_count += 1

    # 将更新后的数据写回文件
    with open(camera_locations, "w", newline="", encoding="utf-8") as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=",")
        csv_writer.writerows(updated_rows)

    logging.debug(f"Processed {line_count} lines.")
    return recs


def load_and_prepare_image(image_path):
    im = cv2.imread(image_path)
    im2 = np.copy(im)
    im[:, :, 0] = im2[:, :, 2]
    im[:, :, 1] = im2[:, :, 1]
    im[:, :, 2] = im2[:, :, 0]
    return im


def process_features(recs, dem_data, pixel_x, pixel_y, camera_location, features, M):
    features_list = []
    with open(features, encoding="utf-8") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=",")
        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                line_count += 1
                indx = row.index(pixel_x)
                indy = row.index(pixel_y)
            else:
                if int(row[indx]) == 0 and int(row[indy]) == 0:
                    symbol = row[1]
                    longitude = float(row[4])
                    latitude = float(row[5])
                    elevation = get_dem_elevation(
                        dem_data, (longitude, latitude), coord_type="wgs84"
                    )
                    easting, northing = geo_transformer.wgs84_to_utm(
                        longitude, latitude
                    )
                    camera_easting, camera_northing, camera_elevation = camera_location
                    relative_easting = easting - camera_easting
                    relative_northing = northing - camera_northing
                    relative_elevation = elevation - camera_elevation
                    p = np.array(
                        [relative_elevation, relative_northing, relative_easting]
                    )
                    p = p / p[2]
                    pp2 = np.matmul(np.linalg.inv(M), p)
                    pp2 = pp2 / pp2[2]
                    features_list.append((symbol, pp2))
    return features_list


def plot_features_with_red_and_yellow(
    recs,
    dem_data,
    pixel_x,
    pixel_y,
    camera_location,
    features,
    image_path,
    outputfile,
    M,
):
    im = load_and_prepare_image(image_path)
    img_height, img_width, _ = im.shape  # 获取图像的宽度和高度
    plt.figure(figsize=(40, 20))
    plt.imshow(im)

    for rec in recs:
        symbol = rec["symbol"]
        pixel = rec["pixel"]
        if pixel[0] != 0 or pixel[1] != 0:
            plt.text(pixel[0] + 7, pixel[1] - 4, symbol, color="red", fontsize=32)
            plt.plot(pixel[0], pixel[1], marker="s", markersize=8, color="red")

    features_list = process_features(
        recs, dem_data, pixel_x, pixel_y, camera_location, features, M
    )
    for symbol, pp2 in features_list:
        # 检查重投影后的像素坐标是否在图像范围内
        if 0 <= pp2[0] < img_width and 0 <= pp2[1] < img_height:
            print(
                f"读取点: Symbol={symbol}, 重投影后的像素坐标=({pp2[0]:.2f}, {pp2[1]:.2f})"
            )
            plt.text(pp2[0] + 7, pp2[1] - 4, symbol, color="yellow", fontsize=32)
            plt.plot(pp2[0], pp2[1], marker="s", markersize=8, color="yellow")
        else:
            print(
                f"跳过点: Symbol={symbol}, 重投影后的像素坐标=({pp2[0]:.2f}, {pp2[1]:.2f}) 超出图像范围"
            )

    plt.savefig(
        outputfile.replace(".jpg", "_2_output.png"), dpi=300, bbox_inches="tight"
    )
    plt.subplots_adjust(left=0.05, right=0.98, top=0.98, bottom=0.05)  # 移除边距
    plt.tight_layout(pad=1.0)  # 冗余保险
    plt.show()


# **********
# Main function
# **********
def do_it(
    image_name,
    json_file,
    features,
    camera_locations,
    pixel_x,
    pixel_y,
    output,
    dem_file,
):
    # 确保工作目录为脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # 检查图像文件是否存在
    image_path = os.path.join("historical photos", image_name)
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    # 加载图像
    im = load_and_prepare_image(image_path)

    # 加载DEM数据（DEM范围为UTM）
    dem_data = load_dem_data(dem_file)

    recs = read_points_data(features, pixel_x, pixel_y, 1.0, dem_data)
    locations = read_camera_locations(camera_locations, dem_data)

    pixels = np.array([rec["pixel"] for rec in recs])
    pos3ds = np.array([rec["pos3d"] for rec in recs])
    symbols = [rec["symbol"] for rec in recs]

    # 保持show参数为False来计算误差
    num_matches12, homographies = find_homographies(
        recs,
        locations,
        im,
        False,
        70.0,
        output,
        pixel_x,
        pixel_y,
        dem_data,
    )
    num_matches2 = num_matches12[:, 1]
    num_matches2[num_matches2 == 0] = 1000000
    min_idx = np.argmin(num_matches2)
    print("Minimum average reprojection error:", np.min(num_matches2))
    print("err1:", num_matches12[min_idx, 0])
    print("err2:", num_matches12[min_idx, 1])
    print(
        f"推测相机位置: {locations[min_idx]['pos3d']}, pointid: {min_idx + 1}, grid_code: {locations[min_idx]['grid_code']}"
    )

    best_M, best_mask = homographies[min_idx]

    # 调用新增的第一个函数生成红色和黄色特征点图像
    plot_features_with_red_and_yellow(
        recs,
        dem_data,
        pixel_x,
        pixel_y,
        locations[min_idx]["pos3d"],
        features,
        image_path,
        output,
        best_M,
    )

    # 调用find_homography函数内部的绘制功能生成绿色和紫色特征点图像
    find_homography(
        recs,
        pixels,
        pos3ds,
        symbols,
        locations[min_idx]["pos3d"],
        im,
        True,
        70.0,
        output,
        pixel_x,
        pixel_y,
        dem_data,
    )


def main():
    images_info = [
        {
            "image_name": "1898.jpg",
            "json_file": "1898.json",
            "features": "feature_points_with_annotations.csv",
            "camera_locations": "potential_camera_locations.csv",
            "pixel_x": "Pixel_x",
            "pixel_y": "Pixel_y",
            "output": "zOutput_1898.jpg",
            "scale": 1.0,
            "dem_file": "dem_dx.tif",
        },
        {
            "image_name": "1900-1910.jpg",
            "json_file": "1900-1910.json",
            "features": "feature_points_with_annotations.csv",
            "camera_locations": "potential_camera_locations.csv",
            "pixel_x": "Pixel_x_1900-1910.jpg",
            "pixel_y": "Pixel_y_1900-1910.jpg",
            "output": "zOutput_1900-1910.jpg",
            "scale": 1.0,
            "dem_file": "dem_dx.tif",
        },
        {
            "image_name": "1910.jpg",
            "json_file": "1910.json",
            "features": "feature_points_with_annotations.csv",
            "camera_locations": "potential_camera_locations.csv",
            "pixel_x": "Pixel_x_1910.jpg",
            "pixel_y": "Pixel_y_1910.jpg",
            "output": "zOutput_1910.jpg",
            "scale": 1.0,
            "dem_file": "dem_dx.tif",
        },
        {
            "image_name": "1920-1930.jpg",
            "json_file": "1920-1930.json",
            "features": "feature_points_with_annotations.csv",
            "camera_locations": "potential_camera_locations.csv",
            "pixel_x": "Pixel_x_1920-1930.jpg",
            "pixel_y": "Pixel_y_1920-1930.jpg",
            "output": "zOutput_1920-1930.jpg",
            "scale": 1.0,
            "dem_file": "dem_dx.tif",
        },
        {
            "image_name": "1925-1930.jpg",
            "json_file": "1925-1930.json",
            "features": "feature_points_with_annotations.csv",
            "camera_locations": "potential_camera_locations.csv",
            "pixel_x": "Pixel_x_1925-1930.jpg",
            "pixel_y": "Pixel_y_1925-1930.jpg",
            "output": "zOutput_1925-1930.jpg",
            "scale": 1.0,
            "dem_file": "dem_dx.tif",
        },
        {
            "image_name": "Kuliang.jpg",
            "json_file": "Kuliang.json",
            "features": "feature_points_with_annotations.csv",
            "camera_locations": "potential_camera_locations.csv",
            "pixel_x": "Pixel_x_Kuliang.jpg",
            "pixel_y": "Pixel_y_Kuliang.jpg",
            "output": "zOutput_Kuliang.jpg",
            "scale": 1.0,
            "dem_file": "dem_dx.tif",
        },
        {
            "image_name": "Siems Siemssen.jpg",
            "json_file": "Siems Siemssen.json",
            "features": "feature_points_with_annotations.csv",
            "camera_locations": "potential_camera_locations.csv",
            "pixel_x": "Pixel_x_Siems Siemssen.jpg",
            "pixel_y": "Pixel_y_Siems Siemssen.jpg",
            "output": "zOutput_Siems Siemssen.jpg",
            "scale": 1.0,
            "dem_file": "dem_dx.tif",
        },
    ]

    # 指定要处理的图像信息
    target_info = images_info[
        0
    ]  # 修改此索引以选择要处理的图像，例如 0 表示处理第一个图像

    do_it(
        target_info["image_name"],
        target_info["json_file"],
        target_info["features"],
        target_info["camera_locations"],
        target_info["pixel_x"],
        target_info["pixel_y"],
        target_info["output"],
        target_info["dem_file"],
    )


if __name__ == "__main__":
    main()

print("**********************")
print("Done!")
