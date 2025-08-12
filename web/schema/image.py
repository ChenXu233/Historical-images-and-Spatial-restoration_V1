from pydantic import BaseModel


class Images(BaseModel):
    """图片模型
    Args:
        name (str): 图片名称
        path (str): 图片路径
    """

    name: str
    path: str

    class Config:
        orm_mode = True
