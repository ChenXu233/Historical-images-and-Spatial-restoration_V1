from sqlalchemy import Integer, ForeignKey, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import TYPE_CHECKING
from typing import Optional

if TYPE_CHECKING:
    from model.images import Images

from database import Base


class CameraParam(Base):
    __tablename__ = "camera_params"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    image_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("images.id"), nullable=False
    )
    image: Mapped["Images"] = relationship("Images", back_populates="camera_params")

    focal_length: Mapped[float] = mapped_column(Float, nullable=False)
    sensor_width: Mapped[float] = mapped_column(Float, nullable=False)
    sensor_height: Mapped[float] = mapped_column(Float, nullable=False)
    reprojection_error: Mapped[float] = mapped_column(Float, nullable=False)

    # 相机内参矩阵K，使用JSON类型存储numpy数组
    camera_matrix: Mapped[dict] = mapped_column(JSON, nullable=False)

    # 旋转矩阵R，使用JSON类型存储numpy数组
    rotation_matrix: Mapped[dict] = mapped_column(JSON, nullable=True)

    # 畸变系数，使用JSON类型存储numpy数组
    dist_coeffs: Mapped[dict] = mapped_column(JSON, nullable=True)

    # 优化后的旋转向量，使用JSON类型存储numpy数组
    optimized_rotation_vector: Mapped[dict] = mapped_column(JSON, nullable=True)

    # 优化后的平移向量，使用JSON类型存储numpy数组
    optimized_translation_vector: Mapped[dict] = mapped_column(JSON, nullable=True)
