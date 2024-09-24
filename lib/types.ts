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
}

export interface Job {
  crawl_count: number;
  created_at: string;
  file_mapping: FileMapping;
  job_id: string;
  name: string;
  queries: Query[];
  rate_limit: number;
  scheduling: Scheduling;
  source: string;
  status: string;
  user_id: string;
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
}

export interface JobCardProps {
  job: Job;
  onClick: () => void;
  onPause: () => void;
  onDelete: () => void;
}
