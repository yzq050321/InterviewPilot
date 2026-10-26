const API_BASE = "";

async function readError(response: Response, fallback: string): Promise<never> {
  try {
    const payload: unknown = await response.json();
    if (payload && typeof payload === "object" && "detail" in payload) {
      const detail = (payload as { detail: unknown }).detail;
      if (typeof detail === "string") throw new Error(detail);
    }
  } catch (error) {
    if (error instanceof Error && error.message !== "") {
      if (!(error instanceof SyntaxError)) throw error;
    }
  }
  throw new Error(`${fallback}（HTTP ${response.status}）`);
}

export async function registerHr(
  email: string,
  password: string,
  inviteCode: string
): Promise<{ access_token: string; role: "hr"; email: string }> {
  const response = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, invite_code: inviteCode }),
  });
  if (!response.ok) return readError(response, "受邀注册失败");
  return response.json();
}

export async function requestTrial(input: {
  name: string;
  email: string;
  company: string;
  note: string;
}): Promise<{ message: string; request_id: number }> {
  const response = await fetch(`${API_BASE}/api/auth/trial-request`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) return readError(response, "试用申请提交失败");
  return response.json();
}
