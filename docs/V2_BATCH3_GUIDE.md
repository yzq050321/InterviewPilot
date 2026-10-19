# InterviewPilot V2 第一阶段 · 批次 3：HR 招聘任务前端

**来源**：以你上传的 `frontend/src` 源码和上一批 `backend/app/job_routes.py` 接口为依据。

## 本批交付

- HR 后台增加「管理招聘任务」入口，进入 `/admin/jobs`。
- HR 可以创建任务、查看任务列表、复制邀请链接、停用任务。
- 候选人通过 `/invite/:inviteCode` 查看招聘岗位要求，填写姓名，开始 AI 面试。
- 新建面试仍使用现有的候选人 Token、聊天、结束面试、评估报告生成流程。
- 兼容旧版首页 `/`、现有 HR 列表 `/admin` 与详情 `/admin/interviews/:id`。

**暂未实现**：重新启用已停用任务、岗位要求参与 Agent 提示词、邀请链接访问限流、按任务独立统计候选人；后续专门完善。这批不能直接部署到公网。

## 一、解压并覆盖前端对应源码

**只允许在 Windows 本地项目的 V2 开发分支上操作，暂不动腾讯云。**

1. 在 VS Code Windows CMD 终端：

   ```cmd
   cd /d D:\projects\interview-pilot
   git branch --show-current
   git status --short
   ```

2. 确认是 `feat/hr-job-invitations`，且没有意外的未提交修改。若有，请先停止确认。

3. 将 `InterviewPilot_V2_Batch3_Frontend.zip` **解压到 `D:\projects\interview-pilot` 项目根目录**。

   ZIP 内已经包含 `frontend/` 和 `docs/` 两个目录。Windows 提示合并文件夹、覆盖同名文件时，**核对列表必须仅有以下三个既有文件**，才同意覆盖：

   - `frontend/src/App.tsx`
   - `frontend/src/App.css`
   - `frontend/src/pages/AdminDashboardPage.tsx`

   实际需要覆盖的只有 **3 个文件**：`App.tsx`、`App.css`、`AdminDashboardPage.tsx`。`jobApi.ts` 和两个页面是新增文件。若覆盖提示出现其他文件，请暂停。

4. 解压完成后检查新文件：

   ```cmd
   dir frontend\src\pages\AdminJobsPage.tsx
   dir frontend\src\pages\JobInvitationPage.tsx
   dir frontend\src\services\jobApi.ts
   ```

## 二、前端构建验证（无需启动 AI）

```cmd
cd /d D:\projects\interview-pilot\frontend
npm run build
```

**要求**：输出构建成功，不出现 TypeScript 错误。如报错停止，不要执行后面的 Git 提交或云端部署。

## 三、启动本地后端与前端

确保你已完成批次 2 的本地 MySQL 迁移，已存在 `job_postings` 表与 `interviews.job_id` 列；原有 25 条面试应保留。

### 终端 A（Windows CMD）

```cmd
cd /d D:\projects\interview-pilot\backend
python -m uvicorn main:app --reload
```

### 终端 B（Windows CMD）

```cmd
cd /d D:\projects\interview-pilot\frontend
npm run dev
```

在浏览器打开 `http://localhost:5173/admin/login`。

**注意**：本地 Vite 开发模式通过 `http://127.0.0.1:8000` 调 API；请确认本地后端监听 8000 端口。生产模式则通过当前 HTTPS 网站的 `/api` 调用。

## 四、端到端手工验收（使用虚构候选人）

1. 登录本地 HR 管理后台（使用本地 HR 凭据，勿外传），进入 `/admin`。原有候选人列表应保留。
2. 点击「管理招聘任务」进入 `/admin/jobs`；填写：
   - 任务名：`V2 功能验收 - Python 后端实习`；
   - 岗位：`Python 后端实习生`；
   - 要求：`熟悉 Python、FastAPI、MySQL`；
   - 难度：`中等`。
3. 创建任务后，应在列表看到新任务，状态「进行中」，且显示 `/invite/...` 链接。
4. 复制邀请链接，在**同一台电脑的另外一个浏览器标签页**打开；应看到岗位、要求、难度和姓名输入框。
5. 输入虚构候选人名，如「演示候选人V2」，点击「开始 AI 面试」。**这一步会真正调用 DeepSeek，可能需要等待几十秒并产生费用；只运行一次。**
6. 能进入 `/interview/{id}`，看到 AI 第一题；提交一条测试回答；结束面试，生成报告（也会调用 AI）。HR 后台刷新后应看到新面试，可进入详情并查看报告。
7. 回到 `/admin/jobs`，停用该招聘任务；刷新旧邀请链接，应提示邀请无效或已停用。旧面试记录依旧能在 HR 后台读取。
8. 打开旧首页 `/`，确认仍可填写候选人及岗位；原有 HR 详情 `/admin/interviews/{id}` 正常。

**注意**：邀请链接是可转发的；只用于本地测试。当前邀约 API 暂未实现限流，不能在公网发布。

## 五、异常处理与回滚

- **浏览器打不开 `/admin/jobs`**：先看 `npm run build` 是否成功；确认刷新访问的是本地开发网站而非旧 Cloudflare 链接。
- **401**：重新登录本地 HR；不需要修改管理员密码或 JWT 配置。
- **500 / `job_postings` 不存在**：确认本地 MySQL 已按上一批迁移，不能重复执行迁移 SQL。
- **502 / 504（创建面试）**：是 AI 服务调用失败或超时，前端页面其他流程可单独验收；不要反复点击以避免费用。
- **前端编译失败**：停止提交，发错误日志。不需要修改数据库或重部署。
- **需要撤销本次前端改动**：若尚未提交 Git，可在项目根目录执行下列命令（**会撤销此批覆盖的三个既有前端文件，请确保这些文件无其他想保留的更改**）：

  ```cmd
  git restore -- frontend/src/App.tsx frontend/src/App.css frontend/src/pages/AdminDashboardPage.tsx
  ```

  新增文件由你自行确认后删除。不要使用 `git clean -fd` 或 `git reset --hard`。

## 六、提交到当前 V2 分支

**仅在本地测试通过后执行**：

```cmd
cd /d D:\projects\interview-pilot

git status --short

git add frontend/src/App.tsx frontend/src/App.css frontend/src/pages/AdminDashboardPage.tsx frontend/src/pages/AdminJobsPage.tsx frontend/src/pages/JobInvitationPage.tsx frontend/src/services/jobApi.ts docs/V2_BATCH3_GUIDE.md

git commit -m "feat: add HR job management and candidate invitation pages"

git status --short
```

不要执行 `git push origin main`；也暂时不要部署到腾讯云。

## 开发记录建议

在 `docs/V2_DEV_NOTES.md` 批次 3 一栏补充完成情况，例如：前端构建是否通过、HR 创建任务测试结果、AI 邀请面试测试结果、需要后续完成的限流及 Agent 岗位要求接入。

## 下一批计划

- 将岗位要求真正传入 Agent 出题上下文；
- 邀请接口按 IP/任务限流及失败处理，降低公开链接滥用风险；
- HR 任务按岗位统计候选人、评估与人工复核；
- 实现综合能力维度提问与有依据的评分；
- 通过整体验收后再部署云端。
