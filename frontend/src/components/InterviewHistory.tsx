
import type { InterviewHistory as InterviewHistoryType } from "../types/interview";

type InterviewHistoryProps = {
  interviewHistory: InterviewHistoryType[];
  historyLoading: boolean;
  historyError: string;
  onSelectInterview: (interviewId: number) => void;
};

export default function InterviewHistory({
  interviewHistory,
  historyLoading,
  historyError,
  onSelectInterview,
}: InterviewHistoryProps) {
  return (
    <section className="history-card">
      <div className="history-heading">
        <div>
          <h2>✦ 历史面试记录</h2>
          <p>回顾每一次练习，见证自己的成长</p>
        </div>

        <span className="history-count">
          共 {interviewHistory.length} 场
        </span>
      </div>

      {historyLoading && (
        <p className="history-message">
          正在加载历史面试...
        </p>
      )}

      {historyError && (
        <p className="error">{historyError}</p>
      )}

      {!historyLoading &&
        !historyError &&
        interviewHistory.length === 0 && (
          <p className="history-message">
            暂无历史面试记录
          </p>
        )}

      {!historyLoading &&
        !historyError &&
        interviewHistory.map((item) => (
          <div
            className="history-item"
            key={item.interview_id}
            role="button"
            tabIndex={0}
            onClick={() =>
              onSelectInterview(item.interview_id)
            }
            onKeyDown={(e) => {
              if (
                e.key === "Enter" ||
                e.key === " "
              ) {
                e.preventDefault();
                onSelectInterview(item.interview_id);
              }
            }}
            style={{ cursor: "pointer" }}
          >
            <div className="history-info">
              <h3>{item.position}</h3>

              <p>
                面试 #{item.interview_id}
                {" · "}
                {item.difficulty}
                {" · "}
                {new Date(
                  item.created_at
                ).toLocaleString("zh-CN")}
              </p>
            </div>

            <span
              className={
                item.status === "completed"
                  ? "history-status completed"
                  : "history-status ongoing"
              }
            >
              {item.status === "completed"
                ? "✓ 已结束"
                : "● 进行中"}
            </span>
          </div>
        ))}
    </section>
  );
}