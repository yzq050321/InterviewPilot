
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import EvaluationReport from "../components/EvaluationReport";
import { getInterviewEvaluation } from "../services/api";
import type { Evaluation } from "../types/interview";

function ReportPage() {
  // 获取 URL 中的面试 ID
  const { id } = useParams<{ id: string }>();

  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadReport() {
      setLoading(true);
      setError("");
      setEvaluation(null);

      const interviewId = Number(id);

      if (!Number.isInteger(interviewId) || interviewId <= 0) {
        setError("无效的面试 ID");
        setLoading(false);
        return;
      }

      try {
        const report = await getInterviewEvaluation(interviewId);

        if (!cancelled) {
          setEvaluation(report);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "获取评估报告失败"
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadReport();

    return () => {
      cancelled = true;
    };
  }, [id]);

  return (
    <section>
      <h1>AI 面试评估报告</h1>

      <p>
        <Link to="/history">← 返回历史记录</Link>
      </p>

      {loading && (
        <p className="history-message">
          正在加载评估报告...
        </p>
      )}

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {evaluation && (
        <EvaluationReport
          evaluation={evaluation}
          isHistory
        />
      )}
    </section>
  );
}

export default ReportPage;