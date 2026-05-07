/**
 * Billing API
 * Endpoints for Stripe checkout, customer portal, subscription, and usage.
 */

import { apiClient } from './client';

export interface SubscriptionDTO {
  plan: 'pro' | 'business' | 'enterprise' | 'locked';
  status: 'trialing' | 'active' | 'past_due' | 'canceled' | 'incomplete' | 'incomplete_expired' | 'unpaid' | 'no_subscription';
  current_period_end: string;
  trial_end: string;
  cancel_at_period_end: boolean;
  monthly_page_limit: number;
  monthly_pages_used: number;
  concurrent_job_limit: number;
  features: {
    js_rendering: boolean;
    proxy_rotation: boolean;
    webhooks: boolean;
    anti_bot: boolean;
  };
  has_billing_account: boolean;
}

export interface UsageDTO {
  pages_used: number;
  pages_limit: number;
  pages_percentage: number;
  concurrent_job_limit: number;
  billing_period_end: string;
  plan: string;
}

export interface CreateCheckoutRequest {
  plan?: 'pro' | 'business';
  interval?: 'month' | 'year';
  is_trial?: boolean;
}

export interface CreateCheckoutResponse {
  checkout_url: string;
}

export interface CreatePortalResponse {
  portal_url: string;
}

export const billingAPI = {
  getSubscription: (token: string) =>
    apiClient.get<SubscriptionDTO>('/billing/subscription', token),

  getUsage: (token: string) =>
    apiClient.get<UsageDTO>('/billing/usage', token),

  createCheckoutSession: (token: string, body: CreateCheckoutRequest) =>
    apiClient.post<CreateCheckoutResponse>('/billing/checkout', token, body),

  createPortalSession: (token: string) =>
    apiClient.post<CreatePortalResponse>('/billing/portal', token),
};
