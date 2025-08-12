from pydantic import BaseModel


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
