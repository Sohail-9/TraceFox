import { fetchJson, postJson } from "./api";
import type {
  GitHubBootstrapResponse,
  GitHubRepositoryListResponse,
  GitHubTrackRepositoryResponse,
  GitHubTrackedResources,
} from "@/types/backend";

export async function fetchGitHubRepositories(): Promise<GitHubRepositoryListResponse> {
  return fetchJson<GitHubRepositoryListResponse>("/integrations/github/repos");
}

export async function trackGitHubRepository(fullName: string): Promise<GitHubTrackRepositoryResponse> {
  return postJson<GitHubTrackRepositoryResponse>("/integrations/github/repos", {
    full_name: fullName,
  });
}

export async function fetchTrackedRepositories(): Promise<GitHubTrackedResources> {
  return fetchJson<GitHubTrackedResources>("/integrations/github/tracked");
}

export async function bootstrapGitHubRepository(fullName: string): Promise<GitHubBootstrapResponse> {
  return postJson<GitHubBootstrapResponse>("/integrations/github/repos/bootstrap", {
    full_name: fullName,
  });
}
