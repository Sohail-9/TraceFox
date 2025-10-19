export type NotificationMessage = {
  channel: string;
  body: string;
  severity: string;
};

export type AnalyticsReport = {
  commit_id: string;
  tests_generated: number;
  tests_failed: number;
  notifications_sent: number;
  anomalies_detected: number;
  insights: string[];
};

export type PipelineState = {
  latest_report: AnalyticsReport | null;
  last_commit: Record<string, unknown> | null;
  last_deployment: Record<string, unknown> | null;
};

