/**
 * Notification Center Component
 * Bell icon with dropdown panel showing recent notifications
 */

'use client';

import React, { useState, useEffect } from 'react';
import { useSession } from '@clerk/nextjs';
import {
  Button,
  Badge,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@snowforge/ui';
import {
  Bell,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Info,
  Settings,
  Trash2,
  Check,
  ExternalLink,
} from 'lucide-react';
import { Notification } from '@/lib/types/notifications';
import { formatDistanceToNow } from 'date-fns';
import Link from 'next/link';

export function NotificationCenter() {
  const { session } = useSession();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);

  // Fetch notifications
  useEffect(() => {
    const fetchNotifications = async () => {
      if (!session) return;

      try {
        // In production, fetch from API
        // const token = await session.getToken();
        // const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/notifications`, {
        //   headers: { Authorization: `Bearer ${token}` }
        // });
        // const data = await response.json();

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
            created_at: new Date(Date.now() - 1000 * 60 * 5).toISOString(), // 5 min ago
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
            created_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(), // 30 min ago
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
            created_at: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(), // 2 hours ago
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
            created_at: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(), // 1 day ago
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
            created_at: new Date(Date.now() - 1000 * 60 * 60 * 48).toISOString(), // 2 days ago
            metadata: { job_id: 'job-3', job_name: 'Real Estate Listings' },
          },
        ];

        setNotifications(mockNotifications);
        setUnreadCount(mockNotifications.filter((n) => !n.read).length);
      } catch (error) {
        console.error('Error fetching notifications', error);
      }
    };

    fetchNotifications();
  }, [session]);

  const getNotificationIcon = (type: Notification['type']) => {
    switch (type) {
      case 'success':
        return <CheckCircle2 className="h-5 w-5 text-green-600" />;
      case 'error':
        return <XCircle className="h-5 w-5 text-red-600" />;
      case 'warning':
        return <AlertCircle className="h-5 w-5 text-yellow-600" />;
      case 'info':
        return <Info className="h-5 w-5 text-blue-600" />;
    }
  };

  const handleMarkAsRead = async (notificationId: string) => {
    // In production, send API request
    setNotifications(
      notifications.map((n) =>
        n.id === notificationId ? { ...n, read: true } : n
      )
    );
    setUnreadCount((prev) => Math.max(0, prev - 1));
  };

  const handleMarkAllAsRead = async () => {
    // In production, send API request
    setNotifications(notifications.map((n) => ({ ...n, read: true })));
    setUnreadCount(0);
  };

  const handleDelete = async (notificationId: string) => {
    // In production, send API request
    setNotifications(notifications.filter((n) => n.id !== notificationId));
    const notification = notifications.find((n) => n.id === notificationId);
    if (notification && !notification.read) {
      setUnreadCount((prev) => Math.max(0, prev - 1));
    }
  };

  const unreadNotifications = notifications.filter((n) => !n.read);
  const readNotifications = notifications.filter((n) => n.read);

  return (
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <Badge
              variant="destructive"
              className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs"
            >
              {unreadCount > 9 ? '9+' : unreadCount}
            </Badge>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-[400px] p-0">
        <div className="flex items-center justify-between border-b border-border p-4">
          <h3 className="font-semibold">Notifications</h3>
          <div className="flex items-center gap-2">
            {unreadCount > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleMarkAllAsRead}
                className="text-xs"
              >
                <Check className="mr-1 h-3 w-3" />
                Mark all read
              </Button>
            )}
            <Link href="/dashboard/settings?tab=notifications">
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <Settings className="h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>

        <Tabs defaultValue="all" className="w-full">
          <TabsList className="w-full rounded-none border-b">
            <TabsTrigger value="all" className="flex-1">
              All ({notifications.length})
            </TabsTrigger>
            <TabsTrigger value="unread" className="flex-1">
              Unread ({unreadCount})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="all" className="mt-0 max-h-[400px] overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Bell className="h-12 w-12 text-muted-foreground mb-4 opacity-50" />
                <p className="text-sm text-muted-foreground">No notifications yet</p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {notifications.map((notification) => (
                  <NotificationItem
                    key={notification.id}
                    notification={notification}
                    onMarkAsRead={handleMarkAsRead}
                    onDelete={handleDelete}
                    getIcon={getNotificationIcon}
                  />
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="unread" className="mt-0 max-h-[400px] overflow-y-auto">
            {unreadNotifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <CheckCircle2 className="h-12 w-12 text-green-600 mb-4 opacity-50" />
                <p className="text-sm text-muted-foreground">All caught up!</p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {unreadNotifications.map((notification) => (
                  <NotificationItem
                    key={notification.id}
                    notification={notification}
                    onMarkAsRead={handleMarkAsRead}
                    onDelete={handleDelete}
                    getIcon={getNotificationIcon}
                  />
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>

        {notifications.length > 0 && (
          <div className="border-t border-border p-2">
            <Link href="/dashboard/notifications" onClick={() => setIsOpen(false)}>
              <Button variant="ghost" className="w-full text-xs">
                View All Notifications
              </Button>
            </Link>
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// Notification Item Component
interface NotificationItemProps {
  notification: Notification;
  onMarkAsRead: (id: string) => void;
  onDelete: (id: string) => void;
  getIcon: (type: Notification['type']) => React.ReactElement;
}

function NotificationItem({
  notification,
  onMarkAsRead,
  onDelete,
  getIcon,
}: NotificationItemProps) {
  return (
    <div
      className={`p-4 hover:bg-muted/50 transition-colors ${
        !notification.read ? 'bg-brand-accent/5' : ''
      }`}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5">{getIcon(notification.type)}</div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-1">
            <h4 className="text-sm font-medium line-clamp-1">{notification.title}</h4>
            {!notification.read && (
              <div className="h-2 w-2 rounded-full bg-brand-accent flex-shrink-0 mt-1" />
            )}
          </div>

          <p className="text-sm text-muted-foreground line-clamp-2 mb-2">
            {notification.message}
          </p>

          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">
              {formatDistanceToNow(new Date(notification.created_at), {
                addSuffix: true,
              })}
            </span>

            <div className="flex items-center gap-1">
              {notification.link && (
                <Link href={notification.link}>
                  <Button variant="ghost" size="sm" className="h-7 px-2 text-xs">
                    <ExternalLink className="h-3 w-3 mr-1" />
                    View
                  </Button>
                </Link>
              )}

              {!notification.read && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    onMarkAsRead(notification.id);
                  }}
                  className="h-7 px-2 text-xs"
                >
                  <Check className="h-3 w-3" />
                </Button>
              )}

              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(notification.id);
                }}
                className="h-7 px-2 text-xs text-red-600 hover:text-red-700"
              >
                <Trash2 className="h-3 w-3" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
