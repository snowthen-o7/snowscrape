/**
 * Google account query/mutation hooks.
 */

'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSession } from '@clerk/nextjs';
import { integrationsAPI, type GoogleAccount } from '@/lib/api/integrations';
import { toast } from '@/lib/toast';

const KEY = ['google-accounts'] as const;

export function useGoogleAccounts() {
  const { session } = useSession();

  return useQuery<GoogleAccount[]>({
    queryKey: KEY,
    queryFn: async () => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      const data = await integrationsAPI.listGoogleAccounts(token);
      return data.accounts ?? [];
    },
    enabled: !!session,
    staleTime: 30_000,
  });
}

export function useStartGoogleOAuth() {
  const { session } = useSession();

  return useMutation({
    mutationFn: async () => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return integrationsAPI.getGoogleAuthUrl(token);
    },
    onError: (error: any) => {
      toast.error(error?.message ?? 'Failed to start Google connection');
    },
  });
}

export function useCompleteGoogleOAuth() {
  const { session } = useSession();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ code, state }: { code: string; state: string }) => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return integrationsAPI.completeGoogleOAuth(token, code, state);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY });
    },
    onError: (error: any) => {
      toast.error(error?.message ?? 'Failed to complete Google connection');
    },
  });
}

export function useRevokeGoogleAccount() {
  const { session } = useSession();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return integrationsAPI.revokeGoogleAccount(token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY });
      toast.success('Google account disconnected');
    },
    onError: (error: any) => {
      toast.error(error?.message ?? 'Failed to disconnect Google account');
    },
  });
}
