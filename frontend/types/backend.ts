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
