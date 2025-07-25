from pydantic import BaseModel, Field, ConfigDict
import numpy as np
from typing import Tuple
from scipy.interpolate import RegularGridInterpolator


class Feature(BaseModel):
    object_id: int = Field(
        ..., description="特征的唯一对象标识，用于在系统中区分不同的特征"
    )
    pixel_x: float = Field(
        ...,
        description="特征在图像像素坐标系中的X轴坐标，用于定位特征在图像中的水平位置",
    )
    pixel_y: float = Field(
        ...,
        description="特征在图像像素坐标系中的Y轴坐标，用于定位特征在图像中的垂直位置",
    )
    symbol: str = Field(..., description="特征对应的符号标识，可用于直观表示或分类特征")
    name: str = Field(..., description="特征的名称，用于对特征进行文字描述和识别")
    height: float = Field(
        ..., description="特征的高度，通常表示特征在现实世界中的垂直尺寸"
    )
    longitude: float = Field(
        ..., description="特征所在位置的经度，用于在地理坐标系中确定特征的东西方向位置"
    )
    latitude: float = Field(
        ..., description="特征所在位置的纬度，用于在地理坐标系中确定特征的南北方向位置"
    )
    elevation: float | None = Field(
        ..., description="特征所在位置的海拔高度，即相对于海平面的垂直高度"
    )


class DEMData(BaseModel):
    interpolator: RegularGridInterpolator = Field(
        ..., description="用于插值计算的地形数据插值器"
    )
    x_range: Tuple[float, float] = Field(..., description="地形数据在X轴上的范围")
    y_range: Tuple[float, float] = Field(..., description="地形数据在Y轴上的范围")
    utm_x_range: Tuple[float | None, float | None] = Field(
        ..., description="地形数据在UTM坐标系中的X轴范围"
    )
    utm_y_range: Tuple[float | None, float | None] = Field(
        ..., description="地形数据在UTM坐标系中的Y轴范围"
    )
    data: np.ndarray = Field(..., description="地形数据数组")

    model_config = ConfigDict(arbitrary_types_allowed=True)  # 添加配置项


class CameraLocation(BaseModel):
    grid_code: int = Field(..., description="相机位置的网格代码，用于唯一标识相机位置")
    pos3d: np.ndarray = Field(
        ..., description="相机位置的三维坐标，包括X、Y、Z轴的坐标值"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)  # 添加配置项


class PointData(BaseModel):
    pixel: np.ndarray = Field(
        ..., description="特征在图像中的像素坐标，通常为二维数组 [x, y]"
    )
    pos3d: np.ndarray = Field(
        ..., description="特征在三维空间中的坐标，通常为三维数组 [x, y, z]"
    )
    symbol: str = Field(..., description="特征对应的符号标识")
    name: str = Field(..., description="特征的名称")

    model_config = ConfigDict(arbitrary_types_allowed=True)  # 添加配置项
