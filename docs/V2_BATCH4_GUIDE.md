# InterviewPilot V2 · 第四批后端优化操作指南

> 适用项目：`D:\projects\interview-pilot`；仅本地 Windows；分支 `feat/hr-job-invitations`。
>
> 本批不改变 MySQL 表结构、不修改密钥配置、不部署到腾讯云。

## 1. 本批实现范围

1. HR 岗位要求参与邀请面试**首题生成**、**动态追问**和**AI 评估报告**的提示词；旧版无招聘任务的面试保持原来的参数调用方式。
2. 对公开的创建面试请求进行**演示级限流**：邀请码每分钟至多 5 次、每小时至多 20 次；所有面试创建入口合计每分钟 30 次。
3. 限流发生在 AI 调用前，以降低接口滥用带来的 AI 费用风险。受限请求返回 429 和 `Retry-After`。
4. 原候选人 Token、HR JWT、评估报告访问权限均保持不变。
5. 更新 HR 招聘任务页面中的旧提示文字。

**重要边界：** 招聘要求仍由 HR 手动录入，AI 生成结果并非客观可靠的能力证明。不要将真实候选人信息或敏感企业要求用于演示；AI 评价只能用于 HR 人工复核。

## 2. 解压前确认

在 **Windows 本地 VS Code CMD 终端**执行：

```cmd
cd /d D:\projects\interview-pilot
git branch --show-current
git status --short
```

确保是 `feat/hr-job-invitations` 分支，且 `git status --short` 无意料之外的输出；有改动先处理，不要覆盖。

将 ZIP **解压到项目根目录**：`D:\projects\interview-pilot`。

ZIP 会覆盖以下**你原本已有的**文件：

- `backend/app/job_routes.py`
- `backend/app/services/agent_service.py`
- `backend/app/services/evaluation_service.py`
- `backend/tests/test_job_routes_v2.py`（更新第二批单元测试，以兼容岗位要求参数）

ZIP 不会覆盖 `backend/main.py`；下一步用适配脚本针对你现有代码做精确修改。

新增文件：

- `backend/app/interview_create_limiter.py`
- `backend/tests/test_batch4_job_context.py`
- `backend/tests/test_batch4_flow.py`
- `tools/apply_batch4.py`
- `docs/V2_BATCH4_GUIDE.md`

## 3. 安全应用 main.py 与 HR 页面提示的修改

仍在项目根目录，运行：

```cmd
python tools\apply_batch4.py
python -m compileall -q backend\main.py backend\app\job_routes.py backend\app\interview_create_limiter.py backend\app\services\agent_service.py backend\app\services\evaluation_service.py
```

脚本会先检查旧代码中的位置是否与本批基础版本一致，**再写文件**，并在项目外保存备份：

- `D:\projects\interview-pilot-v2-backups\main_before_batch4.py`
- `D:\projects\interview-pilot-v2-backups\AdminJobsPage_before_batch4.tsx`

如果脚本提示找不到替换位置，**停止**并把错误发给我，不要自行粘贴猜测修改。

## 4. 运行自动化测试（不调用 DeepSeek、不写入本地 MySQL）

```cmd
cd /d D:\projects\interview-pilot\backend
python -m pytest -q tests\test_job_routes_v2.py tests\test_batch4_job_context.py tests\test_batch4_flow.py
cd ..
```

**预期：** `10 passed`。这些用例使用内存 SQLite 和模拟 LLM；不会产生真实 AI 费用，不会修改原来的 25 条面试记录。

如果失败，先保存报错，不要进行 Git 提交。

## 5. 构建前端

```cmd
cd /d D:\projects\interview-pilot\frontend
npm run build
cd ..
```

前端 UI 功能基本不变，但 `AdminJobsPage.tsx` 会更新说明文字，因此仍需要跑一次构建。

## 6. 本地业务验收（一次即可，使用虚构测试资料）

- 启动本地 FastAPI 与 React。
- HR 创建一条新招聘任务，要求写得**具体**，例如“熟悉 FastAPI 依赖注入、MySQL 索引、异步编程”。
- 复制该任务邀请链接，使用虚构姓名创建一次面试（将调用真实 DeepSeek）。
- 检查第一道题及追问是否合理涉及这些岗位知识点。大模型存在随机性，不保证每道题逐字包含岗位要求。
- 面试结束生成报告，从 HR 后台查看；候选人端不应直接看到报告。
- 若要测限流，使用自动测试即可，不要连续调用真实 AI 产生费用。
- 如仍需确认兼容性，可用旧版候选人入口进行一次测试，但无需为此反复付费调用。

## 7. 确认 Git 变更并提交到 V2 分支

```cmd
cd /d D:\projects\interview-pilot
git status --short
git add backend\main.py backend\app\job_routes.py backend\app\interview_create_limiter.py backend\app\services\agent_service.py backend\app\services\evaluation_service.py backend\tests\test_job_routes_v2.py backend\tests\test_batch4_job_context.py backend\tests\test_batch4_flow.py frontend\src\pages\AdminJobsPage.tsx tools\apply_batch4.py docs\V2_BATCH4_GUIDE.md
git commit -m "feat: use HR requirements in AI interview and rate limit creation"
git status --short
```

暂时不要合并 `main`，不要在腾讯云执行操作。检查成功后再安排后续 V2 部署。

## 8. 重要技术限制及下阶段计划

- 本批限流是**单进程内存版**；重启会重置额度，多 Worker/多服务器不会共享。正式公网使用 Redis/网关限流、身份验证和费用配额。
- 旧公开 `/api/interviews` 路由仍可创建演示面试，但已纳入全局 30 次/分钟限制；**这不是完整的抗滥用安全策略**。
- 未修改原有报告评分字段：`technical_score`、`completeness_score`、`clarity_score`、`overall_score`。下一批按 HR 反馈设计沟通、学习、执行能力的情境题和**有问答证据的评估**，不能只增加空泛分数。
- 新的岗位要求只影响之后生成的问题/报告，不会修改已保存的历史题目和已生成评估。
- 如果本地测试通过，我们会在部署前单独检查服务器数据库的 V2 迁移状态、备份和密钥，不能将本地 SQL 迁移当作腾讯云已经迁移。
