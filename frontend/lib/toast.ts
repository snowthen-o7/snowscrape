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
      duration: 5000,
    });
  },

  error: (title: string, options?: ToastOptions) => {
    baseToast({
      title,
      description: options?.description,
      variant: 'destructive',
      duration: 30000,
    });
  },

  info: (title: string, options?: ToastOptions) => {
    baseToast({
      title,
      description: options?.description,
      duration: 5000,
    });
  },

  warning: (title: string, options?: ToastOptions) => {
    baseToast({
      title,
      description: options?.description,
      duration: 8000,
    });
  },
};
