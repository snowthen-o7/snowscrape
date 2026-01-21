// types.ts

export interface FileMapping {
  delimiter: string;
  enclosure: string;
  escape: string;
  url_column: string;
}

export interface FormData {
  name: string;
  rate_limit: number;
  source: string;
  file_mapping: FileMapping;
  scheduling: Scheduling;
  queries: Query[];
  proxy_config?: ProxyConfig;
  render_config?: RenderConfig;
  export_config?: ExportConfig;
  notification_config?: NotificationConfig;
}

export interface Job {
  created_at: string;
  file_mapping: FileMapping;
  job_id: string;
  link_count: number;
  name: string;
  queries: Query[];
  rate_limit: number;
  scheduling: Scheduling;
  source: string;
  status: string;
  user_id: string;
  results_s3_key?: string;
  last_run?: string;
  proxy_config?: ProxyConfig;
  render_config?: RenderConfig;
  export_config?: ExportConfig;
  notification_config?: NotificationConfig;
}

export interface JobDetailsModalProps {
  closeModal: () => void;
  jobId: string; // Assuming `jobId` is a string
  token: string; // Assuming `token` is a string
}

export interface Query {
  join: boolean;
  name: string;
  query: string;
  type: 'xpath' | 'regex' | 'jsonpath';
}

export interface Scheduling {
  days: string[];
  hours: number[];
  minutes: number[];
}

export interface JobCardProps {
  job: Job;
  onClick: () => void;
  onPause?: () => void;
  onResume?: () => void;
  onDelete: () => void;
  onDownload?: (format: string) => void;
  onPreview?: () => void;
}

export interface Template {
  template_id: string;
  user_id: string;
  name: string;
  description?: string;
  config: {
    file_mapping: FileMapping;
    queries: Query[];
    scheduling: Scheduling;
  };
  created_at: string;
  last_used?: string | null;
}

export interface Webhook {
  webhook_id: string;
  user_id: string;
  job_id?: string | null;
  url: string;
  events: string[];
  secret?: string;
  active: boolean;
  created_at: string;
  total_deliveries: number;
  failed_deliveries: number;
}

export interface ProxyConfig {
  enabled: boolean;
  geo_targeting?: 'us' | 'eu' | 'as' | 'any';
  rotation_strategy?: 'random' | 'round-robin';
  max_retries?: number;
  fallback_to_direct?: boolean;
}

export interface RenderConfig {
  enabled: boolean;
  wait_strategy?: 'load' | 'domcontentloaded' | 'networkidle';
  wait_timeout_ms?: number;
  wait_for_selector?: string | null;
  capture_screenshot?: boolean;
  screenshot_full_page?: boolean;
  block_resources?: string[];
  fallback_to_standard?: boolean;
}

export interface ExportConfig {
  enabled: boolean;
  formats?: ('json' | 'csv' | 'xlsx')[];
  destination?: 's3' | 'local' | 'webhook';
  s3_bucket?: string | null;
  webhook_url?: string | null;
  include_screenshots?: boolean;
  compress?: boolean;
}

export interface NotificationConfig {
  enabled: boolean;
  email_on_success?: boolean;
  email_on_failure?: boolean;
  email_addresses?: string[];
  webhook_on_success?: boolean;
  webhook_on_failure?: boolean;
  webhook_url?: string | null;
}
