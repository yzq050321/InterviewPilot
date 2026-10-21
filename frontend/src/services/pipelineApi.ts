/** Batch 9: HR follow-up APIs. Always use same-origin /api, no candidate credentials. */
export type RecruitmentStage = "new" | "contact" | "next_round" | "decision" | "closed";
export const stageLabels: Record<RecruitmentStage, string> = {
  new: "待处理", contact: "待沟通", next_round: "下一轮",
  decision: "待决定", closed: "流程结束",
};
export type Followup = {
  id: number; interview_id: number; old_stage: RecruitmentStage;
  new_stage: RecruitmentStage; note: string; created_at: string;
};
export type PipelineDetail = { interview_id: number; stage: RecruitmentStage; history: Followup[] };
export type StageRow = { interview_id: number; stage: RecruitmentStage };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = sessionStorage.getItem("admin_token");
  if (!token) throw new Error("请先登录 HR 账号");
  const response = await fetch(path, {
    ...init,
    headers: { ...init?.headers, Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    if (response.status === 401) throw new Error("登录失效或无权限，请重新登录");
    let message = `操作失败（HTTP ${response.status}）`;
    try { const data: unknown = await response.json();
      if (data && typeof data === "object" && "detail" in data && typeof data.detail === "string") message = data.detail;
    } catch { /* retain generic error */ }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}
function base(): string {
  return sessionStorage.getItem("admin_role") === "demo" ? "/api/demo" : "/api/admin";
}
export function getPipelineOverview(): Promise<StageRow[]> {
  return request<StageRow[]>(`${base()}/pipeline`);
}
export function getPipelineDetail(interviewId: number): Promise<PipelineDetail> {
  return request<PipelineDetail>(`${base()}/interviews/${interviewId}/pipeline`);
}
export function saveFollowup(interviewId: number, stage: RecruitmentStage, note: string): Promise<{ interview_id: number; stage: RecruitmentStage; followup: Followup }> {
  if (sessionStorage.getItem("admin_role") === "demo") throw new Error("演示账号仅可查看，不能修改招聘流程");
  return request(`/api/admin/interviews/${interviewId}/pipeline`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ stage, note }),
  });
}
