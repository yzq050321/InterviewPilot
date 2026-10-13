import type { InterviewDetail } from "../types/interview";
const API_BASE = "http://127.0.0.1:8000";

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
 * 创建模拟面试
 */
export async function createInterview(
  position: string,
  difficulty: string
): Promise<{
  interview_id: number;
  question: string;
}> {
  const response = await fetch(`${API_BASE}/api/interviews`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
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
  answer: string
): Promise<{ next_question: string }> {
  const response = await fetch(
    `${API_BASE}/api/interviews/followup`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        interview_id: interviewId,
        answer,
      }),
    }
  );

  if (!response.ok) {
    let message = `提交回答失败：${response.status}`;

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

  return response.json();
}


/**
 * 结束指定面试
 */
export async function completeInterview(
  interviewId: number
): Promise<void> {
  const response = await fetch(
    `${API_BASE}/api/interviews/${interviewId}/complete`,
    {
      method: "PATCH",
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
  const response = await fetch(
    `${API_BASE}/api/interviews/${interviewId}/evaluation`,
    {
      method: "POST",
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
  const response = await fetch(
    `${API_BASE}/api/interviews/${interviewId}`
  );

  if (!response.ok) {
    throw new Error(
      `获取面试详情失败：${response.status}`
    );
  }

  const data: InterviewDetail = await response.json();

  return data;
}