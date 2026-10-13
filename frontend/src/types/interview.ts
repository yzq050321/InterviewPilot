
export type Message = {
  role: "assistant" | "user";
  content: string;
};

export type Evaluation = {
  id: number;
  interview_id: number;
  technical_score: number | null;
  completeness_score: number | null;
  clarity_score: number | null;
  overall_score: number | null;
  summary: string;
  strengths: string[];
  weaknesses: string[];
  suggestions: string[];
};

export interface InterviewHistory {
  interview_id: number;
  position: string;
  difficulty: string;
  status: string;
  created_at: string;
}

export type InterviewMessage = {
  id: number;
  role: string;
  content: string;
  created_at: string;
};

export type InterviewDetail = {
  interview_id: number;
  position: string;
  difficulty: string;
  status: string;
  created_at: string;
  messages: InterviewMessage[];
};