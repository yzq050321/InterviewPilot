import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { registerHr } from "../services/accountApi";

export default function AdminRegisterPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading) return;
    if (password !== confirm) {
      setError("两次输入的密码不一致");
      return;
    }
    if (password.length < 8) {
      setError("密码至少 8 位");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const data = await registerHr(email.trim(), password, inviteCode.trim());
      sessionStorage.setItem("admin_token", data.access_token);
      sessionStorage.setItem("admin_role", data.role);
      navigate("/admin/jobs", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "受邀注册失败");
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
            <h2>受邀注册 HR 账号</h2>
            <p>仅限拿到邀请码的招聘方；公开访客请使用只读 Demo</p>
          </div>
        </div>

        <form onSubmit={(event) => { void handleSubmit(event); }}>
          <div className="form-group">
            <label htmlFor="register-email">工作邮箱</label>
            <input
              id="register-email"
              type="email"
              required
              value={email}
              disabled={loading}
              autoComplete="email"
              placeholder="name@company.com"
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>

          <div className="form-group">
            <label htmlFor="register-password">设置密码</label>
            <input
              id="register-password"
              type="password"
              required
              minLength={8}
              value={password}
              disabled={loading}
              autoComplete="new-password"
              placeholder="至少 8 位"
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>

          <div className="form-group">
            <label htmlFor="register-confirm">确认密码</label>
            <input
              id="register-confirm"
              type="password"
              required
              minLength={8}
              value={confirm}
              disabled={loading}
              autoComplete="new-password"
              placeholder="再次输入密码"
              onChange={(event) => setConfirm(event.target.value)}
            />
          </div>

          <div className="form-group">
            <label htmlFor="register-invite">HR 邀请码</label>
            <input
              id="register-invite"
              type="text"
              required
              value={inviteCode}
              disabled={loading}
              autoComplete="off"
              placeholder="向项目维护者获取"
              onChange={(event) => setInviteCode(event.target.value)}
            />
          </div>

          <p className="auth-note">
            没有邀请码？可以<Link to="/admin/trial">申请试用</Link>，
            或使用只读 Demo 账号体验。
          </p>

          <button
            type="submit"
            className="start-button"
            disabled={loading || !email.trim() || !password || !confirm || !inviteCode.trim()}
          >
            {loading ? "正在创建账号..." : "受邀注册并进入工作台"}
          </button>
        </form>

        {error && <p className="error" role="alert">{error}</p>}

        <p className="auth-footer">
          已有账号？<Link to="/admin/login">返回登录</Link>
        </p>
      </section>
    </main>
  );
}
