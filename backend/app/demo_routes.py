"""Read-only, fully synthetic HR demo endpoints.

Demo JWT cannot call existing /api/admin/... routes (which still require role=admin).
These endpoints never query MySQL and never invoke AI or expose invite tokens.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.admin_auth import require_demo

router = APIRouter(prefix="/api/demo", tags=["HR只读演示（虚构数据）"], dependencies=[Depends(require_demo)])

# Intentionally outside normal auto-increment range. No corresponding DB rows exist.
DEMO_JOB_ID = 900000001
DEMO_INTERVIEW_ID = 900000001
DEMO_IN_PROGRESS_ID = 900000002
DATE = "2026-10-20T10:00:00"

# 预置虚构样例，仅用于展示功能。绝不使用、缓存或导出真实招聘数据。
DEMO_JOB = {
    "job_id": DEMO_JOB_ID,
    "title": "演示岗位 · Python 后端实习生（虚构）",
    "position": "Python 后端实习生",
    "requirements": "熟悉 Python、FastAPI、MySQL；能解释技术方案并描述学习、协作和执行思路。",
    "difficulty": "中等",
    "is_active": True,
    "created_at": DATE,
    "invite_code": "",
    "invite_path": "",
}

# 每条回答均为公开演示用途的人工撰写样例，不是真实候选人信息。
DEMO_QA = [
    ("请描述 FastAPI 中 Depends 的作用。", "我会用 Depends 集中注入数据库会话，让路由专注业务逻辑。"),
    ("如何保证数据库会话在异常时关闭？", "使用 yield 依赖，在 finally 中关闭 Session，并配合事务回滚。"),
    ("如果产品经理的需求表述模糊，你会怎么办？", "先复述目标并列出不明确之处，再通过例子确认验收标准。"),
    ("若团队成员对方案有不同看法，你如何沟通？", "我会先理解对方担忧，用可验证的指标比较方案，再记录最终结论。"),
    ("遇到陌生的消息队列技术，你会如何学习？", "先读官方快速入门，再搭建最小示例验证生产与消费链路。"),
    ("学习过程中发现资料互相矛盾怎么办？", "优先核对版本与官方文档，用测试用例验证并记录结果。"),
    ("两天内交付 API，你会怎样安排任务？", "先确认接口契约与验收条件，再拆分开发、测试和联调任务。"),
    ("上线前发现关键接口异常，你如何处理？", "先评估影响并同步风险，阻断发布，修复后回归测试并记录复盘。"),
]
DEMO_MESSAGES = [
    {"id": index * 2 + offset + 1, "role": role, "content": content, "created_at": DATE}
    for index, (question, answer) in enumerate(DEMO_QA)
    for offset, (role, content) in enumerate((("assistant", question), ("user", answer)))
]

DEMO_INTERVIEWS = [
    {
        "interview_id": DEMO_INTERVIEW_ID,
        "candidate_name": "演示候选人甲（虚构）",
        "position": "Python 后端实习生",
        "difficulty": "中等",
        "status": "completed",
        "job_id": DEMO_JOB_ID,
        "evaluation_status": "ready",
        "review_status": "follow_up",
        "created_at": DATE,
    },
    {
        "interview_id": DEMO_IN_PROGRESS_ID,
        "candidate_name": "演示候选人乙（虚构）",
        "position": "Python 后端实习生",
        "difficulty": "中等",
        "status": "in_progress",
        "job_id": DEMO_JOB_ID,
        "evaluation_status": "not_started",
        "review_status": "pending",
        "created_at": DATE,
    },
]

DEMO_REPORT = {
    "id": DEMO_INTERVIEW_ID,
    "interview_id": DEMO_INTERVIEW_ID,
    "technical_score": 76,
    "completeness_score": 80,
    "clarity_score": 82,
    "overall_score": 79,
    "summary": "虚构示例：回答展示了基本的依赖管理与协作思路；仍需 HR 结合实际面试验证。此分数仅为演示样本。",
    "strengths": ["可以说明 Depends 的使用目的", "会通过澄清需求确认验收条件"],
    "weaknesses": ["部分回答未给出具体项目证据"],
    "suggestions": ["请通过后续实际情境问题及项目材料人工复核"],
    "created_at": DATE,
    "competency_assessment": {
        "version": 1,
        "review_notice": "演示数据全部虚构；评分仅为界面样例，不构成真实招聘结论。",
        "dimensions": {
            "technical": {"score": 76, "evidence": DEMO_QA[0][1], "observation": "能简要解释依赖注入目的。", "limitations": "未结合真实项目验证。", "answer_count": 2},
            "communication": {"score": 82, "evidence": DEMO_QA[2][1], "observation": "提出澄清目标和确认验收标准的步骤。", "limitations": "文字回答不能代表真实协作表现。", "answer_count": 2},
            "learning": {"score": 78, "evidence": DEMO_QA[4][1], "observation": "学习计划包含文档与最小实验。", "limitations": "未验证学习效率。", "answer_count": 2},
            "execution": {"score": 80, "evidence": DEMO_QA[6][1], "observation": "回答包含任务拆分与验收。", "limitations": "未验证实际交付能力。", "answer_count": 2},
        },
    },
}


@router.get("/jobs")
def demo_jobs():
    return [DEMO_JOB]


@router.get("/interviews")
def demo_interviews():
    return DEMO_INTERVIEWS


@router.get("/interviews/{interview_id}")
def demo_interview_detail(interview_id: int):
    entry = next((item for item in DEMO_INTERVIEWS if item["interview_id"] == interview_id), None)
    if entry is None:
        raise HTTPException(status_code=404, detail="演示面试不存在")
    return {
        **entry,
        "evaluation_error": None,
        "review_note": "虚构示例：建议补充项目实践材料。" if interview_id == DEMO_INTERVIEW_ID else None,
        "reviewed_at": DATE if interview_id == DEMO_INTERVIEW_ID else None,
        "messages": DEMO_MESSAGES if interview_id == DEMO_INTERVIEW_ID else DEMO_MESSAGES[:3],
    }


@router.get("/interviews/{interview_id}/evaluation")
def demo_evaluation(interview_id: int):
    if interview_id != DEMO_INTERVIEW_ID:
        raise HTTPException(status_code=404, detail="演示报告不存在")
    return DEMO_REPORT
