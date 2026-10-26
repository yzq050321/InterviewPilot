# InterviewPilot Frontend

React 19 + TypeScript + Vite 前端，包含候选人端与 HR 招聘工作台。

## 页面

| 路由 | 说明 |
| --- | --- |
| `/` | 候选人首页，创建模拟面试 |
| `/invite/:inviteCode` | 通过 HR 邀请链接进入指定岗位；可选上传 PDF/DOCX 简历 |
| `/interview/:id` | 候选人面试聊天、刷新恢复与结束面试 |
| `/admin/login` | HR / Demo 登录 |
| `/admin` | 全部面试列表与筛选 |
| `/admin/jobs` | 岗位工作台：统计、搜索、筛选、创建任务 |
| `/admin/jobs/:jobId` | 岗位详情、邀请链接、候选人列表 |
| `/admin/interviews/:id` | 完整问答、评估报告、招聘阶段、人工复核 |

## 本地开发

```bash
npm ci
npm run dev
```

Vite 已配置 `/api` 代理到 `http://127.0.0.1:8000`，因此前端代码使用同源 `/api`，不写死后端地址。生产环境由 Nginx 托管 `dist` 并把 `/api` 反代到 FastAPI。

## 构建与检查

```bash
npm run build   # tsc -b + vite build
npm run lint    # oxlint
```

当前 `npm run lint` 有 5 条 React Hook 规范警告，均为非阻断项；`npm run build` 通过。

## 简历上传

- 邀请页支持 `PDF / DOCX`，前端先校验扩展名与 5 MB 上限。
- 用户必须勾选同意后才能提交；表单使用 `FormData` 调用
  `/api/job-invitations/{code}/interviews/with-resume`。
- 原文件不保存；后端只保存解析后的文本、文件名和同意时间。
- 扫描版 PDF 没有文字层时会返回 400，前端展示后端错误。

## 认证与恢复

- HR 登录 Token 存在 `sessionStorage`，Demo 角色单独标记。
- 候选人 Token 存在 `sessionStorage`，键名为 `interview_token_{interviewId}`。
- 未确认的答题以 `{requestId, questionId, answer}` 存在 `pending_answer_{interviewId}`；刷新后复用同一 `request_id`，避免超时重试重复计费。
- 前端不保存 API Key；所有模型调用都经后端转发。
