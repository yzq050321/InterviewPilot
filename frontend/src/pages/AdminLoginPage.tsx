
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { loginAdmin } from "../services/api";

export default function AdminLoginPage() {
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const navigate = useNavigate();

    async function handleLogin() {
        if (!username.trim() || !password || loading) return;

        setLoading(true);
        setError("");

        try {
            const data = await loginAdmin(username.trim(), password);

            // 暂时保存在当前浏览器标签页中
            sessionStorage.setItem("admin_token", data.access_token);
            sessionStorage.setItem("admin_role", data.role);

            // 登录成功后进入管理后台
            navigate("/admin");
        } catch (err) {
            setError(
                err instanceof Error ? err.message : "管理员登录失败"
            );
        } finally {
            setLoading(false);
        }
    }

    return (
        <main className="admin-login-page">
            <section className="interview-card">
                <div className="card-heading">
                    <div className="card-icon">▣</div>
                    <div>
                        <h2>招聘管理后台</h2>
                        <p>支持 HR 管理员及独立演示账号登录</p>
                    </div>
                </div>

                <div className="form-group">
                    <label htmlFor="admin-username">HR 账号</label>
                    <input
                        id="admin-username"
                        type="text"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        autoComplete="username"
                        placeholder="请输入HR 账号"
                    />
                </div>

                <div className="form-group">
                    <label htmlFor="admin-password">登录密码</label>
                    <input
                        id="admin-password"
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        autoComplete="current-password"
                        placeholder="请输入登录密码"
                    />
                </div>


                <button
                    type="button"
                    className="start-button"
                    onClick={handleLogin}
                    disabled={!username.trim() || !password || loading}
                >
                    {loading ? "正在登录..." : "登录管理后台"}
                </button>

                {error && (
                    <p className="error" role="alert">
                        {error}
                    </p>
                )}
            </section>
        </main>
    );
}