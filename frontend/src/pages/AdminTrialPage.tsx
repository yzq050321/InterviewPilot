import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { requestTrial } from "../services/accountApi";

export default function AdminTrialPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading) return;
    setLoading(true);
    setError("");
    try {
      const result = await requestTrial({
        name: name.trim(),
        email: email.trim(),
        company: company.trim(),
        note: note.trim(),
      });
      setSuccess(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "试用申请提交失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="admin-login-page">
      <section className="interview-card">
        <div className="card-heading">
          <div className="card-icon">✦</div>
          <div>
            <h2>申请 InterviewPilot 试用</h2>
            <p>提交后由维护者人工审核；不会自动开通账号</p>
          </div>
        </div>

        {success ? (
          <div className="trial-success" role="status">
            <strong>申请已收到</strong>
            <p>{success}</p>
            <p className="auth-note">审核通过后，我们会把 HR 邀请码发送到你的邮箱。</p>
            <Link className="start-button trial-back" to="/admin/login">返回登录</Link>
          </div>
        ) : (
          <form onSubmit={(event) => { void handleSubmit(event); }}>
            <div className="form-group">
              <label htmlFor="trial-name">你的姓名</label>
              <input id="trial-name" required maxLength={100} value={name}
                disabled={loading} placeholder="请输入姓名"
                onChange={(event) => setName(event.target.value)} />
            </div>
            <div className="form-group">
              <label htmlFor="trial-email">工作邮箱</label>
              <input id="trial-email" type="email" required maxLength={255} value={email}
                disabled={loading} autoComplete="email" placeholder="name@company.com"
                onChange={(event) => setEmail(event.target.value)} />
            </div>
            <div className="form-group">
              <label htmlFor="trial-company">公司 / 团队（可选）</label>
              <input id="trial-company" maxLength={200} value={company}
                disabled={loading} placeholder="例如：某科技公司 HR 团队"
                onChange={(event) => setCompany(event.target.value)} />
            </div>
            <div className="form-group">
              <label htmlFor="trial-note">使用场景（可选）</label>
              <textarea id="trial-note" rows={3} maxLength={1000} value={note}
                disabled={loading} placeholder="例如：想测试 Python 后端实习生的简历面试流程"
                onChange={(event) => setNote(event.target.value)} />
            </div>
            <p className="auth-note">
              公开 Demo 只能查看虚构数据；试用账号需要人工审核，避免 AI 成本被滥用。
            </p>
            <button type="submit" className="start-button"
              disabled={loading || !name.trim() || !email.trim()}>
              {loading ? "正在提交..." : "提交试用申请"}
            </button>
          </form>
        )}

        {error && <p className="error" role="alert">{error}</p>}
        {!success && <p className="auth-footer">已有邀请码？<Link to="/admin/register">受邀注册</Link></p>}
      </section>
    </main>
  );
}
