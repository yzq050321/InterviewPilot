
# InterviewPilot V2 开发记录

## 项目目标

根据 HR 的反馈，把个人 AI 模拟面试工具升级为
HR 主导的 AI 招聘面试系统。

## HR 核心反馈

1. B 端：尽量通过 AI 减少招聘人员的重复操作。
2. C 端：除了技术能力，还应关注沟通、学习、执行能力。
3. 简化产品操作，降低招聘人员的使用门槛。

## 当前 V1 已实现

- React + TypeScript + Vite 前端
- FastAPI + MySQL + SQLAlchemy 后端
- DeepSeek + LangChain Agent + Chroma RAG
- 候选人创建面试、AI 提问、动态追问
- 面试结束生成 AI 评估报告
- HR 登录、面试列表、问答和评估详情
- 候选人随机访问 Token
- HR bcrypt + JWT 认证
- 登录失败限流
- 腾讯云 Lighthouse + Nginx + systemd 部署
- 临时 Cloudflare HTTPS 演示入口

## V2 第一阶段目标

HR 创建招聘任务
→ 生成邀请链接
→ 候选人通过链接参加指定岗位面试
→ 面试记录关联招聘任务
→ HR 查看候选人及评估结果

## V2 数据模型设计

新增 JobPosting：
- id
- title
- position
- requirements
- difficulty
- invite_code（唯一随机字符串）
- is_active
- created_at

计划在 Interview 中增加 nullable job_id 外键。
必须配合 MySQL 数据库迁移，保留旧面试数据。

## 开发原则

- 本地开发和测试通过后再部署服务器
- V2 使用独立 Git 分支
- 不提交 .env、API Key、管理员密码
- 不使用真实候选人数据测试
- AI 评分仅辅助 HR 人工复核
- 新增功能不能破坏现有候选人和 HR 流程
- 每个开发批次集中完成多个相关任务

## 开发进度

批次 1：
- [ ] 建立 feat/hr-job-invitations 分支
- [ ] 新增 JobPosting SQLAlchemy 模型
- [ ] 创建本开发记录
- [ ] 完成模型语法及映射检查

批次 2（待开始）：
- [ ] MySQL 本地数据库迁移
- [ ] Interview 增加 job_id
- [ ] HR 招聘任务 API
- [ ] 面试邀请 API
- [ ] 身份验证与异常测试

批次 3（待开始）：
- [ ] HR 招聘任务管理界面
- [ ] 候选人邀请入口
- [ ] 前后端联调

批次 4（待开始）：
- [ ] 完整业务验收
- [ ] 腾讯云部署
- [ ] README 与截图更新