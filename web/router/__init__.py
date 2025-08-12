from fastapi import FastAPI
from matplotlib.pylab import f

from router.dotting_view import dotting_router
from router.upload import upload


def init_router(app: FastAPI):
    """初始化路由
    Args:
        app (FastAPI): 应用实例
    Returns:
        FastAPI: 应用实例
    """

    app.include_router(dotting_router)
    app.include_router(upload)
    return app
