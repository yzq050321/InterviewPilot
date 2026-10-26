# Changelog

## v2.2.0 — 2026-10-26

### Added

- **简历上传与解析**：候选人邀请页支持 PDF / DOCX（5 MB、20 页），后端只保存解析文本、文件名和同意时间，不保存原文件。
- **简历驱动面试**：首题优先从简历中与岗位相关的项目切入；技术追问与软技能题可携带简历背景。
- **简历感知评估**：简历仅作为背景参考，Prompt 明确要求评分证据必须来自面试回答。
- **新接口**：`POST /api/job-invitations/{invite_code}/interviews/with-resume`（multipart）。
- **新迁移**：`20261026_resume_interview.sql`，为 `interviews` 增加 `resume_text / resume_filename / resume_consent_at`。
- **测试**：新增 6 个简历解析测试 + 6 个简历面试 API 测试；总计 71 个用例。

### Security / Privacy

- 简历文本按不可信数据注入，JSON 编码，明确不是系统指令。
- 限制文件大小、页数、DOCX 解压后大小；扫描版 PDF 明确拒绝，不做 OCR。
- 前端要求勾选同意后才能提交；原文件不上传、不落盘。

## v2.1.0 — 2026-10-24

### Added

- **HR 招聘工作台**：岗位统计、搜索/状态筛选、岗位详情、面试筛选、响应式布局与移动端底部导航。
- **招聘阶段与跟进**：`recruitment_stage`（new / contact / next_round / decision / closed）、append-only `interview_followups` 历史、备注必填、行锁事务；与 AI 复核状态独立。
- **邀请有效期**：创建岗位可选 7 / 14 / 30 天；过期返回 410，且在 AI 调用前拒绝；NULL 失败关闭；已有面试不受影响。
- **答题幂等与恢复**：`request_id + question_id`、`interview_answer_attempts` 唯一约束、15 分钟租约、重放缓存、结束面试时拦截处理中答题。
- **AI 用量记录**：`MODEL_USAGE_ENABLED=1` 可选开启，JSONL 记录 stage / trace / token / 耗时 / 估算费用；不记录正文、密钥或邀请码。
- `docs/ARCHITECTURE.md`：请求链路、数据模型、关键取舍、失败矩阵与代码阅读顺序。
- `/api/health`：供 Nginx 反代后的公网探活使用，返回服务名与版本。

### Changed

- 重写 README：补充 V2.1 功能、架构图、数据模型、接口表、关键设计取舍、测试与部署说明。
- 前端 `index.html`：补齐中文标题、description、Open Graph 与 theme-color，替换 Vite 默认标题。
- 候选人首页默认岗位改为「Python 后端开发实习生」，与目标岗位和演示截图保持一致。
- FastAPI 版本号更新为 `2.1.0`，补充 API 描述。
- `.env.example` 补齐管理员、Demo、AI 用量与 DashScope 配置。
- `requirements.txt` 改为直接依赖范围，移除 torch/transformers 等未使用的大依赖。
- `.gitignore` 修复对 `backend/migrations/*.sql` 的误伤，迁移文件可正常 `git add`。

### Fixed

- 新增 `backend/pytest.ini`，将测试范围限定为 `backend/tests/`；此前 `pytest -q` 会收集根目录下会真实调用模型的临时脚本，导致收集失败。
- HR 面试详情页的 `strengths / weaknesses / suggestions` 按列表渲染；后端返回 JSON 数组，原先直接渲染会缺少分隔和项目符号。
- `has_active_attempt` 只把租约内（15 分钟）的 `processing` 记录视为进行中；worker 崩溃留下的过期记录不再永久阻止候选人结束面试。
- 前端生产 API 使用同源 `/api`，开发环境由 Vite proxy 转发，避免写死 `127.0.0.1:8000`。

### Verification

- `python -m pytest -q`：59 个用例（当前沙箱 56 passed，3 个用量测试受临时目录权限限制；在普通本地环境应全部通过）。
- `npm run build`：通过（TypeScript + Vite）。
- `python -m compileall`：通过。
