from pathlib import Path

from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    DEBUG: bool = False
    PORT: int = 8081
    LOG_PATH: Path = Path("./logs")
    APP_NAME: str = "宝石检测"
    DATABASE_URI: str = "sqlite:///./test.db"  # 示例数据库URI

    class Config:
        env_file = ".env"  # 指定 .env 文件路径
        env_file_encoding = "utf-8"  # 指定文件编码
        extra = "allow"


CONFIG = AppConfig()  # type: ignore
print(f"Loaded configuration: {CONFIG.model_dump()}")  # 打印配置项

# 示例：打印配置
if __name__ == "__main__":
    print(CONFIG.model_dump())
