/** Batch 8: Front-end projections of existing authorized job / interview data.
 * No new HR permissions, database fields, or candidate information are introduced.
 */
import type { JobPosting } from "./jobApi";
import type { getAdminInterviews } from "./api";

export type WorkspaceInterview = Awaited<ReturnType<typeof getAdminInterviews>>[number];

export function interviewsForJob(items: WorkspaceInterview[], jobId: number): WorkspaceInterview[] {
  // Use the server's job_id FK, NOT matching human-readable position strings.
  return items.filter((item) => item.job_id === jobId);
}

export function summarizeJob(items: WorkspaceInterview[]) {
  return {
    total: items.length,
    completed: items.filter((item) => item.status === "completed").length,
    ready: items.filter((item) => item.evaluation_status === "ready").length,
    pendingReview: items.filter((item) => item.status === "completed" && item.review_status === "pending").length,
    failed: items.filter((item) => item.evaluation_status === "failed").length,
  };
}

export function summarizeWorkspace(jobs: JobPosting[], interviews: WorkspaceInterview[]) {
  const jobIds = new Set(jobs.map((item) => item.job_id));
  const linked = interviews.filter((item) => item.job_id !== null && jobIds.has(item.job_id));
  return { activeJobs: jobs.filter((job) => job.is_active).length, ...summarizeJob(linked) };
}

export function showDate(value: string | null | undefined): string {
  if (!value) return "—";
  return value.replace("T", " ").slice(0, 16);
}
