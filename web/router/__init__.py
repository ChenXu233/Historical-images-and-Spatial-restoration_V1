from fastapi import FastAPI

from router.dotting_view import dotting_router


def init_router(app: FastAPI):
    app.include_router(dotting_router)

    return app
