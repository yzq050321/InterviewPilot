# -*- coding: utf-8 -*-
"""V2 第六批 HR UI 美化安装器：只覆盖三个经过 SHA256 校验的前端文件。"""
import argparse
import hashlib
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
FILES = {'frontend/src/App.css': {'before': 'd702a6500f929dee512cf9ba723db4fe0d494ceaf57af1eea7d6166fa8c25fc4', 'after': '643bec108fb606cd98bb0e2ff1eaf5b2c7b34dfda5dda58febce91a9b5c1cb69'}, 'frontend/src/pages/AdminDashboardPage.tsx': {'before': 'cbc886caba1321032d374b403d9be09bbb03810c1d07784f8916c930e1397ff0', 'after': '2f5507903d7625e37a391ea6551c013298281170709a4df173492371def42762'}, 'frontend/src/pages/AdminInterviewDetailPage.tsx': {'before': '9c54b1c6bd290a8a53e457bdfa26322f39302ce9b560f9206e88a88d2fa6dde6', 'after': 'f73f976561134207212e126bd881bac1eb2ec3501e3460295c29224918b5ac90'}}

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run_git(*args):
    return subprocess.run(["git", *args], cwd=PROJECT, capture_output=True, text=True, check=True).stdout.strip()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="仅检查，不覆盖")
    args = parser.parse_args()
    branch = run_git("branch", "--show-current")
    if branch != "feat/hr-job-invitations":
        raise SystemExit("停止：当前分支不是 feat/hr-job-invitations，而是 " + branch)
    checks = []
    for rel, expected in FILES.items():
        target = PROJECT / rel
        payload = PROJECT / "batch6_ui_payload" / rel
        if not target.is_file() or not payload.is_file():
            raise SystemExit("停止：文件缺失：" + rel)
        if sha256(payload) != expected["after"]:
            raise SystemExit("停止：安装包文件 SHA256 校验失败：" + rel)
        current = sha256(target)
        if current == expected["after"]:
            checks.append((rel, "已是新版，跳过"))
        elif current == expected["before"]:
            checks.append((rel, "准备更新"))
        else:
            raise SystemExit("停止：本地文件与上传时的版本不一致，请先保留改动并反馈：" + rel)
    print("目标分支：", branch)
    for rel, result in checks:
        print(f"{result}: {rel}")
    if args.check:
        print("校验通过；尚未修改文件。")
        return
    to_update = [rel for rel, desc in checks if desc == "准备更新"]
    if not to_update:
        print("三个文件已经是新版本；未修改。")
        return
    backup_root = PROJECT.parent / "interview-pilot-v2-backups" / ("ui-batch6-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    for rel in to_update:
        dest = backup_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT / rel, dest)
    print("备份完成：", backup_root)
    for rel in to_update:
        target = PROJECT / rel
        shutil.copy2(PROJECT / "batch6_ui_payload" / rel, target)
        if sha256(target) != FILES[rel]["after"]:
            raise SystemExit("更新后校验失败，请从备份恢复：" + rel)
    print("安装成功，已更新",len(to_update),"个前端文件。未改后端、数据库或认证。")

if __name__ == "__main__":
    main()
