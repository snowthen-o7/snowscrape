/**
 * Webhooks API
 * Endpoints for managing webhook configurations
 */

import { apiClient, APIClient } from './client';

export interface Webhook {
  id: string;
  name: string;
  url: string;
  events: string[];
  headers?: Record<string, string>;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateWebhookDTO {
  name: string;
  url: string;
  events: string[];
  headers?: Record<string, string>;
  secret?: string;
}

export type UpdateWebhookDTO = Partial<CreateWebhookDTO>;

export interface WebhookDelivery {
  id: string;
  webhook_id: string;
  event: string;
  payload: any;
  status: 'pending' | 'success' | 'failed';
  response_code?: number;
  response_body?: string;
  attempts: number;
  created_at: string;
  delivered_at?: string;
}

export class WebhooksAPI {
  constructor(private client: APIClient) {}

  /**
   * List all webhooks
   */
  async list(token: string): Promise<Webhook[]> {
    return this.client.request<Webhook[]>('/webhooks', token);
  }

  /**
   * Get a specific webhook by ID
   */
  async get(id: string, token: string): Promise<Webhook> {
    return this.client.request<Webhook>(`/webhooks/${id}`, token);
  }

  /**
   * Create a new webhook
   */
  async create(data: CreateWebhookDTO, token: string): Promise<Webhook> {
    return this.client.request<Webhook>('/webhooks', token, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * Update an existing webhook
   */
  async update(id: string, data: UpdateWebhookDTO, token: string): Promise<Webhook> {
    return this.client.request<Webhook>(`/webhooks/${id}`, token, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  /**
   * Delete a webhook
   */
  async delete(id: string, token: string): Promise<void> {
    return this.client.request<void>(`/webhooks/${id}`, token, {
      method: 'DELETE',
    });
  }

  /**
   * Test a webhook (send test payload)
   */
  async test(id: string, token: string): Promise<WebhookDelivery> {
    return this.client.request<WebhookDelivery>(`/webhooks/${id}/test`, token, {
      method: 'POST',
    });
  }

  /**
   * Get webhook delivery history
   */
  async deliveries(id: string, token: string, limit = 50): Promise<WebhookDelivery[]> {
    return this.client.request<WebhookDelivery[]>(
      `/webhooks/${id}/deliveries?limit=${limit}`,
      token
    );
  }

  /**
   * Enable a webhook
   */
  async enable(id: string, token: string): Promise<Webhook> {
    return this.client.request<Webhook>(`/webhooks/${id}/enable`, token, {
      method: 'POST',
    });
  }

  /**
   * Disable a webhook
   */
  async disable(id: string, token: string): Promise<Webhook> {
    return this.client.request<Webhook>(`/webhooks/${id}/disable`, token, {
      method: 'POST',
    });
  }
}

// Export singleton instance
export const webhooksAPI = new WebhooksAPI(apiClient);
