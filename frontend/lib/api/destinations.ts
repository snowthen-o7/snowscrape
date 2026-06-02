/**
 * Export Destinations API
 * Endpoints for creating, listing, deleting Google Docs export destinations.
 */

import { apiClient } from './client';

export type DestinationMode = 'new_doc_per_run' | 'one_doc_per_row';
export type DestinationFormat = 'structured_log' | 'compact_list' | 'narrative';

export interface ExportDestination {
  destination_id: string;
  user_id: string;
  name: string;
  type: 'google_docs';
  drive_folder_id: string;
  naming_template: string;
  mode: DestinationMode;
  format_template: DestinationFormat;
  google_user_id: string;
  created_at: string;
}

export interface CreateDestinationInput {
  name: string;
  type: 'google_docs';
  drive_folder_id: string;
  naming_template: string;
  mode: DestinationMode;
  format_template: DestinationFormat;
}

export const destinationsAPI = {
  list: (token: string) =>
    apiClient.get<{ destinations: ExportDestination[] }>('/export-destinations', token),

  create: (token: string, input: CreateDestinationInput) =>
    apiClient.post<ExportDestination>('/export-destinations', token, input),

  delete: (token: string, destinationId: string) =>
    apiClient.delete<Record<string, never>>(`/export-destinations/${destinationId}`, token),
};
