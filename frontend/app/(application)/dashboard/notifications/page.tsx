/**
 * Notifications Page
 * View and manage all notifications
 */

'use client';

import { useState, useEffect } from 'react';
import { useSession } from '@clerk/nextjs';
import { AppLayout } from '@/components/layout';
import { PageHeader } from '@snowforge/ui';
import { Button } from '@snowforge/ui';
import { Card, CardContent } from '@snowforge/ui';
import { Badge } from '@snowforge/ui';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@snowforge/ui';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@snowforge/ui';
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
import { EmptyState } from '@snowforge/ui';

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
        // TODO: Implement notification API endpoint
        // const token = await session.getToken();
        // const notifications = await notificationsAPI.list(token);
        // setNotifications(notifications);

        // For now, no notifications - persistent notification storage not yet implemented
        setNotifications([]);
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
                  !notification.read ? 'border-accent bg-accent/5' : ''
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
                            <div className="h-2 w-2 rounded-full bg-accent" />
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
