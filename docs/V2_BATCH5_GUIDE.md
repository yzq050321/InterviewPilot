# InterviewPilot V2 第五批：结构化综合能力面试与证据化报告

> 仅适用于 Windows 本地 `feat/hr-job-invitations` 分支。**先备份再改库**。本批不要部署腾讯云，也不要合并 `main`。

## 这批做了什么

- HR 邀请创建的面试按服务器控制的固定八答顺序进行：技术（第1/2答）、沟通（第3/4答）、学习（第5/6答）、执行（第7/8答）。
- 首题仍来自原来的岗位技术出题；第1答后技术追问，第2答后进入沟通情境；其余按阶段切换，每阶段包含一次情境题和一次追问。
- 第8次回答后提示“结束面试”，不再调用 AI 生成第9题。候选人仍可手动提前结束，未覆盖维度不会被硬评。
- 招聘邀请面试的 HR 报告新增四维文字情境评估；每个有分数的维度必须能从候选人对应阶段回答中**逐字找到证据**，否则该维度为未评分。
- 旧版独立面试保持既有技术提问逻辑，历史评估数据不受影响。
- 修复候选人生成报告响应泄露 `overall_score` 的问题：候选人只能得到“已生成”确认，HR JWT 仍可查看分数与报告。

**重要限制**：这些分数不能代表实际工作能力、人格或录用概率。简短文字回答只是有限证据；HR 必须人工复核。不要使用真实候选人隐私数据测试。

## 0. 前置检查：不能省略

在 Windows 本地 VS Code CMD 终端：

```cmd
cd /d D:\projects\interview-pilot
git branch --show-current
git status --short
```

应为 `feat/hr-job-invitations`。工作区如有你自己的修改，先保存/提交；之前的 `V2_batch4_sources.zip` 等临时文件可以在项目外保留，不要提交。

停止本地正在运行的 uvicorn（在它的终端按 `Ctrl+C`），然后把 ZIP **解压到项目根目录** `D:\projects\interview-pilot`，允许覆盖压缩包内列出的源文件。不要覆盖整个 `backend` 文件夹；保持原有目录不变。

本 ZIP 实际会覆盖：`backend/main.py`、`backend/app/models.py`、`backend/app/services/agent_service.py`、`backend/app/services/evaluation_service.py`、`frontend/src/pages/AdminInterviewDetailPage.tsx`；新增 `backend/app/structured_interview.py`、迁移 SQL、本指南与新测试。包内不包含 `.env`、模型密钥、数据库连接配置或完整数据库。

## 1. 代码语法与编译

```cmd
cd /d D:\projects\interview-pilot
python -m compileall -q backend\main.py backend\app\models.py backend\app\structured_interview.py backend\app\services\agent_service.py backend\app\services\evaluation_service.py
cd backend
python -m pytest -q tests\test_job_routes_v2.py tests\test_batch4_job_context.py tests\test_batch4_flow.py tests\test_batch5_structured.py
cd ..
cd frontend
npm run build
cd ..
```

通过预期：之前 10 项 + 本批 11 项 = **21 passed**，并且 `npm run build` 成功。以上测试用 SQLite、模拟 AI，不调用真实 DeepSeek、不修改本地 MySQL。

如果失败，请停止，保留完整报错，不要迁移数据库。

## 2. 备份本地 MySQL（先备份）

根据你本机实际安装的是 MySQL 8.4，使用你之前已验证的可执行文件路径：

```cmd
mkdir D:\projects\interview-pilot-v2-backups
"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqldump.exe" -u root -p --single-transaction --routines --triggers --result-file="D:\projects\interview-pilot-v2-backups\interview_pilot_before_batch5.sql" interview_pilot
```

**不要将这个备份放进 Git 仓库**。输入本地 MySQL 密码时不会显示字符。若你的本地用户名或连接端口已变，以实际配置为准，不要误操作腾讯云数据库。

验证备份：

```cmd
dir D:\projects\interview-pilot-v2-backups\interview_pilot_before_batch5.sql
findstr /C:"Dump completed on" D:\projects\interview-pilot-v2-backups\interview_pilot_before_batch5.sql
```

必须**非 0 字节**且有完整导出结束标记。未通过就停止。

## 3. MySQL 本地迁移（只执行一次）

先检查新字段是否已经存在：

```cmd
"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" -u root -p interview_pilot -e "SHOW COLUMNS FROM evaluations LIKE 'competency_assessment'; SELECT COUNT(*) AS existing_interviews FROM interviews;"
```

若 `competency_assessment` 已存在，**跳过迁移，直接验证**。若不存在，在项目根目录执行：

```cmd
cd /d D:\projects\interview-pilot
"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" --default-character-set=utf8mb4 -u root -p interview_pilot < backend\migrations\20261019_competency_assessment.sql
```

出现 SQL 错误就停止，不要重复执行。迁移仅为 `evaluations` 表增加一个允许 NULL 的 JSON 字段，不会删除或重写原有记录。

验证：

```cmd
"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" -u root -p interview_pilot -e "SHOW COLUMNS FROM evaluations LIKE 'competency_assessment'; SELECT COUNT(*) AS existing_interviews FROM interviews; SELECT COUNT(*) AS existing_evaluations FROM evaluations;"
```

应看到 `competency_assessment` 类型为 `json`、可空 `YES`，旧数据仍存在。

## 4. 本地业务验收（会产生真实 AI API 费用）

分别启动：

```cmd
cd /d D:\projects\interview-pilot\backend
python -m uvicorn main:app --reload
```

```cmd
cd /d D:\projects\interview-pilot\frontend
npm run dev
```

- HR 登录 `/admin/login` 并在 `/admin/jobs` 新建一条**虚构岗位**，复制邀请链接。
- 使用虚构的候选人名称进入邀请面试；连续回答八次，依次应出现技术追问、沟通情境及追问、学习情境及追问、执行情境及追问、结束提示。
- 最终点击“结束面试”，系统生成报告后 HR 在对应详情页看到四维新面板，证据摘录必须来自本次候选人真实回答。
- 若提前结束（例如只回答两次），HR 报告中未覆盖的维度应显示“证据不足 · 未评分”，而不是虚构分数。
- 通过浏览器开发者工具也不应能从候选人的 `POST /api/interviews/{id}/evaluation` 响应中读取 `overall_score` 或四维报告；HR JWT 的 GET 报告仍正常。

**业务说明**：原有候选人面试页面允许主动结束，因此八次回答属于“完整覆盖”路径，而不是强制候选人完成的要求。文字情境评分不是实际沟通能力或实际执行能力的直接测量。

## 5. Git 提交

在 Windows 项目根目录：

```cmd
cd /d D:\projects\interview-pilot
git status --short
git add backend\main.py backend\app\models.py backend\app\structured_interview.py backend\app\services\agent_service.py backend\app\services\evaluation_service.py backend\tests\test_batch5_structured.py frontend\src\pages\AdminInterviewDetailPage.tsx docs\V2_BATCH5_GUIDE.md
git add -f backend\migrations\20261019_competency_assessment.sql
git diff --cached --stat
git commit -m "feat: add structured competency interview and evidence-based HR report"
git status --short
```

若工作区只剩源码打包 ZIP 的 `??`，可将临时 ZIP 移出仓库，**不要提交 `.env`、备份 SQL 或源码 ZIP**。这次 SQL 是可信的表结构迁移，才需要 `git add -f`，不要对整个目录使用 `-f`。

## 6. 失败与回滚

- **自动测试失败**：不要迁移，保留报错。Git 恢复已提交版本的方法是先确认要舍弃本批改动，随后针对本批源文件逐个 `git restore`；不要随意运行 `git reset --hard`。
- **SQL 迁移失败**：停止，记录完整错误。若已经新增字段，不要二次执行。
- **代码回退后数据库多出可空字段**：对旧版 SQLAlchemy 代码通常无影响，可以先保留；不要急于删除字段。
- **必须完全回滚数据库**：先确认没有要保留的新报告，再评估删除新 JSON 列或恢复备份。恢复备份会覆盖现有数据库数据，不能在未确认时执行。
- 腾讯云仍运行稳定的 V1，不受本地 V2 开发影响；**不得直接对线上服务器执行本迁移**。

## 7. 项目记录

本地 `docs/V2_DEV_NOTES.md` 可在提交成功后追加：

`批次 5：结构化八答面试、四维证据化评估、候选人评估 POST 不再返回评分；本地 DB evaluations 新增 competency_assessment JSON；待线上部署。`

## 验收后一次性反馈

告诉我：`pytest` 结果、`npm run build` 结果、本地迁移检查结果、八次回答后的 HR 新报告截图（虚构信息）、Git 提交结果。
