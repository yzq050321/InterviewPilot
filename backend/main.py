from fastapi import FastAPI, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Interview, Message, Evaluation, JobPosting
from app.interview_create_limiter import require_create_capacity
# V2_BATCH4_JOB_CONTEXT
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
    generate_competency_question_agent,
)
from app.admin_auth import (
    authenticate_admin,
    authenticate_demo,
    create_admin_token,
    create_demo_token,
    require_admin,
)

logger = logging.getLogger(__name__)
from openai import APITimeoutError
from app.candidate_auth import (
    create_candidate_token,
    verify_candidate_token,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Request
from app.login_limiter import (
    is_login_blocked,
    record_login_failure,
    clear_login_failures,
    cleanup_expired_records,
)

from app.job_routes import router as job_router
from app.structured_interview import stage_after_answer, CLOSING_MESSAGE, QUESTION_LIMIT
from app.admin_workflow import router as admin_workflow_router
from app.demo_routes import router as demo_router
from app.evaluation_workflow import get_evaluation_state, generate_and_store_report
from app.model_usage import model_usage_scope, link_interview_to_trace

# 创建 FastAPI 应用
app = FastAPI(
    title="InterviewPilot API",
    version="1.0.0"
)

app.include_router(job_router)
app.include_router(admin_workflow_router)
app.include_router(demo_router)

candidate_bearer = HTTPBearer(auto_error=False)

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



# HR 管理员登录请求
class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1)
    
    
    

# HR 管理员登录接口
@app.post("/api/admin/login")
def admin_login(
    login_data: AdminLoginRequest,
    request: Request,
):
    # 从实际连接信息中获取客户端 IP
    # 不信任前端自行提供的 X-Forwarded-For
    client_ip = (
        request.client.host
        if request.client is not None
        else "unknown"
    )

    
    # 清理已经过期的登录记录
    cleanup_expired_records()

    # 1. 检查登录是否被暂时限制
    if is_login_blocked(client_ip):
        raise HTTPException(
            status_code=429,
            detail="登录失败次数过多，请15分钟后再试",
        )

    # 2. 验证真实管理员或独立 Demo 凭证（均受同一登录限流保护）。
    # Demo 不取得 require_admin 权限，也不读取任何真实数据库内容。
    if authenticate_admin(login_data.username, login_data.password):
        role = "admin"
    elif authenticate_demo(login_data.username, login_data.password):
        role = "demo"
    else:
        record_login_failure(client_ip)
        raise HTTPException(status_code=401, detail="账号或密码错误")

    clear_login_failures(client_ip)
    token = create_admin_token() if role == "admin" else create_demo_token()
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 7200,
        "role": role,
    }


# 定义创建面试时的数据格式
class InterviewCreate(BaseModel):

    # 候选人姓名
    candidate_name: str = Field(min_length=1, max_length=100)
    

    # 岗位名称
    position: str = Field(min_length=1, max_length=100)

    # 面试难度由招聘系统统一决定，暂不允许候选人修改
    difficulty: Literal["中等"] = "中等"

    @field_validator("candidate_name", "position")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("该字段不能为空")

        return value

# 创建 AI 面试题接口
@app.post("/api/interviews")
async def create_interview(
    request: InterviewCreate,
    db: Session = Depends(get_db)
):
    # 1. AI 请求调用前限流（包括不带邀请码的旧版入口）
    require_create_capacity()

    # 2. 调用 DeepSeek 生成第一道面试题
    try:
        with model_usage_scope(stage="first_question") as usage_trace:
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
        # 为这场面试生成专属访问凭证
        candidate_token, candidate_token_hash = create_candidate_token()

        interview = Interview(
            candidate_name=request.candidate_name,
            candidate_token_hash=candidate_token_hash,
            position=request.position,
            difficulty=request.difficulty,
            status="in_progress"
        )

        # 先将新面试加入数据库会话
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
        link_interview_to_trace(usage_trace, interview.id)

        # 3. 返回创建结果
        
        return {
            "interview_id": interview.id,
            "interview_token": candidate_token,
            "candidate_name": interview.candidate_name,
            "position": interview.position,
            "difficulty": interview.difficulty,
            "question": question
        }

    
    except Exception:
        db.rollback()
        logger.exception("保存面试记录失败")

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
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(candidate_bearer),
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

    
    # 验证候选人是否有权操作这场面试
    if (
        credentials is None
        or not verify_candidate_token(
            credentials.credentials,
            interview.candidate_token_hash
        )
    ):
        raise HTTPException(
            status_code=401,
            detail="无权操作该场面试",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if interview.status != "in_progress":
        raise HTTPException(
            status_code=400,
            detail="当前面试已结束"
        )

    # 招聘任务结构化面试最多八次候选人回答：四维、每维两次。
    if interview.job_id is not None:
        answered = db.scalars(
            select(Message.id).where(
                Message.interview_id == interview.id,
                Message.role == "user",
            )
        ).all()
        if len(answered) >= QUESTION_LIMIT:
            raise HTTPException(status_code=409, detail="面试问题已全部回答，请结束面试")

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

        # 邀请面试的提问维度由后端控制，避免模型一直只问技术题。
        job = db.get(JobPosting, interview.job_id) if interview.job_id is not None else None
        requirements = job.requirements if job is not None else None
        answer_count = sum(1 for item in history if item["role"] == "user")
        next_stage = stage_after_answer(answer_count) if interview.job_id is not None else None

        with model_usage_scope(
            stage="followup" if next_stage in (None, "technical_followup") else (next_stage or "closing"),
            interview_id=interview.id,
            job_id=interview.job_id,
        ):
            if next_stage == "finished":
                # 第八次回答后不额外调用模型，提示候选人提交完成。
                next_question = CLOSING_MESSAGE
            elif next_stage in (None, "technical_followup"):
                args = (interview.position, interview.difficulty, history)
                if requirements:
                    args += (requirements,)
                next_question = await run_in_threadpool(generate_followup_agent, *args)
            else:
                next_question = await run_in_threadpool(
                    generate_competency_question_agent,
                    interview.position,
                    interview.difficulty,
                    requirements,
                    next_stage,
                    history,
                )

    except HTTPException:
        raise
    except Exception:
        logger.exception("生成下一道面试题失败")
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
            "next_question": next_question,
            "finished_questions": next_stage == "finished",
            "interview_stage": next_stage,
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="保存面试消息失败"
        )


@app.get("/api/interviews")
def list_interviews(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
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

    # 批量确认报告是否存在，避免 N+1 查询及旧数据状态不准确。
    report_ids = set(db.scalars(select(Evaluation.interview_id)).all())

    # 2. 转换为 JSON 可序列化的数据
    result = []

    for interview in interviews:
        
    
        result.append({
            "interview_id": interview.id,
            "candidate_name": interview.candidate_name,
            "position": interview.position,
            "difficulty": interview.difficulty,
            "status": interview.status,
            "job_id": interview.job_id,
            "evaluation_status": get_evaluation_state(interview, interview.id in report_ids),
            "review_status": interview.review_status,
            "created_at": interview.created_at
        })

    # 3. 返回历史面试列表
    return result



# HR 管理员查看指定候选人的完整面试记录
@app.get("/api/admin/interviews/{interview_id}")
def get_admin_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    # 1. 查询面试
    interview = db.get(Interview, interview_id)

    if interview is None:
        raise HTTPException(
            status_code=404,
            detail="面试不存在"
        )

    # 2. 查询完整问答记录
    stmt = (
        select(Message)
        .where(Message.interview_id == interview_id)
        .order_by(Message.id.asc())
    )

    messages = db.scalars(stmt).all()

    # 3. 整理聊天记录
    message_list = []

    for message in messages:
        message_list.append({
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at,
        })

    has_report = db.scalar(select(Evaluation.id).where(Evaluation.interview_id == interview_id)) is not None

    # 4. 返回面试信息和完整问答
    return {
        "interview_id": interview.id,
        "candidate_name": interview.candidate_name,
        "position": interview.position,
        "difficulty": interview.difficulty,
        "status": interview.status,
        "job_id": interview.job_id,
        "evaluation_status": get_evaluation_state(interview, has_report),
        "evaluation_error": interview.evaluation_error if not has_report else None,
        "review_status": interview.review_status,
        "review_note": interview.review_note,
        "reviewed_at": interview.reviewed_at,
        "created_at": interview.created_at,
        "messages": message_list,
    }

# 获取指定面试详情及聊天记录
@app.get("/api/interviews/{interview_id}")
def get_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(candidate_bearer),
):
    # 1. 查询面试基本信息
    interview = db.get(Interview, interview_id)

    if interview is None:
        raise HTTPException(
            status_code=404,
            detail="面试不存在"
        )

    # 2. 验证候选人访问凭证
    if (
        credentials is None
        or not verify_candidate_token(
            credentials.credentials,
            interview.candidate_token_hash
        )
    ):
        raise HTTPException(
            status_code=401,
            detail="无权访问该场面试",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. 查询这场面试的所有消息
    stmt = (
        select(Message)
        .where(Message.interview_id == interview_id)
        .order_by(Message.id.asc())
    )

    messages = db.scalars(stmt).all()

    # 4. 整理消息数据
    message_list = []

    for message in messages:
        message_list.append({
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at
        })

    # 5. 返回面试及其消息
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
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(candidate_bearer),
):
    # 1. 查询面试
    interview = db.get(Interview, interview_id)

    if interview is None:
        raise HTTPException(
            status_code=404,
            detail="面试不存在"
        )


    # 验证候选人是否有权结束这场面试
    if (
        credentials is None
        or not verify_candidate_token(
            credentials.credentials,
            interview.candidate_token_hash
        )
    ):
        raise HTTPException(
            status_code=401,
            detail="无权结束该场面试",
            headers={"WWW-Authenticate": "Bearer"},
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
def get_interview_evaluation(
    interview_id: int,
    _: None = Depends(require_admin),
):

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
            "competency_assessment": evaluation.competency_assessment,
            "created_at": evaluation.created_at
        }



@app.post("/api/interviews/{interview_id}/evaluation")
async def create_interview_evaluation(
    interview_id: int,
    credentials: HTTPAuthorizationCredentials | None = Depends(candidate_bearer),
):
    # 第一步：查询面试
    with SessionLocal() as db:
        interview = db.get(Interview, interview_id)

        if interview is None:
            raise HTTPException(
                status_code=404,
                detail="面试不存在"
            )

        # 验证候选人是否有权生成这场面试的报告
        if (
            credentials is None
            or not verify_candidate_token(
                credentials.credentials,
                interview.candidate_token_hash
            )
        ):
            raise HTTPException(
                status_code=401,
                detail="无权生成该场面试的评估报告",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 只有已结束的面试才能生成报告
        if interview.status != "completed":
            raise HTTPException(
                status_code=400,
                detail="请先结束面试，再生成评估报告"
            )

    # 与 HR 恢复入口共用一次原子领取、模型调用和报告保存流程。
    # 返回结果不含任何 HR 评分或报告内容。
    return await generate_and_store_report(
        interview_id, session_factory=SessionLocal, generator=generate_evaluation
    )
