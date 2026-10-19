"""Safely patch the two existing source files for InterviewPilot V2 batch 2.

Run at the project root: python tools/apply_hr_jobs_batch2.py
This script does not connect to any database or cloud server.
"""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "backend" / "app" / "models.py"
MAIN = ROOT / "backend" / "main.py"
BACKUP = ROOT.parent / "interview-pilot-v2-backups"


def insert_once(path: Path, marker: str, replacement: str, already: str) -> bool:
    original = path.read_text(encoding="utf-8-sig")
    if already in original:
        print(f"已包含 V2 修改，跳过：{path.relative_to(ROOT)}")
        return False
    if original.count(marker) != 1:
        raise RuntimeError(f"无法唯一定位修改位置，未修改：{path}")
    BACKUP.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP / (path.name + ".before-v2-batch2")
    if not backup_path.exists():
        shutil.copy2(path, backup_path)
    changed = original.replace(marker, replacement, 1)
    path.write_text(changed, encoding="utf-8", newline="\n")
    print(f"已更新：{path.relative_to(ROOT)}")
    return True


def main():
    if not MODELS.is_file() or not MAIN.is_file():
        raise SystemExit("请在 InterviewPilot 项目根目录解压文件后运行。")

    models_marker = 'class Interview(Base):\n    __tablename__ = "interviews"'
    models_replacement = '''class Interview(Base):
    __tablename__ = "interviews"

    # V2：来源招聘任务，旧版面试允许为空
    job_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_postings.id"), nullable=True, index=True
    )'''
    if 'class JobPosting(Base):' not in MODELS.read_text(encoding="utf-8-sig"):
        raise RuntimeError("models.py 缺少批次 1 的 JobPosting 类，请先完成批次 1。")
    # Preflight checks for both files so an obvious mismatch fails early.
    main_text = MAIN.read_text(encoding="utf-8-sig")
    if "from app.job_routes import router as job_router" not in main_text:
        if main_text.count("# 创建 FastAPI 应用") != 1 or main_text.count("candidate_bearer = HTTPBearer(auto_error=False)") != 1:
            raise RuntimeError("main.py 与提供的版本不匹配，请先停止并反馈。")

    insert_once(
        MODELS,
        models_marker,
        models_replacement,
        'ForeignKey("job_postings.id")',
    )
    insert_once(
        MAIN,
        "# 创建 FastAPI 应用",
        "from app.job_routes import router as job_router\n\n# 创建 FastAPI 应用",
        "from app.job_routes import router as job_router",
    )
    insert_once(
        MAIN,
        "candidate_bearer = HTTPBearer(auto_error=False)",
        "app.include_router(job_router)\n\ncandidate_bearer = HTTPBearer(auto_error=False)",
        "app.include_router(job_router)",
    )
    print("源代码补丁应用完成。这里只修改了源文件，没有执行数据库迁移。")


if __name__ == "__main__":
    main()
