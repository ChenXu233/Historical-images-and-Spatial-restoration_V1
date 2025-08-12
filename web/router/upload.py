from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.requests import Request
from sqlalchemy.orm import Session
import os
import uuid
from pathlib import Path

from schema.building_point import BuildingPoint
from schema.features import Feature
from model.feature import Feature as FeatureModel
from model.building_point import BuildingPoint as BuildingPointModels
from model.images import Images as ImagesModel
from database import get_db

upload = APIRouter(prefix="/api", tags=["upload_building_point"])

# 创建上传目录
UPLOAD_DIR = Path("./uploaded_images")
UPLOAD_DIR.mkdir(exist_ok=True)


@upload.post("/upload_building_point")
async def upload_building_point(
    request: Request, building_point: BuildingPoint, db: Session = Depends(get_db)
):
    building_point_models = BuildingPointModels(**building_point.model_dump())
    db.add(building_point_models)
    db.commit()
    return {"status": "success"}


@upload.post("/upload_features")
async def _upload_features(
    request: Request, feature: Feature, db: Session = Depends(get_db)
):
    feature_model = FeatureModel(**feature.model_dump())
    db.add(feature_model)
    db.commit()
    return {"status": "success"}


@upload.post("/upload_image")
async def upload_image(
    request: Request, image: UploadFile = File(...), db: Session = Depends(get_db)
):
    # 检查文件名是否存在
    if image.filename is None:
        raise ValueError("No filename provided")

    # 生成唯一文件名
    file_extension = os.path.splitext(image.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename

    # 保存文件
    with open(file_path, "wb") as buffer:
        buffer.write(await image.read())

    # 保存到数据库
    image_model = ImagesModel(name=image.filename, path=str(file_path))
    db.add(image_model)
    db.commit()
    db.refresh(image_model)

    return {"status": "success", "filename": unique_filename, "path": str(file_path)}
