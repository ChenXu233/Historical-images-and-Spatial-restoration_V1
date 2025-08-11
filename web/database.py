from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from typing import Generator


from config import CONFIG

# 声明基类（用于模型继承）
Base = declarative_base()

# 创建同步数据库引擎
engine: Engine = create_engine(
    CONFIG.DATABASE_URI,
    pool_size=10,  # 连接池初始大小
    max_overflow=20,  # 连接池最大溢出连接数
    pool_timeout=30,  # 连接池超时时间（秒）
    pool_recycle=3600,  # 连接回收时间（秒，避免长连接问题）
    pool_pre_ping=True,  # 预检查连接有效性
    echo=CONFIG.DEBUG,  # 调试模式输出SQL日志
)

# 创建会话工厂（用于生成数据库会话）
SessionLocal = sessionmaker(
    autocommit=False,  # 自动提交关闭（手动控制事务）
    autoflush=False,  # 自动刷新关闭（手动控制刷新）
    bind=engine,  # 绑定数据库引擎
)


# 依赖函数：获取数据库会话（常用于FastAPI路由）
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 创建所有表结构（建议在应用启动时执行一次）
def init_db():
    """初始化数据库"""
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully.")
