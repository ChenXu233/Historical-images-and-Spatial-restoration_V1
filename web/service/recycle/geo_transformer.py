import numpy as np
from typing import Tuple
from pyproj import Transformer

from logger import logging


class GeoCoordTransformer:
    def __init__(self):
        self.to_utm = Transformer.from_crs("epsg:4326", "epsg:32650", always_xy=True)
        self.to_wgs84 = Transformer.from_crs("epsg:32650", "epsg:4326", always_xy=True)

    def wgs84_to_utm(
        self, lon: float, lat: float
    ) -> Tuple[float, float]:  # 注意顺序：先经度，后纬度
        try:
            easting, northing = self.to_utm.transform(lon, lat)
            if np.isinf(easting) or np.isinf(northing):
                raise ValueError("Invalid UTM coordinates")
            return easting, northing
        except Exception as e:
            logging.exception(f"坐标转换失败: {str(e)}")
            raise e

    def utm_to_wgs84(self, easting: float, northing: float) -> Tuple[float, float]:
        try:
            lon, lat = self.to_wgs84.transform(
                easting, northing
            )  # 注意顺序：先经度，后纬度
            if np.isinf(lat) or np.isinf(lon):
                raise ValueError("Invalid WGS84 coordinates")
            return lon, lat
        except Exception as e:
            logging.exception(f"坐标转换失败: {str(e)}")
            raise e


geo_transformer = GeoCoordTransformer()
