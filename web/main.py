from uvicorn import run
from config import CONFIG
from app import create_app

app = create_app()

if __name__ == "__main__":
    if CONFIG.DEBUG:
        run(
            app,
            host="127.0.0.1",
            port=CONFIG.PORT,
        )
    else:
        run(
            app,
            host="0.0.0.0",
            port=CONFIG.PORT,
        )
