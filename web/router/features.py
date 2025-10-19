from fastapi import APIRouter, Depends, HTTPException
from fastapi.requests import Request
from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi.responses import JSONResponse
import numpy as np

from model.feature import Feature as FeatureModel
from model.building_point import BuildingPoint as BuildingPointModels
from model.images import Images as ImagesModel
from model.camera_param import CameraParam
from schema.features import UploadFeatures
from database import get_db

from service.recycle.main import EPNP_calculate
from service.recycle.utils import (
    load_dem_data,
    load_features_from_orm,
    load_points_data_from_orm,
)

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

        # 删除之前的相机参数
        db.query(CameraParam).filter(CameraParam.image_id == image.id).delete()

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

        # 只有当特征点数量大于等于4时才计算相机位置
        if len(features.features) >= 4:
            try:
                # 获取图片特征点
                loaded_features = load_features_from_orm(image.id, db)
                if not loaded_features:
                    return JSONResponse(
                        content={"message": "特征点上传成功，但未找到特征点数据"}
                    )

                # 获取DEM文件路径和特征点文件路径
                dem = load_dem_data(dem_file_path="./service/recycle/DEM1.tif")

                points = load_points_data_from_orm(loaded_features, dem)

                (
                    camera_position,
                    focal_length,
                    sensor_size,
                    reprojection_error,
                    params,
                ) = EPNP_calculate(points)

                # 更新相机位置
                db.query(ImagesModel).filter(ImagesModel.id == image.id).update(
                    {"calculated_camera_locations": str(camera_position)}
                )

                # 保存相机参数到数据库
                # 转换numpy数组为字典格式以便存储
                # 处理相机内参矩阵K
                if "K" in params and hasattr(params["K"], "tolist"):
                    camera_matrix_dict = {
                        "data": params["K"].tolist(),
                        "shape": params["K"].shape,
                        "dtype": str(params["K"].dtype),
                    }
                else:
                    camera_matrix_dict = {
                        "data": [],
                        "shape": (0, 0),
                        "dtype": "unknown",
                    }

                # 处理旋转矩阵R
                rotation_matrix_dict = None
                if "R" in params and hasattr(params["R"], "tolist"):
                    rotation_matrix_dict = {
                        "data": params["R"].tolist(),
                        "shape": params["R"].shape,
                        "dtype": str(params["R"].dtype),
                    }

                # 处理畸变系数dist_coeffs
                dist_coeffs_dict = None
                if "dist_coeffs" in params and hasattr(params["dist_coeffs"], "tolist"):
                    dist_coeffs_dict = {
                        "data": params["dist_coeffs"].tolist(),
                        "shape": params["dist_coeffs"].shape,
                        "dtype": str(params["dist_coeffs"].dtype),
                    }

                # 处理优化后的旋转向量optimized_rotation_vector
                optimized_rotation_vector_dict = None
                if "optimized_rotation_vector" in params and hasattr(
                    params["optimized_rotation_vector"], "tolist"
                ):
                    optimized_rotation_vector_dict = {
                        "data": params["optimized_rotation_vector"].tolist(),
                        "shape": params["optimized_rotation_vector"].shape,
                        "dtype": str(params["optimized_rotation_vector"].dtype),
                    }

                # 处理优化后的平移向量optimized_translation_vector
                optimized_translation_vector_dict = None
                if "optimized_translation_vector" in params and hasattr(
                    params["optimized_translation_vector"], "tolist"
                ):
                    optimized_translation_vector_dict = {
                        "data": params["optimized_translation_vector"].tolist(),
                        "shape": params["optimized_translation_vector"].shape,
                        "dtype": str(params["optimized_translation_vector"].dtype),
                    }

                # 创建相机参数记录
                camera_param = CameraParam(
                    image_id=image.id,
                    focal_length=focal_length,
                    sensor_width=sensor_size[0],
                    sensor_height=sensor_size[1],
                    reprojection_error=reprojection_error,
                    camera_matrix=camera_matrix_dict,
                    rotation_matrix=rotation_matrix_dict,
                    dist_coeffs=dist_coeffs_dict,
                    optimized_rotation_vector=optimized_rotation_vector_dict,
                    optimized_translation_vector=optimized_translation_vector_dict,
                )

                db.add(camera_param)
                db.commit()

                return JSONResponse(
                    content={
                        "status": "success",
                        "message": f"""特征点上传成功且相机位置计算完成，相机参数如下：焦距：{focal_length} mm，传感器尺寸：{sensor_size[0]} x {sensor_size[1]} mm，重投影误差：{reprojection_error} px,相机原点：{camera_position}
""",
                    }
                )
            except Exception as calc_error:
                db.rollback()
                # 即使相机位置计算失败，特征点上传还是成功的
                return JSONResponse(
                    content={
                        "status": "partial_success",
                        "message": f"特征点上传成功，但相机位置计算失败: {str(calc_error)}",
                    }
                )
        else:
            return JSONResponse(
                content={
                    "message": "特征点上传成功，但特征点数量不足4个，不进行相机位置计算"
                }
            )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"上传特征点时发生错误: {str(e)}")
