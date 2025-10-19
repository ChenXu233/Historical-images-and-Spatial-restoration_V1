from fastapi import APIRouter, Depends, HTTPException
from fastapi.requests import Request
from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi.responses import JSONResponse

from model.feature import Feature as FeatureModel
from model.building_point import BuildingPoint as BuildingPointModels
from model.images import Images as ImagesModel
from schema.features import UploadFeatures
from database import get_db
from .api import api


@api.post("/upload_features")
async def upload_features(
    request: Request,
    features: UploadFeatures,
    db: Session = Depends(get_db),
):
    try:
        image = (
            db.query(ImagesModel)
            .filter(ImagesModel.id == features.features[0].image_id)
            .first()
        )
        if not image:
            raise HTTPException(status_code=404, detail="图片不存在")

        for i in features.features:
            # 检查是否已存在具有相同像素坐标和图片ID的特征点
            existing_feature = (
                db.query(FeatureModel)
                .filter(
                    and_(
                        FeatureModel.pixel_x == i.x,
                        FeatureModel.pixel_y == i.y,
                        FeatureModel.image_id == i.image_id,
                    )
                )
                .first()
            )
            if existing_feature:
                continue

            if i.name and i.longitude and i.latitude:
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


@api.delete("/images/{image_id}/features/{feature_id}")
async def delete_feature(image_id: int, feature_id: int, db: Session = Depends(get_db)):
    try:
        # 检查图片是否存在
        image = db.query(ImagesModel).filter(ImagesModel.id == image_id).first()
        if not image:
            raise HTTPException(status_code=404, detail="图片不存在")

        # 删除该图片的指定特征点
        feature = (
            db.query(FeatureModel)
            .filter(FeatureModel.id == feature_id, FeatureModel.image_id == image_id)
            .first()
        )
        if not feature:
            raise HTTPException(status_code=404, detail="特征点不存在")

        # 删除特征点
        db.delete(feature)
        db.commit()

        return JSONResponse(content={"message": "特征点删除成功"})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除特征点时发生错误: {str(e)}")
