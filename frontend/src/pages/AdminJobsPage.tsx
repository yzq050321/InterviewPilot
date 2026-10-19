import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  createJob,
  deactivateJob,
  getJobs,
} from "../services/jobApi";
import type { CreateJobInput, Difficulty, JobPosting } from "../services/jobApi";

const INITIAL_FORM: CreateJobInput = {
  title: "",
  position: "",
  requirements: "",
  difficulty: "中等",
};

export default function AdminJobsPage() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<JobPosting[]>([]);
  const [form, setForm] = useState<CreateJobInput>({ ...INITIAL_FORM });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [busyJobId, setBusyJobId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!sessionStorage.getItem("admin_token")) {
      navigate("/admin/login", { replace: true });
      return;
    }
    let cancelled = false;
    getJobs()
      .then((data) => { if (!cancelled) setJobs(data); })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : "招聘任务加载失败";
        if (message.includes("管理员登录")) {
          navigate("/admin/login", { replace: true });
        } else {
          setError(message);
        }
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [navigate]);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving) return;
    setError("");
    setNotice("");
    setSaving(true);
    try {
      const newJob = await createJob({
        title: form.title.trim(),
        position: form.position.trim(),
        requirements: form.requirements.trim(),
        difficulty: form.difficulty,
      });
      setJobs((prev) => [newJob, ...prev]);
      setForm({ ...INITIAL_FORM });
      setNotice("招聘任务已创建，可以在下方复制邀请链接。");
    } catch (err) {
      const message = err instanceof Error ? err.message : "创建招聘任务失败";
      if (message.includes("管理员登录")) navigate("/admin/login", { replace: true });
      else setError(message);
    } finally {
      setSaving(false);
    }
  }

  async function handleCopy(job: JobPosting) {
    setError("");
    setNotice("");
    const url = `${window.location.origin}${job.invite_path}`;
    try {
      if (!navigator.clipboard?.writeText) throw new Error("浏览器不支持自动复制，请手动复制链接");
      await navigator.clipboard.writeText(url);
      setNotice(`已复制「${job.title}」的邀请链接。`);
    } catch {
      setError(`复制失败，请手动选中以下链接：${url}`);
    }
  }

  async function handleDeactivate(job: JobPosting) {
    if (busyJobId !== null || !job.is_active) return;
    if (!window.confirm(`确定停用「${job.title}」？停用后新候选人不能再通过链接创建面试。`)) return;
    setError("");
    setNotice("");
    setBusyJobId(job.job_id);
    try {
      const updated = await deactivateJob(job.job_id);
      setJobs((prev) => prev.map((item) => item.job_id === updated.job_id ? updated : item));
      setNotice(`已停用「${job.title}」。`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "停用任务失败";
      if (message.includes("管理员登录")) navigate("/admin/login", { replace: true });
      else setError(message);
    } finally {
      setBusyJobId(null);
    }
  }

  return (
    <main className="admin-dashboard">
      <section className="interview-card jobs-page">
        <div className="jobs-heading">
          <div>
            <h2>招聘任务管理</h2>
            <p className="jobs-subtitle">创建岗位任务 → 复制链接 → 邀请候选人参加 AI 面试</p>
          </div>
          <Link className="jobs-back" to="/admin">← 返回招聘后台</Link>
        </div>

        <form className="jobs-form" onSubmit={(event) => { void handleCreate(event); }}>
          <h3>创建招聘任务</h3>
          <div className="form-group">
            <label htmlFor="job-title">任务名称</label>
            <input id="job-title" required maxLength={100} value={form.title} disabled={saving}
              placeholder="例如：2026 秋招 Python 后端实习生"
              onChange={(event) => setForm((prev) => ({ ...prev, title: event.target.value }))} />
          </div>
          <div className="form-group">
            <label htmlFor="job-position">招聘岗位</label>
            <input id="job-position" required maxLength={100} value={form.position} disabled={saving}
              placeholder="例如：Python 后端开发实习生"
              onChange={(event) => setForm((prev) => ({ ...prev, position: event.target.value }))} />
          </div>
          <div className="form-group">
            <label htmlFor="job-requirements">岗位要求（候选人打开链接也能看到）</label>
            <textarea id="job-requirements" required maxLength={2000} rows={4} value={form.requirements} disabled={saving}
              placeholder="例如：熟悉 Python、FastAPI，了解 MySQL。请不要填写内部保密信息。"
              onChange={(event) => setForm((prev) => ({ ...prev, requirements: event.target.value }))} />
          </div>
          <div className="form-group">
            <label htmlFor="job-difficulty">面试难度</label>
            <select id="job-difficulty" value={form.difficulty} disabled={saving}
              onChange={(event) => setForm((prev) => ({ ...prev, difficulty: event.target.value as Difficulty }))}>
              <option value="简单">简单</option>
              <option value="中等">中等</option>
              <option value="困难">困难</option>
            </select>
          </div>
          <p className="jobs-hint">岗位要求将用于 AI 出题、动态追问和报告参考；请勿填写保密信息。</p>
          <button className="start-button" type="submit" disabled={saving || !form.title.trim() || !form.position.trim() || !form.requirements.trim()}>
            {saving ? "正在创建..." : "＋ 创建招聘任务"}
          </button>
        </form>

        {error && <p className="error" role="alert">{error}</p>}
        {notice && <p className="jobs-notice" role="status">{notice}</p>}

        <section className="jobs-list">
          <h3>招聘任务列表（{jobs.length}）</h3>
          {loading && <p>正在加载任务...</p>}
          {!loading && jobs.length === 0 && <p className="jobs-hint">还没有招聘任务，可以从上方创建第一条。</p>}
          {!loading && jobs.map((job) => (
            <article className="jobs-item" key={job.job_id}>
              <div className="jobs-item-top">
                <div>
                  <h4>{job.title}</h4>
                  <p>{job.position} · {job.difficulty} · 任务 #{job.job_id}</p>
                </div>
                <span className={job.is_active ? "jobs-tag active" : "jobs-tag"}>
                  {job.is_active ? "进行中" : "已停用"}
                </span>
              </div>
              <p className="jobs-requirements">{job.requirements}</p>
              <div className="jobs-url">{`${window.location.origin}${job.invite_path}`}</div>
              <div className="jobs-actions">
                <button type="button" className="admin-detail-button" disabled={!job.is_active}
                  onClick={() => { void handleCopy(job); }}>复制邀请链接</button>
                <button type="button" className="jobs-stop" disabled={!job.is_active || busyJobId !== null}
                  onClick={() => { void handleDeactivate(job); }}>
                  {busyJobId === job.job_id ? "停用中..." : job.is_active ? "停用任务" : "已停用"}
                </button>
              </div>
            </article>
          ))}
        </section>
      </section>
    </main>
  );
}
