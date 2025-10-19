from fastapi import FastAPI
from .images import api as images_api
from .features import api as features_api
from .building_points import api as building_points_api
from .camera import api as camera_api


def init_router(app: FastAPI):
    """初始化路由
    Args:
        app (FastAPI): 应用实例
    Returns:
        FastAPI: 应用实例
    """

    app.include_router(images_api)
    app.include_router(features_api)
    app.include_router(building_points_api)
    app.include_router(camera_api)
    return app
