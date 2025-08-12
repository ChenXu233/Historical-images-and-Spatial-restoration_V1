from sqlalchemy import Integer, String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Images(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    path: Mapped[str] = mapped_column(String, index=True)

    features: Mapped[list["Feature"]] = relationship("Feature", back_populates="image")


from model.feature import Feature
