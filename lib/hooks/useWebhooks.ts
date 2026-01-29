/**
 * Webhooks Query Hooks
 * React Query hooks for webhook-related data fetching
 */

'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSession } from '@clerk/nextjs';
import { webhooksAPI, type CreateWebhookDTO, type UpdateWebhookDTO } from '@/lib/api';
import { toast } from '@/lib/toast';

/**
 * Fetch all webhooks
 */
export function useWebhooks() {
  const { session } = useSession();

  return useQuery({
    queryKey: ['webhooks'],
    queryFn: async () => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return webhooksAPI.list(token);
    },
    enabled: !!session,
  });
}

/**
 * Fetch a single webhook by ID
 */
export function useWebhook(id: string | null) {
  const { session } = useSession();

  return useQuery({
    queryKey: ['webhooks', id],
    queryFn: async () => {
      const token = await session?.getToken();
      if (!token || !id) throw new Error('Not authenticated or missing ID');
      return webhooksAPI.get(id, token);
    },
    enabled: !!session && !!id,
  });
}

/**
 * Create a new webhook
 */
export function useCreateWebhook() {
  const queryClient = useQueryClient();
  const { session } = useSession();

  return useMutation({
    mutationFn: async (data: CreateWebhookDTO) => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return webhooksAPI.create(data, token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] });
      toast.success('Webhook created successfully');
    },
    onError: (error: any) => {
      toast.error('Failed to create webhook', {
        description: error?.message || 'An unknown error occurred',
      });
    },
  });
}

/**
 * Update an existing webhook
 */
export function useUpdateWebhook() {
  const queryClient = useQueryClient();
  const { session } = useSession();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: UpdateWebhookDTO }) => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return webhooksAPI.update(id, data, token);
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] });
      queryClient.invalidateQueries({ queryKey: ['webhooks', variables.id] });
      toast.success('Webhook updated successfully');
    },
    onError: (error: any) => {
      toast.error('Failed to update webhook', {
        description: error?.message || 'An unknown error occurred',
      });
    },
  });
}

/**
 * Delete a webhook
 */
export function useDeleteWebhook() {
  const queryClient = useQueryClient();
  const { session } = useSession();

  return useMutation({
    mutationFn: async (id: string) => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return webhooksAPI.delete(id, token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] });
      toast.success('Webhook deleted successfully');
    },
    onError: (error: any) => {
      toast.error('Failed to delete webhook', {
        description: error?.message || 'An unknown error occurred',
      });
    },
  });
}

/**
 * Test a webhook
 */
export function useTestWebhook() {
  const { session } = useSession();

  return useMutation({
    mutationFn: async (id: string) => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return webhooksAPI.test(id, token);
    },
    onSuccess: () => {
      toast.success('Test webhook sent successfully');
    },
    onError: (error: any) => {
      toast.error('Failed to test webhook', {
        description: error?.message || 'An unknown error occurred',
      });
    },
  });
}

/**
 * Fetch webhook delivery history
 */
export function useWebhookDeliveries(id: string | null, limit = 50) {
  const { session } = useSession();

  return useQuery({
    queryKey: ['webhooks', id, 'deliveries', limit],
    queryFn: async () => {
      const token = await session?.getToken();
      if (!token || !id) throw new Error('Not authenticated or missing ID');
      return webhooksAPI.deliveries(id, token, limit);
    },
    enabled: !!session && !!id,
  });
}
