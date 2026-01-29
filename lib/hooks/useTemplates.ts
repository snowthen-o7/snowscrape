/**
 * Templates Query Hooks
 * React Query hooks for template-related data fetching
 */

'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSession } from '@clerk/nextjs';
import { templatesAPI, type CreateTemplateDTO, type UpdateTemplateDTO } from '@/lib/api';
import { toast } from '@/lib/toast';

/**
 * Fetch all templates
 */
export function useTemplates() {
  const { session } = useSession();

  return useQuery({
    queryKey: ['templates'],
    queryFn: async () => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return templatesAPI.list(token);
    },
    enabled: !!session,
  });
}

/**
 * Fetch public templates only
 */
export function usePublicTemplates() {
  const { session } = useSession();

  return useQuery({
    queryKey: ['templates', 'public'],
    queryFn: async () => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return templatesAPI.listPublic(token);
    },
    enabled: !!session,
  });
}

/**
 * Fetch a single template by ID
 */
export function useTemplate(id: string | null) {
  const { session } = useSession();

  return useQuery({
    queryKey: ['templates', id],
    queryFn: async () => {
      const token = await session?.getToken();
      if (!token || !id) throw new Error('Not authenticated or missing ID');
      return templatesAPI.get(id, token);
    },
    enabled: !!session && !!id,
  });
}

/**
 * Create a new template
 */
export function useCreateTemplate() {
  const queryClient = useQueryClient();
  const { session } = useSession();

  return useMutation({
    mutationFn: async (data: CreateTemplateDTO) => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return templatesAPI.create(data, token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] });
      toast.success('Template created successfully');
    },
    onError: (error: any) => {
      toast.error('Failed to create template', {
        description: error?.message || 'An unknown error occurred',
      });
    },
  });
}

/**
 * Update an existing template
 */
export function useUpdateTemplate() {
  const queryClient = useQueryClient();
  const { session } = useSession();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: UpdateTemplateDTO }) => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return templatesAPI.update(id, data, token);
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['templates'] });
      queryClient.invalidateQueries({ queryKey: ['templates', variables.id] });
      toast.success('Template updated successfully');
    },
    onError: (error: any) => {
      toast.error('Failed to update template', {
        description: error?.message || 'An unknown error occurred',
      });
    },
  });
}

/**
 * Delete a template
 */
export function useDeleteTemplate() {
  const queryClient = useQueryClient();
  const { session } = useSession();

  return useMutation({
    mutationFn: async (id: string) => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return templatesAPI.delete(id, token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] });
      toast.success('Template deleted successfully');
    },
    onError: (error: any) => {
      toast.error('Failed to delete template', {
        description: error?.message || 'An unknown error occurred',
      });
    },
  });
}
