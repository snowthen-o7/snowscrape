/**
 * Notification Types and Interfaces
 */

export type NotificationType = 'success' | 'error' | 'warning' | 'info';

export type NotificationCategory = 'job' | 'system' | 'billing' | 'security';

export interface Notification {
  id: string;
  user_id: string;
  type: NotificationType;
  category: NotificationCategory;
  title: string;
  message: string;
  link?: string;
  read: boolean;
  created_at: string;
  metadata?: {
    job_id?: string;
    job_name?: string;
    [key: string]: any;
  };
}

export interface NotificationPreferences {
  email_notifications: boolean;
  job_completed: boolean;
  job_failed: boolean;
  weekly_digest: boolean;
  security_alerts: boolean;
  browser_notifications: boolean;
}
