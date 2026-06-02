/**
 * Google Integrations API
 * Endpoints for Google account connection (OAuth) and management.
 */

import { apiClient } from './client';

export interface GoogleAccount {
  google_user_id: string;
  email: string;
  name: string;
  connected_at: string | null;
}

export interface GoogleAuthUrlResponse {
  auth_url: string;
  state: string;
}

export interface GoogleCallbackResponse {
  email: string;
  name: string;
}

export const integrationsAPI = {
  getGoogleAuthUrl: (token: string) =>
    apiClient.get<GoogleAuthUrlResponse>('/integrations/google/auth-url', token),

  completeGoogleOAuth: (token: string, code: string, state: string) =>
    apiClient.post<GoogleCallbackResponse>('/integrations/google/callback', token, { code, state }),

  listGoogleAccounts: (token: string) =>
    apiClient.get<{ accounts: GoogleAccount[] }>('/integrations/google', token),

  revokeGoogleAccount: (token: string) =>
    apiClient.delete<Record<string, never>>('/integrations/google', token),
};
