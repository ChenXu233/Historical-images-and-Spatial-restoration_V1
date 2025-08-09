from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI()

    @app.get("/")
    async def read_root():
        return {"message": "Hello, World!"}

    return app
