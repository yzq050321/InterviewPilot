
import type {
  InterviewDetail as InterviewDetailType,
} from "../types/interview";

type InterviewDetailProps = {
  interview: InterviewDetailType;
  detailLoading: boolean;
  loading: boolean;
  finishing: boolean;
  onResumeInterview: (interviewId: number) => void;
  onLoadEvaluation: (interviewId: number) => void;
};

export default function InterviewDetail({
  interview,
  detailLoading,
  loading,
  finishing,
  onResumeInterview,
  onLoadEvaluation,
}: InterviewDetailProps) {
  return (
    <section className="chat-card">
      <div className="chat-header">
        <div>
          <h2>✦ 历史面试详情</h2>
          <p>
            {interview.position}
            {" · "}
            {interview.difficulty}
          </p>
        </div>

        <span className="chat-status">
          面试 #{interview.interview_id}
          {" · "}
          {interview.status === "completed"
            ? "已结束"
            : "进行中"}
        </span>
      </div>

      <div className="chat-messages">
        {interview.messages.length === 0 ? (
          <p className="history-message">
            这场面试暂无对话记录
          </p>
        ) : (
          interview.messages.map((message) => (
            <div
              key={message.id}
              className={`chat-message ${message.role}`}
            >
              <div className="message-avatar">
                {message.role === "assistant"
                  ? "✦"
                  : "我"}
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
          ))
        )}
      </div>

      {interview.status === "in_progress" && (
        <div className="answer-area">
          <button
            type="button"
            className="start-button"
            onClick={() =>
              onResumeInterview(interview.interview_id)
            }
            disabled={
              detailLoading || loading || finishing
            }
          >
            {detailLoading
              ? "正在恢复面试..."
              : "✦ 继续这场模拟面试 →"}
          </button>
        </div>
      )}

      {interview.status === "completed" && (
        <div className="answer-area">

          <button
            type="button"
            className="start-button"
            onClick={() =>
              onLoadEvaluation(interview.interview_id)
            }
          >
            查看历史 AI 评估报告 →
          </button>
        </div>
      )}
    </section>
  );
}