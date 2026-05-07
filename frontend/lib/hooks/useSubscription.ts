/**
 * Billing query/mutation hooks.
 */

'use client';

import { useQuery, useMutation } from '@tanstack/react-query';
import { useSession } from '@clerk/nextjs';
import { billingAPI, type SubscriptionDTO, type UsageDTO, type CreateCheckoutRequest } from '@/lib/api';

export function useSubscription() {
  const { session } = useSession();

  return useQuery<SubscriptionDTO>({
    queryKey: ['billing', 'subscription'],
    queryFn: async () => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return billingAPI.getSubscription(token);
    },
    enabled: !!session,
    staleTime: 60_000,
    retry: (failureCount, error: any) => {
      if (error?.status === 401 || error?.status === 403) return false;
      return failureCount < 3;
    },
  });
}

export function useUsage() {
  const { session } = useSession();

  return useQuery<UsageDTO>({
    queryKey: ['billing', 'usage'],
    queryFn: async () => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return billingAPI.getUsage(token);
    },
    enabled: !!session,
    staleTime: 30_000,
    retry: (failureCount, error: any) => {
      if (error?.status === 401 || error?.status === 403) return false;
      return failureCount < 3;
    },
  });
}

export function useStartCheckout() {
  const { session } = useSession();

  return useMutation({
    mutationFn: async (body: CreateCheckoutRequest) => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return billingAPI.createCheckoutSession(token, body);
    },
    onSuccess: (data) => {
      window.location.href = data.checkout_url;
    },
  });
}

export function useOpenPortal() {
  const { session } = useSession();

  return useMutation({
    mutationFn: async () => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return billingAPI.createPortalSession(token);
    },
    onSuccess: (data) => {
      window.location.href = data.portal_url;
    },
  });
}
