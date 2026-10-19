import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { createInvitedInterview, getJobInvitation } from "../services/jobApi";
import type { InvitedInterview, JobInvitation } from "../services/jobApi";

type Props = { onStarted: (interview: InvitedInterview) => void };

export default function JobInvitationPage({ onStarted }: Props) {
  const { inviteCode } = useParams<{ inviteCode: string }>();
  const [job, setJob] = useState<JobInvitation | null>(null);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!inviteCode) {
      setLoading(false);
      setError("邀请链接缺少邀请码");
      return;
    }
    let cancelled = false;
    setLoading(true);
    setJob(null);
    setError("");
    getJobInvitation(inviteCode)
      .then((data) => { if (!cancelled) setJob(data); })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "邀请链接不可用");
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [inviteCode]);

  async function handleStart(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!inviteCode || !job || !name.trim() || starting) return;
    setError("");
    setStarting(true);
    try {
      const result = await createInvitedInterview(inviteCode, name.trim());
      onStarted(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建面试失败，请稍后再试");
    } finally {
      setStarting(false);
    }
  }

  return (
    <section className="interview-card invite-page">
      <div className="card-heading">
        <div className="card-icon">✦</div>
        <div>
          <h2>AI 招聘面试邀请</h2>
          <p>请确认岗位信息后开始面试</p>
        </div>
      </div>
      {loading && <p>正在验证邀请链接...</p>}
      {!loading && job && (
        <>
          <div className="invite-job-info">
            <h3>{job.title}</h3>
            <p><strong>招聘岗位：</strong>{job.position}</p>
            <p><strong>面试难度：</strong>{job.difficulty}</p>
            <p><strong>岗位要求：</strong></p>
            <p className="invite-requirements">{job.requirements}</p>
          </div>
          <form onSubmit={(event) => { void handleStart(event); }}>
            <div className="form-group">
              <label htmlFor="invited-candidate-name">候选人姓名</label>
              <input id="invited-candidate-name" required maxLength={100} autoComplete="name"
                value={name} disabled={starting} placeholder="请输入你的姓名"
                onChange={(event) => setName(event.target.value)} />
            </div>
            <p className="jobs-hint">面试岗位及难度由招聘方设定，面试结束后评估报告供招聘方查看。请使用测试资料进行演示。</p>
            <button type="submit" className="start-button" disabled={starting || !name.trim()}>
              {starting ? "AI 正在生成第一道面试题，请稍候..." : "开始 AI 面试 →"}
            </button>
          </form>
        </>
      )}
      {error && <p className="error" role="alert">{error}</p>}
      {!loading && !job && <p className="card-footer"><Link to="/">返回首页</Link></p>}
    </section>
  );
}
