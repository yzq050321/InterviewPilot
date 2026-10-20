# InterviewPilot V2 · 批次 6：HR 评估恢复与人工复核

此批基于用户上传的 **2026-10-20** 本地开发分支源码，不涉及腾讯云部署。

## 做了什么

1. 报告生成工作流：候选人正常完成后生成、HR 对丢失或失败的报告重新生成，复用同一套后端逻辑。
2. 持久化评估状态：`not_started`、`pending`、`generating`、`failed`、`ready`。旧报告即使状态字段为空，也按“已生成”显示。
3. MySQL 原子领取生成任务，避免并发请求重复调用 AI。生成任务超过 15 分钟可由 HR 重试；实际超时不等于取消旧的 API 调用，所以有并发防护。
4. HR 人工复核状态：`pending`（待复核）、`reviewed`（已复核）、`follow_up`（需后续沟通）及可编辑备注；**这些状态不是录用/淘汰结果**。
5. 招聘后台按候选人/岗位/编号、面试、报告、复核状态筛选。
6. HR 一键恢复已有已完成但未生成报告的面试，不要求候选人再次做题。

> 本批不支持自动录用、自动淘汰、批量重试、企业多租户或后台任务队列。AI 分数仅为辅助材料，所有结论须 HR 人工核实。

## 1. 检查分支并安装源码（Windows CMD）

先关闭本地 FastAPI 服务。在 `D:\projects\interview-pilot` 项目根目录解压 ZIP。ZIP 含 `batch6_payload`、`tools`、`docs`，**没有直接覆盖既有源码**。

```cmd
cd /d D:\projects\interview-pilot
git branch --show-current
git status --short
python tools\apply_batch6.py --check
```

必须在 `feat/hr-job-invitations` 分支，且没有未提交的受跟踪文件变更。确认检查通过再运行：

```cmd
python tools\apply_batch6.py
python -m compileall -q backend\main.py backend\app\models.py backend\app\admin_workflow.py backend\app\evaluation_workflow.py
```

脚本校验现有源码 SHA-256。发现上传后又修改过文件时会停止，**不要跳过校验**。脚本自动把被替换的旧文件备份至项目同级 `interview-pilot-v2-backups` 下的时间戳目录，不更改 MySQL。

## 2. 后端自动测试与前端构建

```cmd
cd /d D:\projects\interview-pilot\backend
python -m pytest -q tests\test_job_routes_v2.py tests\test_batch4_job_context.py tests\test_batch4_flow.py tests\test_batch5_structured.py tests\test_batch6_workflow.py
cd ..\frontend
npm run build
cd ..
```

新的 `test_batch6_workflow.py` 使用临时 SQLite 与假的评估函数，不请求 DeepSeek。此前 21 项应保持通过；本批新增 9 项测试。若已有测试由于依赖变更失败，**先停下来发送错误，不要迁移数据库**。

## 3. 备份本地 MySQL（必须先做）

这次需要对 `interviews` 表增加 6 个新字段。此前数据库中可能有多场真实测试，必须先备份。

```cmd
cd /d D:\projects\interview-pilot
mkdir D:\projects\interview-pilot-v2-backups
"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqldump.exe" -u root -p --single-transaction --routines --triggers --result-file="D:\projects\interview-pilot-v2-backups\interview_pilot_before_batch6.sql" interview_pilot

dir D:\projects\interview-pilot-v2-backups\interview_pilot_before_batch6.sql
findstr /C:"Dump completed on" D:\projects\interview-pilot-v2-backups\interview_pilot_before_batch6.sql
```

请确认 SQL 文件非零字节、带有 `Dump completed on`，否则停止。

迁移前先检查（用户名/端口若不同按本地实际情况调整）：

```cmd
"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" -u root -p interview_pilot -e "SHOW COLUMNS FROM interviews LIKE 'evaluation_state'; SHOW COLUMNS FROM interviews LIKE 'review_status'; SELECT COUNT(*) AS interview_count FROM interviews; SELECT COUNT(*) AS evaluation_count FROM evaluations;"
```

仅在**两个字段均不存在**的情况下执行一次迁移：

```cmd
"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" --default-character-set=utf8mb4 -u root -p interview_pilot < backend\migrations\20261020_hr_review_workflow.sql
```

如果已有一个字段但另一个没有，说明迁移不完整，**不要盲目重复执行**，先反馈。

成功后验证：

```cmd
"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" -u root -p interview_pilot -e "SHOW COLUMNS FROM interviews LIKE 'evaluation_state'; SHOW COLUMNS FROM interviews LIKE 'evaluation_error'; SHOW COLUMNS FROM interviews LIKE 'evaluation_started_at'; SHOW COLUMNS FROM interviews LIKE 'review_status'; SHOW COLUMNS FROM interviews LIKE 'review_note'; SHOW COLUMNS FROM interviews LIKE 'reviewed_at'; SELECT COUNT(*) AS interview_count FROM interviews; SELECT COUNT(*) AS evaluation_count FROM evaluations;"
```

预期六个新字段都存在，原有行数没有因迁移减少。SQL 与模型中不包含 `candidate_token_hash` 值，不会变更旧有候选人凭证。

**警告：** `20261020_hr_review_workflow_rollback.sql` 仅作为参考；运行会**永久删除新复核备注和状态**。未经确认、备份验证，不要执行回滚 SQL。

## 4. 本地页面验收

后端：

```cmd
cd /d D:\projects\interview-pilot\backend
python -m uvicorn main:app --reload
```

前端新开 CMD 终端：

```cmd
cd /d D:\projects\interview-pilot\frontend
npm run dev
```

登录 `http://localhost:5173/admin/login`。

- 进入 HR 后台 `/admin`：检查新增「评估状态」「人工复核」列和 4 个筛选条件（姓名/岗位/编号、面试状态、评估状态、复核状态）。旧面试报告应显示“报告已生成”。
- 打开一场**已完成且没有评估报告**的测试面试：应显示「待生成报告」和「重新生成 AI 评估报告」。单击一次后等待，后端将真实调用 DeepSeek（可能计费）。**如果数据库中没有这样的面试，可以不做付费恢复演示，自动测试已覆盖。**
- 打开已存在报告的面试（如之前的 #28，具体以数据库为准）：选择「需后续沟通」，填入简短测试备注，点击「保存人工复核」；刷新详情页和列表，状态/备注应仍存在。再改回「待人工复核」可检查状态重置。
- 测试筛选条件，确保显示匹配项。无需重做八道题。
- 浏览器候选人端依然不展示 HR 分数；自动测试也会检查候选人生成报告接口响应不包含分数。

边界条件：如果候选人浏览器在 AI 生成失败后关闭，HR 可使用恢复按钮；连续点击、多进程并发请求会返回 409 而非重复调用 AI。生成进程崩溃超过 15 分钟后可再次尝试。

## 5. 安全与交付

**现有管理员密码曾经在聊天中对外分享过**，将 V2 部署公网前，请更换真实管理员密码；避免使用 `123456` 作为具有完整权限的管理员密码。演示账号应另行隔离权限和虚构数据。

此批仍没有生产级后台任务队列、分布式限流、审计日志、多租户或个人信息数据保留策略。不要将它描述为可直接上线的商业化招聘系统。

Git 暂存（确认测试与 MySQL 迁移成功后）：

```cmd
cd /d D:\projects\interview-pilot
rmdir /s /q batch6_payload
git add backend\main.py backend\app\models.py backend\app\admin_workflow.py backend\app\evaluation_workflow.py backend\tests\test_batch6_workflow.py frontend\src\services\api.ts frontend\src\services\adminWorkflowApi.ts frontend\src\pages\AdminDashboardPage.tsx frontend\src\pages\AdminInterviewDetailPage.tsx tools\apply_batch6.py docs\V2_BATCH6_GUIDE.md
git add -f backend\migrations\20261020_hr_review_workflow.sql backend\migrations\20261020_hr_review_workflow_rollback.sql
git diff --cached --stat
git commit -m "feat: add HR evaluation recovery, review workflow and filters"
git status --short
```

不要提交 `.env`、API Key、MySQL 备份或源码 ZIP。暂时不要合并 `main` 或部署腾讯云。若一切顺利，可以选择 `git push origin feat/hr-job-invitations`。

## 6. 出错时怎么办

- **脚本指纹不匹配**：上传最新源码再生成差异；不要强行覆盖。
- **pytest 失败**：停止迁移；提供失败用例和最后 30 行日志。
- **SQL 错误**：停止，不要重复执行；保留本地数据库备份。
- **报告 502**：AI 失败状态持久化，稍后由 HR 重试。
- **报告 409**：表示正在生成、已有报告，或原请求被新请求取代，刷新状态再判断。
- **报告旧数据**：以前已生成的报告不用重新生成，详情状态会优先按数据库实际是否存在报告判断。
- **评估失败后的短暂并发**：不自动继续无限重试，避免意外大额 API 费用。

## 7. 开发记录

本批之后更新 `docs/V2_DEV_NOTES.md`，记录批次 6、提交号、数据库迁移、验证情况。发布线上前需要单独备份**服务器** MySQL，再运行对应迁移。**本指南所有数据库操作仅针对 Windows 本地。**
