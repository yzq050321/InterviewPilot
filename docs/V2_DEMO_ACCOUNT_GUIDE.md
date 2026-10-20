# InterviewPilot V2：独立 HR Demo 账号（只读、虚构数据）

## 这次实现的范围

- **正式管理员完全保留**：现有 `ADMIN_USERNAME`、`ADMIN_PASSWORD_HASH`、`ADMIN_JWT_SECRET` 不用更改。
- **Demo 账号必须手动启用**：新增 `DEMO_USERNAME` 和 `DEMO_PASSWORD_HASH`，不提供默认账号密码。
- **Demo JWT 是 `role=demo`**，与原有 `role=admin` 区分，过期时间均为 2 小时；所有原有写接口依旧只允许 admin。
- Demo 只允许访问 `/api/demo/*` 下四个 **GET** 演示接口，它们只返回代码中人工编写的虚构岗位、面试问答和报告；**不会查询真实 MySQL、不会调用 DeepSeek、不会修改招聘业务记录**。
- 前端登录后区分 Demo / 管理员：Demo 能浏览候选人筛选、虚构岗位、虚构问答与四维报告；不可创建招聘任务、生成真实邀请码、重试报告或提交人工复核。
- **无需 MySQL 迁移**，不接触腾讯云线上服务器，直到本地回归成功。

> **产品取舍**：为避免 Demo 凭证访问真实候选人和消耗 AI 额度，本版 Demo 是只读样例，不支持真正创建岗位/面试。如果 HR 要操作完整真实流程，仍由正式管理员发放独立测试招聘邀请并控制预算。不要把真实 HR 凭证交给 HR 体验方。

## 1. Windows 本地安装（仅限 `feat/hr-job-invitations` 分支）

先在 Windows 本地把 ZIP 的**内容直接解压**到 `D:\projects\interview-pilot`，应出现：

```
interview-pilot\
  demo_auth_payload\
  tools\apply_demo_auth.py
  docs\V2_DEMO_ACCOUNT_GUIDE.md
```

使用 VS Code **CMD** 终端，不要在腾讯云上运行下面的 Windows 命令：

```cmd
cd /d D:\projects\interview-pilot
git branch --show-current
git status --short
python tools\apply_demo_auth.py --check
```

`--check` 必须出现所有文件 `OK`。如果出现 `MISMATCH`、`ALREADY EXISTS` 或 `STOP`，**不要强行覆盖**，把原始输出发回来。检查通过再执行：

```cmd
python tools\apply_demo_auth.py
python -m compileall -q backend\main.py backend\app\admin_auth.py backend\app\demo_routes.py
```

脚本将原文件备份到**项目目录外**的 `D:\projects\interview-pilot-v2-backups\demo-auth-...` 文件夹，并且只更改本批指定的文件。注意解压过程中不需要覆盖任何已有源码；源码位于 `demo_auth_payload/`，由脚本检查后安装。

## 2. 配置本地 Demo 账号，不粘贴任何明文密码到聊天

从项目根目录执行：

```cmd
cd /d D:\projects\interview-pilot\backend
python -c "from app.admin_auth import hash_password; import getpass; print('DEMO_PASSWORD_HASH=' + hash_password(getpass.getpass('输入独立演示密码: ')))"
```

终端会交互式读入密码（不会回显），然后打印 **bcrypt 哈希**。选择**与管理员不同**且不易猜测的至少 12 位密码/长口令。请将结果只复制到本地 `backend/.env`，并添加：

```text
DEMO_USERNAME=hrdemo
DEMO_PASSWORD_HASH=<填入刚刚得到的 bcrypt 哈希，别保留尖括号>
```

不要修改 `ADMIN_*` 现有配置，不要把 `.env` 加入 Git，也不要把实际密码发给助手。未配置这两个变量时，Demo 登录自动关闭；移除这两个变量后，已有 Demo JWT 也会被拒绝。

## 3. 测试（先后端，再前端）

请确保本地 MySQL 启动且 `.env` 配置完整。**下面的测试使用预置虚构样本和假数据，不调用 DeepSeek，也不会修改真实 MySQL。**

```cmd
cd /d D:\projects\interview-pilot\backend
python -m pytest -q tests\test_job_routes_v2.py tests\test_batch4_job_context.py tests\test_batch4_flow.py tests\test_batch5_structured.py tests\test_batch6_workflow.py tests\test_demo_account.py
```

预期为原有 30 项 + 本批 6 项，即 `36 passed`（仍以 Windows 本地实际结果为准）。

```cmd
cd /d D:\projects\interview-pilot\frontend
npm run build
```

两项都通过后分别启动 `uvicorn main:app --reload` 和 `npm run dev`，打开 `http://localhost:5173/admin/login`：

1. 用 `hrdemo` 和刚设置的独立密码登录：看到 **只读演示** 提示，列表只有虚构候选人；可以按状态筛选、查看模拟四维报告；无创建任务或复核保存按钮。
2. 用真正的管理员账号登录：仍能看到原有真实招聘任务和候选人，创建/复核等按钮正常。
3. 可选：用 Demo JWT 请求 `/api/admin/jobs`、`/api/interviews`，应该收到 401；正常无需手工抓取 Token，自动化测试已有覆盖。

## 4. Git 提交（只在 Windows 本地）

```cmd
cd /d D:\projects\interview-pilot
git add backend\main.py backend\app\admin_auth.py backend\app\demo_routes.py backend\tests\test_demo_account.py frontend\src\pages\AdminLoginPage.tsx frontend\src\pages\AdminDashboardPage.tsx frontend\src\pages\AdminInterviewDetailPage.tsx frontend\src\pages\AdminJobsPage.tsx frontend\src\services\api.ts frontend\src\services\jobApi.ts tools\apply_demo_auth.py docs\V2_DEMO_ACCOUNT_GUIDE.md
git diff --cached --stat
git commit -m "feat: add isolated read-only HR demo account"
git push origin feat/hr-job-invitations
git status --short
```

**严禁提交**：`backend/.env`、各种备份 `.sql`、`demo_auth_payload/`、下载的 ZIP 或真实账号密码。以上 `git add` 为精确文件列表。

## 5. 腾讯云部署（先不执行，等待本地全部通过再逐步指导）

- 当前服务器仍继续服务，**无需立即部署本批文件**。登录功能更新只在服务器安装完整改动后才会生效。
- 正式部署前要再次备份服务器 `.env`，服务器中 `frontend/src/services/api.ts` 的 `API_BASE` 必须保持为 `""`，不要直接把 Windows 开发地址发布到 HTTPS 网站。
- 本批**没有数据库迁移**。上线时单独设置服务器 `DEMO_USERNAME` 和 `DEMO_PASSWORD_HASH`，保留原有管理员凭证和 JWT 密钥。
- 安装、推送及云端验证会分步进行，保留以前的腾讯云代码、静态文件及数据库备份。

## 安全说明

- 只读 Demo 是应用层的隔离：Demo JWT **不能访问原有 admin 路由**，并且其自己的演示 GET 路由不查询数据库。前端隐藏控件只是体验辅助，真正的限制在后端。
- 网站其他本来就开放的**候选人公共面试入口**仍然开放；Demo 角色没有让它们获得新权限，既有 API 限流仍需保持。
- 本批不提供公用弱密码。即使是演示账户也请设置独立的强密码、通过私聊发送给 HR，结束演示后可从环境配置中禁用。
- 评分为**人为编写的虚构样本**，不用于真实招聘筛选；演示模式会显著标注这一点。
