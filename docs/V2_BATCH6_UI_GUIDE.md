# InterviewPilot V2 · 第六批 HR UI 优化指南

## 目的

本包只美化 HR 后台（候选人筛选和人工复核）：

- 搜索、状态筛选统一为紫白色圆角表单，增加 **重置筛选**；
- 面试、报告与人工复核状态显示为可辨识的标签；
- 人工复核状态、备注输入、字符计数、保存按钮和保存成功反馈统一视觉；
- 处理移动端窄屏、禁用状态、键盘聚焦与减少动画偏好。

**没有修改后端、数据库、API、JWT、候选人页面或 DeepSeek 逻辑。**

## 1. 提交第六批功能（先做）

确保在 Windows 本地 `D:\projects\interview-pilot` 且分支为 `feat/hr-job-invitations`。

```cmd
cd /d D:\projects\interview-pilot
git branch --show-current
git status --short
```

只暂存已验收的第六批功能文件，先看 `git diff --cached --name-only`，确保没有 `.env`、备份、ZIP 或 `batch6_payload`。

```cmd
git add backend frontend/src docs/V2_BATCH6_GUIDE.md tools/apply_batch6.py
git add -f backend/migrations/20261020_hr_review_workflow.sql
git diff --cached --name-only
git commit -m "feat: add HR review workflow and evaluation recovery"
git push origin feat/hr-job-invitations
```

如 Git 提示无更改，先检查是否已经提交；不要为凑提交重复修改文件。

## 2. 安装本 UI 包

ZIP **直接解压到项目根目录** `D:\projects\interview-pilot`，不要解压成一个额外的顶级文件夹。

本 ZIP 包含：

```
batch6_ui_payload/frontend/src/App.css
batch6_ui_payload/frontend/src/pages/AdminDashboardPage.tsx
batch6_ui_payload/frontend/src/pages/AdminInterviewDetailPage.tsx
tools/apply_batch6_ui.py
docs/V2_BATCH6_UI_GUIDE.md
```

运行：

```cmd
cd /d D:\projects\interview-pilot
python tools\apply_batch6_ui.py --check
python tools\apply_batch6_ui.py
```

脚本按上传时三个文件的 SHA256 校验，校验不通过就**停止，不覆盖**。更新前的原文件会自动备份到项目外的 `D:\projects\interview-pilot-v2-backups\ui-batch6-日期时间`。

## 3. 前端构建和视觉验收

```cmd
cd /d D:\projects\interview-pilot\frontend
npm run build
npm run dev
```

本地浏览器打开 `/admin`，检查筛选框、重置筛选、表格和状态标签。打开 `/admin/interviews/28` 或任意**已有评估**的测试面试，检查复核面板、备注字符计数、保存成功提示；刷新后复核结果仍保留。

只做真实已有记录的复核测试即可，不需要调用 DeepSeek 或重新面试。

## 4. UI 单独提交

```cmd
cd /d D:\projects\interview-pilot
git add frontend/src/App.css frontend/src/pages/AdminDashboardPage.tsx frontend/src/pages/AdminInterviewDetailPage.tsx tools/apply_batch6_ui.py docs/V2_BATCH6_UI_GUIDE.md
git diff --cached --name-only
git commit -m "style: polish HR filters and review controls"
git push origin feat/hr-job-invitations
```

不要 `git add .`，避免提交安装包 payload 与上传文件。

## 5. 回滚 UI

如果 UI 有问题，先不要动后端或数据库。因为 UI 是独立提交，可在确认无其他待提交改动后使用 `git revert <UI提交号>` 创建撤销 UI 的提交；或者从项目外的自动备份恢复这三个前端文件并重新构建。
