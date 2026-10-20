# InterviewPilot — AI 智能面试与招聘管理系统

> 面向招聘初筛场景的全栈 AI 应用原型：**HR 发布招聘任务 → 生成邀请链接 → 候选人参与结构化 AI 面试 → 生成辅助评估报告 → HR 人工复核**。
>
> **项目定位：**个人独立开发及业务试点探索项目，当前用于技术展示和模拟招聘流程；AI 评估仅供人工参考，不应用作自动录用、淘汰或其他高影响招聘决定。

**在线演示：** https://vm-0-12-ubuntu.tail2c8f81.ts.net/  
**HR 登录入口：** https://vm-0-12-ubuntu.tail2c8f81.ts.net/admin/login  
**GitHub V2 开发分支：** [`feat/hr-job-invitations`](https://github.com/yzq050321/InterviewPilot/tree/feat/hr-job-invitations)

演示站点运行在腾讯云服务器上，通过 Tailscale Funnel 提供 HTTPS 访问。演示入口可能受服务器及隧道运行状态影响。独立的 HR Demo 账号仅能查看**虚构样例数据**，如需体验请向项目维护者索取临时演示凭证；不公开正式管理员凭证。

## 项目功能

### HR 招聘管理端

- **招聘任务管理：**创建、查看和管理招聘岗位，配置岗位名称、岗位要求与面试难度，生成候选人专属招聘邀请入口。
- **候选人管理：**搜索和筛选面试记录，查看面试状态、AI 报告生成状态和 HR 人工复核状态。
- **面试详情：**按顺序查看完整问答、技术与情境能力评估、证据及改进建议。
- **人工复核：**由 HR 记录审核状态及备注，AI 评分仅作为辅助信息。
- **报告状态与恢复：**对生成中、已完成及失败状态进行跟踪，支持符合条件的重试，减少重复生成问题。
- **独立演示身份：**只读 Demo 工作台使用预置虚构任务、候选人和报告，不查询真实 MySQL 招聘数据，也不触发 AI 调用。

### 候选人面试端

- 通过 HR 邀请链接进入对应岗位的 AI 面试；根据招聘任务要求进行**八道结构化题目**，覆盖技术理解、沟通、学习和执行等维度。
- 根据此前回答组织上下文与动态追问，支持主动结束面试。
- 使用每场面试独立的随机访问凭证保护会话；候选人端不展示 HR 专用评分及完整评估报告。

### 大语言模型与知识检索

- **DeepSeek + LangChain：**生成面试题、动态追问及辅助评估。
- **RAG：**通过 Qwen Embedding 和 Chroma 对技术文档进行向量化检索。
- **Tool Calling：**在需要时让面试 Agent 调用知识检索工具，辅助组织相关技术问题。
- 当前知识库以部分 Python 后端相关知识为主，属于小规模验证，尚未形成覆盖全部岗位的企业级知识库。

## 页面预览

以下截图来自项目早期的页面展示，部分功能与样式可能已随 V2 迭代发生变化；正式投递前建议替换为最新截图，并使用虚构测试数据。

| 候选人首页 | AI 面试问答 |
| --- | --- |
| ![候选人入口](docs/candidate-home.png) | ![AI 面试问答](docs/ai-interview.png) |

| HR 招聘后台 | HR 评估报告 |
| --- | --- |
| ![HR 招聘管理](docs/hr-dashboard.png) | ![HR 评估报告](docs/hr-report.png) |

## 典型业务流程

```text
HR 创建招聘任务并生成邀请链接
                ↓
候选人进入岗位面试 → 服务器校验会话凭证
                ↓
FastAPI 组织岗位要求 / 既有问答 / 阶段信息
                ↓
LangChain + DeepSeek（按需查询 RAG 知识）
                ↓
SQLAlchemy / MySQL 持久化面试与问答
                ↓
候选人结束面试 → AI 评估状态跟踪与报告生成
                ↓
HR 查看报告、核对回答证据并人工复核
```

## 技术架构

| 层次 | 实现 |
| --- | --- |
| Web 前端 | React、TypeScript、Vite、React Router |
| 后端 API | Python、FastAPI、Pydantic |
| 数据持久化 | MySQL、SQLAlchemy |
| 大模型与 Agent | DeepSeek、LangChain、Tool Calling |
| 知识检索 | Qwen Embedding、Chroma |
| 登录与授权 | bcrypt、JWT、候选人随机访问 Token、按身份限制 API |
| 自动化测试 | pytest（关键招聘、面试和权限场景） |
| 部署 | 腾讯云 Lighthouse、Ubuntu、Nginx、systemd、Tailscale Funnel |

**安全边界：**正式管理员与只读 Demo 使用不同角色；Demo JWT 不能读取管理员招聘任务或真实候选人记录。候选人也不能通过猜测面试编号读取他人问答或 HR 评估内容。这些措施属于当前原型的基础防护，不代表系统已经通过企业生产环境的完整安全、合规与隐私审计。

## 本地开发

**前置要求：**Python、Node.js、MySQL，以及有权限使用的 DeepSeek / Embedding API 服务。具体版本以项目依赖清单为准。

1. 获取源码并进入 `feat/hr-job-invitations` 分支：

   ```bash
   git clone https://github.com/yzq050321/InterviewPilot.git
   cd InterviewPilot
   git switch feat/hr-job-invitations
   ```

2. 创建并激活 Python 虚拟环境，在 `backend` 目录安装依赖：

   ```bash
   cd backend
   python -m venv .venv
   # Windows CMD: .venv\Scripts\activate
   # Linux/macOS: source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. 根据 `backend/.env.example` 创建本地 `backend/.env` 并填入开发环境的数据库与 API 配置；还需设置 `ADMIN_USERNAME`、`ADMIN_PASSWORD_HASH` 与足够长度的随机 `ADMIN_JWT_SECRET`。如需启用只读 Demo，再配置 `DEMO_USERNAME` 和 `DEMO_PASSWORD_HASH`。所有密码哈希使用项目已有的 `hash_password` 工具生成，**不要提交真实密钥或 `.env`**。

4. 创建独立的本地 MySQL 数据库，按项目当前数据库模型和 `backend/migrations/` 中的 SQL 迁移说明**依次**准备表结构。迁移前备份；每条已执行迁移不要重复运行。此项目目前不是一键自动迁移的全新数据库安装程序，请根据迁移文件检查依赖关系，不要直接在已有生产库上试验。

5. 根据需要构建知识库，然后启动后端：

   ```bash
   python build_knowledge.py
   python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```

   本地接口文档： http://127.0.0.1:8000/docs

6. 在另一个终端启动前端：

   ```bash
   cd frontend
   npm ci
   npm run dev
   ```

   浏览器访问 Vite 终端输出的本地地址（通常为 http://localhost:5173 ）。

## 验证与测试

在 `backend` 目录运行关键测试：

```bash
python -m pytest -q tests/test_job_routes_v2.py tests/test_batch4_job_context.py tests/test_batch4_flow.py tests/test_batch5_structured.py tests/test_batch6_workflow.py tests/test_demo_account.py
```

这组测试曾在 V2 演示验收时通过 **36 项**；是否继续通过以当前源码实际执行结果为准。前端生产构建：

```bash
cd frontend
npm run build
```

发布前还应回归测试：招聘任务与邀请、完整面试、报告生成与失败重试、HR 人工复核，以及 Demo Token 无法访问真实管理员 API。

## 演示与部署说明

- 生产前端静态资源由 Nginx 托管，`/api` 请求反向代理到本机 FastAPI。
- FastAPI 由 `interviewpilot.service` 管理，MySQL 用于存储业务记录。
- 演示站点目前通过 **Tailscale Funnel** 提供固定格式的 HTTPS 访问地址，**并不代表配备独立购买的域名或生产级 SLA**。
- 开发环境与服务器生产环境的前端 API 基地址可能不同；生产构建应使用同源 `/api` 路径，不要把本地 `127.0.0.1:8000` 打包到公网网页中。
- 不公开正式管理员密码；如对外提供演示凭证，应限时使用并根据需要关闭 Demo 账号。

## 现阶段限制与 V2.1 计划

当前项目已完成可演示的招聘业务闭环，仍属于**业务试点原型**。正式用于企业招聘前还需进一步完善真实候选人授权、隐私保留与删除、审计日志、稳定性监控及多用户权限设计。

下一阶段围绕实际 HR 工作流重点推进：

- 按岗位组织招聘工作台、候选人进展和人工复核。
- 记录 LLM 调用 Token、耗时和成本，对照不同低成本模型。
- 优化面试报告证据展示、失败恢复及业务操作效率。
- 对生产化需求进行额外的安全、隐私与可靠性验证。

## 项目性质

InterviewPilot 是个人独立开发的 AI 应用项目。AI 对候选人回答所生成的分数和建议存在不确定性，应由 HR 结合岗位要求和其他材料进行人工复核；不建议把模型评分作为招聘自动化决策的唯一依据。
