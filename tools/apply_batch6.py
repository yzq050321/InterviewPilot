"""Batch 6 install helper. Verifies source fingerprints and backs up originals.

Usage (from repo root): python tools/apply_batch6.py --check
                       python tools/apply_batch6.py
"""
from __future__ import annotations
import argparse
import hashlib
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

EXPECTED = {'backend/main.py': '41c1f6776cfb62fcc5922e60afe393769a48a69b66d7a39a607c88e51b2d9a69', 'backend/app/models.py': '1e44d49a0dc80515ecd06bbc083cedf7b094f196f9fe671c641a7fc226e6af8f', 'backend/app/evaluation_workflow.py': None, 'backend/app/admin_workflow.py': None, 'backend/migrations/20261020_hr_review_workflow.sql': None, 'backend/migrations/20261020_hr_review_workflow_rollback.sql': None, 'backend/tests/test_batch6_workflow.py': None, 'frontend/src/services/api.ts': 'b452f82300500947fb87d689f36c993ed05b2e85a5167b5c3cb61b741897106d', 'frontend/src/services/adminWorkflowApi.ts': None, 'frontend/src/pages/AdminDashboardPage.tsx': '7245e3976794697812bdff6b0def632c0f9af665c9f3eeb3b3cfba4e36151093', 'frontend/src/pages/AdminInterviewDetailPage.tsx': '81fc8308aca3fde3b60902b74c03584a62daa8434481bb66912bf667097f6cb0'}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate without changing anything")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parent.parent
    payload = repo / "batch6_payload"
    if not payload.is_dir():
        raise SystemExit("未找到 batch6_payload；请将 ZIP 解压到项目根目录")
    branch = subprocess.run(["git", "branch", "--show-current"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()
    if branch != "feat/hr-job-invitations":
        raise SystemExit(f"当前分支为 {branch!r}；只能在 feat/hr-job-invitations 上安装")
    # Protect already modified, staged and tracked source files. Untracked local ZIPs allowed.
    status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=repo, capture_output=True, text=True, check=True).stdout
    if status.strip():
        raise SystemExit("存在未提交的受跟踪文件变更；请先处理 Git 状态：\n" + status)
    actions = []
    for name, old_hash in EXPECTED.items():
        old = repo / name
        new = payload / name
        if not new.is_file():
            raise SystemExit(f"缺少文件：{new}")
        current = sha(old) if old.exists() else None
        if current == sha(new):
            print("已是新版本：", name)
            continue
        if current != old_hash:
            raise SystemExit(f"文件与上传时不一致，已停止，未修改任何文件：{name}")
        actions.append((name, old, new))
    print("待更新文件：", len(actions))
    for name, _, _ in actions:
        print("  ", name)
    if args.check:
        print("检查完成：未修改任何文件。")
        return
    backup_dir = repo.parent / "interview-pilot-v2-backups" / ("batch6_source_before_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    for name, old, new in actions:
        if old.exists():
            backup = backup_dir / name
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(old, backup)
        old.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(new, old)
    print("更新成功。源文件备份：", backup_dir if backup_dir.exists() else "本批无旧文件")
    print("注意：本脚本没有操作 MySQL，也没有提交 Git。")

if __name__ == "__main__":
    main()
