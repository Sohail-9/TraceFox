export type Severity = "critical" | "major" | "minor" | string;

export type FindingCategory =
  | "security"
  | "performance"
  | "bug"
  | "style"
  | "test_gap"
  | string;

export type ReviewFinding = {
  id: string;
  file_path: string;
  line_number: number;
  severity: Severity;
  category: FindingCategory;
  description: string;
  suggested_fix?: string | null;
  code_diff?: string | null;
  confidence_score: number;
};

export type TestType = "unit" | "integration" | "e2e" | "security" | "performance" | string;

export type TestCase = {
  id: string;
  pull_request_id: string;
  finding_id?: string | null;
  test_name: string;
  test_type: TestType;
  test_code: string;
  priority: number;
  root_cause_mapping?: string | null;
  language: string;
  framework: string;
};

export type ReviewSummary = {
  review_id: string;
  pr_id: string;
  summary: string;
  findings: ReviewFinding[];
  mermaid_diagram?: string | null;
  total_findings: number;
  critical_count: number;
  major_count: number;
  minor_count: number;
  created_at: string;
  tests?: TestCase[];
  rca?: RCAFinding[];
};

export type RCAFinding = {
  id: string;
  test_execution_id: string;
  category: string;
  root_cause_summary: string;
  root_cause_details: Record<string, unknown>;
  correlated_commits: Array<Record<string, unknown>>;
  suggested_fixes: Array<Record<string, unknown>>;
  confidence_score: number;
  prevention_recommendations: string[];
};

export type GenerateTestsResponse = {
  job_id: string;
  test_cases: TestCase[];
  total_generated: number;
};

export type TestExecutionSummary = {
  execution_id: string;
  status: string;
  total_tests: number;
  passed: number;
  failed: number;
  flaky: number;
  skipped: number;
  execution_time_ms: number;
  results_url?: string;
};

export type TestExecutionResult = {
  execution_id: string;
  test_case_id: string;
  test_name: string;
  status: string;
  execution_time_ms: number;
  error_message?: string | null;
  stack_trace?: string | null;
};

export type TestResultsResponse = TestExecutionSummary & {
  results: TestExecutionResult[];
};

export type RCAResponse = RCAFinding;

export type WebhookResponse = {
  status: string;
  job_id?: string;
  message?: string;
  review_id?: string;
};

export interface GitHubRepositorySummary {
  id: number;
  full_name: string;
  description?: string | null;
  clone_url: string;
  default_branch: string;
  html_url: string;
  private: boolean;
}

export interface GitHubTrackedRepository {
  repo_id: number;
  full_name: string;
  description?: string | null;
  clone_url: string;
  default_branch: string;
  html_url: string;
  private: boolean;
  clone_path?: string | null;
  sync_status: string;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface GitHubRepositoryListResponse {
  repositories: GitHubRepositorySummary[];
}

export interface GitHubTrackRepositoryResponse {
  repository: GitHubTrackedRepository;
  clone_job: Record<string, unknown>;
}

export interface GitHubBootstrapResponse {
  status: string;
  task: string;
}

export interface GitHubTrackedResources {
  repositories: GitHubTrackedRepository[];
  clone_jobs: GitHubCloneJob[];
}

export interface GitHubCloneJob {
  job_id: string;
  full_name: string;
  status: string;
  message?: string | null;
  clone_path?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export type OperationsSnapshot = {
  active_pr_id: string | null;
  total_prs: number;
  pr_registry: Array<{
    pr_id: string;
    provider?: string;
    repository_id?: string;
    repository_name?: string;
    repository_url?: string;
    pull_request_number?: number;
    pull_request_title?: string;
    pull_request_author?: string;
    action?: string;
    event_type?: string;
    received_at?: string;
    payload?: Record<string, unknown>;
  }>;
  summary: {
    total_reviews: number;
    total_findings: number;
    critical: number;
    major: number;
    minor: number;
    latest?: {
      pr_id: string;
      summary: string;
      total_findings: number;
      critical_count: number;
      major_count: number;
      minor_count: number;
      created_at: string;
    } | null;
    per_pr?: Record<
      string,
      {
        review_id: string;
        summary: string;
        total_findings: number;
        critical: number;
        major: number;
        minor: number;
        created_at: string;
      }
    >;
  };
  tests: {
    total_cases: number;
    per_pr: Record<string, number>;
  };
  executions: {
    total_runs: number;
    latest?: {
      execution_id?: string;
      pr_id?: string | null;
      status: string;
      passed: number;
      failed: number;
      flaky: number;
      skipped: number;
      total_tests: number;
      execution_time_ms: number;
      completed_at?: string | null;
    } | null;
    per_pr_counts?: Record<string, number>;
    latest_per_pr?: Record<
      string,
      {
        execution_id?: string;
        status: string;
        passed: number;
        failed: number;
        flaky: number;
        skipped: number;
        total_tests: number;
        execution_time_ms: number;
        completed_at?: string | null;
      }
    >;
  };
  rca: {
    total: number;
    latest?: {
      execution_id: string;
      category: string;
      summary: string;
    } | null;
    per_pr_counts?: Record<string, number>;
    latest_per_pr?: Record<
      string,
      {
        execution_id: string;
        category: string;
        summary: string;
      }
    >;
  };
  quality: {
    repositories: Record<string, {
      pass: number;
      fail: number;
      flaky: number;
    }>;
  };
  activity: Array<{
    id: string;
    title: string;
    detail: string;
    tone: string;
    timestamp?: string;
  }>;
  checklist: {
    webhook: boolean;
    review: boolean;
    tests: boolean;
    execution: boolean;
  };
  latest_payload?: Record<string, unknown> | null;
};
