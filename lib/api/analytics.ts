/**
 * Analytics API
 * Endpoints for usage analytics and metrics
 */

import { apiClient, APIClient } from './client';

export interface UsageMetrics {
  period: string;
  api_calls: number;
  data_extracted: number;
  jobs_executed: number;
  success_rate: number;
}

export interface CostMetrics {
  period: string;
  total_cost: number;
  breakdown: {
    lambda: number;
    storage: number;
    data_transfer: number;
    other: number;
  };
}

export interface PerformanceMetrics {
  avg_runtime: number;
  p50_runtime: number;
  p95_runtime: number;
  p99_runtime: number;
  total_jobs: number;
  successful_jobs: number;
  failed_jobs: number;
}

export class AnalyticsAPI {
  constructor(private client: APIClient) {}

  /**
   * Get usage metrics for a time period
   */
  async usage(
    period: '7d' | '30d' | '90d',
    token: string
  ): Promise<UsageMetrics> {
    return this.client.request<UsageMetrics>(
      `/analytics/usage?period=${period}`,
      token
    );
  }

  /**
   * Get cost metrics for a time period
   */
  async cost(
    period: '7d' | '30d' | '90d',
    token: string
  ): Promise<CostMetrics> {
    return this.client.request<CostMetrics>(
      `/analytics/cost?period=${period}`,
      token
    );
  }

  /**
   * Get performance metrics
   */
  async performance(
    period: '7d' | '30d' | '90d',
    token: string
  ): Promise<PerformanceMetrics> {
    return this.client.request<PerformanceMetrics>(
      `/analytics/performance?period=${period}`,
      token
    );
  }

  /**
   * Get job-specific analytics
   */
  async jobAnalytics(
    jobId: string,
    period: '7d' | '30d' | '90d',
    token: string
  ): Promise<any> {
    return this.client.request<any>(
      `/analytics/jobs/${jobId}?period=${period}`,
      token
    );
  }

  /**
   * Get trending data (API calls, data volume over time)
   */
  async trends(
    metric: 'api_calls' | 'data_volume' | 'jobs',
    period: '7d' | '30d' | '90d',
    token: string
  ): Promise<Array<{ date: string; value: number }>> {
    return this.client.request<Array<{ date: string; value: number }>>(
      `/analytics/trends/${metric}?period=${period}`,
      token
    );
  }
}

// Export singleton instance
export const analyticsAPI = new AnalyticsAPI(apiClient);
