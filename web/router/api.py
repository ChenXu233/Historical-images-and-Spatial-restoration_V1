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

from service.recycle.main import EPNP_calculate
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
                "name": f.building_point.name,
                "pixel_x": f.pixel_x,
                "pixel_y": f.pixel_y,
                "longitude": f.building_point.longitude,
                "latitude": f.building_point.latitude,
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


@api.post("/calculate_camera_position/{image_id}")
async def calculate_camera_position(
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

        camera_position, focal_length, sensor_size, reprojection_error = EPNP_calculate(
            points
        )

        db.query(ImagesModel).filter(ImagesModel.id == image_id).update(
            {"calculated_camera_locations": str(camera_position)}
        )
        db.commit()

        return JSONResponse(
            content={
                "status": "success",
                "camera_position": camera_position,
                "message": f"""最优解：
焦距：{focal_length} mm，
传感器尺寸：{sensor_size[0]} x {sensor_size[1]} mm，
重投影误差：{reprojection_error} px
相机原点：{camera_position}
""",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计算相机位置时发生错误: {str(e)}")


# @api.post("/calculate_building_positions/{building_point_id}/{image_id}")
# async def calculate_building_positions(
#     building_point_id: int = Form(...),
#     image_id: int = Form(...),
#     db: Session = Depends(get_db),
# ):
#     """
#     计算建筑点位置,使用重投影误差最小的相机参数，进行重投影计算
#     """
#     try:
#         # 获取图片信息
#         image = db.query(ImagesModel).filter(ImagesModel.id == image_id).first()
#         if not image:
#             raise HTTPException(status_code=404, detail="图片未找到")

#         # 获取建筑点信息
#         building_point = (
#             db.query(BuildingPointModels)
#             .filter(BuildingPointModels.id == building_point_id)
#             .first()
#         )
#         if not building_point:
#             raise HTTPException(status_code=404, detail="建筑点未找到")

#         # 获取图片特征点
#         features = load_features_from_orm(image_id, db)

#         if not features:
#             raise HTTPException(status_code=400, detail="图片没有特征点")

#         # 获取DEM文件路径和特征点文件路径
#         dem = load_dem_data(dem_file_path="./service/recycle/DEM1.tif")

#         points = load_points_data_from_orm(features, dem)

#         # 使用EPNP算法计算相机位置和参数
#         camera_position, focal_length, sensor_size, reprojection_error = EPNP_calculate(
#             points
#         )

#         # 计算建筑点的重投影位置
#         # 1. 获取建筑点的经纬度和高程
#         building_lon = building_point.longitude
#         building_lat = building_point.latitude
#         building_elev = get_dem_elevation(
#             dem, (building_lon, building_lat), coord_type="wgs84"
#         )

#         # 2. 将建筑点从WGS84转换到UTM坐标系
#         building_easting, building_northing = geo_transformer.wgs84_to_utm(
#             building_lon, building_lat
#         )
#         building_utm = np.array([building_easting, building_northing, building_elev])

#         # 3. 从EPNP结果中获取相机在UTM坐标系的位置
#         camera_lon, camera_lat, camera_elev = camera_position
#         camera_easting, camera_northing = geo_transformer.wgs84_to_utm(
#             camera_lon, camera_lat
#         )
#         camera_origin = np.array([camera_easting, camera_northing, camera_elev])

#         # 4. 构建相机内参矩阵K
#         # 从points中获取图像尺寸
#         if len(points) > 0:
#             image_width = max(pixel.pixel[0] for pixel in points)
#             image_height = max(pixel.pixel[1] for pixel in points)
#         else:
#             image_width, image_height = 1920, 1080

#         # 计算像素大小
#         sensor_width, sensor_height = sensor_size
#         pixel_size_width = sensor_width / image_width
#         pixel_size_height = sensor_height / image_height

#         # 构建相机内参矩阵K
#         fx = focal_length / pixel_size_width
#         fy = focal_length / pixel_size_height
#         K = np.array(
#             [[fx, 0, image_width / 2], [0, fy, image_height / 2], [0, 0, 1]],
#             dtype=np.float32,
#         )

#         # 5. 计算旋转矩阵R
#         # 从EPNP结果中获取相机姿态参数
#         # 这里我们需要重新运行solvePnP获取旋转矩阵
#         pos3d = np.array([rec.pos3d for rec in points], dtype=np.float64).reshape(-1, 3)
#         pixels = np.array([rec.pixel for rec in points], dtype=np.float64).reshape(
#             -1, 2
#         )
#         dist_coeffs = np.zeros((4, 1), dtype=np.float64)

#         # 使用solvePnP获取旋转向量
#         success, rvec, tvec = cv2.solvePnP(
#             pos3d, pixels, K, dist_coeffs, flags=cv2.SOLVEPNP_EPNP
#         )
#         if success:
#             # 优化旋转向量和平移向量
#             rvec, tvec = cv2.solvePnPRefineLM(pos3d, pixels, K, dist_coeffs, rvec, tvec)

#             # 将旋转向量转换为旋转矩阵
#             R_matrix, _ = cv2.Rodrigues(rvec)

#             # 6. 计算建筑点在相机坐标系中的坐标
#             # 计算建筑点相对于相机的位置
#             relative_position = building_utm - camera_origin

#             # 将相对位置从UTM坐标系转换到相机坐标系
#             camera_coords = R_matrix @ relative_position

#             # 7. 投影到图像平面
#             projected = K @ camera_coords
#             projected /= projected[2]  # 归一化

#             pixel_x, pixel_y = projected[0], projected[1]

#             # 8. 记录结果到数据库
#             # 检查是否已存在该建筑点和图像的特征点
#             existing_feature = (
#                 db.query(FeatureModel)
#                 .filter(
#                     FeatureModel.building_point_id == building_point_id,
#                     FeatureModel.image_id == image_id,
#                 )
#                 .first()
#             )

#             if existing_feature:
#                 # 更新现有特征点
#                 existing_feature.pixel_x = pixel_x
#                 existing_feature.pixel_y = pixel_y
#             else:
#                 # 创建新的特征点
#                 new_feature = FeatureModel(
#                     pixel_x=pixel_x,
#                     pixel_y=pixel_y,
#                     image_id=image_id,
#                     building_point_id=building_point_id,
#                 )
#                 db.add(new_feature)

#             db.commit()

#             return JSONResponse(
#                 content={
#                     "status": "success",
#                     "message": "建筑点重投影位置计算成功",
#                     "building_point": {
#                         "id": building_point.id,
#                         "name": building_point.name,
#                         "longitude": building_point.longitude,
#                         "latitude": building_point.latitude,
#                     },
#                     "reprojected_position": {
#                         "pixel_x": float(pixel_x),
#                         "pixel_y": float(pixel_y),
#                     },
#                     "camera_params": {
#                         "focal_length": focal_length,
#                         "sensor_size": sensor_size,
#                         "reprojection_error": reprojection_error,
#                     },
#                 }
#             )
#         else:
#             raise HTTPException(status_code=500, detail="相机姿态计算失败")

#     except HTTPException:
#         raise
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(
#             status_code=500, detail=f"计算建筑点重投影位置时发生错误: {str(e)}"
#         )
