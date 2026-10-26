import { useEffect, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import {
  createInvitedInterview,
  createInvitedInterviewWithResume,
  getJobInvitation,
} from "../services/jobApi";
import type { InvitedInterview, JobInvitation } from "../services/jobApi";

type Props = { onStarted: (interview: InvitedInterview) => void };

const MAX_RESUME_BYTES = 5 * 1024 * 1024;
const ALLOWED_RESUME = /\.(pdf|docx)$/i;

export default function JobInvitationPage({ onStarted }: Props) {
  const { inviteCode } = useParams<{ inviteCode: string }>();
  const [job, setJob] = useState<JobInvitation | null>(null);
  const [name, setName] = useState("");
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [consent, setConsent] = useState(false);
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

  function handleResumeChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    if (!file) {
      setResumeFile(null);
      setConsent(false);
      return;
    }
    if (!ALLOWED_RESUME.test(file.name)) {
      setError("简历仅支持 PDF 或 DOCX 格式");
      setResumeFile(null);
      setConsent(false);
      event.target.value = "";
      return;
    }
    if (file.size > MAX_RESUME_BYTES) {
      setError("简历文件不能超过 5 MB");
      setResumeFile(null);
      setConsent(false);
      event.target.value = "";
      return;
    }
    setError("");
    setResumeFile(file);
    setConsent(false);
  }

  async function handleStart(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!inviteCode || !job || !name.trim() || starting) return;
    if (resumeFile && !consent) {
      setError("请先阅读并同意简历使用说明");
      return;
    }
    setError("");
    setStarting(true);
    try {
      const result = resumeFile
        ? await createInvitedInterviewWithResume(inviteCode, name.trim(), resumeFile, consent)
        : await createInvitedInterview(inviteCode, name.trim());
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
          <p>请确认岗位信息，上传简历后开始面试</p>
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

            <div className="resume-upload">
              <label htmlFor="candidate-resume">上传简历（可选）</label>
              <input
                id="candidate-resume"
                type="file"
                accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                disabled={starting}
                onChange={handleResumeChange}
              />
              <p className="jobs-hint">
                支持 PDF / DOCX，最大 5 MB；PDF 最多 20 页，解析文本最多 8000 字。
                AI 会结合简历中的项目提问；原文件不会保存，只保存解析后的文字用于本次面试。
              </p>
              {resumeFile && (
                <p className="resume-selected">
                  已选择：<strong>{resumeFile.name}</strong>
                  （{(resumeFile.size / 1024).toFixed(0)} KB）
                </p>
              )}
              {resumeFile && (
                <label className="resume-consent">
                  <input
                    type="checkbox"
                    checked={consent}
                    disabled={starting}
                    onChange={(event) => setConsent(event.target.checked)}
                  />
                  <span>
                    我已阅读并同意：将简历解析后的文字用于本次 AI 面试；
                    原文件不上传、不保存。
                  </span>
                </label>
              )}
            </div>

            <p className="jobs-hint">
              面试岗位及难度由招聘方设定，面试结束后评估报告供招聘方查看。
              请使用测试资料进行演示。
            </p>
            <button
              type="submit"
              className="start-button"
              disabled={starting || !name.trim() || Boolean(resumeFile && !consent)}
            >
              {starting
                ? (resumeFile ? "AI 正在解析简历并生成第一题..." : "AI 正在生成第一道面试题，请稍候...")
                : "开始 AI 面试 →"}
            </button>
          </form>
        </>
      )}
      {error && <p className="error" role="alert">{error}</p>}
      {!loading && !job && <p className="card-footer"><Link to="/">返回首页</Link></p>}
    </section>
  );
}
