from re import A
from fastapi import APIRouter, Depends, HTTPException
from fastapi.requests import Request
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List
from fastapi.responses import JSONResponse

from model.building_point import BuildingPoint as BuildingPointModels
from model.feature import Feature as FeatureModel
from schema.building_point import BuildingPoint
from database import get_db
from .api import api


class BuildingPointData:
    name: str
    longitude: float
    latitude: float


class BuildingPointsUpload:
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


@api.put("/building_points/{point_id}")
async def update_building_point(
    point_id: int, building_point: BuildingPoint, db: Session = Depends(get_db)
):
    """
    更新建筑点信息
    """
    try:
        # 检查建筑点是否存在
        existing_point = (
            db.query(BuildingPointModels)
            .filter(BuildingPointModels.id == point_id)
            .first()
        )
        if not existing_point:
            raise HTTPException(status_code=404, detail="建筑点不存在")

        # 检查是否已存在具有相同名称、经纬度的建筑点
        duplicate_point = (
            db.query(BuildingPointModels)
            .filter(
                and_(
                    BuildingPointModels.name == building_point.name,
                    BuildingPointModels.longitude == building_point.longitude,
                    BuildingPointModels.latitude == building_point.latitude,
                    BuildingPointModels.id != point_id,
                )
            )
            .first()
        )

        if duplicate_point:
            raise HTTPException(
                status_code=400, detail="已存在具有相同名称和坐标的建筑点"
            )

        # 更新建筑点信息
        existing_point.name = building_point.name
        existing_point.latitude = building_point.latitude
        existing_point.longitude = building_point.longitude

        db.commit()
        db.refresh(existing_point)

        return JSONResponse(
            content={
                "status": "success",
                "message": "建筑点更新成功",
                "data": {
                    "id": existing_point.id,
                    "name": existing_point.name,
                    "latitude": existing_point.latitude,
                    "longitude": existing_point.longitude,
                },
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新建筑点时发生错误: {str(e)}")


@api.delete("/building_points/{point_id}")
async def delete_building_point(point_id: int, db: Session = Depends(get_db)):
    """
    删除建筑点及其相关特征点
    """
    try:
        # 检查建筑点是否存在
        existing_point = (
            db.query(BuildingPointModels)
            .filter(BuildingPointModels.id == point_id)
            .first()
        )
        if not existing_point:
            raise HTTPException(status_code=404, detail="建筑点不存在")

        # 删除与该建筑点相关的所有特征点
        db.query(FeatureModel).filter(
            FeatureModel.building_point_id == point_id
        ).delete()

        # 删除建筑点
        db.delete(existing_point)
        db.commit()

        return JSONResponse(content={"status": "success", "message": "建筑点删除成功"})
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除建筑点时发生错误: {str(e)}")
