from fastapi import FastAPI, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Interview, Message, Evaluation
from app.services.llm_service import (
    generate_question,
    generate_followup,
    generate_followup_with_history
)
from app.database import SessionLocal
from app.services.evaluation_service import generate_evaluation
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal
import logging
from app.services.agent_service import (
    generate_followup_agent,
    generate_question_agent,
)

logger = logging.getLogger(__name__)
from openai import APITimeoutError

# 创建 FastAPI 应用
app = FastAPI(
    title="InterviewPilot API",
    version="1.0.0"
)


# 允许 React 前端访问 FastAPI 后端
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 根路径接口：访问 http://127.0.0.1:8000/
@app.get("/")
def home():
    return {
        "message": "Welcome to InterviewPilot API"
    }

# 健康检查接口：访问 /health
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "InterviewPilot backend is running!"
    }


# 定义创建面试时的数据格式
class InterviewCreate(BaseModel):

    # 岗位名称
    position: str = Field(min_length=1, max_length=100)

    # 面试难度
    difficulty: Literal["简单", "中等", "困难"]

    @field_validator("position")
    @classmethod
    def validate_position(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("岗位名称不能为空")

        return value

# 创建 AI 面试题接口
@app.post("/api/interviews")
async def create_interview(
    request: InterviewCreate,
    db: Session = Depends(get_db)
):
    # 1. 调用 DeepSeek 生成第一道面试题
    try:
        question = await run_in_threadpool(
            generate_question_agent,
            request.position,
            request.difficulty
        )

    except APITimeoutError:
        logger.exception("DeepSeek 生成面试题超时")

        raise HTTPException(
            status_code=504,
            detail="AI 服务响应超时，请稍后重试"
        )

    except Exception:
        logger.exception("创建面试时 AI 题目生成失败")

        raise HTTPException(
            status_code=502,
            detail="AI 面试题生成失败"
        )

    # 2. 创建面试记录并保存 AI 问题
    try:
        interview = Interview(
            position=request.position,
            difficulty=request.difficulty,
            status="in_progress"
        )

        db.add(interview)

        # 将 INSERT 发送给数据库，获取自增 ID
        db.flush()

        message = Message(
            interview_id=interview.id,
            role="assistant",
            content=question
        )

        db.add(message)

        # 提交事务，一起保存面试和问题
        db.commit()

        # 3. 返回创建结果
        return {
            "interview_id": interview.id,
            "position": interview.position,
            "difficulty": interview.difficulty,
            "question": question
        }

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="保存面试记录失败"
        )


# 定义用户提交回答的数据结构
class AnswerRequest(BaseModel):
    # 当前面试的 ID
    interview_id: int = Field(gt=0)

    # 用户对当前问题的回答
    answer: str = Field(min_length=1)

# AI 动态追问接口
@app.post("/api/interviews/followup")
async def interview_followup(
    request: AnswerRequest,
    db: Session = Depends(get_db)
):
    # 1. 查询当前面试
    interview = db.get(
        Interview,
        request.interview_id
    )

    if interview is None:
        raise HTTPException(
            status_code=404,
            detail="面试不存在"
        )

    if interview.status != "in_progress":
        raise HTTPException(
            status_code=400,
            detail="当前面试已结束"
        )

    # 2. 查询这场面试最近的一道 AI 问题
    stmt = (
        select(Message)
        .where(
            Message.interview_id == interview.id,
            Message.role == "assistant"
        )
        .order_by(Message.id.desc())
        .limit(1)
    )

    last_question = db.scalar(stmt)

    if last_question is None:
        raise HTTPException(
            status_code=400,
            detail="当前面试还没有问题"
        )


    # 3. 查询历史消息并调用 DeepSeek 生成追问
    try:
        # 查询当前面试的完整历史
        history_stmt = (
            select(Message)
            .where(Message.interview_id == interview.id)
            .order_by(Message.id.asc())
        )

        history_messages = db.scalars(history_stmt).all()

        # 转换为 LangChain 消息需要的数据结构
        history = [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in history_messages
        ]

        # 将用户本次回答加入上下文
        history.append({
            "role": "user",
            "content": request.answer
        })

        # 根据完整历史生成下一道追问
        next_question = await run_in_threadpool(
            generate_followup_agent,
            interview.position,
            interview.difficulty,
            history
        )

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="AI 追问生成失败"
        )
        


    # 4. 保存用户回答和 AI 追问
    try:
        user_message = Message(
            interview_id=interview.id,
            role="user",
            content=request.answer
        )

        ai_message = Message(
            interview_id=interview.id,
            role="assistant",
            content=next_question
        )

        db.add_all([
            user_message,
            ai_message
        ])

        # 同一事务提交两条消息
        db.commit()

        return {
            "interview_id": interview.id,
            "next_question": next_question
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="保存面试消息失败"
        )


@app.get("/api/interviews")
def list_interviews(
    db: Session = Depends(get_db)
):
    # 1. 查询所有历史面试
    interviews = (
        db.query(Interview)
        .order_by(
            Interview.created_at.desc(),
            Interview.id.desc()
        )
        .all()
    )

    # 2. 转换为 JSON 可序列化的数据
    result = []

    for interview in interviews:
        result.append({
            "interview_id": interview.id,
            "position": interview.position,
            "difficulty": interview.difficulty,
            "status": interview.status,
            "created_at": interview.created_at
        })

    # 3. 返回历史面试列表
    return result

@app.get("/api/interviews/{interview_id}")
def get_interview(
    interview_id: int,
    db: Session = Depends(get_db)
):
    # 1. 查询面试基本信息
    interview = db.get(Interview, interview_id)

    if interview is None:
        raise HTTPException(
            status_code=404,
            detail="面试不存在"
        )

    # 2. 查询这场面试的所有消息
    stmt = (
        select(Message)
        .where(Message.interview_id == interview_id)
        .order_by(Message.id.asc())
    )

    messages = db.scalars(stmt).all()

    # 3. 整理消息数据
    message_list = []

    for message in messages:
        message_list.append({
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at
        })

    # 4. 返回面试及其消息
    return {
        "interview_id": interview.id,
        "position": interview.position,
        "difficulty": interview.difficulty,
        "status": interview.status,
        "created_at": interview.created_at,
        "messages": message_list
    }


@app.patch("/api/interviews/{interview_id}/complete")
def complete_interview(
    interview_id: int,
    db: Session = Depends(get_db)
):
    # 1. 查询面试
    interview = db.get(Interview, interview_id)

    if interview is None:
        raise HTTPException(
            status_code=404,
            detail="面试不存在"
        )

    # 2. 检查面试是否已经结束
    if interview.status == "completed":
        raise HTTPException(
            status_code=400,
            detail="面试已经结束"
        )

    # 3. 修改面试状态
    interview.status = "completed"

    # 4. 提交数据库事务
    try:
        db.commit()
        return {
            "interview_id": interview.id,
            "status": "completed",
            "message": "面试已结束"
        }
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="更新面试状态失败"
        )



@app.get("/api/interviews/{interview_id}/evaluation")
def get_interview_evaluation(interview_id: int):

    # 第一步：创建数据库会话
    with SessionLocal() as db:

        # 第二步：根据面试 ID 查询报告
        evaluation = (
            db.query(Evaluation)
            .filter(
                Evaluation.interview_id == interview_id
            )
            .first()
        )

        # 第三步：如果没有报告，返回 404
        if evaluation is None:
            raise HTTPException(
                status_code=404,
                detail="评估报告不存在"
            )

        # 第四步：返回报告数据
        return {
            "id": evaluation.id,
            "interview_id": evaluation.interview_id,
            "technical_score": evaluation.technical_score,
            "completeness_score": evaluation.completeness_score,
            "clarity_score": evaluation.clarity_score,
            "overall_score": evaluation.overall_score,
            "summary": evaluation.summary,
            "strengths": evaluation.strengths,
            "weaknesses": evaluation.weaknesses,
            "suggestions": evaluation.suggestions,
            "created_at": evaluation.created_at
        }


@app.post("/api/interviews/{interview_id}/evaluation")
async def create_interview_evaluation(interview_id: int):

    # 第一步：查询面试
    with SessionLocal() as db:
        interview = db.get(Interview, interview_id)

        if interview is None:
            raise HTTPException(
                status_code=404,
                detail="面试不存在"
            )

        # 只有已结束的面试才能生成报告
        if interview.status != "completed":
            raise HTTPException(
                status_code=400,
                detail="请先结束面试，再生成评估报告"
            )

        # 检查是否已有评估报告
        existing = db.scalar(
            select(Evaluation).where(
                Evaluation.interview_id == interview_id
            )
        )

        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail="该面试已有评估报告"
            )

        # 读取面试历史
        messages = db.scalars(
            select(Message)
            .where(Message.interview_id == interview_id)
            .order_by(Message.id.asc())
        ).all()

        history = [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in messages
        ]

        position = interview.position
        difficulty = interview.difficulty

    # 第二步：检查是否有用户回答
    if not any(msg["role"] == "user" for msg in history):
        raise HTTPException(
            status_code=400,
            detail="面试没有用户回答，无法生成报告"
        )

    # 第三步：调用 AI
    try:
        report = await run_in_threadpool(
            generate_evaluation,
            position=position,
            difficulty=difficulty,
            history=history
        )
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="AI 评估生成失败，请稍后重试"
        )

    # 第四步：保存评估报告
    with SessionLocal() as db:

        # AI 调用期间可能已有其他请求生成报告
        existing = db.scalar(
            select(Evaluation).where(
                Evaluation.interview_id == interview_id
            )
        )

        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail="该面试已有评估报告"
            )

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
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail="评估报告保存失败"
            )

        return {
            "evaluation_id": evaluation.id,
            "interview_id": evaluation.interview_id,
            "overall_score": evaluation.overall_score,
            "message": "评估报告生成成功"
        }



