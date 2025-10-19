from typing import List, Tuple
from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
import numpy as np

from model.images import Images as ImagesModel
from model.camera_param import CameraParam
from database import get_db

from service.recycle.main import reprojection_point
from service.recycle.utils import (
    load_dem_data,
    load_features_from_orm,
    load_points_data_from_orm,
    pixel_to_geo,
)

api = APIRouter(prefix="/api", tags=["camera"])


@api.post("/calculate_geo_to_pixel/{image_id}")
async def get_calculate_geo_to_pixel(
    image_id: int,
    points_position: List[List[float]],
    db: Session = Depends(get_db),
):
    image = db.query(ImagesModel).filter(ImagesModel.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="图片未找到")

    camera_param = (
        db.query(CameraParam).filter(CameraParam.image_id == image_id).first()
    )
    if not camera_param:
        raise HTTPException(status_code=404, detail="相机参数未找到")

    dem = load_dem_data(dem_file_path="./service/recycle/DEM1.tif")

    points = load_points_data_from_orm(load_features_from_orm(image_id, db), dem)
    if not points:
        raise HTTPException(status_code=400, detail="图片没有特征点")

    pixels = reprojection_point(
        np.array(points_position, dtype=np.float64).reshape(-1, 3),
        np.array(camera_param.camera_matrix["data"], dtype=np.float64),
        np.array(camera_param.dist_coeffs["data"], dtype=np.float64),
        np.array(camera_param.optimized_rotation_vector["data"], dtype=np.float64),
        np.array(camera_param.optimized_translation_vector["data"], dtype=np.float64),
    )

    return JSONResponse(content={"status": "success", "pixel": pixels})


@api.get("/calculate_pixel_to_geo/{image_id}")
async def get_calculate_pixel_to_geo(
    image_id: int, pixels: Tuple[float, float], db: Session = Depends(get_db)
):
    image = db.query(ImagesModel).filter(ImagesModel.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="图片未找到")

    camera_param = (
        db.query(CameraParam).filter(CameraParam.image_id == image_id).first()
    )
    if not camera_param:
        raise HTTPException(status_code=404, detail="相机参数未找到")

    dem = load_dem_data(dem_file_path="./service/recycle/DEM1.tif")

    points = load_points_data_from_orm(load_features_from_orm(image_id, db), dem)
    if not points:
        raise HTTPException(status_code=400, detail="图片没有特征点")

    control_points = [
        {
            "pixel": point.pixel,
            "pos3d": point.pos3d,
            "symbol": point.symbol,
        }
        for point in points
    ]

    geo_point = pixel_to_geo(
        pixels,
        np.array(camera_param.camera_matrix["data"], dtype=np.float64),
        np.array(camera_param.rotation_matrix["data"], dtype=np.float64),
        List[image.calculated_camera_locations],
        dem,
        control_points,
    )

    return JSONResponse(content={"status": "success", "geo": geo_point})
