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

api = APIRouter(prefix="/api", tags=["features"])


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

        # 删除之前的特征点
        db.query(FeatureModel).filter(FeatureModel.image_id == image.id).delete()

        image.features = []

        for feature in features.features:
            feature_model = FeatureModel(
                pixel_x=feature.x,
                pixel_y=feature.y,
                image_id=image.id,
                building_point_id=feature.building_point_id,
            )
            db.add(feature_model)
        db.commit()

        return JSONResponse(content={"message": "特征点上传成功"})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"上传特征点时发生错误: {str(e)}")
