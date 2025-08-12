from fastapi import FastAPI, staticfiles
from fastapi.requests import Request
from fastapi.responses import RedirectResponse

from pathlib import Path

from router import init_router
from database import init_db


def create_app() -> FastAPI:
    app = FastAPI()

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
