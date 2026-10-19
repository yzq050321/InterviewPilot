
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getAdminInterviews } from "../services/api";

type AdminInterview = {
    interview_id: number;
    candidate_name: string | null;
    position: string;
    difficulty: string;
    status: string;
    created_at: string;
};

export default function AdminDashboardPage() {
    const navigate = useNavigate();

    const [interviews, setInterviews] = useState<AdminInterview[]>([]);

    const totalCount = interviews.length;

    const completedCount = interviews.filter(
        (interview) => interview.status === "completed"
    ).length;

    const inProgressCount = interviews.filter(
        (interview) => interview.status === "in_progress"
    ).length;
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const token = sessionStorage.getItem("admin_token");


    useEffect(() => {
        if (!token) {
            navigate("/admin/login", { replace: true });
            return;
        }

        let cancelled = false;

        async function loadInterviews() {
            try {
                const data = await getAdminInterviews();

                if (!cancelled) {
                    setInterviews(data);
                }
            } catch (err) {
                if (!cancelled) {
                    const message =
                        err instanceof Error
                            ? err.message
                            : "加载候选人面试记录失败";

                    if (
                        message.includes("管理员未登录") ||
                        message.includes("管理员登录已失效")
                    ) {
                        navigate("/admin/login", { replace: true });
                        return;
                    }

                    setError(message);
                }
            } finally {
                if (!cancelled) {
                    setLoading(false);
                }
            }
        }

        void loadInterviews();

        return () => {
            cancelled = true;
        };
    }, [token, navigate]);

    function handleLogout() {
        sessionStorage.removeItem("admin_token");
        navigate("/admin/login");
    }

    if (!token) {
        return (
            <main className="admin-dashboard">
                <section className="interview-card">
                    <h2>请先登录招聘管理后台</h2>
                    <p>登录后可以查看候选人面试记录和 AI 评估报告。</p>

                    <button
                        type="button"
                        className="start-button"
                        onClick={() => navigate("/admin/login")}
                    >
                        前往管理员登录
                    </button>
                </section>
            </main>
        );
    }

    return (
        <main className="admin-dashboard">
            <section className="interview-card">
                <div className="card-heading">
                    <div className="card-icon">▣</div>
                    <div>
                        <h2>招聘管理后台</h2>
                        <p>候选人面试记录管理</p>
                    </div>
                </div>


                <button
                    type="button"
                    className="admin-logout-button"
                    onClick={handleLogout}
                >
                    <span>退出登录</span>
                    <span aria-hidden="true">↗</span>
                </button>

                {loading && <p>正在加载候选人面试记录...</p>}

                {error && (
                    <p className="error" role="alert">
                        {error}
                    </p>
                )}

                {!loading && !error && (
                    <>

                        <div className="admin-stats">
                            <div className="admin-stat-card">
                                <div className="admin-stat-icon">▦</div>
                                <p>面试总数</p>
                                <strong>{totalCount}</strong>
                                <span>累计面试记录</span>
                            </div>

                            <div className="admin-stat-card">
                                <div className="admin-stat-icon">✓</div>
                                <p>已完成</p>
                                <strong>{completedCount}</strong>
                                <span>已结束的面试</span>
                            </div>

                            <div className="admin-stat-card">
                                <div className="admin-stat-icon">◷</div>
                                <p>进行中</p>
                                <strong>{inProgressCount}</strong>
                                <span>尚未结束的面试</span>
                            </div>
                        </div>
                        <h3>候选人面试列表（共 {interviews.length} 场）</h3>

                        {interviews.length === 0 ? (
                            <p>暂无候选人面试记录。</p>
                        ) : (
                            <div style={{ overflowX: "auto" }}>
                                <table
                                    style={{
                                        width: "100%",
                                        borderCollapse: "collapse",
                                        textAlign: "left",
                                    }}
                                >
                                    <thead>
                                        <tr>
                                            <th>面试编号</th>
                                            <th>候选人</th>
                                            <th>应聘岗位</th>
                                            <th>状态</th>
                                            <th>面试时间</th>
                                            <th>操作</th>
                                        </tr>
                                    </thead>

                                    <tbody>
                                        {interviews.map((interview) => (
                                            <tr key={interview.interview_id}>
                                                <td>{interview.interview_id}</td>
                                                <td>{interview.candidate_name || "未填写"}</td>
                                                <td>{interview.position}</td>
                                                <td>
                                                    {interview.status === "completed"
                                                        ? "已完成"
                                                        : "进行中"}
                                                </td>
                                                <td>
                                                    {interview.created_at
                                                        ? interview.created_at.replace("T", " ").slice(0, 19)
                                                        : "—"}
                                                </td>

                                                <td>
                                                    <button
                                                        type="button"
                                                        className="admin-detail-button"
                                                        onClick={() =>
                                                            navigate(`/admin/interviews/${interview.interview_id}`)
                                                        }
                                                    >
                                                        查看详情 →
                                                    </button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </>
                )}
            </section>
        </main>
    );
}