
import type { Evaluation } from "../types/interview";

type EvaluationReportProps = {
  evaluation: Evaluation;
  isHistory?: boolean;
};

export default function EvaluationReport({
  evaluation,
  isHistory = false,
}: EvaluationReportProps) {
  const scores = [
    {
      label: "技术能力",
      score: evaluation.technical_score,
    },
    {
      label: "回答完整性",
      score: evaluation.completeness_score,
    },
    {
      label: "表达清晰度",
      score: evaluation.clarity_score,
    },
  ];

  return (
    <section className="evaluation-card">
      <div className="evaluation-heading">
        <span className="question-tag">
          {isHistory
            ? "HISTORY EVALUATION"
            : "AI EVALUATION"}
        </span>

        <h2>
          {isHistory
            ? "历史 AI 面试能力评估报告"
            : "AI 面试能力评估报告"}
        </h2>

        <p>
          {isHistory
            ? `面试 #${evaluation.interview_id}`
            : "基于本次面试对话生成的综合能力分析"}
        </p>
      </div>

      <div className="overall-score">
        <span>综合评分</span>
        <strong>
          {evaluation.overall_score ?? "—"}
        </strong>
        <span>/ 100</span>
      </div>

      {!isHistory && (
        <div className="score-list">
          {scores.map((item) => (
            <div
              className="score-item"
              key={item.label}
            >
              <div className="score-label">
                <span>{item.label}</span>
                <strong>
                  {item.score ?? "—"}/100
                </strong>
              </div>

              <div className="score-track">
                <div
                  className="score-fill"
                  style={{
                    width: `${Math.max(
                      0,
                      Math.min(100, item.score ?? 0)
                    )}%`,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="evaluation-section">
        <h3>面试综合评价</h3>
        <p>{evaluation.summary}</p>
      </div>

      <div className="evaluation-section">
        <h3>表现优势</h3>
        <ul>
          {evaluation.strengths.map(
            (item, index) => (
              <li key={index}>{item}</li>
            )
          )}
        </ul>
      </div>

      <div className="evaluation-section">
        <h3>需要提升的方面</h3>
        <ul>
          {evaluation.weaknesses.map(
            (item, index) => (
              <li key={index}>{item}</li>
            )
          )}
        </ul>
      </div>

      <div className="evaluation-section">
        <h3>AI 改进建议</h3>
        <ul>
          {evaluation.suggestions.map(
            (item, index) => (
              <li key={index}>{item}</li>
            )
          )}
        </ul>
      </div>
    </section>
  );
}