"""Apply InterviewPilot V2 Batch 4 to the existing backend/main.py.

Uses exact anchors; validates before writing. Re-runnable.
Writes one backup outside the git repository before changing main.py.
"""
from pathlib import Path
import ast
import shutil

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "backend" / "main.py"
FRONTEND = ROOT / "frontend" / "src" / "pages" / "AdminJobsPage.tsx"
BACKUP_DIR = ROOT.parent / "interview-pilot-v2-backups"
MARKER = "# V2_BATCH4_JOB_CONTEXT"


def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{name}: 预期出现 1 次，实际 {count} 次；未修改文件")
    return text.replace(old, new, 1)


def apply() -> None:
    original = MAIN.read_text(encoding="utf-8-sig")
    if MARKER in original:
        print("main.py 已完成第四批修改，跳过（可重复执行）")
        return
    text = original
    text = replace_once(
        text,
        "from app.models import Interview, Message, Evaluation",
        "from app.models import Interview, Message, Evaluation, JobPosting\n"
        "from app.interview_create_limiter import require_create_capacity\n"
        + MARKER,
        "main.py 导入",
    )
    text = replace_once(
        text,
        '''    # 1. 调用 DeepSeek 生成第一道面试题
    try:''',
        '''    # 1. AI 请求调用前限流（包括不带邀请码的旧版入口）
    require_create_capacity()

    # 2. 调用 DeepSeek 生成第一道面试题
    try:''',
        "旧版创建面试限流",
    )
    text = replace_once(
        text,
        '''        history.append({
            "role": "user",
            "content": request.answer
        })

        # 根据完整历史生成下一道追问
        next_question = await run_in_threadpool(
            generate_followup_agent,
            interview.position,
            interview.difficulty,
            history
        )''',
        '''        history.append({
            "role": "user",
            "content": request.answer
        })

        # 邀请面试读取 HR 要求；旧面试保持原有调用方式。
        job = db.get(JobPosting, interview.job_id) if interview.job_id is not None else None
        requirements = job.requirements if job is not None else None
        args = (interview.position, interview.difficulty, history)
        if requirements:
            args += (requirements,)

        next_question = await run_in_threadpool(generate_followup_agent, *args)''',
        "招聘要求驱动追问",
    )
    text = replace_once(
        text,
        '''        position = interview.position
        difficulty = interview.difficulty

    # 第二步：检查是否有用户回答''',
        '''        position = interview.position
        difficulty = interview.difficulty
        job = db.get(JobPosting, interview.job_id) if interview.job_id is not None else None
        job_requirements = job.requirements if job is not None else None

    # 第二步：检查是否有用户回答''',
        "AI 报告关联招聘要求",
    )
    text = replace_once(
        text,
        '''        report = await run_in_threadpool(
            generate_evaluation,
            position=position,
            difficulty=difficulty,
            history=history
        )''',
        '''        report_kwargs = {
            "position": position,
            "difficulty": difficulty,
            "history": history,
        }
        if job_requirements:
            report_kwargs["requirements"] = job_requirements
        report = await run_in_threadpool(generate_evaluation, **report_kwargs)''',
        "AI 报告传入招聘要求",
    )
    ast.parse(text, filename=str(MAIN))

    # HR 页面上上一批的说明已经过时。本批顺带更新，不影响表单功能。
    frontend_original = FRONTEND.read_text(encoding="utf-8-sig")
    old_hint = "当前版本岗位要求用于任务展示；AI 出题按岗位与难度生成，下一阶段将结合岗位要求定制。"
    new_hint = "岗位要求将用于 AI 出题、动态追问和报告参考；请勿填写保密信息。"
    if frontend_original.count(old_hint) != 1:
        if new_hint in frontend_original:
            frontend_new = frontend_original
        else:
            raise RuntimeError("HR 页面提示语与第三批版本不一致；未修改任何文件")
    else:
        frontend_new = frontend_original.replace(old_hint, new_hint, 1)

    BACKUP_DIR.mkdir(exist_ok=True)
    snapshot = BACKUP_DIR / "main_before_batch4.py"
    if not snapshot.exists():
        shutil.copy2(MAIN, snapshot)
    frontend_snapshot = BACKUP_DIR / "AdminJobsPage_before_batch4.tsx"
    if not frontend_snapshot.exists():
        shutil.copy2(FRONTEND, frontend_snapshot)
    MAIN.write_text(text, encoding="utf-8")
    if frontend_new != frontend_original:
        FRONTEND.write_text(frontend_new, encoding="utf-8")
    print("已更新 backend/main.py 和 HR 页面说明文字")
    print("原始备份：", snapshot, frontend_snapshot)
    print("未更改数据库结构；暂未启动 DeepSeek 调用")


if __name__ == "__main__":
    apply()
