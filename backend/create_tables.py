
from app.database import Base, engine
from app.models import Interview, Message, Evaluation

# 导入模型，让 SQLAlchemy 注册表结构
#from app import models

# 根据 ORM 模型创建数据表
Base.metadata.create_all(bind=engine)

print("数据库表创建完成！")