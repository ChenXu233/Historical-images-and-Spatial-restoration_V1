from pydantic import BaseModel


class BuildingPoint(BaseModel):
    name: str
    latitude: float
    longitude: float

    class Config:
        orm_mode = True
