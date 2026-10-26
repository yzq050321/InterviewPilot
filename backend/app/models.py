
from datetime import datetime
from sqlalchemy import Column, Integer, JSON, Boolean, UniqueConstraint
from sqlalchemy import (
    String,
    Text,
    ForeignKey,
    DateTime,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# 面试表
class Interview(Base):
    __tablename__ = "interviews"

    # V2：来源招聘任务，旧版面试允许为空
    job_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_postings.id"), nullable=True, index=True
    )

    # 主键
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )
    
    # 候选人访问凭证哈希
    candidate_token_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
    )
    
    # 候选人姓名
    candidate_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    # 目标岗位
    position: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    # 面试难度
    difficulty: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    # 面试状态
    status: Mapped[str] = mapped_column(
        String(30),
        default="in_progress",
        nullable=False
    )

    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )

    # AI 报告状态：pending / generating / failed / ready；旧记录为 NULL。
    evaluation_state: Mapped[str | None] = mapped_column(String(20), nullable=True)
    evaluation_error: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evaluation_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # HR 人工复核：pending / reviewed / follow_up（不自动录用或淘汰）。
    review_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Batch 9：人工招聘流程阶段，独立于 AI 评估和人工复核状态。
    recruitment_stage: Mapped[str] = mapped_column(
        String(24), nullable=False, default="new", server_default="new"
    )

    # V2.2：候选人上传简历后只保存解析文本，不保存原文件。
    resume_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    resume_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resume_consent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 一场面试对应多条消息
    messages: Mapped[list["Message"]] = relationship(
        back_populates="interview",
        cascade="all, delete-orphan"
    )


# 消息表
class Message(Base):
    __tablename__ = "messages"

    # 主键
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    # 所属面试 ID（外键）
    interview_id: Mapped[int] = mapped_column(
        ForeignKey("interviews.id"),
        nullable=False,
        index=True
    )

    # 消息角色：user / assistant
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    # 消息正文
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    # 消息创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )

    # 每条消息属于一场面试
    interview: Mapped["Interview"] = relationship(
        back_populates="messages"
    )


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    interview_id = Column(
        Integer,
        ForeignKey("interviews.id"),
        nullable=False,
        unique=True
    )

    technical_score = Column(
        Integer,
        nullable=True
    )

    completeness_score = Column(
        Integer,
        nullable=True
    )

    clarity_score = Column(
        Integer,
        nullable=True
    )

    overall_score = Column(
        Integer,
        nullable=True
    )

    # 招聘版综合能力结构化评估；旧版报告可为空
    competency_assessment = Column(
        JSON,
        nullable=True,
    )

    summary = Column(
        Text,
        nullable=False
    )

    strengths = Column(
        JSON,
        nullable=False
    )

    weaknesses = Column(
        JSON,
        nullable=False
    )

    suggestions = Column(
        JSON,
        nullable=False
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )
    
    
    
# HR 招聘任务表
class JobPosting(Base):
    __tablename__ = "job_postings"

    # 招聘任务 ID
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    # 招聘任务名称，例如：Python 后端实习生招聘
    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # 招聘岗位
    position: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # 岗位要求，由 HR 填写
    requirements: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # 面试难度
    difficulty: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="中等",
    )

    # 随机邀请码
    # 后续由后端使用 secrets 生成，不能使用自增 ID 代替
    invite_code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    # 是否允许候选人通过邀请链接创建面试
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    # Batch 10A: 邀请链接到期时间，以 UTC naive DATETIME 存储。
    invite_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class InterviewFollowup(Base):
    """Append-only HR follow-up log. Does not change the candidate's AI report."""
    __tablename__ = "interview_followups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    interview_id: Mapped[int] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    old_stage: Mapped[str] = mapped_column(String(24), nullable=False)
    new_stage: Mapped[str] = mapped_column(String(24), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class HRUser(Base):
    """Invite-only HR account. Password is bcrypt-hashed; email is unique."""
    __tablename__ = "hr_users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="hr", server_default="hr")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TrialRequest(Base):
    """Public trial application; admin reviews it out-of-band."""
    __tablename__ = "trial_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company: Mapped[str | None] = mapped_column(String(200), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class AnswerAttempt(Base):
    """One durable candidate answer attempt per interview question."""
    __tablename__ = "interview_answer_attempts"
    __table_args__ = (
        UniqueConstraint("interview_id", "question_id", name="uq_answer_attempt_question"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    interview_id: Mapped[int] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    request_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    answer_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    next_question_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
