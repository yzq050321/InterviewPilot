import type { InterviewDetail } from "../types/interview";
const API_BASE = "";

/**
 * 获取历史面试记录
 */
export async function getInterviewHistory() {
  const response = await fetch(`${API_BASE}/api/interviews`);

  if (!response.ok) {
    throw new Error(`获取历史面试记录失败：${response.status}`);
  }

  return response.json();
}


/**
 * 获取指定面试的 AI 评估报告
 */
export async function getInterviewEvaluation(
  interviewId: number
) {
  const response = await fetch(
    `${API_BASE}/api/interviews/${interviewId}/evaluation`
  );

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error("该面试暂无 AI 评估报告");
    }

    throw new Error(`获取评估报告失败：${response.status}`);
  }

  return response.json();
}



/**
 * 创建面试
 */
export async function createInterview(
  candidateName: string,
  position: string,
  difficulty: string
): Promise<{
  interview_id: number;
  interview_token: string;
  candidate_name: string;
  question: string;
  question_id: number;
}> {
  const response = await fetch(`${API_BASE}/api/interviews`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      candidate_name: candidateName,
      position,
      difficulty,
    }),
  });

  if (!response.ok) {
    throw new Error(`创建面试失败：${response.status}`);
  }

  return response.json();
}



/**
 * 提交用户回答并获取 AI 追问
 */
export async function submitInterviewAnswer(
  interviewId: number,
  answer: string,
  requestId: string,
  questionId: number
): Promise<{ next_question: string; question_id: number; replayed: boolean }> {
  const token = sessionStorage.getItem(`interview_token_${interviewId}`);
  if (!token) throw new Error("面试访问凭证不存在，请重新开始面试");

  const response = await fetch(`${API_BASE}/api/interviews/followup`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ interview_id: interviewId, answer, request_id: requestId, question_id: questionId }),
  });

  if (!response.ok) {
    let message = `提交回答失败：${response.status}`;
    try {
      const data = await response.json();
      if (typeof data.detail === "string") message = data.detail;
    } catch {
      // Preserve HTTP status if response is not JSON.
    }
    throw new Error(message);
  }
  return response.json();
}


/**
 * 结束指定面试
 */
export async function completeInterview(
  interviewId: number
): Promise<void> {
  // 读取当前面试的候选人访问凭证
  const token = sessionStorage.getItem(
    `interview_token_${interviewId}`
  );

  if (!token) {
    throw new Error("面试访问凭证不存在，请重新开始面试");
  }

  const response = await fetch(
    `${API_BASE}/api/interviews/${interviewId}/complete`,
    {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    let message = `结束面试失败：${response.status}`;

    try {
      const errorData = await response.json();

      if (typeof errorData.detail === "string") {
        message = errorData.detail;
      }
    } catch {
      // 无法解析错误响应时，保留默认错误信息
    }

    throw new Error(message);
  }
}



/**
 * 生成 AI 面试评估报告
 */
export async function generateInterviewEvaluation(
  interviewId: number
): Promise<void> {
  // 读取当前面试的候选人访问凭证
  const token = sessionStorage.getItem(
    `interview_token_${interviewId}`
  );

  if (!token) {
    throw new Error("面试访问凭证不存在，无法生成评估报告");
  }

  const response = await fetch(
    `${API_BASE}/api/interviews/${interviewId}/evaluation`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    let message = `生成评估报告失败：${response.status}`;

    try {
      const errorData = await response.json();

      if (typeof errorData.detail === "string") {
        message = errorData.detail;
      }
    } catch {
      // 无法解析错误响应时，保留默认错误信息
    }

    throw new Error(message);
  }

  // 确保 POST 请求返回了有效结果
  const data = await response.json();

  if (!data) {
    throw new Error("评估报告生成失败");
  }
}



/**
 * 获取指定面试的详情和聊天记录
 */
export async function getInterviewDetail(
  interviewId: number
): Promise<InterviewDetail> {
  // 读取当前面试的候选人访问凭证
  const token = sessionStorage.getItem(
    `interview_token_${interviewId}`
  );

  if (!token) {
    throw new Error("面试访问凭证不存在，请重新开始面试");
  }

  const response = await fetch(
    `${API_BASE}/api/interviews/${interviewId}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    throw new Error(
      `获取面试详情失败：${response.status}`
    );
  }

  const data: InterviewDetail = await response.json();

  return data;
}


/**
 * HR 管理员登录
 */
export async function loginAdmin(
  username: string,
  password: string
): Promise<{
  access_token: string;
  token_type: string;
  expires_in: number;
  role: "admin" | "demo";
}> {
  const response = await fetch(
    `${API_BASE}/api/admin/login`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        username,
        password,
      }),
    }
  );

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("管理员账号或密码错误");
    }

    throw new Error(`管理员登录失败：${response.status}`);
  }

  return response.json();
}


/**
 * HR 获取全部候选人面试记录
 */
export async function getAdminInterviews(): Promise<
  {
    interview_id: number;
    candidate_name: string | null;
    position: string;
    difficulty: string;
    status: string;
    job_id: number | null;
    evaluation_status: import("./adminWorkflowApi").EvaluationStatus;
    review_status: import("./adminWorkflowApi").ReviewStatus;
    created_at: string;
  }[]
> {
  const token = sessionStorage.getItem("admin_token");

  if (!token) {
    throw new Error("管理员未登录，请先登录");
  }

  const path = sessionStorage.getItem("admin_role") === "demo"
    ? "/api/demo/interviews" : "/api/interviews";
  const response = await fetch(
    `${API_BASE}${path}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (response.status === 401) {
    sessionStorage.removeItem("admin_token");
    throw new Error("管理员登录已失效，请重新登录");
  }

  if (!response.ok) {
    throw new Error(`获取候选人面试记录失败：${response.status}`);
  }

  return response.json();
}


/**
 * HR 查看指定候选人的完整面试记录
 */
export async function getAdminInterviewDetail(
  interviewId: number
): Promise<{
  interview_id: number;
  candidate_name: string | null;
  position: string;
  difficulty: string;
  status: string;
  job_id: number | null;
  evaluation_status: import("./adminWorkflowApi").EvaluationStatus;
  evaluation_error: string | null;
  review_status: import("./adminWorkflowApi").ReviewStatus;
  review_note: string | null;
  reviewed_at: string | null;
  has_resume?: boolean;
  resume_filename?: string | null;
  resume_text?: string | null;
  created_at: string;
  messages: { id: number; role: string; content: string; created_at: string }[];
}> {
  const token = sessionStorage.getItem("admin_token");

  if (!token) {
    throw new Error("管理员未登录，请先登录");
  }

  const path = sessionStorage.getItem("admin_role") === "demo"
    ? `/api/demo/interviews/${interviewId}` : `/api/admin/interviews/${interviewId}`;
  const response = await fetch(
    `${API_BASE}${path}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (response.status === 401) {
    sessionStorage.removeItem("admin_token");
    throw new Error("管理员登录已失效，请重新登录");
  }

  if (!response.ok) {
    throw new Error(`获取面试详情失败：${response.status}`);
  }

  return response.json();
}


/**
 * HR 查看指定面试的 AI 评估报告
 */
export async function getAdminInterviewEvaluation(
  interviewId: number
): Promise<{
  id: number;
  interview_id: number;
  technical_score: number;
  completeness_score: number;
  clarity_score: number;
  overall_score: number;
  summary: string;
  strengths: string[];
  weaknesses: string[];
  suggestions: string[];
  created_at: string;
}> {
  const token = sessionStorage.getItem("admin_token");

  if (!token) {
    throw new Error("管理员未登录，请先登录");
  }

  const path = sessionStorage.getItem("admin_role") === "demo"
    ? `/api/demo/interviews/${interviewId}/evaluation`
    : `/api/interviews/${interviewId}/evaluation`;
  const response = await fetch(
    `${API_BASE}${path}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (response.status === 401) {
    sessionStorage.removeItem("admin_token");
    throw new Error("管理员登录已失效，请重新登录");
  }

  if (response.status === 404) {
    throw new Error("该面试尚未生成 AI 评估报告");
  }

  if (!response.ok) {
    throw new Error(`获取 AI 评估报告失败：${response.status}`);
  }

  return response.json();
}