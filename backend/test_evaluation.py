
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Interview, Message
from app.services.evaluation_service import generate_evaluation


def test_evaluation():

    # 第一步：选择要评估的面试
    interview_id = 2

    # 第二步：连接数据库
    db = SessionLocal()

    try:
        # 查询面试信息
        interview = db.get(Interview, interview_id)

        if interview is None:
            print("面试不存在")
            return

        print("面试岗位：", interview.position)
        print("面试难度：", interview.difficulty)

        # 第三步：查询完整历史消息
        stmt = (
            select(Message)
            .where(Message.interview_id == interview_id)
            .order_by(Message.id.asc())
        )

        messages = db.scalars(stmt).all()

        # 转换为 AI 评估函数需要的格式
        history = [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in messages
        ]

    finally:
        # 查询结束后关闭数据库连接
        db.close()

    print("历史消息数量：", len(history))

    # 第四步：调用 DeepSeek
    print("正在调用 DeepSeek 生成评估报告...")

    report = generate_evaluation(
        position=interview.position,
        difficulty=interview.difficulty,
        history=history
    )

    # 第五步：输出评估结果
    print("\n===== AI 面试评估报告 =====")

    print(
        report.model_dump_json(indent=2)
    )


if __name__ == "__main__":
    test_evaluation()