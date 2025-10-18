from fastapi import FastAPI, staticfiles
from fastapi.requests import Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from pathlib import Path

from router import init_router
from database import init_db


def create_app() -> FastAPI:
    app = FastAPI()

    # 添加CORS中间件以允许跨域请求
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 允许所有来源
        allow_credentials=True,
        allow_methods=["*"],  # 允许所有HTTP方法
        allow_headers=["*"],  # 允许所有HTTP头
    )

    init_db()

    @app.get("/")
    async def read_root(request: Request):
        return RedirectResponse(request.url_for("dotting"))

    app = init_router(app)

    app.mount(
        "/static",
        staticfiles.StaticFiles(directory=Path(__file__).parent / "static"),
        name="static",
    )

    return app
