/**
 * Toast notification utilities
 * Wraps shadcn/ui toast for consistent usage across the app
 */

import { toast as baseToast } from '@snowforge/ui';

type ToastOptions = {
  description?: string;
};

export const toast = {
  success: (title: string, options?: ToastOptions) => {
    baseToast({
      title,
      description: options?.description,
      variant: 'default',
    });
  },

  error: (title: string, options?: ToastOptions) => {
    baseToast({
      title,
      description: options?.description,
      variant: 'destructive',
    });
  },

  info: (title: string, options?: ToastOptions) => {
    baseToast({
      title,
      description: options?.description,
    });
  },

  warning: (title: string, options?: ToastOptions) => {
    baseToast({
      title,
      description: options?.description,
    });
  },
};
