
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Interview, Message


def test_create_and_read():
    # 创建数据库会话
    with SessionLocal() as db:
        try:
            # 1. 创建一场面试
            interview = Interview(
                position="Java后端开发实习生",
                difficulty="中等",
                status="in_progress"
            )

            db.add(interview)

            # 将 INSERT 发送给数据库
            # 并获取数据库生成的 ID
            db.flush()

            interview_id = interview.id

            print("创建面试，ID：", interview_id)

            # 2. 创建一条 AI 面试问题
            message = Message(
                interview_id=interview_id,
                role="assistant",
                content="请解释 Java 中 HashMap 的工作原理。"
            )

            db.add(message)

            # 提交事务
            db.commit()

            print("面试和消息保存成功！")

            # 3. 查询刚刚创建的面试
            stmt = select(Interview).where(
                Interview.id == interview_id
            )

            saved_interview = db.scalar(stmt)

            if saved_interview is None:
                raise ValueError("未找到刚创建的面试")

            print("查询到面试：", saved_interview.position)

            # 4. 查询这场面试的所有消息
            stmt = select(Message).where(
                Message.interview_id == interview_id
            ).order_by(Message.id)

            messages = db.scalars(stmt).all()

            for msg in messages:
                print("角色：", msg.role)
                print("内容：", msg.content)

        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    test_create_and_read()