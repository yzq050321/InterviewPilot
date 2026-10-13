
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Interview, Message, Evaluation
from app.services.evaluation_service import generate_evaluation


def test_save_evaluation():
    interview_id = 2

    # 第一步：查询面试与历史消息
    with SessionLocal() as db:
        interview = db.get(Interview, interview_id)

        if interview is None:
            print("面试不存在")
            return

        position = interview.position
        difficulty = interview.difficulty

        # 检查是否已经存在评估报告
        existing = db.scalar(
            select(Evaluation).where(
                Evaluation.interview_id == interview_id
            )
        )

        if existing is not None:
            print("该面试已有评估报告，无需重复生成")
            return

        stmt = (
            select(Message)
            .where(Message.interview_id == interview_id)
            .order_by(Message.id.asc())
        )

        messages = db.scalars(stmt).all()

        history = [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in messages
        ]

    if not any(item["role"] == "user" for item in history):
        print("没有用户回答，无法生成评估报告")
        return

    # 第二步：调用 DeepSeek
    print("正在生成 AI 评估报告...")

    report = generate_evaluation(
        position=position,
        difficulty=difficulty,
        history=history
    )

    print("AI 评估报告生成成功！")

    # 第三步：保存报告到 MySQL
    with SessionLocal() as db:
        evaluation = Evaluation(
            interview_id=interview_id,
            technical_score=report.technical_score,
            completeness_score=report.completeness_score,
            clarity_score=report.clarity_score,
            overall_score=report.overall_score,
            summary=report.summary,
            strengths=report.strengths,
            weaknesses=report.weaknesses,
            suggestions=report.suggestions
        )

        try:
            db.add(evaluation)
            db.commit()
            db.refresh(evaluation)

            print("评估报告保存成功！")
            print("报告 ID：", evaluation.id)
            print("面试 ID：", evaluation.interview_id)
            print("综合评分：", evaluation.overall_score)

        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    test_save_evaluation()