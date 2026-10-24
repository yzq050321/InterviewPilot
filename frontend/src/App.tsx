
import { useEffect, useRef, useState } from "react";
import "./App.css";
import {
  createInterview,
  submitInterviewAnswer,
  completeInterview,
  generateInterviewEvaluation,
  getInterviewDetail,
} from "./services/api";
import type {
  Message,
  Evaluation,
} from "./types/interview";
import InterviewForm from "./components/InterviewForm";
import InterviewChat from "./components/InterviewChat";
import AdminLoginPage from "./pages/AdminLoginPage";
import AdminDashboardPage from "./pages/AdminDashboardPage";
import AdminInterviewDetailPage from "./pages/AdminInterviewDetailPage";
import AdminJobsPage from "./pages/AdminJobsPage";
import AdminJobDetailPage from "./pages/AdminJobDetailPage";
import JobInvitationPage from "./pages/JobInvitationPage";
import type { InvitedInterview, Difficulty } from "./services/jobApi";
import {
  Link,
  NavLink,
  Route,
  Routes,
  useNavigate,
  useMatch,
  useLocation,
} from "react-router-dom";

function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const showHrDock = location.pathname.startsWith("/admin") && location.pathname !== "/admin/login" && Boolean(sessionStorage.getItem("admin_token"));
  const interviewMatch = useMatch("/interview/:id");
  const routeInterviewId = interviewMatch?.params.id;
  const chatRef = useRef<HTMLElement | null>(null);
  const [candidateName, setCandidateName] = useState("");
  const [position, setPosition] = useState("Python 后端开发实习生");
  const [difficulty, setDifficulty] = useState<Difficulty>("中等");
  const [interviewId, setInterviewId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [completed, setCompleted] = useState(false);
  const [, setDetailLoading] = useState(false);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [finishing, setFinishing] = useState(false);
  const submittingRef = useRef(false);
  // One durable request identifier per unanswered question. Keep it on timeout,
  // so a retry reuses the same identifier rather than paying for another LLM call.
  type PendingAnswer = { requestId: string; questionId: number; answer: string };
  function pendingKey(id: number) { return `pending_answer_${id}`; }
  function readPending(id: number): PendingAnswer | null {
    try {
      const raw = sessionStorage.getItem(pendingKey(id));
      if (!raw) return null;
      const parsed: unknown = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object") return null;
      const candidate = parsed as Partial<PendingAnswer>;
      if (typeof candidate.requestId !== "string" || typeof candidate.questionId !== "number" || typeof candidate.answer !== "string") return null;
      return candidate as PendingAnswer;
    } catch { return null; }
  }



  // 创建一场新的模拟面试

  async function startInterview() {
    if (!candidateName.trim()) {
      setError("请输入候选人姓名");
      return;
    }

    if (!position.trim()) {
      setError("请输入面试岗位");
      return;
    }

    setLoading(true);
    setError("");
    setCompleted(false);
    setEvaluation(null);

    try {
      const data = await createInterview(
        candidateName.trim(),
        position.trim(),
        "中等"
      );

      // 仅在当前浏览器标签页会话中保存这场面试的访问凭证
      sessionStorage.setItem(
        `interview_token_${data.interview_id}`,
        data.interview_token
      );
      sessionStorage.removeItem(pendingKey(data.interview_id));
      setInterviewId(data.interview_id);
      setDifficulty("中等");
      navigate(`/interview/${data.interview_id}`);

      setMessages([
        {
          id: data.question_id,
          role: "assistant",
          content: data.question,
        },
      ]);

      setAnswer("");

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "开始面试失败"
      );
    } finally {
      setLoading(false);
    }
  }

  // 邀请面试复用现有候选人 Token、问答及完成报告流程。
  function handleInvitationStarted(data: InvitedInterview) {
    sessionStorage.setItem(`interview_token_${data.interview_id}`, data.interview_token);
    sessionStorage.removeItem(pendingKey(data.interview_id));
    setCandidateName(data.candidate_name);
    setPosition(data.position);
    setDifficulty(data.difficulty);
    setInterviewId(data.interview_id);
    setMessages([{ id: data.question_id, role: "assistant", content: data.question }]);
    setAnswer("");
    setError("");
    setCompleted(false);
    setEvaluation(null);
    navigate(`/interview/${data.interview_id}`);
  }

  // 提交回答，获取 AI 追问

  async function submitAnswer() {
    if (
      interviewId === null ||
      !answer.trim() ||
      loading ||
      finishing ||
      completed ||
      submittingRef.current
    ) {
      return;
    }

    // 立即锁定，防止重复提交
    submittingRef.current = true;

    const currentAnswer = answer.trim();
    const currentQuestion = [...messages].reverse().find((item) => item.role === "assistant");
    if (!currentQuestion?.id) {
      setError("无法确认当前题目，请刷新面试页面后再试");
      submittingRef.current = false;
      return;
    }
    const previous = readPending(interviewId);
    if (previous && (previous.questionId !== currentQuestion.id || previous.answer !== currentAnswer)) {
      // Do not silently reuse a request id with different content.
      // A changed question means the previous response has already been saved.
      if (previous.questionId === currentQuestion.id) {
        setError("这道题有尚未确认的提交，请先用原回答重试或刷新页面");
        submittingRef.current = false;
        return;
      }
      sessionStorage.removeItem(pendingKey(interviewId));
    }
    const pending: PendingAnswer = previous && previous.questionId === currentQuestion.id
      ? previous
      : { requestId: crypto.randomUUID(), questionId: currentQuestion.id, answer: currentAnswer };
    sessionStorage.setItem(pendingKey(interviewId), JSON.stringify(pending));

    setLoading(true);
    setError("");
    try {
      const data = await submitInterviewAnswer(
        interviewId, currentAnswer, pending.requestId, pending.questionId
      );
      setMessages((prev) => [
        ...prev,
        { role: "user", content: currentAnswer },
        { id: data.question_id, role: "assistant", content: data.next_question },
      ]);
      sessionStorage.removeItem(pendingKey(interviewId));
      setAnswer("");
      setCompleted(false);
      setEvaluation(null);
    } catch (err) {
      // Retain pending request id/answer for safe replays after timeouts.
      setError(err instanceof Error ? err.message : "提交回答失败，请使用原回答重试");
    } finally {
      submittingRef.current = false;
      setLoading(false);
    }
  }




  async function generateReport(id: number) {
  // 通知后端生成评估报告，并保存到数据库
    // 候选人不读取报告内容，报告由 HR 在 B 端查看
    await generateInterviewEvaluation(id);
  }



  async function finishInterview() {
    if (interviewId === null || loading || finishing || completed) {
      return;
    }
    const userAnswers = messages.filter(
      (message) => message.role === "user"
    );

    if (userAnswers.length === 0) {
      setError(
        "请至少回答一道面试题后，再结束面试并生成报告"
      );
      return;
    }

    const confirmed = window.confirm(
      "确定要结束本次面试吗？结束后将生成 AI 能力评估报告。"
    );

    if (!confirmed) return;

    setFinishing(true);
    setError("");

    try {
      // 结束面试并保存完成状态
      await completeInterview(interviewId);

      setCompleted(true);

      // 继续生成评估报告，供后续 B 端查看
      await generateReport(interviewId);

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "结束面试或生成评估报告失败"
      );
    } finally {
      setFinishing(false);
    }
  }


  async function retryGenerateReport() {
    if (interviewId === null || finishing) {
      return;
    }

    setFinishing(true);
    setError("");

    try {
      await generateReport(interviewId);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "生成报告失败"
      );
    } finally {
      setFinishing(false);
    }
  }

  




  useEffect(() => {
    if (!routeInterviewId) return;

    const id = Number(routeInterviewId);

    // 检查 URL 中的 ID 是否有效
    if (!Number.isInteger(id) || id <= 0) {
      setError("无效的面试 ID");
      return;
    }

    // 当前面试已加载，不需要重复请求
    if (interviewId === id) return;

    let cancelled = false;

    async function restoreFromUrl() {
      setDetailLoading(true);
      setError("");

      try {
        const data = await getInterviewDetail(id);

        if (cancelled) return;

        setInterviewId(data.interview_id);
        setPosition(data.position);
        setDifficulty(data.difficulty as Difficulty);

        setMessages(
          data.messages.map((message) => ({
            id: message.id,
            role: message.role === "user" ? "user" : "assistant",
            content: message.content,
          }))
        );

        const last = [...data.messages].reverse().find((item) => item.role === "assistant");
        const pending = readPending(id);
        if (pending && (!last || pending.questionId !== last.id || data.status !== "in_progress")) {
          sessionStorage.removeItem(pendingKey(id));
        }
        setAnswer(pending && last?.id === pending.questionId && data.status === "in_progress" ? pending.answer : "");
        setCompleted(data.status !== "in_progress");

        // C 端不读取 AI 评估报告
        setEvaluation(null);

      } catch (err) {
        if (cancelled) return;

        setError(
          err instanceof Error
            ? err.message
            : "加载面试失败"
        );
      } finally {
        if (!cancelled) {
          setDetailLoading(false);
        }
      }
    }

    void restoreFromUrl();

    return () => {
      cancelled = true;
    };
  }, [routeInterviewId, interviewId]);


  return (
    <div className="app">

      <header className="navbar">
        <div className="brand">
          <div className="brand-icon">✦</div>
          <span>InterviewPilot</span>
        </div>


        <nav className="nav-links">
          <Link to="/">首页</Link>

          {interviewId !== null && (
            <Link to={`/interview/${interviewId}`}>
              当前面试
            </Link>
          )}

          <Link to="/admin/login">
            招聘方入口
          </Link>
        </nav>
      </header>

      <main className="main-content">
        <Routes>
          <Route
            path="/admin/login"
            element={<AdminLoginPage />}
          />

          <Route
            path="/admin"
            element={<AdminDashboardPage />}
          />

          <Route path="/admin/jobs" element={<AdminJobsPage />} />
          <Route path="/admin/jobs/:jobId" element={<AdminJobDetailPage />} />
          <Route path="/invite/:inviteCode" element={<JobInvitationPage onStarted={handleInvitationStarted} />} />

          <Route
            path="/admin/interviews/:id"
            element={<AdminInterviewDetailPage />}
          />
          <Route
            path="/"
            element={
              <>
                <section className="hero">
                  <div className="hero-badge">✦ AI POWERED INTERVIEW</div>
                  <h1>
                    以专业展现实力，
                    <span>让每一次回答都被看见</span>
                  </h1>
                  <p>智能生成面试题 · 实时深度追问 · 多维能力评估</p>
                </section>


                <InterviewForm
                  candidateName={candidateName}
                  position={position}
                  loading={loading}
                  interviewId={interviewId}
                  onCandidateNameChange={setCandidateName}
                  onPositionChange={setPosition}
                  onStartInterview={startInterview}
                />
                {error && <p className="error" role="alert">{error}</p>}
              </>
            }
          />

          <Route
            path="/interview/:id"
            element={
              <>
                {interviewId !== null ? (
                  <>
                    <InterviewChat
                      interviewId={interviewId}
                      position={position}
                      difficulty={difficulty}
                      messages={messages}
                      answer={answer}
                      loading={loading}
                      finishing={finishing}
                      completed={completed}
                      hasEvaluation={evaluation !== null}
                      chatRef={chatRef}
                      onAnswerChange={setAnswer}
                      onSubmitAnswer={submitAnswer}
                      onFinishInterview={finishInterview}
                      onRetryReport={retryGenerateReport}
                    />
                  </>
                ) : (
                  <p className="history-message">
                    尚未加载面试，请返回首页开始面试，或从历史记录恢复面试。
                  </p>
                )}
                {error && <p className="error" role="alert">{error}</p>}
              </>
            }
          />

          
        </Routes>
      </main>
      {showHrDock && <nav className="hr-mobile-dock" aria-label="招聘后台快捷导航">
        <NavLink to="/admin/jobs" className={({ isActive }) => isActive ? "active" : ""}>▣<span>岗位</span></NavLink>
        <NavLink to="/admin" end className={({ isActive }) => isActive ? "active" : ""}>☷<span>全部面试</span></NavLink>
      </nav>}
    </div>
  );
}

export default App;