from sqlalchemy import Integer, String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Label(Base):
    __tablename__ = "label"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)

    pixel_x: Mapped[int] = mapped_column(Integer, nullable=False)
    pixel_y: Mapped[int] = mapped_column(Integer, nullable=False)

    building_point_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("building_point.id"), nullable=False
    )
    building_point: Mapped["BuildingPoint"] = relationship(
        "BuildingPoint", back_populates="labels"
    )


from model.building_point import BuildingPoint
