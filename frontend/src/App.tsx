
import { useEffect, useRef, useState } from "react";
import "./App.css";
import {
  getInterviewEvaluation,
  getInterviewHistory,
  createInterview,
  submitInterviewAnswer,
  completeInterview,
  generateInterviewEvaluation,
  getInterviewDetail,
} from "./services/api";
import type {
  Message,
  Evaluation,
  InterviewHistory as InterviewHistoryType,
  InterviewDetail as InterviewDetailType,
} from "./types/interview";
import InterviewForm from "./components/InterviewForm";
import InterviewChat from "./components/InterviewChat";
import EvaluationReport from "./components/EvaluationReport";
import InterviewHistory from "./components/InterviewHistory";
import InterviewDetail from "./components/InterviewDetail";

function App() {
  const chatRef = useRef<HTMLElement | null>(null);
  const [scrollToChat, setScrollToChat] = useState(false);
  const [position, setPosition] = useState("Java后端开发实习生");
  const [difficulty, setDifficulty] = useState("中等");
  const [interviewId, setInterviewId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [completed, setCompleted] = useState(false);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [finishing, setFinishing] = useState(false);
  const [interviewHistory, setInterviewHistory] = useState<InterviewHistoryType[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [selectedInterview, setSelectedInterview] = useState<InterviewDetailType | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [historyEvaluation, setHistoryEvaluation] = useState<Evaluation | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState("");
  const submittingRef = useRef(false);


  // 创建一场新的模拟面试

  async function startInterview() {
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
        position.trim(),
        difficulty
      );

      setInterviewId(data.interview_id);

      setMessages([
        {
          role: "assistant",
          content: data.question,
        },
      ]);

      setAnswer("");

      void fetchInterviewHistory();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "创建面试失败"
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
    // 第一步：通知后端生成 AI 评估报告
    await generateInterviewEvaluation(id);

    // 第二步：获取完整评估报告
    const report: Evaluation =
      await getInterviewEvaluation(id);

    // 第三步：保存到 React 状态
    setEvaluation(report);
  }

  async function finishInterview() {
    if (
      interviewId === null ||
      loading ||
      finishing ||
      completed
    ) {
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
      // 调用封装后的结束面试接口
      await completeInterview(interviewId);

      setCompleted(true);

      // 保留原来的评估报告生成逻辑
      await generateReport(interviewId);

      // 刷新历史面试记录
      void fetchInterviewHistory();
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

  async function fetchInterviewHistory() {
    setHistoryLoading(true);
    setHistoryError("");

    try {
      const data: InterviewHistoryType[] =
        await getInterviewHistory();

      setInterviewHistory(data);
    } catch (err) {
      setHistoryError(
        err instanceof Error
          ? err.message
          : "获取历史面试失败"
      );
    } finally {
      setHistoryLoading(false);
    }
  }


  async function loadInterviewDetail(interviewId: number) {
    setDetailLoading(true);
    setDetailError("");
    setSelectedInterview(null);
    setHistoryEvaluation(null);
    setReportError("");

    try {
      const data: InterviewDetailType =
        await getInterviewDetail(interviewId);

      setSelectedInterview(data);
    } catch (err) {
      setDetailError(
        err instanceof Error
          ? err.message
          : "获取面试详情失败"
      );
    } finally {
      setDetailLoading(false);
    }
  }

  // 恢复历史面试
  async function resumeInterview(id: number) {
    setDetailLoading(true);
    setDetailError("");

    try {
      const data: InterviewDetailType =
        await getInterviewDetail(id);

      if (data.status !== "in_progress") {
        throw new Error("该面试已经结束，无法继续");
      }

      // 恢复面试基本信息
      setInterviewId(data.interview_id);
      setPosition(data.position);
      setDifficulty(data.difficulty);

      // 恢复历史对话
      setMessages(
        data.messages.map((message) => ({
          role: message.role === "user" ? "user" : "assistant",
          content: message.content,
        }))
      );

      // 重置当前输入和报告状态
      setAnswer("");
      setCompleted(false);
      setEvaluation(null);
      setError("");

      // 关闭历史详情
      setSelectedInterview(null);
      setHistoryEvaluation(null);

      // 返回面试区域
      setScrollToChat(true);

    } catch (err) {
      setDetailError(
        err instanceof Error ? err.message : "恢复面试失败"
      );
    } finally {
      setDetailLoading(false);
    }
  }


  async function loadHistoryEvaluation(interviewId: number) {
    setReportLoading(true);
    setReportError("");
    setHistoryEvaluation(null);

    try {
      const data: Evaluation =
        await getInterviewEvaluation(interviewId);

      setHistoryEvaluation(data);
    } catch (err) {
      setReportError(
        err instanceof Error
          ? err.message
          : "获取评估报告失败"
      );
    } finally {
      setReportLoading(false);
    }
  }

  useEffect(() => {
    void fetchInterviewHistory();
  }, []);

  useEffect(() => {
    if (!scrollToChat || interviewId === null) return;

    chatRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });

    setScrollToChat(false);
  }, [scrollToChat, interviewId]);

  return (
    <div className="app">
      <header className="navbar">
        <div className="brand">
          <div className="brand-icon">✦</div>
          <span>InterviewPilot</span>
        </div>

        <span className="nav-description">
          AI 智能模拟面试平台
        </span>
      </header>

      <main className="main-content">
        <section className="hero">
          <div className="hero-badge">
            ✦ AI POWERED INTERVIEW
          </div>

          <h1>
            让每一次练习，
            <span>都更接近理想 Offer</span>
          </h1>

          <p>
            智能生成面试题 · 实时深度追问 · 多维能力评估
          </p>
        </section>


        <InterviewForm
          position={position}
          difficulty={difficulty}
          loading={loading}
          interviewId={interviewId}
          onPositionChange={setPosition}
          onDifficultyChange={setDifficulty}
          onStartInterview={startInterview}
        />


        {interviewId !== null && (
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
        )}


        {evaluation && (
          <EvaluationReport evaluation={evaluation} />
        )}

        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}



        <InterviewHistory
          interviewHistory={interviewHistory}
          historyLoading={historyLoading}
          historyError={historyError}
          onSelectInterview={loadInterviewDetail}
        />
        {detailLoading && (
          <p className="history-message">
            正在加载面试详情...
          </p>
        )}

        {detailError && (
          <p className="error" role="alert">
            {detailError}
          </p>
        )}


        {selectedInterview && (
          <InterviewDetail
            interview={selectedInterview}
            detailLoading={detailLoading}
            loading={loading}
            finishing={finishing}
            reportLoading={reportLoading}
            onResumeInterview={resumeInterview}
            onLoadEvaluation={loadHistoryEvaluation}
          />
        )}

        {reportError && (
          <p className="error" role="alert">
            {reportError}
          </p>
        )}

        {historyEvaluation && (
          <EvaluationReport
            evaluation={historyEvaluation}
            isHistory
          />
        )}
      </main>
    </div>
  );
}

export default App;