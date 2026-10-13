
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# 加载 .env 配置
load_dotenv()

# 检查数据库密码是否存在
password = os.getenv("DB_PASSWORD")

if not password:
    raise ValueError("请先在 .env 中配置 DB_PASSWORD")

# 构建数据库连接地址
# URL.create 可以正确处理密码中的特殊字符
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
    pool_pre_ping=True
)

# 测试连接
try:
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT DATABASE(), VERSION()")
        )

        database_name, version = result.one()

        print("数据库连接成功！")
        print("当前数据库：", database_name)
        print("MySQL 版本：", version)

except Exception as e:
    print("数据库连接失败：")
    print(type(e).__name__)
    # 避免直接打印可能包含敏感信息的异常详情