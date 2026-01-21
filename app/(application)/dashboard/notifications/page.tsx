/**
 * Notifications Page
 * View and manage all notifications
 */

'use client';

import { useState, useEffect } from 'react';
import { useSession } from '@clerk/nextjs';
import { AppLayout } from '@/components/layout/AppLayout';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  CheckCircle2,
  XCircle,
  AlertCircle,
  Info,
  Check,
  Trash2,
  ExternalLink,
  Bell,
  Filter,
} from 'lucide-react';
import { Notification } from '@/lib/types/notifications';
import { formatDistanceToNow } from 'date-fns';
import Link from 'next/link';
import { toast } from '@/lib/toast';
import { EmptyState } from '@/components/EmptyState';

export default function NotificationsPage() {
  const { session } = useSession();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [filter, setFilter] = useState<'all' | 'unread' | 'read'>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

  // Fetch notifications
  useEffect(() => {
    const fetchNotifications = async () => {
      if (!session) return;

      try {
        // Mock notifications for demo
        const mockNotifications: Notification[] = [
          {
            id: '1',
            user_id: 'user-1',
            type: 'success',
            category: 'job',
            title: 'Job Completed Successfully',
            message: 'Amazon Product Scraper has finished extracting 1,250 records',
            link: '/dashboard/job-1',
            read: false,
            created_at: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
            metadata: { job_id: 'job-1', job_name: 'Amazon Product Scraper' },
          },
          {
            id: '2',
            user_id: 'user-1',
            type: 'error',
            category: 'job',
            title: 'Job Failed',
            message: 'LinkedIn Profile Extractor encountered an error: Rate limit exceeded',
            link: '/dashboard/job-2',
            read: false,
            created_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
            metadata: { job_id: 'job-2', job_name: 'LinkedIn Profile Extractor' },
          },
          {
            id: '3',
            user_id: 'user-1',
            type: 'warning',
            category: 'billing',
            title: 'Approaching Usage Limit',
            message: 'You have used 85% of your monthly API call quota',
            link: '/dashboard/settings?tab=billing',
            read: true,
            created_at: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
          },
          {
            id: '4',
            user_id: 'user-1',
            type: 'info',
            category: 'system',
            title: 'New Template Available',
            message: 'Check out our new Google Maps scraper template',
            link: '/dashboard/templates',
            read: true,
            created_at: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
          },
          {
            id: '5',
            user_id: 'user-1',
            type: 'success',
            category: 'job',
            title: 'Scheduled Job Started',
            message: 'Real Estate Listings job has started running',
            link: '/dashboard/job-3',
            read: true,
            created_at: new Date(Date.now() - 1000 * 60 * 60 * 48).toISOString(),
            metadata: { job_id: 'job-3', job_name: 'Real Estate Listings' },
          },
          {
            id: '6',
            user_id: 'user-1',
            type: 'info',
            category: 'security',
            title: 'New API Key Created',
            message: 'A new API key was created for your account',
            link: '/dashboard/settings?tab=api-keys',
            read: true,
            created_at: new Date(Date.now() - 1000 * 60 * 60 * 72).toISOString(),
          },
        ];

        setNotifications(mockNotifications);
      } catch (error) {
        console.error('Error fetching notifications', error);
      }
    };

    fetchNotifications();
  }, [session]);

  const getNotificationIcon = (type: Notification['type']) => {
    switch (type) {
      case 'success':
        return <CheckCircle2 className="h-6 w-6 text-green-600" />;
      case 'error':
        return <XCircle className="h-6 w-6 text-red-600" />;
      case 'warning':
        return <AlertCircle className="h-6 w-6 text-yellow-600" />;
      case 'info':
        return <Info className="h-6 w-6 text-blue-600" />;
    }
  };

  const handleMarkAsRead = async (notificationId: string) => {
    setNotifications(
      notifications.map((n) =>
        n.id === notificationId ? { ...n, read: true } : n
      )
    );
    toast.success('Marked as read');
  };

  const handleMarkAllAsRead = async () => {
    setNotifications(notifications.map((n) => ({ ...n, read: true })));
    toast.success('All notifications marked as read');
  };

  const handleDelete = async (notificationId: string) => {
    setNotifications(notifications.filter((n) => n.id !== notificationId));
    toast.success('Notification deleted');
  };

  const handleDeleteAll = async () => {
    if (!confirm('Are you sure you want to delete all notifications?')) return;
    setNotifications([]);
    toast.success('All notifications deleted');
  };

  // Filter notifications
  const filteredNotifications = notifications.filter((notification) => {
    const matchesReadStatus =
      filter === 'all' ||
      (filter === 'unread' && !notification.read) ||
      (filter === 'read' && notification.read);

    const matchesCategory =
      categoryFilter === 'all' || notification.category === categoryFilter;

    return matchesReadStatus && matchesCategory;
  });

  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <AppLayout>
      <div className="space-y-6 p-6">
        <PageHeader
          title="Notifications"
          description="Stay updated on your jobs, system alerts, and account activity"
          actions={
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <Button variant="outline" size="sm" onClick={handleMarkAllAsRead}>
                  <Check className="mr-2 h-4 w-4" />
                  Mark All Read
                </Button>
              )}
              {notifications.length > 0 && (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleDeleteAll}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Clear All
                </Button>
              )}
            </div>
          }
        />

        {/* Filters */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <Tabs value={filter} onValueChange={(v: any) => setFilter(v)}>
            <TabsList>
              <TabsTrigger value="all">
                All ({notifications.length})
              </TabsTrigger>
              <TabsTrigger value="unread">
                Unread ({unreadCount})
              </TabsTrigger>
              <TabsTrigger value="read">
                Read ({notifications.length - unreadCount})
              </TabsTrigger>
            </TabsList>
          </Tabs>

          <Select value={categoryFilter} onValueChange={setCategoryFilter}>
            <SelectTrigger className="w-[180px]">
              <Filter className="mr-2 h-4 w-4" />
              <SelectValue placeholder="Category" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              <SelectItem value="job">Jobs</SelectItem>
              <SelectItem value="system">System</SelectItem>
              <SelectItem value="billing">Billing</SelectItem>
              <SelectItem value="security">Security</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Notifications List */}
        {filteredNotifications.length === 0 ? (
          <EmptyState
            icon={<Bell className="h-12 w-12" />}
            title={
              filter === 'unread'
                ? 'All caught up!'
                : notifications.length === 0
                ? 'No notifications yet'
                : 'No notifications found'
            }
            description={
              filter === 'unread'
                ? 'You have no unread notifications'
                : notifications.length === 0
                ? 'Notifications will appear here when you have new activity'
                : 'Try adjusting your filters'
            }
            action={
              filter !== 'all' || categoryFilter !== 'all'
                ? {
                    label: 'Clear Filters',
                    onClick: () => {
                      setFilter('all');
                      setCategoryFilter('all');
                    },
                  }
                : undefined
            }
          />
        ) : (
          <div className="space-y-3">
            {filteredNotifications.map((notification) => (
              <Card
                key={notification.id}
                className={`${
                  !notification.read ? 'border-brand-accent bg-brand-accent/5' : ''
                }`}
              >
                <CardContent className="p-6">
                  <div className="flex items-start gap-4">
                    <div className="mt-1">{getNotificationIcon(notification.type)}</div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-4 mb-2">
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold">{notification.title}</h3>
                          {!notification.read && (
                            <div className="h-2 w-2 rounded-full bg-brand-accent" />
                          )}
                        </div>
                        <Badge variant="outline" className="capitalize">
                          {notification.category}
                        </Badge>
                      </div>

                      <p className="text-sm text-muted-foreground mb-3">
                        {notification.message}
                      </p>

                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">
                          {formatDistanceToNow(new Date(notification.created_at), {
                            addSuffix: true,
                          })}
                        </span>

                        <div className="flex items-center gap-2">
                          {notification.link && (
                            <Link href={notification.link}>
                              <Button variant="outline" size="sm">
                                <ExternalLink className="mr-2 h-4 w-4" />
                                View
                              </Button>
                            </Link>
                          )}

                          {!notification.read && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleMarkAsRead(notification.id)}
                            >
                              <Check className="mr-2 h-4 w-4" />
                              Mark Read
                            </Button>
                          )}

                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(notification.id)}
                            className="text-red-600 hover:text-red-700"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
