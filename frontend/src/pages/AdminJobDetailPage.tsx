import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { getAdminInterviews } from "../services/api";
import { deactivateJob, getJobs } from "../services/jobApi";
import type { JobPosting } from "../services/jobApi";
import { evaluationLabels, reviewLabels } from "../services/adminWorkflowApi";
import { interviewsForJob, showDate, summarizeJob } from "../services/jobWorkspace";
import type { WorkspaceInterview } from "../services/jobWorkspace";

type RecordFilter = "all" | "pending" | "completed" | "failed";

export default function AdminJobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const demoMode = sessionStorage.getItem("admin_role") === "demo";
  const [job, setJob] = useState<JobPosting | null>(null);
  const [interviews, setInterviews] = useState<WorkspaceInterview[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [filter, setFilter] = useState<RecordFilter>("all");
  const [keyword, setKeyword] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!sessionStorage.getItem("admin_token")) { navigate("/admin/login", { replace: true }); return; }
    if (!jobId || !/^[1-9]\d*$/.test(jobId)) { setError("岗位编号无效"); setLoading(false); return; }
    let cancelled = false;
    Promise.all([getJobs(), getAdminInterviews()])
      .then(([jobList, interviewList]) => {
        if (cancelled) return;
        setJob(jobList.find((item) => item.job_id === Number(jobId)) ?? null);
        setInterviews(interviewList);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : "加载岗位详情失败";
        if (message.includes("未登录") || message.includes("已失效")) navigate("/admin/login", { replace: true });
        else setError(message);
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [jobId, navigate]);

  const linked = useMemo(() => job ? interviewsForJob(interviews, job.job_id) : [], [job, interviews]);
  const stats = useMemo(() => summarizeJob(linked), [linked]);
  const visible = useMemo(() => linked.filter((item) => {
    const matchesText = `${item.candidate_name ?? ""} ${item.interview_id}`.toLowerCase().includes(keyword.trim().toLowerCase());
    if (!matchesText) return false;
    if (filter === "pending") return item.status === "completed" && item.review_status === "pending";
    if (filter === "completed") return item.status === "completed";
    if (filter === "failed") return item.evaluation_status === "failed";
    return true;
  }), [linked, keyword, filter]);

  async function copyInvitation() {
    if (!job || !job.is_active || demoMode || !job.invite_path) return;
    setError(""); setNotice("");
    const link = `${window.location.origin}${job.invite_path}`;
    try {
      if (!navigator.clipboard?.writeText) throw new Error("浏览器不支持自动复制");
      await navigator.clipboard.writeText(link);
      setNotice("候选人面试邀请链接已复制。请仅发送给目标候选人。");
    } catch { setError("复制失败，请手动复制下方邀请链接。"); }
  }

  async function stopJob() {
    if (!job || !job.is_active || demoMode || busy) return;
    if (!window.confirm(`确定停用「${job.title}」？停用后新候选人无法使用旧邀请链接创建面试。`)) return;
    setError(""); setNotice(""); setBusy(true);
    try {
      const result = await deactivateJob(job.job_id);
      setJob(result);
      setNotice("岗位已停用；已有面试记录和报告保持不变。");
    } catch (err) {
      const message = err instanceof Error ? err.message : "停用失败";
      if (message.includes("未登录") || message.includes("已失效")) navigate("/admin/login", { replace: true });
      else setError(message);
    } finally { setBusy(false); }
  }

  return (
    <main className="admin-dashboard hr-workspace">
      <nav className="hr-workspace-nav" aria-label="招聘后台导航"><Link className="is-current" to="/admin/jobs">岗位工作台</Link><Link to="/admin">全部面试</Link></nav>
      <section className="interview-card hr-workspace-panel hr-detail-page">
        <Link to="/admin/jobs" className="hr-back-link">← 返回岗位工作台</Link>
        {error && <p className="error" role="alert">{error}</p>}
        {notice && <p className="jobs-notice" role="status">{notice}</p>}
        {loading ? <p>正在加载岗位详情...</p> : !job ? !error && <p>未找到该岗位，或当前账号无权查看。</p> : <>
          <div className="hr-workspace-heading">
            <div>
              <span className="hr-eyebrow">招聘任务 #{job.job_id}{demoMode ? " · 虚构演示" : ""}</span>
              <h2>{job.title}</h2>
              <p>{job.position} · {job.difficulty}难度 · {job.is_active ? "招聘中" : "已停用"} · 创建于 {showDate(job.created_at)}</p>
            </div>
            {!demoMode && <div className="hr-heading-actions"><button type="button" className="hr-primary-btn" onClick={() => { void copyInvitation(); }} disabled={!job.is_active}>复制面试邀请</button><button type="button" className="jobs-stop" disabled={!job.is_active || busy} onClick={() => { void stopJob(); }}>{busy ? "停用中..." : job.is_active ? "停用岗位" : "已停用"}</button></div>}
          </div>
          <div className="hr-workspace-stats" aria-label="岗位面试统计">
            <div><strong>{stats.total}</strong><span>面试记录</span></div>
            <div><strong>{stats.completed}</strong><span>已完成面试</span></div>
            <div><strong>{stats.ready}</strong><span>报告已生成</span></div>
            <div><strong>{stats.pendingReview}</strong><span>待人工复核</span></div>
          </div>
          {stats.failed > 0 && <p className="hr-warning" role="status">有 {stats.failed} 场面试的 AI 报告生成失败，请在对应面试详情中查看恢复方式。</p>}
          <section className="hr-detail-panel" aria-label="岗位要求"><h3>岗位要求</h3><p className="jobs-requirements">{job.requirements}</p></section>
          {!demoMode && <section className="hr-detail-panel" aria-label="面试邀请"><h3>面试邀请</h3><p className="jobs-hint">仅已启用的岗位允许新候选人通过链接参加面试。请注意候选人信息保护。</p><div className="jobs-url">{`${window.location.origin}${job.invite_path}`}</div><div className="hr-heading-actions"><button type="button" className="admin-detail-button" disabled={!job.is_active} onClick={() => { void copyInvitation(); }}>复制链接</button><a className="admin-detail-button" href={job.invite_path} target="_blank" rel="noopener noreferrer">预览邀请页 ↗</a></div></section>}
          <section aria-label="此岗位面试列表" className="hr-detail-panel">
            <div className="hr-list-title"><h3>候选人面试记录</h3><span>显示 {visible.length} / {linked.length} 场</span></div>
            <div className="hr-workspace-filters" role="search" aria-label="岗位内筛选"><input aria-label="按候选人或面试编号搜索" placeholder="搜索候选人姓名或面试编号" value={keyword} onChange={(e) => setKeyword(e.target.value)} /><div className="hr-filter-buttons" role="group" aria-label="面试筛选">{([ ["all", "全部"], ["pending", "待复核"], ["completed", "已完成"], ["failed", "报告失败"] ] as const).map(([v, label]) => <button key={v} type="button" className={filter === v ? "is-selected" : ""} aria-pressed={filter === v} onClick={() => setFilter(v)}>{label}</button>)}</div></div>
            {visible.length === 0 ? <p className="jobs-hint">{linked.length ? "没有符合筛选条件的面试记录。" : "这个岗位暂时没有面试记录。"}</p> : <div className="hr-candidate-list">{visible.map((entry) => <article key={entry.interview_id} className="hr-candidate-card"><div><strong>{entry.candidate_name || "未填写姓名"}</strong><p>面试 #{entry.interview_id} · {showDate(entry.created_at)}</p></div><div className="hr-candidate-flags"><span>{entry.status === "completed" ? "面试已完成" : "面试中"}</span><span>{evaluationLabels[entry.evaluation_status] || "未评估"}</span><span>{reviewLabels[entry.review_status] || "待人工复核"}</span></div><Link className="admin-detail-button" to={`/admin/interviews/${entry.interview_id}`}>查看面试 →</Link></article>)}</div>}
            <p className="jobs-hint">本页按面试记录统计，不按姓名合并候选人；HR 复核结论仍需在面试详情中人工确认。</p>
          </section>
        </>}
      </section>
    </main>
  );
}
