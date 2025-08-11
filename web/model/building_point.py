from database import Base

from sqlalchemy import Integer, String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship


class BuildingPoint(Base):
    __tablename__ = "building_point"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    labels: Mapped[list["Label"]] = relationship(
        "Label", back_populates="building_point"
    )


from model.label import Label
