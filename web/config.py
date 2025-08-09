from pathlib import Path

from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    DEBUG: bool = False
    PORT: int = 8080
    LOG_PATH: Path = Path("./logs")
    APP_NAME: str = "宝石检测"

    class Config:
        env_file = ".env"  # 指定 .env 文件路径
        env_file_encoding = "utf-8"  # 指定文件编码
        extra = "allow"
