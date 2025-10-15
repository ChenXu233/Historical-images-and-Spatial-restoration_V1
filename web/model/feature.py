from sqlalchemy import Integer, String, ForeignKey

from sqlalchemy.orm import Mapped, mapped_column, relationship


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.building_point import BuildingPoint
    from model.images import Images

from database import Base


class Feature(Base):
    __tablename__ = "feature"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    pixel_x: Mapped[int] = mapped_column(Integer, nullable=False)
    pixel_y: Mapped[int] = mapped_column(Integer, nullable=False)

    building_point_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("building_point.id"), nullable=False
    )
    building_point: Mapped["BuildingPoint"] = relationship(
        "BuildingPoint", back_populates="features"
    )

    image_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("images.id"), nullable=False
    )
    image: Mapped["Images"] = relationship("Images", back_populates="features")
