"use client";

import useSWR from "swr";
import type { KeyedMutator } from "swr";

import { apiClient } from "@/lib/api-client";
import type { OperationsSnapshot, ReviewSummary } from "@/types/backend";

export function useOperations() {
  return useSWR<OperationsSnapshot>(
    "/operations/console",
    () => apiClient.getOperations(),
    { refreshInterval: 15_000 }
  );
}

export function useReview(prId: string | null) {
  const key = prId ? `/reviews/pr/${prId}?include_tests=true&include_rca=true` : null;
  return useSWR<ReviewSummary | null>(
    key,
    async () => {
      try {
        return await apiClient.getReview(prId as string);
      } catch (error) {
        if (error instanceof Error && /404/.test(error.message)) {
          return null;
        }
        throw error;
      }
    },
    { refreshInterval: 10_000 }
  );
}

export async function submitFindingFeedback(
  findingId: string,
  reaction: string,
  revalidate?: KeyedMutator<ReviewSummary>
) {
  await apiClient.submitFeedback(findingId, {
    feedback_type: reaction,
    timestamp: new Date().toISOString(),
  });
  if (revalidate) {
    await revalidate();
  }
}
