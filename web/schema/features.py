from pydantic import BaseModel
from typing import List


class Feature(BaseModel):
    """特征点
    Args:
        x (float): 图片x维度
        y (float): 图片y维度

        image_id (int): 图片ID
    """

    x: float
    y: float
    image_id: int

    class Config:
        orm_mode = True


class UploadFeature(BaseModel):
    """上传特征点
    Args:
        x (float): 图片x维度
        y (float): 图片y维度
        image_id (int): 图片ID
        building_point_id (int, optional): 建筑点ID
        name (str, optional): 特征点名称
        symbol (str, optional): 特征点符号
        longitude (float, optional): 经度
        latitude (float, optional): 纬度
    """

    x: float
    y: float
    image_id: int
    building_point_id: int | None = None
    name: str | None = None
    longitude: float | None = None
    latitude: float | None = None

    class Config:
        orm_mode = True


class UploadFeatures(BaseModel):
    """批量上传特征点
    Args:
        features (list[UploadFeature]): 特征点列表
    """

    features: List[UploadFeature]

    class Config:
        orm_mode = True
