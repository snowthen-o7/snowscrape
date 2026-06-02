/**
 * API Client
 * Centralized API interface for all backend communication
 */

import { jobsAPI } from './jobs';
import { templatesAPI } from './templates';
import { webhooksAPI } from './webhooks';
import { analyticsAPI } from './analytics';

export { apiClient, APIClient, APIError } from './client';
export { jobsAPI, type CreateJobDTO, type UpdateJobDTO } from './jobs';
export { templatesAPI, type CreateTemplateDTO, type UpdateTemplateDTO } from './templates';
export { webhooksAPI, type CreateWebhookDTO, type UpdateWebhookDTO, type Webhook, type WebhookDelivery } from './webhooks';
export { analyticsAPI, type UsageMetrics, type CostMetrics, type PerformanceMetrics } from './analytics';

// Export a unified API object
export const api = {
  jobs: jobsAPI,
  templates: templatesAPI,
  webhooks: webhooksAPI,
  analytics: analyticsAPI,
};

export { billingAPI } from './billing';
export type {
  SubscriptionDTO,
  UsageDTO,
  CreateCheckoutRequest,
  CreateCheckoutResponse,
  CreatePortalResponse,
} from './billing';

export { apiKeysAPI } from './api-keys';
export type { ApiKeyListItem, CreateApiKeyResponse } from './api-keys';

export { integrationsAPI } from './integrations';
export type {
  GoogleAccount,
  GoogleAuthUrlResponse,
  GoogleCallbackResponse,
} from './integrations';

export { destinationsAPI } from './destinations';
export type {
  ExportDestination,
  CreateDestinationInput,
  DestinationMode,
  DestinationFormat,
} from './destinations';
