from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from pathlib import Path
import os
import uuid

from model.images import Images as ImagesModel
from model.feature import Feature as FeatureModel
from database import get_db

api = APIRouter(prefix="/api", tags=["images"])

# 创建上传目录
UPLOAD_DIR = Path(__file__).parent.parent / "static" / "uploaded_images"
UPLOAD_DIR.mkdir(exist_ok=True)


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
async def upload_image(image: UploadFile = File(...), db: Session = Depends(get_db)):
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


@api.delete("/images/{image_id}")
async def delete_image(image_id: int, db: Session = Depends(get_db)):
    """
    删除图片及其相关数据
    """
    try:
        # 获取图片信息
        image = db.query(ImagesModel).filter(ImagesModel.id == image_id).first()
        if not image:
            raise HTTPException(status_code=404, detail="图片未找到")

        # 删除图片相关的特征点
        db.query(FeatureModel).filter(FeatureModel.image_id == image_id).delete()

        # 删除图片文件
        file_path = (
            Path(__file__).parent.parent
            / "static"
            / "uploaded_images"
            / Path(image.path).name
        )
        if file_path.exists():
            try:
                os.remove(file_path)
            except Exception as e:
                # 文件删除失败，记录日志但继续执行
                print(f"删除图片文件时出错: {str(e)}")

        # 从数据库中删除图片记录
        db.delete(image)
        db.commit()

        return JSONResponse(content={"message": "图片删除成功"})
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除图片时发生错误: {str(e)}")
