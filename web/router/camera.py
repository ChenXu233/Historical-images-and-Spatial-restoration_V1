from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse

from model.images import Images as ImagesModel
from database import get_db

from service.recycle.main import EPNP_calculate
from service.recycle.utils import (
    load_dem_data,
    load_features_from_orm,
    load_points_data_from_orm,
)
from .api import api


@api.post("/calculate_camera_position")
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
