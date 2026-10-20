
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getAdminInterviews } from "../services/api";
import { evaluationLabels, reviewLabels } from "../services/adminWorkflowApi";
import type { EvaluationStatus, ReviewStatus } from "../services/adminWorkflowApi";

type AdminInterview = {
    interview_id: number;
    candidate_name: string | null;
    position: string;
    difficulty: string;
    status: string;
    created_at: string;
    job_id: number | null;
    evaluation_status: EvaluationStatus;
    review_status: ReviewStatus;
};

export default function AdminDashboardPage() {
    const navigate = useNavigate();

    const [interviews, setInterviews] = useState<AdminInterview[]>([]);
    const [keyword, setKeyword] = useState("");
    const [statusFilter, setStatusFilter] = useState("all");
    const [reportFilter, setReportFilter] = useState("all");
    const [reviewFilter, setReviewFilter] = useState("all");
    const visibleInterviews = interviews.filter((item) => {
        const matchKeyword = `${item.candidate_name || ""} ${item.position} ${item.interview_id}`
            .toLowerCase().includes(keyword.trim().toLowerCase());
        return matchKeyword
            && (statusFilter === "all" || item.status === statusFilter)
            && (reportFilter === "all" || item.evaluation_status === reportFilter)
            && (reviewFilter === "all" || item.review_status === reviewFilter);
    });

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


                <div className="jobs-dashboard-entry">
                    <div>
                        <strong>招聘任务与面试邀请</strong>
                        <p>创建招聘岗位、复制邀请链接，让候选人进入指定岗位的 AI 面试。</p>
                    </div>
                    <button type="button" className="admin-detail-button"
                        onClick={() => navigate("/admin/jobs")}>管理招聘任务 →</button>
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
                        <h3>候选人面试列表（符合筛选 {visibleInterviews.length} / {interviews.length} 场）</h3>
                        <div className="workflow-filters" role="search" aria-label="筛选候选人面试">
                            <label className="workflow-filter-field workflow-filter-keyword">
                                <span>姓名 / 岗位 / 编号</span>
                                <input aria-label="按姓名、岗位或编号筛选" placeholder="搜索候选人或面试编号" value={keyword}
                                    onChange={(event) => setKeyword(event.target.value)} />
                            </label>
                            <label className="workflow-filter-field">
                                <span>面试状态</span>
                                <select aria-label="面试状态筛选" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                                    <option value="all">全部面试状态</option>
                                    <option value="in_progress">进行中</option>
                                    <option value="completed">已完成</option>
                                </select>
                            </label>
                            <label className="workflow-filter-field">
                                <span>评估状态</span>
                                <select aria-label="评估状态筛选" value={reportFilter} onChange={(event) => setReportFilter(event.target.value)}>
                                    <option value="all">全部评估状态</option>
                                    {Object.entries(evaluationLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                                </select>
                            </label>
                            <label className="workflow-filter-field">
                                <span>人工复核</span>
                                <select aria-label="复核状态筛选" value={reviewFilter} onChange={(event) => setReviewFilter(event.target.value)}>
                                    <option value="all">全部人工复核状态</option>
                                    {Object.entries(reviewLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                                </select>
                            </label>
                            <button type="button" className="workflow-reset-button"
                                disabled={!keyword && statusFilter === "all" && reportFilter === "all" && reviewFilter === "all"}
                                onClick={() => {
                                    setKeyword(""); setStatusFilter("all"); setReportFilter("all"); setReviewFilter("all");
                                }}>重置筛选</button>
                        </div>

                        {visibleInterviews.length === 0 ? (
                            <p>{interviews.length === 0 ? "暂无候选人面试记录。" : "当前筛选条件下没有面试记录。"}</p>
                        ) : (
                            <div className="admin-table-scroll">
                                <table className="admin-interviews-table">
                                    <thead>
                                        <tr>
                                            <th>面试编号</th>
                                            <th>候选人</th>
                                            <th>应聘岗位</th>
                                            <th>面试状态</th>
                                            <th>评估状态</th>
                                            <th>人工复核</th>
                                            <th>面试时间</th>
                                            <th>操作</th>
                                        </tr>
                                    </thead>

                                    <tbody>
                                        {visibleInterviews.map((interview) => (
                                            <tr key={interview.interview_id}>
                                                <td>{interview.interview_id}</td>
                                                <td>{interview.candidate_name || "未填写"}</td>
                                                <td>{interview.position}</td>
                                                <td>
                                                    <span className={`workflow-status-pill ${interview.status === "completed" ? "is-complete" : "is-progress"}`}>
                                                        {interview.status === "completed" ? "已完成" : "进行中"}
                                                    </span>
                                                </td>
                                                <td><span className={`workflow-status-pill eval-${interview.evaluation_status}`}>
                                                    {evaluationLabels[interview.evaluation_status] || "—"}
                                                </span></td>
                                                <td><span className={`workflow-status-pill review-${interview.review_status}`}>
                                                    {reviewLabels[interview.review_status] || "待人工复核"}
                                                </span></td>
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