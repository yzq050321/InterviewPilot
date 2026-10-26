# InterviewPilot V2.2 开发记录

> 详细设计见 [`ARCHITECTURE.md`](ARCHITECTURE.md)，版本变更见根目录 [`CHANGELOG.md`](../CHANGELOG.md)。

## 项目目标

根据 HR 反馈，把个人 AI 模拟面试工具升级为 HR 主导的 AI 招聘面试系统：

1. B 端：减少招聘人员的重复操作。
2. C 端：除技术能力外，覆盖沟通、学习、执行能力。
3. 降低 HR 的使用门槛，并让面试结果真正进入后续招聘管理。

## 开发原则

- 本地测试通过后再部署服务器。
- 不提交 `.env`、API Key、管理员密码、数据库备份。
- 不使用真实候选人数据测试；Demo 只读虚构数据。
- AI 评分仅辅助 HR 人工复核，不自动录用/淘汰。
- 新增功能不能破坏既有候选人和 HR 流程。
- 每个批次集中完成多个相关任务，并补回归测试。

## 批次完成情况

| 批次 | 内容 | 状态 |
| --- | --- | --- |
| 1 | `JobPosting` 模型、开发记录 | 完成 |
| 2 | MySQL 迁移、`interview.job_id`、岗位/邀请 API | 完成 |
| 3 | HR 岗位管理、候选人邀请页、前后端联调 | 完成 |
| 4 | 岗位上下文、邀请流程、限流与权限测试 | 完成 |
| 5 | 四维结构化面试、证据校验 | 完成 |
| 6 | 报告状态机、并发租约、HR 重试与人工复核 | 完成 |
| 7 | 只读 Demo 账号与虚构数据隔离 | 完成 |
| 8 | 响应式 HR 岗位工作台、岗位详情、移动端导航 | 完成 |
| 9 | 招聘阶段、append-only 跟进历史、Demo pipeline | 完成 |
| 10A | 邀请有效期 7/14/30 天、过期 410、失败关闭 | 完成 |
| 10B | 答题幂等、`request_id`/`question_id`、15 分钟租约、刷新恢复 | 完成 |
| 7（成本） | AI 用量 telemetry、JSONL、离线汇总脚本 | 完成 |
| 11 (V2.2) | 简历 PDF/DOCX 解析、只存文本、简历驱动首题/追问/评估 | 完成 |

## V2.2 数据模型增量

- `interviews.resume_text`：解析后的简历文本，最多 8000 字。
- `interviews.resume_filename`：展示用文件名，不保存原文件。
- `interviews.resume_consent_at`：候选人同意将简历文本用于本次面试的时间。

## V2.1 数据模型增量

- `job_postings.invite_expires_at`：UTC 到期时间；旧岗位迁移时给 7 天宽限期。
- `interviews.recruitment_stage`：`new / contact / next_round / decision / closed`。
- `interview_followups`：append-only 阶段变化与备注历史。
- `interview_answer_attempts`：`(interview_id, question_id)` 唯一，`request_id` 唯一，记录 `processing / done / failed` 与缓存的下一题。

## 验证记录（2026-10-26）

- `python -m pytest -q`：71 个用例；当前沙箱 66 passed（排除 5 个用量测试），普通本地环境应全部通过。
- 新增简历解析/简历面试测试 12 个。
- `npm run build`：通过（TypeScript + Vite）。
- `python -m compileall`：通过。
- 线上演示：<https://vm-0-12-ubuntu.tail2c8f81.ts.net/>

## 已知边界

当前仍是单机、单租户的可运行原型：没有 Redis/任务队列、没有 Alembic、没有审计日志与数据保留策略，限流为进程内内存实现。简历文本属于 PII，当前没有 TTL/删除接口/字段加密；扫描版 PDF 不支持 OCR。生产化路线见 README 的“项目边界”和“后续计划”。
