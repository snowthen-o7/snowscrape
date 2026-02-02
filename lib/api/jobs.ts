/**
 * Jobs API
 * Endpoints for managing scraping jobs
 */

import { apiClient, APIClient } from './client';
import { Job } from '@/lib/types';

export interface CreateJobDTO {
  name: string;
  source: string;
  rate_limit?: number;
  queries: Array<{
    name: string;
    type: string;
    query: string;
    join?: boolean;
  }>;
  scheduling?: {
    days: number[];
    hours: number[];
    minutes: number[];
  };
  file_mapping?: {
    delimiter: string;
    enclosure: string;
    escape: string;
    url_column: string;
  };
  proxy_config?: {
    enabled: boolean;
    geo_targeting?: string;
    rotation_strategy?: string;
    max_retries?: number;
    fallback_to_direct?: boolean;
  };
  render_config?: {
    enabled: boolean;
    wait_strategy?: string;
    wait_timeout_ms?: number;
    wait_for_selector?: string | null;
    capture_screenshot?: boolean;
    screenshot_full_page?: boolean;
    block_resources?: string[];
    fallback_to_standard?: boolean;
  };
}

export type UpdateJobDTO = Partial<CreateJobDTO>;

export interface DownloadResponse {
  url: string;
  filename: string;
}

export class JobsAPI {
  constructor(private client: APIClient) {}

  /**
   * List all jobs for the authenticated user
   */
  async list(token: string): Promise<Job[]> {
    // Backend endpoint is /jobs/status (returns { jobs: Job[], count: number })
    const response = await this.client.request<{ jobs: Job[]; count: number }>(
      '/jobs/status',
      token
    );
    return response.jobs || [];
  }

  /**
   * Get a specific job by ID
   */
  async get(id: string, token: string): Promise<Job> {
    return this.client.request<Job>(`/jobs/${id}`, token);
  }

  /**
   * Create a new job
   */
  async create(data: CreateJobDTO, token: string): Promise<Job> {
    return this.client.request<Job>('/jobs', token, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * Update an existing job
   */
  async update(id: string, data: UpdateJobDTO, token: string): Promise<Job> {
    return this.client.request<Job>(`/jobs/${id}`, token, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  /**
   * Delete a job
   */
  async delete(id: string, token: string): Promise<void> {
    return this.client.request<void>(`/jobs/${id}`, token, {
      method: 'DELETE',
    });
  }

  /**
   * Pause a job
   */
  async pause(id: string, token: string): Promise<Job> {
    return this.client.request<Job>(`/jobs/${id}/pause`, token, {
      method: 'POST',
    });
  }

  /**
   * Resume a paused job
   */
  async resume(id: string, token: string): Promise<Job> {
    return this.client.request<Job>(`/jobs/${id}/resume`, token, {
      method: 'POST',
    });
  }

  /**
   * Trigger a job to run immediately
   */
  async run(id: string, token: string): Promise<Job> {
    return this.client.request<Job>(`/jobs/${id}/run`, token, {
      method: 'POST',
    });
  }

  /**
   * Download job results in specified format
   */
  async download(
    id: string,
    format: 'csv' | 'json' | 'xlsx' | 'parquet' | 'sql',
    token: string
  ): Promise<DownloadResponse> {
    return this.client.request<DownloadResponse>(
      `/jobs/${id}/download?format=${format}`,
      token
    );
  }

  /**
   * Get job execution history
   */
  async history(id: string, token: string): Promise<any[]> {
    return this.client.request<any[]>(`/jobs/${id}/history`, token);
  }

  /**
   * Get job results/preview
   */
  async results(id: string, token: string, limit = 100): Promise<any[]> {
    return this.client.request<any[]>(
      `/jobs/${id}/results?limit=${limit}`,
      token
    );
  }

  /**
   * Preview a URL and extract DOM structure for visual builder
   */
  async preview(url: string, token: string): Promise<PagePreviewResponse> {
    return this.client.request<PagePreviewResponse>('/scraper/preview', token, {
      method: 'POST',
      body: JSON.stringify({ url }),
    });
  }

  /**
   * Test extraction with given selectors on a URL
   */
  async testExtraction(
    url: string,
    selectors: Array<{ name: string; type: string; selector: string }>,
    token: string
  ): Promise<any[]> {
    return this.client.request<any[]>('/scraper/test', token, {
      method: 'POST',
      body: JSON.stringify({ url, selectors }),
    });
  }
}

export interface PagePreviewResponse {
  url: string;
  title: string;
  elements: Array<{
    id: string;
    type: string;
    text: string;
    xpath: string;
    css: string;
    path: string;
  }>;
  tier_info?: {
    tier_used: number;
    tier_name: string;
    cost_per_page: number;
    escalation_log: string[];
  };
}

// Export singleton instance
export const jobsAPI = new JobsAPI(apiClient);
