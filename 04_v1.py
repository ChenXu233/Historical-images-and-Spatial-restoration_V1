"""
将DEM 数据导出为STL文件

"""

import numpy as np
import plotly.graph_objects as go
import rasterio
from pyproj import Transformer
from scipy.spatial import Delaunay, ConvexHull
from shapely.geometry import Polygon, Point
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator
import pandas as pd
import trimesh


def read_dem(file_path):
    with rasterio.open(file_path) as dataset:
        dem_data = dataset.read(1)
        transform = dataset.transform
        x_min = transform[2]
        y_min = transform[5]
        cell_size = abs(transform[0])
        print(f"DEM分辨率: {cell_size:.8f} 度/像素")
        print(
            f"DEM数据范围: 经度 [{x_min:.6f} -> {x_min + cell_size * dem_data.shape[1]:.6f}]"
        )
        print(f"纬度 [{y_min:.6f} -> {y_min - cell_size * dem_data.shape[0]:.6f}]")
    return dem_data, x_min, y_min, cell_size


def get_elevation_points_within_polygon(dem_data, polygon, x_min, y_min, cell_size):
    elevations = []
    latitudes = []
    longitudes = []

    # 确保多边形是有效的
    if not polygon.is_valid:
        polygon = polygon.buffer(0)

    # 遍历每个像素中心点
    for row in range(dem_data.shape[0]):
        for col in range(dem_data.shape[1]):
            lon = x_min + (col + 0.5) * cell_size  # 像素中心点经度
            lat = y_min - (row + 0.5) * cell_size  # 像素中心点纬度
            point = Point(lon, lat)
            if polygon.contains(point):
                elevations.append(dem_data[row, col])
                latitudes.append(lat)
                longitudes.append(lon)

    return longitudes, latitudes, elevations


def convert_utm_to_wgs84(utm_coordinates, zone_number):
    transformer = Transformer.from_crs(
        f"epsg:326{zone_number}", "epsg:4326", always_xy=True
    )
    return [
        (lon, lat, elev)
        for easting, northing, elev in utm_coordinates
        for lon, lat in [transformer.transform(easting, northing)]
    ]


def convert_wgs84_to_utm(wgs84_coordinates, zone_number):
    transformer = Transformer.from_crs(
        "epsg:4326", f"epsg:326{zone_number}", always_xy=True
    )
    return [
        (easting, northing, elev)
        for lon, lat, elev in wgs84_coordinates
        for easting, northing in [transformer.transform(lon, lat)]
    ]


def create_convex_hull_polygon(wgs84_coords):
    """
    使用边界点生成最小外接多边形（凸包）。
    """
    # 提取经纬度
    coords = np.array([(lon, lat) for lon, lat, _ in wgs84_coords])

    # 计算凸包
    hull = ConvexHull(coords)
    hull_points = coords[hull.vertices]

    # 创建凸包多边形
    convex_hull_polygon = Polygon(hull_points)

    return convex_hull_polygon


def remove_unnecessary_faces(triangles, points):
    """
    删除不必要的立面，即法向量接近垂直的三角面
    """
    valid_triangles = []
    for tri in triangles:
        p1, p2, p3 = points[tri[0]], points[tri[1]], points[tri[2]]
        v1 = np.array(p2) - np.array(p1)
        v2 = np.array(p3) - np.array(p1)
        normal = np.cross(v1, v2)
        normal = normal / np.linalg.norm(normal)
        # 判断法向量是否接近垂直
        if abs(normal[2]) > 0.1:  # 0.1 是一个经验阈值，可以调整
            valid_triangles.append(tri)
    return np.array(valid_triangles)


def export_stl(filename, vertices, faces):
    """
    导出 STL 文件
    """
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
    mesh.export(filename)
    print(f"STL 文件已保存为 {filename}")


def main():
    # 配置参数
    dem_file = "dem_dx.tif"
    boundary_file = "space_boundary_1900-1910.csv"
    feature_file = "feature_points_with_annotations.csv"  # 新增：特征点文件
    pixel_x_col = "Pixel_x_1900-1910.jpg"
    pixel_y_col = "Pixel_y_1900-1910.jpg"
    utm_zone = 50  # 根据实际调整

    # 1. 数据读取
    print("1. 正在读取数据...")
    try:
        # 读取边界点并显式闭合
        utm_coords = pd.read_csv(boundary_file)[
            ["geo_x", "geo_y", "geo_z"]
        ].values.tolist()
        if len(utm_coords) < 3:
            raise ValueError("边界点数量不足（至少需要3个点）")

        # 读取DEM数据
        dem, x_min, y_min, cell_size = read_dem(dem_file)
    except Exception as e:
        print(f"初始化失败: {str(e)}")
        return

    # 读取特征点数据
    try:
        feature_data = pd.read_csv(feature_file)
        feature_points = feature_data[
            (feature_data[pixel_x_col] != 0) & (feature_data[pixel_y_col] != 0)
        ][["Longitude", "Latitude", "Elevation", "Symbol"]].values.tolist()
        if not feature_points:
            raise ValueError("未找到有效的特征点")
        feature_symbols = [symbol for _, _, _, symbol in feature_points]  # 分离出symbol
        feature_points = [
            (lon, lat, elev) for lon, lat, elev, _ in feature_points
        ]  # 只保留坐标
    except Exception as e:
        print(f"读取特征点失败: {str(e)}")
        return

    # 2. 坐标转换
    print("\n2. 坐标转换...")
    wgs84_coords = convert_utm_to_wgs84(utm_coords, utm_zone)
    print("前两个转换后的WGS84坐标: ", wgs84_coords[:2])  # 避免输出过长

    # 特征点坐标转换
    feature_utm_coords = convert_wgs84_to_utm(feature_points, utm_zone)
    print("前两个转换后的特征点UTM坐标: ", feature_utm_coords[:2])  # 避免输出过长

    # 3. 创建凸包多边形
    print("\n3. 创建最小外接多边形...")
    try:
        convex_hull_polygon = create_convex_hull_polygon(wgs84_coords)
        print(f"多边形面积: {convex_hull_polygon.area:.6f} 平方度")

        # 验证多边形有效性
        if not convex_hull_polygon.is_valid:
            print("警告：生成的多边形存在自相交，尝试修复...")
            convex_hull_polygon = convex_hull_polygon.buffer(0)  # 缓冲修复
    except Exception as e:
        print(f"多边形创建失败: {str(e)}")
        return

    # 4. 筛选DEM数据中在多边形内部的点
    print("\n4. 筛选DEM数据点...")
    longitudes, latitudes, elevations = get_elevation_points_within_polygon(
        dem, convex_hull_polygon, x_min, y_min, cell_size
    )
    valid_points = list(zip(longitudes, latitudes, elevations))
    print(f"有效高程点数量: {len(valid_points)}")

    if not valid_points:
        print("错误：未获取到有效高程")
        return

    # 5. 可视化
    print("\n5. 可视化结果...")
    # 转换坐标以便可视化
    utm_valid_points = convert_wgs84_to_utm(valid_points, utm_zone)
    utm_wgs84_coords = convert_wgs84_to_utm(wgs84_coords, utm_zone)

    # 2D边界对比图
    plt.figure(figsize=(12, 6), dpi=300)
    ax = plt.subplot(111)

    # 绘制原始边界点
    ax.plot(*zip(*[(p[0], p[1]) for p in utm_wgs84_coords]), "ro", markersize=4)

    # 绘制生成的凸包多边形边界
    if convex_hull_polygon.geom_type == "Polygon":
        exterior_coords = list(convex_hull_polygon.exterior.coords)
        utm_exterior = convert_wgs84_to_utm(
            [(lon, lat, 0) for lon, lat in exterior_coords], utm_zone
        )
        ax.plot(*zip(*[(p[0], p[1]) for p in utm_exterior]), "b-", linewidth=1.5)

    ax.set_aspect("equal")
    plt.title("2D Boundary Comparison (UTM Coordinates)", fontsize=10)

    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{int(y):,}"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{int(y):,}"))
    ax.tick_params(labelsize=8)  # 调整刻度标签字体大小
    ax.set_xlabel("Easting (m)", fontsize=8)  # 调整X轴标题字体大小
    ax.set_ylabel("Northing (m)", fontsize=8)  # 调整Y轴标题字体大小

    plt.savefig("2d_boundary_comparison.png", dpi=300, bbox_inches="tight")
    plt.show()

    # 生成二维地形图
    plt.figure(figsize=(12, 8), dpi=300)
    ax = plt.subplot(111)
    sc = ax.scatter(
        [p[0] for p in utm_valid_points],
        [p[1] for p in utm_valid_points],
        c=[p[2] for p in utm_valid_points],
        cmap="viridis",
        marker="o",
    )

    # 添加特征点
    feature_x = [p[0] for p in feature_utm_coords]
    feature_y = [p[1] for p in feature_utm_coords]
    ax.scatter(feature_x, feature_y, color="blue", label="Feature Points")
    for i, symbol in enumerate(feature_symbols):
        # 调整 feature text 的字体大小为 10
        ax.text(feature_x[i] + 5, feature_y[i], symbol, fontsize=9, color="black")

    # 添加颜色条并设置字体大小
    cbar = plt.colorbar(sc, label="Elevation (m)")
    cbar.ax.tick_params(labelsize=8)  # 调整颜色条刻度字体大小为 8
    cbar.set_label("Elevation (m)", fontsize=8)  # 调整颜色条标签字体大小为 8

    # 设置标题和轴标签字体大小为 8
    plt.title("2D Terrain Map with Elevation", fontsize=10)
    ax.set_xlabel("Easting (m)", fontsize=8)
    ax.set_ylabel("Northing (m)", fontsize=8)
    ax.set_aspect("equal")

    # 设置网格和刻度格式
    plt.grid(True)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{int(y):,}"))
    ax.xaxis.set_major_locator(MultipleLocator(100))
    ax.yaxis.set_major_locator(MultipleLocator(100))
    ax.tick_params(labelsize=8)  # 调整刻度字体大小为 8

    # 裁剪图形边距
    plt.subplots_adjust(left=0.05, right=0.98, top=0.98, bottom=0.05)
    plt.tight_layout(pad=1.0)

    # 保存图像
    plt.savefig("2d_terrain_map.png", dpi=300, bbox_inches="tight")
    plt.show()

    # 3D地形图
    print("\n5. 使用Delaunay三角剖分生成3D地形图...")
    points = np.array([(p[0], p[1], p[2]) for p in utm_valid_points])
    tri = Delaunay(points[:, :2])
    triangles = remove_unnecessary_faces(tri.simplices, points)

    fig = go.Figure(
        data=[
            go.Mesh3d(
                x=points[:, 0],
                y=points[:, 1],
                z=points[:, 2],
                i=triangles[:, 0],
                j=triangles[:, 1],
                k=triangles[:, 2],
                intensity=points[:, 2],
                colorscale="Viridis",
                opacity=0.8,
                name="Terrain Mesh",
            ),
            go.Scatter3d(
                x=[p[0] for p in feature_utm_coords],
                y=[p[1] for p in feature_utm_coords],
                z=[p[2] for p in feature_utm_coords],
                mode="markers+text",
                marker=dict(size=4, color="blue"),
                text=feature_symbols,
                textposition="top center",
                textfont=dict(size=10),
                name="Feature Points",
            ),
        ]
    )
    fig.update_layout(
        scene=dict(
            xaxis=dict(
                title=dict(
                    text="Easting (m)",
                    font=dict(size=10),  # 设置 X 轴标题字体大小
                ),
                tickformat=",d",
                tickfont=dict(size=10),  # 设置 X 轴刻度字体大小
            ),
            yaxis=dict(
                title=dict(
                    text="Northing (m)",
                    font=dict(size=10),  # 设置 Y 轴标题字体大小
                ),
                tickformat=",d",
                tickfont=dict(size=10),  # 设置 Y 轴刻度字体大小
            ),
            zaxis=dict(
                title=dict(
                    text="Elevation (m)",
                    font=dict(size=10),  # 设置 Z 轴标题字体大小
                ),
                tickformat=",d",
                tickfont=dict(size=10),  # 设置 Z 轴刻度字体大小
            ),
            aspectmode="data",
        ),
        title="3D Terrain Reconstruction with Feature Points",
    )
    fig.show()

    # 导出 HTML 文件
    html_filename = "3d_terrain_map.html"
    fig.write_html(html_filename)
    print(f"HTML 文件已保存为 {html_filename}")

    # 导出 STL 文件
    stl_filename = "3d_terrain_map.stl"
    export_stl(stl_filename, points, triangles)


if __name__ == "__main__":
    main()
