/** InterviewPilot V2 招聘任务接口。生产环境沿用当前 HTTPS 域名访问 /api。 */
const API_BASE = import.meta.env.DEV ? "http://127.0.0.1:8000" : "";

export type Difficulty = "简单" | "中等" | "困难";

export type JobPosting = {
  job_id: number;
  title: string;
  position: string;
  requirements: string;
  difficulty: Difficulty;
  is_active: boolean;
  created_at: string;
  invite_code: string;
  invite_path: string;
};

export type CreateJobInput = {
  title: string;
  position: string;
  requirements: string;
  difficulty: Difficulty;
};

export type JobInvitation = {
  title: string;
  position: string;
  requirements: string;
  difficulty: Difficulty;
};

export type InvitedInterview = {
  interview_id: number;
  interview_token: string;
  candidate_name: string;
  position: string;
  difficulty: Difficulty;
  question: string;
};

async function readError(response: Response, fallback: string): Promise<never> {
  if (response.status === 401) {
    // 只有受管理员保护的接口使用这一分支；候选人接口另行处理。
    throw new Error(`${fallback}（401）`);
  }
  try {
    const payload: unknown = await response.json();
    if (payload && typeof payload === "object" && "detail" in payload) {
      const detail = (payload as { detail: unknown }).detail;
      if (typeof detail === "string") throw new Error(detail);
    }
  } catch (error) {
    if (error instanceof Error && error.message !== "") {
      // 对业务 detail 抛出的 Error 原样保留；解析失败则使用统一错误。
      if (!(error instanceof SyntaxError)) throw error;
    }
  }
  throw new Error(`${fallback}（HTTP ${response.status}）`);
}

async function adminFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const token = sessionStorage.getItem("admin_token");
  if (!token) throw new Error("管理员未登录，请先登录");
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...init.headers,
      Authorization: `Bearer ${token}`,
    },
  });
  if (response.status === 401) {
    sessionStorage.removeItem("admin_token");
    throw new Error("管理员登录已失效，请重新登录");
  }
  return response;
}

export async function getJobs(): Promise<JobPosting[]> {
  const response = await adminFetch("/api/admin/jobs");
  if (!response.ok) return readError(response, "加载招聘任务失败");
  return response.json();
}

export async function createJob(input: CreateJobInput): Promise<JobPosting> {
  const response = await adminFetch("/api/admin/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) return readError(response, "创建招聘任务失败");
  return response.json();
}

export async function deactivateJob(jobId: number): Promise<JobPosting> {
  const response = await adminFetch(`/api/admin/jobs/${jobId}/deactivate`, { method: "PATCH" });
  if (!response.ok) return readError(response, "停用招聘任务失败");
  return response.json();
}

export async function getJobInvitation(inviteCode: string): Promise<JobInvitation> {
  const response = await fetch(
    `${API_BASE}/api/job-invitations/${encodeURIComponent(inviteCode)}`
  );
  if (!response.ok) return readError(response, "面试邀请加载失败");
  return response.json();
}

export async function createInvitedInterview(
  inviteCode: string,
  candidateName: string
): Promise<InvitedInterview> {
  const response = await fetch(
    `${API_BASE}/api/job-invitations/${encodeURIComponent(inviteCode)}/interviews`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ candidate_name: candidateName }),
    }
  );
  if (!response.ok) return readError(response, "创建面试失败");
  return response.json();
}
