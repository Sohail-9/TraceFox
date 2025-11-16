import { fetchJson, postJson } from "@/lib/api";
import type {
  ManualAnalysisPayload,
  OperationsSnapshot,
  ReviewSummary,
} from "@/types/backend";

export const apiClient = {
  getOperations: () => fetchJson<OperationsSnapshot>("/operations/console"),
  getReview: (prId: string) =>
    fetchJson<ReviewSummary>(
      `/reviews/pr/${prId}?include_tests=true&include_rca=true`
    ),
  analyzePullRequest: (payload: ManualAnalysisPayload) =>
    postJson<{ pr_id: string }>("/api/v1/analyze/pr", payload),
  submitFeedback: (
    findingId: string,
    payload: { feedback_type: string; timestamp: string }
  ) => postJson(`/api/v1/feedback/${findingId}`, payload),
};
