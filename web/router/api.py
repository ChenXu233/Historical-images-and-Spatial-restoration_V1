from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form
from fastapi.requests import Request
from sqlalchemy.orm import Session
from sqlalchemy import and_
import os
import uuid
from pathlib import Path

from schema.building_point import BuildingPoint
from schema.features import UploadFeatures
from model.feature import Feature as FeatureModel
from model.building_point import BuildingPoint as BuildingPointModels
from model.images import Images as ImagesModel
from database import get_db
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List

from service.recycle.main import calculate
from service.recycle.utils import (
    load_dem_data,
    load_points_data_from_orm,
    load_features_from_orm,
)


api = APIRouter(prefix="/api", tags=["api"])

# 创建上传目录
UPLOAD_DIR = Path(__file__).parent.parent / "static" / "uploaded_images"
UPLOAD_DIR.mkdir(exist_ok=True)


# 定义建筑点数据模型
class BuildingPointData(BaseModel):
    name: str
    longitude: float
    latitude: float


class BuildingPointsUpload(BaseModel):
    points: List[BuildingPointData]


@api.get("/building_points")
async def get_building_points(db: Session = Depends(get_db)):
    """获取所有建筑点数据"""
    try:
        building_points = db.query(BuildingPointModels).all()
        return [
            {
                "id": bp.id,
                "name": bp.name,
                "latitude": bp.latitude,
                "longitude": bp.longitude,
            }
            for bp in building_points
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api.post("/upload_building_point")
async def upload_building_point(
    request: Request, building_point: BuildingPoint, db: Session = Depends(get_db)
):
    # 检查是否已存在具有相同名称、经纬度的建筑点
    existing_building_point = (
        db.query(BuildingPointModels)
        .filter(
            and_(
                BuildingPointModels.name == building_point.name,
                BuildingPointModels.longitude == building_point.longitude,
                BuildingPointModels.latitude == building_point.latitude,
            )
        )
        .first()
    )

    if existing_building_point:
        return {"status": "success", "message": "建筑点已存在"}

    building_point_models = BuildingPointModels(
        name=building_point.name,
        latitude=building_point.latitude,
        longitude=building_point.longitude,
    )
    building_point_models.features = []
    db.add(building_point_models)
    db.commit()
    return {"status": "success", "message": "建筑点创建成功"}


@api.post("/upload_features")
async def upload_features(
    request: Request,
    features: UploadFeatures,
    db: Session = Depends(get_db),
):
    try:
        for i in features.features:
            image = db.query(ImagesModel).filter(ImagesModel.id == i.image_id).first()
            if not image:
                raise HTTPException(status_code=404, detail="图片不存在")

            # 如果没有提供 building_point_id，则自动创建建筑点
            building_point_id = i.building_point_id
            if (
                not building_point_id
                and i.name
                and i.longitude is not None
                and i.latitude is not None
            ):
                # 检查是否已存在具有相同名称、经纬度的建筑点
                existing_building_point = (
                    db.query(BuildingPointModels)
                    .filter(
                        and_(
                            BuildingPointModels.name == i.name,
                            BuildingPointModels.longitude == i.longitude,
                            BuildingPointModels.latitude == i.latitude,
                        )
                    )
                    .first()
                )

                if existing_building_point:
                    building_point_id = existing_building_point.id
                else:
                    # 创建新的建筑点
                    new_building_point = BuildingPointModels(
                        name=i.name,
                        longitude=i.longitude,
                        latitude=i.latitude,
                    )
                    db.add(new_building_point)
                    db.flush()  # 获取新建筑点的 ID
                    building_point_id = new_building_point.id

            feature = FeatureModel(
                name=i.name,
                pixel_x=i.x,
                pixel_y=i.y,
                image_id=i.image_id,
                building_point_id=building_point_id,
            )
            db.add(feature)
        db.commit()

        return JSONResponse(content={"message": "特征点上传成功"})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"上传特征点时发生错误: {str(e)}")


@api.post("/upload_building_points")
async def upload_building_points(
    request: Request, data: BuildingPointsUpload, db: Session = Depends(get_db)
):
    try:
        created_count = 0
        existing_count = 0

        for point_data in data.points:
            # 检查是否已存在具有相同名称、经纬度的建筑点
            existing_building_point = (
                db.query(BuildingPointModels)
                .filter(
                    and_(
                        BuildingPointModels.name == point_data.name,
                        BuildingPointModels.longitude == point_data.longitude,
                        BuildingPointModels.latitude == point_data.latitude,
                    )
                )
                .first()
            )

            if existing_building_point:
                existing_count += 1
            else:
                # 创建新的建筑点
                new_building_point = BuildingPointModels(
                    name=point_data.name,
                    longitude=point_data.longitude,
                    latitude=point_data.latitude,
                )
                db.add(new_building_point)
                created_count += 1

        db.commit()

        return JSONResponse(
            content={
                "message": f"成功上传 {created_count} 个新建筑点，{existing_count} 个建筑点已存在"
            }
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"上传建筑点时发生错误: {str(e)}")


@api.delete("/images/{image_id}/features")
async def delete_features_for_image(image_id: int, db: Session = Depends(get_db)):
    try:
        # 检查图片是否存在
        image = db.query(ImagesModel).filter(ImagesModel.id == image_id).first()
        if not image:
            raise HTTPException(status_code=404, detail="图片不存在")

        # 删除该图片的所有特征点
        deleted_count = (
            db.query(FeatureModel).filter(FeatureModel.image_id == image_id).delete()
        )
        db.commit()

        return JSONResponse(content={"message": f"成功删除 {deleted_count} 个特征点"})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除特征点时发生错误: {str(e)}")


@api.get("/images")
async def get_images(db: Session = Depends(get_db)):
    """获取所有图片列表"""
    try:
        images = db.query(ImagesModel).all()
        return [
            {
                "id": img.id,
                "name": img.name,
                "path": img.path,
            }
            for img in images
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api.get("/images/{image_id}")
async def get_image(image_id: int, db: Session = Depends(get_db)):
    """获取图片信息"""
    try:
        image = db.query(ImagesModel).filter(ImagesModel.id == image_id).first()
        if not image:
            raise HTTPException(status_code=404, detail="图片未找到")

        return {
            "id": image.id,
            "name": image.name,
            "path": image.path,  # 返回相对路径给前端
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api.get("/images/{image_id}/features")
async def get_image_features(image_id: int, db: Session = Depends(get_db)):
    """获取图片的标注信息"""
    try:
        image = db.query(ImagesModel).filter(ImagesModel.id == image_id).first()
        if not image:
            raise HTTPException(status_code=404, detail="图片未找到")

        features = (
            db.query(FeatureModel).filter(FeatureModel.image_id == image_id).all()
        )
        return [
            {
                "id": f.id,
                "name": f.name,
                "pixel_x": f.pixel_x,
                "pixel_y": f.pixel_y,
                "longitude": f.building_point.longitude if f.building_point else None,
                "latitude": f.building_point.latitude if f.building_point else None,
            }
            for f in features
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api.post("/upload_image")
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

    # 保存到数据库，使用相对路径
    relative_path = f"/static/uploaded_images/{unique_filename}"
    image_model = ImagesModel(name=image.filename, path=relative_path)
    db.add(image_model)
    db.commit()
    db.refresh(image_model)

    return {"status": "success", "filename": unique_filename, "path": relative_path}


@api.post("/calculate_camera_position")
async def calculate_camera_position_endpoint(
    image_id: int = Form(...), db: Session = Depends(get_db)
):
    """
    计算相机位置
    """
    try:
        # 获取图片信息
        image = db.query(ImagesModel).filter(ImagesModel.id == image_id).first()
        if not image:
            raise HTTPException(status_code=404, detail="图片未找到")

        # 获取图片特征点
        features = load_features_from_orm(image_id, db)
        if not features:
            raise HTTPException(status_code=400, detail="图片没有特征点")

        # 获取DEM文件路径和特征点文件路径
        dem = load_dem_data(dem_file_path="./service/recycle/DEM1.tif")

        points = load_points_data_from_orm(features, dem)

        camera_position = calculate(points)

        db.query(ImagesModel).filter(ImagesModel.id == image_id).update(
            {"calculated_camera_locations": str(camera_position)}
        )
        db.commit()

        return JSONResponse(
            content={
                "status": "success",
                "camera_position": camera_position,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计算相机位置时发生错误: {str(e)}")
