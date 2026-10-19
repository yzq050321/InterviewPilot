
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
import {
  Link,
  Route,
  Routes,
  useNavigate,
  useMatch,
} from "react-router-dom";

function App() {
  const navigate = useNavigate();
  const interviewMatch = useMatch("/interview/:id");
  const routeInterviewId = interviewMatch?.params.id;
  const chatRef = useRef<HTMLElement | null>(null);
  const [candidateName, setCandidateName] = useState("");
  const [position, setPosition] = useState("Java后端开发实习生");
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
      setInterviewId(data.interview_id);
      navigate(`/interview/${data.interview_id}`);

      setMessages([
        {
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

    setLoading(true);
    setError("");

    try {
      // 调用封装后的 API
      const data = await submitInterviewAnswer(
        interviewId,
        currentAnswer
      );

      // 更新聊天记录
      setMessages((prev) => [
        ...prev,
        {
          role: "user",
          content: currentAnswer,
        },
        {
          role: "assistant",
          content: data.next_question,
        },
      ]);

      // 清空输入框，重置相关状态
      setAnswer("");
      setCompleted(false);
      setEvaluation(null);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "提交回答失败"
      );
    } finally {
      // 无论成功或失败，都释放提交锁
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

        setMessages(
          data.messages.map((message) => ({
            role: message.role === "user" ? "user" : "assistant",
            content: message.content,
          }))
        );

        setAnswer("");
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
                      difficulty="中等"
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
    </div>
  );
}

export default App;