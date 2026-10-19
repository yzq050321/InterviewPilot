# InterviewPilot V2 第一阶段：开发批次 2

## 作用与边界

本批新增 HR 招聘任务 API、安全邀请码、候选人通过邀请码创建面试、`interviews.job_id` 关联。

**仅限本地测试，不要直接部署到腾讯云。** HR 任务管理前端与候选人邀请页面在下一批制作。邀请码链接 `/invite/{invite_code}` 是未来的前端路由，本批尚无法在浏览器打开它；本批先验证 API。

当前 `requirements` 作为招聘需求保存，**还未纳入 Agent 的面试提示词**，这将在 AI 能力批次中处理。旧 `/api/interviews` 接口暂时保留，兼容已有候选人首页。

## 一、确认工作环境

在 Windows CMD 的项目根目录：

```cmd
cd /d D:\projects\interview-pilot
git branch --show-current
git status --short
```

预期分支 `feat/hr-job-invitations`；开始前工作区应干净。不要在 `main` 分支直接改。

解压本包到 `D:\projects\interview-pilot`，保持 `backend`、`tools`、`docs` 目录结构。若 Windows 提示合并目录，合并即可；不会覆盖旧 `main.py` 和旧 `models.py`。

## 二、自动添加两处代码接线

```cmd
python tools\apply_hr_jobs_batch2.py
python -m compileall -q backend\main.py backend\app\models.py backend\app\job_routes.py
```

脚本**只修改** `backend/main.py` 和 `backend/app/models.py`，备份放在仓库外层的 `D:\projects\interview-pilot-v2-backups`。它不会修改数据库，也不会调用云服务。

预期：JobPosting 已存在，新模型 Interview.job_id 已加入，main.py 已注册 job_router。

## 三、先测试无数据库版本

```cmd
cd backend
python -m pytest -q tests\test_job_routes_v2.py
cd ..
```

这里使用内存 SQLite 和模拟 AI，**不调用 DeepSeek、不连接 MySQL**。若失败，先停止后续迁移，把报错发给助手。

## 四、迁移本地 MySQL（会修改数据库，必须先备份）

项目当前数据库名是 `interview_pilot`。如果你的本地数据库名不同，应替换命令里的名称。

在 Windows CMD 中：

```cmd
cd /d D:\projects\interview-pilot
mkdir D:\projects\interview-pilot-v2-backups
mysqldump -u root -p interview_pilot > D:\projects\interview-pilot-v2-backups\interview_pilot_before_v2.sql
```

若 `mkdir` 提示目录已经存在，可以忽略。`mysqldump` 会交互式要求输入本地 MySQL 密码。切勿在命令里明文填写密码。

**查看备份是否非零字节**：

```cmd
dir D:\projects\interview-pilot-v2-backups\interview_pilot_before_v2.sql
```

确保备份文件实际包含原有数据（不能只有一份 0 字节文件）。如果 `mysqldump` 未安装/失败/数据库名不对，不得继续执行迁移。

确认备份后才执行一次：

```cmd
mysql -u root -p interview_pilot < backend\migrations\20261019_hr_jobs.sql
```s

迁移内容：新建 `job_postings`，新增 `interviews.job_id`（允许 NULL）、索引和外键；**旧面试记录不删除**。不要重复执行；如报错不要自行回滚或重复运行，保存错误消息先确认数据库状态。

迁移后验证：

```cmd
mysql -u root -p interview_pilot -e "SHOW TABLES LIKE 'job_postings'; SHOW COLUMNS FROM interviews LIKE 'job_id'; SELECT COUNT(*) AS existing_interviews FROM interviews;"
```

## 五、本地启动后端并验收

在终端 1：

```cmd
cd /d D:\projects\interview-pilot\backend
python -m uvicorn main:app --reload
```

在浏览器查看 `http://127.0.0.1:8000/docs`：

- POST `/api/admin/jobs`：需先通过原有 `/api/admin/login` 获取真实本地 JWT，然后在 Swagger 的 Authorize 输入 JWT；测试虚构岗位数据。
- GET `/api/admin/jobs`：仅 HR 可查看邀请码与任务。
- GET `/api/job-invitations/{invite_code}`：公共岗位页面数据。
- POST `/api/job-invitations/{invite_code}/interviews`：只传 `candidate_name`，通过后会**真实调用 AI**并创建面试；测试时仅操作一次，避免产生不必要费用。
- PATCH `/api/admin/jobs/{job_id}/deactivate`：停用后邀请接口应返回 404。

若对 Swagger Bearer Token 输入方式不确定，请先使用自动测试结果，不需要把 token 发给别人。

## 六、提交和反馈

```cmd
cd /d D:\projects\interview-pilot
git status --short
git add backend/main.py backend/app/models.py backend/app/job_routes.py backend/migrations/20261019_hr_jobs.sql backend/tests/test_job_routes_v2.py tools/apply_hr_jobs_batch2.py docs/V2_BATCH2_GUIDE.md
git commit -m "feat: add HR job APIs and invitation interview flow"
git status --short
```

现在不要 `git push origin main`，也不要更新腾讯云服务器的数据库。开发分支保持 `feat/hr-job-invitations`。

**一次性反馈：** 自动测试 `pytest` 的结果、本地 MySQL 迁移的验证输出、最后一次 `git commit` 结果。如果遇到报错，请在出错步骤停止，把完整错误贴过来（遮挡个人密码/API Key/token）。

## 安全提醒

1. 已经公开给 HR 的管理员密码在准备下一次正式演示前应更换。
2. 不要使用 `123456` 作为有完整数据库访问权限的管理员密码；演示账户以后应使用只读/虚构数据。
3. 邀请码属于可分享访问入口，不应该放在公开仓库、日志或公开 README 中。
4. **公网邀请创建接口将消耗付费 AI 调用**：当前没有专门的请求频率限制。在上线邀请功能前，应增加限流和滥用保护；请勿直接对公网开放这一批的新接口。
5. 本批 `requirements` 仅保存和展示，不影响 AI 提问；下一阶段需要接入 Agent。
