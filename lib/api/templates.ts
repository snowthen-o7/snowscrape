/**
 * Templates API
 * Endpoints for managing scraper templates
 */

import { apiClient, APIClient } from './client';
import { Template } from '@/lib/types';

export interface CreateTemplateDTO {
  name: string;
  description?: string;
  category?: string;
  config: {
    source?: string;
    queries: any[];
    file_mapping?: any;
    proxy_config?: any;
    render_config?: any;
  };
  is_public?: boolean;
}

export type UpdateTemplateDTO = Partial<CreateTemplateDTO>;

export class TemplatesAPI {
  constructor(private client: APIClient) {}

  /**
   * List all templates (user's + public)
   */
  async list(token: string): Promise<Template[]> {
    return this.client.request<Template[]>('/templates', token);
  }

  /**
   * List public templates only
   */
  async listPublic(token: string): Promise<Template[]> {
    return this.client.request<Template[]>('/templates/public', token);
  }

  /**
   * Get a specific template by ID
   */
  async get(id: string, token: string): Promise<Template> {
    return this.client.request<Template>(`/templates/${id}`, token);
  }

  /**
   * Create a new template
   */
  async create(data: CreateTemplateDTO, token: string): Promise<Template> {
    return this.client.request<Template>('/templates', token, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * Update an existing template
   */
  async update(id: string, data: UpdateTemplateDTO, token: string): Promise<Template> {
    return this.client.request<Template>(`/templates/${id}`, token, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  /**
   * Delete a template
   */
  async delete(id: string, token: string): Promise<void> {
    return this.client.request<void>(`/templates/${id}`, token, {
      method: 'DELETE',
    });
  }

  /**
   * Use a template (create job from template)
   */
  async use(id: string, overrides: any, token: string): Promise<any> {
    return this.client.request<any>(`/templates/${id}/use`, token, {
      method: 'POST',
      body: JSON.stringify(overrides),
    });
  }
}

// Export singleton instance
export const templatesAPI = new TemplatesAPI(apiClient);
