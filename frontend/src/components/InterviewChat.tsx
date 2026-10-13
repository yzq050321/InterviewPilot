
import type { Ref } from "react";
import type { Message } from "../types/interview";

type InterviewChatProps = {
  interviewId: number;
  position: string;
  difficulty: string;
  messages: Message[];
  answer: string;
  loading: boolean;
  finishing: boolean;
  completed: boolean;
  hasEvaluation: boolean;
  chatRef: Ref<HTMLElement>;
  onAnswerChange: (value: string) => void;
  onSubmitAnswer: () => void;
  onFinishInterview: () => void;
  onRetryReport: () => void;
};

export default function InterviewChat({
  interviewId,
  position,
  difficulty,
  messages,
  answer,
  loading,
  finishing,
  completed,
  hasEvaluation,
  chatRef,
  onAnswerChange,
  onSubmitAnswer,
  onFinishInterview,
  onRetryReport,
}: InterviewChatProps) {
  return (
    <section className="chat-card" ref={chatRef}>
      <div className="chat-header">
        <div>
          <h2>✦ AI 模拟面试</h2>
          <p>
            {position} · {difficulty}
          </p>
        </div>

        <span className="chat-status">
          {completed
            ? `✓ 面试 #${interviewId} 已结束`
            : `● 面试 #${interviewId} 进行中`}
        </span>
      </div>

      <div className="chat-messages">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`chat-message ${message.role}`}
          >
            <div className="message-avatar">
              {message.role === "assistant" ? "✦" : "我"}
            </div>

            <div className="message-content">
              <div className="message-role">
                {message.role === "assistant"
                  ? "AI 面试官"
                  : "我的回答"}
              </div>

              <div className="message-text">
                {message.content}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="answer-area">
        <label htmlFor="answer">你的回答</label>

        <textarea
          id="answer"
          value={answer}
          onChange={(e) =>
            onAnswerChange(e.target.value)
          }
          placeholder="请输入你的回答，AI 面试官将根据你的回答继续追问..."
          rows={5}
          disabled={loading || finishing || completed}
        />

        <button
          type="button"
          className="start-button"
          onClick={onSubmitAnswer}
          disabled={
            loading ||
            finishing ||
            completed ||
            !answer.trim()
          }
        >
          {loading
            ? "AI 正在思考下一道问题..."
            : "提交回答，继续面试 →"}
        </button>

        {!completed && (
          <button
            type="button"
            className="finish-button"
            onClick={onFinishInterview}
            disabled={loading || finishing}
          >
            {finishing
              ? "正在结束面试并生成报告..."
              : "结束面试并生成 AI 评估报告"}
          </button>
        )}

        {completed && !hasEvaluation && (
          <button
            type="button"
            className="finish-button"
            onClick={onRetryReport}
            disabled={finishing}
          >
            {finishing
              ? "正在生成评估报告..."
              : "重新尝试生成评估报告"}
          </button>
        )}
      </div>
    </section>
  );
}