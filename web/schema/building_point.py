from pydantic import BaseModel


class BuildingPoint(BaseModel):
    name: str
    latitude: float
    longitude: float
    image_id: int

    class Config:
        orm_mode = True
