
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# 加载环境变量
load_dotenv()

password = os.getenv("DB_PASSWORD")

if not password:
    raise ValueError("未配置 DB_PASSWORD")

# 创建数据库连接地址
database_url = URL.create(
    drivername="mysql+pymysql",
    username=os.getenv("DB_USER", "interview_app"),
    password=password,
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", "3306")),
    database=os.getenv("DB_NAME", "interview_pilot"),
)

# 创建数据库引擎
engine = create_engine(
    database_url,
    pool_pre_ping=True,
    echo=False
)

# 创建 Session 工厂
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False
)

# ORM 模型的基类
class Base(DeclarativeBase):
    pass


# 为 FastAPI 提供数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()