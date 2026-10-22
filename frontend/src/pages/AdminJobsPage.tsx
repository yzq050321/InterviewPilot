import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getAdminInterviews } from "../services/api";
import { createJob, getJobs, invitationIsOpen, invitationDeadline } from "../services/jobApi";
import type { CreateJobInput, Difficulty, JobPosting } from "../services/jobApi";
import { interviewsForJob, summarizeJob, summarizeWorkspace } from "../services/jobWorkspace";
import type { WorkspaceInterview } from "../services/jobWorkspace";

const INITIAL_FORM: CreateJobInput = { title: "", position: "", requirements: "", difficulty: "中等", invite_valid_days: 7 };
const TEMPLATES: { label: string; position: string; requirements: string; difficulty: Difficulty }[] = [
  { label: "Python 后端", position: "Python 后端开发实习生", requirements: "熟悉 Python 基础语法，了解 FastAPI 或其他 Web 框架，了解 MySQL、RESTful API 与 Git，能够描述实际项目中的问题解决过程。", difficulty: "中等" },
  { label: "前端开发", position: "前端开发实习生", requirements: "熟悉 HTML、CSS、JavaScript 基础，了解 React、TypeScript、HTTP 请求与浏览器调试工具，能够说明响应式页面的实现思路。", difficulty: "中等" },
  { label: "AI 应用", position: "AI 应用开发实习生", requirements: "了解 Python、LLM API、Prompt 设计与结构化输出，能解释大模型幻觉、调用成本及错误处理，并结合项目说明实践经验。", difficulty: "中等" },
  { label: "产品实习", position: "产品实习生", requirements: "能够澄清业务需求、拆分任务、设计验收标准，并通过具体情境说明跨团队沟通和结果复盘思路。", difficulty: "中等" },
];

type Filter = "all" | "active" | "inactive";

export default function AdminJobsPage() {
  const navigate = useNavigate();
  const demoMode = sessionStorage.getItem("admin_role") === "demo";
  const [jobs, setJobs] = useState<JobPosting[]>([]);
  const [interviews, setInterviews] = useState<WorkspaceInterview[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [keyword, setKeyword] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<CreateJobInput>({ ...INITIAL_FORM });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!sessionStorage.getItem("admin_token")) {
      navigate("/admin/login", { replace: true });
      return;
    }
    let cancelled = false;
    Promise.all([getJobs(), getAdminInterviews()])
      .then(([jobList, interviewList]) => {
        if (!cancelled) { setJobs(jobList); setInterviews(interviewList); }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : "工作台加载失败";
        if (message.includes("未登录") || message.includes("已失效")) navigate("/admin/login", { replace: true });
        else setError(message);
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [navigate]);

  const totals = useMemo(() => summarizeWorkspace(jobs, interviews), [jobs, interviews]);
  const filtered = useMemo(() => jobs.filter((job) => {
    const textMatch = `${job.title} ${job.position} ${job.job_id}`.toLowerCase().includes(keyword.trim().toLowerCase());
    return textMatch && (filter === "all" || (filter === "active" ? invitationIsOpen(job) : !invitationIsOpen(job)));
  }), [jobs, keyword, filter]);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving || demoMode) return;
    setError(""); setNotice(""); setSaving(true);
    try {
      const job = await createJob({ title: form.title.trim(), position: form.position.trim(), requirements: form.requirements.trim(), difficulty: form.difficulty, invite_valid_days: form.invite_valid_days });
      setJobs((prev) => [job, ...prev]);
      setForm({ ...INITIAL_FORM }); setShowForm(false); setFilter("all"); setKeyword("");
      setNotice(`「${job.title}」创建成功，打开详情即可获取面试邀请链接。`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "创建失败";
      if (message.includes("未登录") || message.includes("已失效")) navigate("/admin/login", { replace: true });
      else setError(message);
    } finally { setSaving(false); }
  }

  function applyTemplate(template: typeof TEMPLATES[number]) {
    setForm({ title: `${template.position}招聘`, position: template.position, requirements: template.requirements, difficulty: template.difficulty, invite_valid_days: form.invite_valid_days });
  }

  return (
    <main className="admin-dashboard hr-workspace">
      <nav className="hr-workspace-nav" aria-label="招聘后台导航">
        <Link className="is-current" to="/admin/jobs" aria-current="page">岗位工作台</Link>
        <Link to="/admin">全部面试</Link>
      </nav>
      <section className="interview-card hr-workspace-panel">
        <div className="hr-workspace-heading">
          <div>
            <span className="hr-eyebrow">InterviewPilot · HR 招聘工作台</span>
            <h2>岗位工作台{demoMode ? " · 只读演示" : ""}</h2>
            <p>{demoMode ? "以下岗位和候选人均为独立虚构样本，不包含真实招聘数据。" : "统一查看招聘岗位、面试进度与需要人工处理的事项。"}</p>
          </div>
          {!demoMode && <button type="button" className="hr-primary-btn" aria-expanded={showForm} aria-controls="new-job-form" onClick={() => setShowForm((prev) => !prev)}>{showForm ? "收起创建表单" : "＋ 创建招聘任务"}</button>}
        </div>

        {error && <p role="alert" className="error">{error}</p>}
        {notice && <p role="status" className="jobs-notice">{notice}</p>}
        {loading ? <p>正在加载工作台...</p> : !error && <>
          <div className="hr-workspace-stats" aria-label="岗位和面试统计">
            <div><strong>{totals.activeJobs}</strong><span>开放岗位</span></div>
            <div><strong>{totals.total}</strong><span>岗位关联面试</span></div>
            <div><strong>{totals.pendingReview}</strong><span>待人工复核</span></div>
            <div><strong>{totals.failed}</strong><span>报告失败待处理</span></div>
          </div>

          {!demoMode && showForm && <form id="new-job-form" className="jobs-form hr-create-form" onSubmit={(event) => { void handleCreate(event); }}>
            <h3>创建招聘任务</h3>
            <p className="jobs-hint">选择一个岗位模板后按实际需求修改；模板仅用于填写表单，不会改变 AI 评估的权限规则。</p>
            <div className="hr-template-row" role="group" aria-label="岗位模板">
              {TEMPLATES.map((template) => <button key={template.label} type="button" disabled={saving} onClick={() => applyTemplate(template)}>{template.label}</button>)}
            </div>
            <div className="hr-form-grid">
              <div className="form-group"><label htmlFor="job-title">招聘任务名称</label><input id="job-title" required maxLength={100} value={form.title} disabled={saving} onChange={(e) => setForm((v) => ({ ...v, title: e.target.value }))} placeholder="例如：2026 秋招 Python 后端实习生" /></div>
              <div className="form-group"><label htmlFor="job-position">应聘岗位</label><input id="job-position" required maxLength={100} value={form.position} disabled={saving} onChange={(e) => setForm((v) => ({ ...v, position: e.target.value }))} placeholder="例如：Python 后端开发实习生" /></div>
            </div>
            <div className="form-group"><label htmlFor="job-requirements">岗位要求（候选人可见）</label><textarea id="job-requirements" required maxLength={2000} rows={4} value={form.requirements} disabled={saving} onChange={(e) => setForm((v) => ({ ...v, requirements: e.target.value }))} placeholder="请描述岗位要求，不要填写企业机密。" /></div>
            <div className="form-group"><label htmlFor="job-difficulty">面试难度</label><select id="job-difficulty" value={form.difficulty} disabled={saving} onChange={(e) => setForm((v) => ({ ...v, difficulty: e.target.value as Difficulty }))}><option value="简单">简单</option><option value="中等">中等</option><option value="困难">困难</option></select></div>
            <div className="form-group"><label htmlFor="job-invite-days">邀请链接有效期</label><select id="job-invite-days" value={form.invite_valid_days} disabled={saving} onChange={(e) => setForm((v) => ({ ...v, invite_valid_days: Number(e.target.value) as 7 | 14 | 30 }))}><option value={7}>7 天（推荐）</option><option value={14}>14 天</option><option value={30}>30 天</option></select><p className="jobs-hint">链接过期后无法新建面试；已开始的面试不受影响。</p></div>
            <button type="submit" className="hr-primary-btn" disabled={saving || !form.title.trim() || !form.position.trim() || !form.requirements.trim()}>{saving ? "正在创建..." : "保存招聘任务"}</button>
          </form>}

          <section aria-label="招聘岗位列表" className="hr-job-list">
            <div className="hr-list-title"><h3>招聘岗位</h3><span>{filtered.length} / {jobs.length} 个岗位</span></div>
            <div className="hr-workspace-filters" role="search" aria-label="筛选招聘岗位">
              <input aria-label="搜索招聘岗位" placeholder="搜索岗位名称或任务编号" value={keyword} onChange={(e) => setKeyword(e.target.value)} />
              <div className="hr-filter-buttons" role="group" aria-label="岗位状态">
                {([ ["all", "全部"], ["active", "招聘中"], ["inactive", "已停用"] ] as const).map(([value, label]) => <button key={value} type="button" aria-pressed={filter === value} className={filter === value ? "is-selected" : ""} onClick={() => setFilter(value)}>{label}</button>)}
              </div>
            </div>
            {filtered.length === 0 ? <p className="jobs-hint">{jobs.length ? "没有符合筛选条件的岗位。" : "目前还没有招聘任务。"}</p> : <div className="hr-job-cards">{filtered.map((job) => {
              const stat = summarizeJob(interviewsForJob(interviews, job.job_id));
              const accepting = invitationIsOpen(job);
              return <article key={job.job_id} className="hr-job-card">
                <div className="hr-job-head"><div><span className={`hr-status-dot ${accepting ? "" : "is-inactive"}`} aria-hidden="true" /><h4>{job.title}</h4></div><span className="hr-job-status">{accepting ? "招聘中" : job.is_active ? "邀请已过期" : "已停用"}</span></div>
                <p className="hr-job-meta">{job.position} · {job.difficulty}难度 · 任务 #{job.job_id} · 邀请截止 {invitationDeadline(job)}</p>
                <div className="hr-job-metrics"><span>面试 {stat.total}</span><span>已完成 {stat.completed}</span><span>报告 {stat.ready}</span><span>待复核 {stat.pendingReview}</span>{stat.failed > 0 && <span className="hr-alert-metric">报告失败 {stat.failed}</span>}</div>
                <div className="hr-job-card-foot"><span>{stat.pendingReview > 0 ? `${stat.pendingReview} 场已结束面试待处理` : "查看该岗位的邀请和面试记录"}</span><Link className="admin-detail-button" to={`/admin/jobs/${job.job_id}`}>查看岗位 →</Link></div>
              </article>;
            })}</div>}
          </section>
        </>}
      </section>
    </main>
  );
}
