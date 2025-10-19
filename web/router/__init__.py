from fastapi import FastAPI
from fastapi import FastAPI
from .api import api


def init_router(app: FastAPI):
    """初始化路由
    Args:
        app (FastAPI): 应用实例
    Returns:
        FastAPI: 应用实例
    """

    app.include_router(api)
    return app
