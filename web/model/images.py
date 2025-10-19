from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import TYPE_CHECKING
from typing import Tuple, Optional

if TYPE_CHECKING:
    from model.feature import Feature
    from model.camera_param import CameraParam

from database import Base


class Images(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    path: Mapped[str] = mapped_column(String, index=True)
    camera_params: Mapped[list["CameraParam"]] = relationship(
        "CameraParam", back_populates="image"
    )

    features: Mapped[list["Feature"]] = relationship("Feature", back_populates="image")
    calculated_camera_locations: Mapped[Optional[Tuple[float, float, float]]] = (
        mapped_column(String)
    )
