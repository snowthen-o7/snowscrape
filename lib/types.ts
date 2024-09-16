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
  id: string;
  name: string;
  status: string;
  crawl_count: number;
}

export interface JobDetailsModalProps {
  jobId: string; // Assuming `jobId` is a string, change if necessary
  closeModal: () => void;
}

export interface Query {
  name: string;
  type: 'xpath' | 'regex' | 'jsonpath';
  query: string;
  join?: string;
}

export interface Scheduling {
  days: string[];
  hours: string[];
}

export interface JobCardProps {
  job: Job;
  onClick: () => void;
  onPause: () => void;
  onDelete: () => void;
}
