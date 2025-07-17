import numpy as np
import cv2
import matplotlib.pyplot as plt
from matplotlib import font_manager
import os

##

from typing import List

##
from logger import logging
from utils import (
    load_and_prepare_image,
    load_dem_data,
    get_features,
    read_camera_locations,
    read_points_data,
)
from schema import Feature, DEMData, CameraLocation, PointData


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
    logging.debug(f"Homography Matrix M: {M}")
    logging.debug(f"Mask: {mask}")
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

        logging.debug(
            f"Camera Location {i}: Grid Code={grids[i]}, Position={loc3ds[i]}, Matches={num_matches[i]}"
        )

    logging.debug(f"Scores: {scores}")

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
        f"推测相机位置: {camera_locations[min_idx].pos3d}, pointid: {min_idx + 1}, grid_code: {camera_locations[min_idx].grid_code}"
    )


if __name__ == "__main__":
    main(
        image_path="1898.jpg",
        dem_path="dem_dx.tif",
        feature_path="feature_points_with_annotations.csv",
        camera_locations_path="potential_camera_locations.csv",
    )
