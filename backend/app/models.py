
from datetime import datetime
from sqlalchemy import Column, Integer, JSON, Boolean
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