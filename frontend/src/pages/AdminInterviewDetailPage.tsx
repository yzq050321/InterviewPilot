
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
    getAdminInterviewDetail,
    getAdminInterviewEvaluation,
} from "../services/api";

type AdminInterviewDetail = Awaited<
    ReturnType<typeof getAdminInterviewDetail>
>;
type AdminEvaluation = Awaited<
    ReturnType<typeof getAdminInterviewEvaluation>
>;

// 后端 V2 新增的报告字段；旧版报告没有此字段时保持兼容。
type CompetencyDimension = {
    score: number | null;
    evidence: string | null;
    observation: string;
    limitations: string;
    answer_count: number;
};
type CompetencyReport = {
    version: number;
    dimensions: Record<string, CompetencyDimension>;
    review_notice: string;
};
const competencyLabels = [
    ["technical", "技术理解与回答"],
    ["communication", "沟通能力情境"],
    ["learning", "学习能力情境"],
    ["execution", "执行能力情境"],
] as const;

function CompetencyPanel({ report }: { report?: CompetencyReport | null }) {
    if (!report?.dimensions) return null;
    return (
        <div className="admin-evaluation-section" style={{ marginTop: 20 }}>
            <h4>四维情境能力评估（需人工复核）</h4>
            <p style={{ color: "#566582", marginBottom: 16 }}>{report.review_notice}</p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
                {competencyLabels.map(([key, label]) => {
                    const item = report.dimensions[key];
                    if (!item) return null;
                    return (
                        <div key={key} style={{ padding: 16, border: "1px solid #dee1f6", borderRadius: 12, background: "#fff" }}>
                            <div style={{ fontWeight: 700 }}>{label}</div>
                            <div style={{ fontSize: 23, fontWeight: 700, margin: "8px 0", color: "#4f46e5" }}>
                                {typeof item.score === "number" ? `${item.score} / 100` : "证据不足 · 未评分"}
                            </div>
                            <p style={{ fontSize: 13 }}>回答数量：{item.answer_count ?? 0}</p>
                            {item.evidence && (
                                <p style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", fontSize: 13 }}>
                                    <strong>原回答摘录：</strong>“{item.evidence}”
                                </p>
                            )}
                            <p style={{ fontSize: 13, whiteSpace: "pre-wrap" }}><strong>观察：</strong>{item.observation}</p>
                            <p style={{ fontSize: 13, whiteSpace: "pre-wrap" }}><strong>限制：</strong>{item.limitations}</p>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

export default function AdminInterviewDetailPage() {
    const navigate = useNavigate();
    const { id } = useParams<{ id: string }>();

    const [interview, setInterview] = useState<AdminInterviewDetail | null>(null);
    const [evaluation, setEvaluation] = useState<AdminEvaluation | null>(null);
    const [evaluationLoading, setEvaluationLoading] = useState(false);
    const [evaluationError, setEvaluationError] = useState("");
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        let cancelled = false;

        async function loadDetail() {
            if (!id || !/^[1-9]\d*$/.test(id)) {
                setError("面试编号无效");
                setLoading(false);
                return;
            }

            try {
                setLoading(true);
                setError("");


                const interviewId = Number(id);

                // 1. 获取候选人基本信息及完整问答
                const data = await getAdminInterviewDetail(interviewId);

                if (cancelled) return;

                setInterview(data);

                // 2. 如果面试已经完成，再读取 AI 评估报告
                setEvaluation(null);
                setEvaluationError("");

                if (data.status === "completed") {
                    setEvaluationLoading(true);

                    try {
                        const report = await getAdminInterviewEvaluation(interviewId);

                        if (cancelled) return;

                        setEvaluation(report);
                    } catch (err) {
                        if (cancelled) return;

                        setEvaluationError(
                            err instanceof Error
                                ? err.message
                                : "AI 评估报告加载失败"
                        );
                    } finally {
                        if (!cancelled) {
                            setEvaluationLoading(false);
                        }
                    }
                }
            } catch (err) {
                if (!cancelled) {
                    const message =
                        err instanceof Error
                            ? err.message
                            : "加载面试详情失败";

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

        void loadDetail();

        return () => {
            cancelled = true;
        };
    }, [id]);

    function handleBack() {
        navigate("/admin");
    }

    return (
        <div className="admin-dashboard">
            <section className="interview-card">
                <button
                    type="button"
                    className="admin-logout-button"
                    onClick={handleBack}
                >
                    ← 返回候选人列表
                </button>

                <div className="card-heading" style={{ marginTop: 24 }}>
                    <div className="card-icon">▣</div>
                    <div>
                        <h2>候选人面试详情</h2>
                        <p>查看候选人的完整 AI 面试问答记录</p>
                    </div>
                </div>

                {loading && <p>正在加载面试详情...</p>}

                {error && (
                    <p className="error" role="alert">
                        {error}
                    </p>
                )}

                {!loading && !error && interview && (
                    <>

                        <div className="admin-interview-info">
                            <div className="admin-info-header">
                                <div>
                                    <h3>候选人信息</h3>
                                    <p>本场 AI 面试的基础资料</p>
                                </div>

                                <span
                                    className={
                                        interview.status === "completed"
                                            ? "admin-status-badge completed"
                                            : "admin-status-badge ongoing"
                                    }
                                >
                                    {interview.status === "completed"
                                        ? "✓ 已完成"
                                        : "◷ 进行中"}
                                </span>
                            </div>

                            <div className="admin-info-grid">
                                <div className="admin-info-item">
                                    <span>候选人姓名</span>
                                    <strong>{interview.candidate_name || "未填写"}</strong>
                                </div>

                                <div className="admin-info-item">
                                    <span>应聘岗位</span>
                                    <strong>{interview.position}</strong>
                                </div>

                                <div className="admin-info-item">
                                    <span>面试时间</span>
                                    <strong>
                                        {interview.created_at.replace("T", " ").slice(0, 19)}
                                    </strong>
                                </div>

                                <div className="admin-info-item">
                                    <span>面试编号</span>
                                    <strong>#{interview.interview_id}</strong>
                                </div>
                            </div>
                        </div>


                        <div className="admin-evaluation">
                            <h3>AI 面试评估报告</h3>

                            {interview.status !== "completed" ? (
                                <p>面试尚未结束，暂无评估报告。</p>
                            ) : evaluationLoading ? (
                                <p>正在加载 AI 评估报告...</p>
                            ) : evaluationError ? (
                                <p className="error" role="alert">
                                    {evaluationError}
                                </p>
                            ) : evaluation ? (
                                <>
                                    <div className="admin-evaluation-scores">
                                        <div>
                                            <span>综合评分</span>
                                            <strong>{evaluation.overall_score}</strong>
                                        </div>
                                        <div>
                                            <span>技术能力</span>
                                            <strong>{evaluation.technical_score}</strong>
                                        </div>
                                        <div>
                                            <span>回答完整度</span>
                                            <strong>{evaluation.completeness_score}</strong>
                                        </div>
                                        <div>
                                            <span>表达清晰度</span>
                                            <strong>{evaluation.clarity_score}</strong>
                                        </div>
                                    </div>

                                    <CompetencyPanel
                                        report={(evaluation as AdminEvaluation & {
                                            competency_assessment?: CompetencyReport | null;
                                        }).competency_assessment}
                                    />

                                    <div className="admin-evaluation-section">
                                        <h4>AI 综合评价</h4>
                                        <p>{evaluation.summary}</p>
                                    </div>

                                    <div className="admin-evaluation-section">
                                        <h4>表现亮点</h4>
                                        <p>{evaluation.strengths}</p>
                                    </div>

                                    <div className="admin-evaluation-section">
                                        <h4>有待提升</h4>
                                        <p>{evaluation.weaknesses}</p>
                                    </div>

                                    <div className="admin-evaluation-section">
                                        <h4>改进建议</h4>
                                        <p>{evaluation.suggestions}</p>
                                    </div>
                                </>
                            ) : (
                                <p>暂无 AI 评估报告。</p>
                            )}
                        </div>
                        <div className="admin-qa-header">
                            <div>
                                <h3>完整面试问答</h3>
                                <p>按时间顺序展示 AI 面试官提问与候选人回答</p>
                            </div>

                            <span className="admin-qa-count">
                                共 {interview.messages.length} 条记录
                            </span>
                        </div>

                        {interview.messages.length === 0 ? (
                            <p>暂无面试问答记录。</p>
                        ) : (
                            <div className="admin-message-list">
                                {interview.messages.map((message) => (
                                    <div
                                        key={message.id}
                                        className={
                                            message.role === "assistant"
                                                ? "admin-message admin-message-ai"
                                                : "admin-message admin-message-user"
                                        }
                                    >
                                        <strong>
                                            {message.role === "assistant"
                                                ? "AI 面试官"
                                                : "候选人回答"}
                                        </strong>

                                        <p style={{ whiteSpace: "pre-wrap" }}>
                                            {message.content}
                                        </p>
                                    </div>
                                ))}
                            </div>
                        )}
                    </>
                )}
            </section>
        </div>
    );
}