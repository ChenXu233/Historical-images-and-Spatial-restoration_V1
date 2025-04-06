import numpy as np
import plotly.graph_objects as go
import rasterio
from pyproj import Transformer
from scipy.spatial import Delaunay
from shapely.geometry import Polygon, Point
import matplotlib.pyplot as plt
import pandas as pd


def read_dem(file_path):
    with rasterio.open(file_path) as dataset:
        dem_data = dataset.read(1)
        transform = dataset.transform
        x_min = transform[2]
        y_min = transform[5]
        cell_size = abs(transform[0])
        print(f"DEM分辨率: {cell_size:.8f} 度/像素")
        print(f"DEM数据范围: 经度 [{x_min:.6f} -> {x_min + cell_size * dem_data.shape[1]:.6f}]")
        print(f"          纬度 [{y_min:.6f} -> {y_min - cell_size * dem_data.shape[0]:.6f}]")
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
    transformer = Transformer.from_crs(f"epsg:326{zone_number}", "epsg:4326", always_xy=True)  # 关键: always_xy=True
    return [(lon, lat, elev) for easting, northing, elev in utm_coordinates
            for lon, lat in [transformer.transform(easting, northing)]]

def convert_wgs84_to_utm(wgs84_coordinates, zone_number):
    transformer = Transformer.from_crs("epsg:4326", f"epsg:326{zone_number}", always_xy=True)
    return [(easting, northing, elev) for lon, lat, elev in wgs84_coordinates
            for easting, northing in [transformer.transform(lon, lat)]]


def create_precise_polygon(wgs84_coords):
    """直接使用有序的原始点创建凹多边形，显式闭合路径"""
    # 提取经纬度
    coords = [(lon, lat) for lon, lat, _ in wgs84_coords]

    # 显式闭合路径（若首尾点不同）
    if coords and (coords[0] != coords[-1]):
        coords.append(coords[0])

    # 创建多边形（假设coords已按实际轮廓顺序排列）
    polygon = Polygon(coords)

    # 验证边界偏差
    original = np.array(coords[:-1])  # 排除闭合点
    processed = np.array(polygon.exterior.coords)[:-1]
    if original.shape[0] != processed.shape[0]:
        print("警告：坐标数量不一致，可能因输入点无序导致简化")
    deviation = np.max(np.abs(original - processed))
    print(f"边界保真度检查: 最大偏差 {deviation:.10f} 度")

    return polygon

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

def main():
    # 配置参数
    dem_file = 'dem_dx.tif'
    boundary_file = 'space_boundary.csv'
    utm_zone = 50  # 根据实际调整

    # 1. 数据读取
    print("1. 正在读取数据...")
    try:
        # 读取边界点并显式闭合
        utm_coords = pd.read_csv(boundary_file)[['geo_x', 'geo_y', 'geo_z']].values.tolist()
        if len(utm_coords) < 3:
            raise ValueError("边界点数量不足（至少需要3个点）")

        # 关键修改1：显式闭合路径（若首尾点不同）
        if (utm_coords[0][0] != utm_coords[-1][0]) or (utm_coords[0][1] != utm_coords[-1][1]):
            utm_coords.append(utm_coords[0].copy())  # 避免原地修改
            print("提示：已显式闭合边界路径")

        # 读取DEM数据
        dem, x_min, y_min, cell_size = read_dem(dem_file)
    except Exception as e:
        print(f"初始化失败: {str(e)}")
        return

    # 2. 坐标转换
    print("\n2. 坐标转换...")
    wgs84_coords = convert_utm_to_wgs84(utm_coords, utm_zone)
    print("前两个转换后的WGS84坐标: ", wgs84_coords[:2])  # 避免输出过长

    # 3. 创建精确多边形
    print("\n3. 创建精确边界...")
    try:
        precise_polygon = create_precise_polygon(wgs84_coords)
        print(f"多边形面积: {precise_polygon.area:.6f} 平方度")

        # 验证多边形有效性
        if not precise_polygon.is_valid:
            print("警告：生成的多边形存在自相交，尝试修复...")
            precise_polygon = precise_polygon.buffer(0)  # 缓冲修复
    except Exception as e:
        print(f"多边形创建失败: {str(e)}")
        return

    # 4. 筛选DEM数据中在多边形内部的点
    print("\n4. 筛选DEM数据点...")
    longitudes, latitudes, elevations = get_elevation_points_within_polygon(
        dem, precise_polygon, x_min, y_min, cell_size
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
    plt.figure(figsize=(12, 6))
    ax = plt.subplot(111)

    # 绘制原始边界点
    ax.plot(
        *zip(*[(p[0], p[1]) for p in utm_wgs84_coords]),
        'ro', markersize=4, label='original boundary points'
    )

    # 绘制生成的多边形边界
    if precise_polygon.geom_type == 'Polygon':
        exterior_coords = list(precise_polygon.exterior.coords)
        utm_exterior = convert_wgs84_to_utm(
            [(lon, lat, 0) for lon, lat in exterior_coords], utm_zone
        )
        ax.plot(
            *zip(*[(p[0], p[1]) for p in utm_exterior]),
            'b-', linewidth=1.5, label='processed boundary points'
        )

    ax.set_aspect('equal')
    ax.legend()
    plt.title("2D Boundary Comparison (UTM Coordinates)")
    plt.show()

    # 3D地形图（保持原代码不变）
    print("\n5. 使用Delaunay三角剖分生成3D地形图...")
    points = np.array([(p[0], p[1], p[2]) for p in utm_valid_points])
    tri = Delaunay(points[:, :2])
    triangles = remove_unnecessary_faces(tri.simplices, points)
    fig = go.Figure(data=[
        go.Mesh3d(
            x=points[:, 0],
            y=points[:, 1],
            z=points[:, 2],
            i=triangles[:, 0],
            j=triangles[:, 1],
            k=triangles[:, 2],
            intensity=points[:, 2],
            colorscale='Viridis',
            opacity=0.8,
            name='Terrain Mesh'
        ),
        go.Scatter3d(
            x=[p[0] for p in utm_wgs84_coords],
            y=[p[1] for p in utm_wgs84_coords],
            z=[p[2] for p in utm_wgs84_coords],
            mode='markers',
            marker=dict(size=4, color='red'),
            name='Original Boundary Points'
        )
    ])
    fig.update_layout(
        scene=dict(
            xaxis_title='Easting (m)',
            yaxis_title='Northing (m)',
            zaxis_title='Elevation (m)',
            aspectmode='data'
        ),
        title='3D Terrain Reconstruction with Precise Boundary'
    )
    fig.show()


if __name__ == "__main__":
    main()
