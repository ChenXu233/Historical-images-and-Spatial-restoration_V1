from typing import List, Tuple
from fastapi import APIRouter, Depends, HTTPException, Form, Body
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
import numpy as np

from model.images import Images as ImagesModel
from model.camera_param import CameraParam
from database import get_db
from pydantic import BaseModel
from service.recycle.main import reprojection_point
from service.recycle.utils import (
    load_dem_data,
    load_features_from_orm,
    load_points_data_from_orm,
    pixel_to_geo,
    geo_transformer,
    get_dem_elevation,
)

api = APIRouter(prefix="/api", tags=["camera"])


class Position(BaseModel):
    longitude: float
    latitude: float


@api.post("/calculate_geo_to_pixel/{image_id}")
async def get_calculate_geo_to_pixel(
    image_id: int,
    points_position: List[Position] = Body(...),
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

    point_highs = [
        get_dem_elevation(
            dem,
            [position.longitude, position.latitude],
            coord_type="wgs84",
        )
        for position in points_position
    ]
    position = [
        geo_transformer.wgs84_to_utm(position.longitude, position.latitude)
        for position in points_position
    ]
    pos3d = np.array(
        [
            [easting, northing, high]
            for (easting, northing), high in zip(position, point_highs)
        ],
        dtype=np.float64,
    ).reshape(-1, 3)

    pixels = reprojection_point(
        pos3d,
        np.array(camera_param.camera_matrix["data"], dtype=np.float64),
        np.array(camera_param.dist_coeffs["data"], dtype=np.float64),
        np.array(camera_param.optimized_rotation_vector["data"], dtype=np.float64),
        np.array(camera_param.optimized_translation_vector["data"], dtype=np.float64),
    )

    return JSONResponse(content={"status": "success", "pixel": pixels})


@api.post("/calculate_pixel_to_geo/{image_id}")
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

    if not image.calculated_camera_locations:
        raise HTTPException(status_code=400, detail="图片没有相机位置")

    camera_location = eval(image.calculated_camera_locations)
    utm = geo_transformer.wgs84_to_utm(camera_location[0], camera_location[1])
    camera_location = [utm[0], utm[1], camera_location[2]]

    geo_point, steps = pixel_to_geo(
        pixels,
        np.array(camera_param.camera_matrix["data"], dtype=np.float64),
        np.array(camera_param.rotation_matrix["data"], dtype=np.float64),
        np.array(camera_location, dtype=np.float64),
        dem,
        control_points,
    )
    geo_point = geo_transformer.utm_to_wgs84(float(geo_point[0]), float(geo_point[1]))

    return JSONResponse(content={"status": "success", "geo": geo_point})
