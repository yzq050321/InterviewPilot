/** HR-only evaluation recovery / review workflow. Candidate endpoints never use these APIs. */
const API_BASE = import.meta.env.DEV ? "http://127.0.0.1:8000" : "";

export type EvaluationStatus = "not_started" | "pending" | "generating" | "failed" | "ready";
export type ReviewStatus = "pending" | "reviewed" | "follow_up";

export const evaluationLabels: Record<EvaluationStatus, string> = {
  not_started: "面试中",
  pending: "待生成报告",
  generating: "正在生成报告",
  failed: "报告生成失败",
  ready: "报告已生成",
};
export const reviewLabels: Record<ReviewStatus, string> = {
  pending: "待人工复核",
  reviewed: "已人工复核",
  follow_up: "需后续沟通",
};

async function authRequest(path: string, init: RequestInit = {}): Promise<Response> {
  const token = sessionStorage.getItem("admin_token");
  if (!token) throw new Error("管理员未登录，请先登录");
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...init.headers, Authorization: `Bearer ${token}` },
  });
  if (response.status === 401) {
    sessionStorage.removeItem("admin_token");
    throw new Error("管理员登录已失效，请重新登录");
  }
  return response;
}

async function readResponse<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    let detail = fallback;
    try {
      const data: unknown = await response.json();
      if (data && typeof data === "object" && "detail" in data && typeof data.detail === "string") {
        detail = data.detail;
      }
    } catch { /* Non-JSON server error. */ }
    throw new Error(`${detail}（HTTP ${response.status}）`);
  }
  return response.json() as Promise<T>;
}

export async function retryEvaluation(interviewId: number): Promise<{ evaluation_id: number; message: string }> {
  return readResponse(
    await authRequest(`/api/admin/interviews/${interviewId}/evaluation/retry`, { method: "POST" }),
    "报告生成失败",
  );
}

export async function updateInterviewReview(
  interviewId: number,
  reviewStatus: ReviewStatus,
  reviewNote: string,
): Promise<{ review_status: ReviewStatus; review_note: string; reviewed_at: string | null }> {
  return readResponse(
    await authRequest(`/api/admin/interviews/${interviewId}/review`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ review_status: reviewStatus, review_note: reviewNote }),
    }),
    "保存人工复核失败",
  );
}
