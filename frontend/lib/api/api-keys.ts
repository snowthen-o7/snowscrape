/**
 * API Keys API
 * Endpoints for creating, listing, and revoking API keys.
 */

import { apiClient } from './client';

export interface ApiKeyListItem {
  api_key_id: string;
  name: string;
  key_prefix: string;
  created_at: string;
  last_used_at: string | null;
  is_active: boolean;
}

export interface CreateApiKeyResponse {
  api_key_id: string;
  name: string;
  key: string;
  key_prefix: string;
  created_at: string;
  message: string;
}

export const apiKeysAPI = {
  list: (token: string) =>
    apiClient.get<{ keys: ApiKeyListItem[] }>('/api-keys', token),

  create: (token: string, name: string) =>
    apiClient.post<CreateApiKeyResponse>('/api-keys', token, { name }),

  delete: (token: string, apiKeyId: string) =>
    apiClient.delete<{ message: string }>(`/api-keys/${apiKeyId}`, token),
};
