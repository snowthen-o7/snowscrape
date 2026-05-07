/**
 * Settings Page
 * User preferences, API keys, billing, and account settings
 */

'use client';

import { useState } from 'react';
import { useUser } from '@clerk/nextjs';
import { AppLayout } from '@/components/layout';
import { PageHeader } from '@snowforge/ui';
import { Button } from '@snowforge/ui';
import { Input } from '@snowforge/ui';
import { Label } from '@snowforge/ui';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@snowforge/ui';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@snowforge/ui';
import { Badge } from '@snowforge/ui';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@snowforge/ui';
import { Switch } from '@snowforge/ui';
import {
  User,
  CreditCard,
  Bell,
  Key,
  Settings as SettingsIcon,
  Trash2,
  Plus,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@snowforge/ui';
import { toast } from '@/lib/toast';
import { useSubscription, useUsage, useOpenPortal, useApiKeys, useDeleteApiKey } from '@/lib/hooks';
import { CreateApiKeyDialog } from '@/components/billing/CreateApiKeyDialog';

function BillingTab() {
  const { data: sub, isLoading: subLoading } = useSubscription();
  const { data: usage } = useUsage();
  const openPortal = useOpenPortal();

  if (subLoading || !sub) {
    return (
      <Card>
        <CardContent className="p-6 text-muted-foreground">Loading…</CardContent>
      </Card>
    );
  }

  const planLabels: Record<string, string> = {
    pro: 'Pro',
    business: 'Business',
    enterprise: 'Enterprise',
    locked: 'Locked',
  };
  const planPrices: Record<string, string> = {
    pro: '$49/month',
    business: '$149/month',
    enterprise: 'Custom',
    locked: '—',
  };

  const statusBadge = () => {
    switch (sub.status) {
      case 'trialing':
        return <Badge variant="secondary">Trialing</Badge>;
      case 'active':
        return <Badge>Active</Badge>;
      case 'past_due':
        return <Badge variant="destructive">Past due</Badge>;
      case 'canceled':
        return <Badge variant="outline">Canceled</Badge>;
      default:
        return <Badge variant="outline">{sub.status}</Badge>;
    }
  };

  let trialBanner: React.ReactNode = null;
  if (sub.status === 'trialing' && sub.trial_end) {
    const ms = new Date(sub.trial_end).getTime() - Date.now();
    const days = Math.max(0, Math.ceil(ms / 86_400_000));
    trialBanner = (
      <div className="rounded bg-muted text-muted-foreground text-sm p-3">
        Trial ends in {days} {days === 1 ? 'day' : 'days'}.
      </div>
    );
  }
  if (sub.cancel_at_period_end) {
    trialBanner = (
      <div className="rounded bg-muted text-muted-foreground text-sm p-3">
        Your subscription is set to cancel at the end of the current period.
      </div>
    );
  }

  const pct = usage?.pages_percentage ?? 0;
  const usageColor =
    pct < 80 ? 'bg-primary' : pct < 95 ? 'bg-amber-500' : 'bg-destructive';

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Current plan</CardTitle>
          <CardDescription>Manage your subscription</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-lg border border-border bg-card p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-2xl font-bold">
                  {planLabels[sub.plan] ?? sub.plan}
                </h3>
                <p className="text-muted-foreground">
                  {planPrices[sub.plan] ?? ''}
                </p>
              </div>
              {statusBadge()}
            </div>
            {trialBanner}
          </div>
          <div className="flex gap-2">
            <Button
              onClick={() => openPortal.mutate()}
              disabled={openPortal.isPending || !sub.has_billing_account}
            >
              Manage subscription
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Usage this period</CardTitle>
          <CardDescription>
            Resets on{' '}
            {usage?.billing_period_end
              ? new Date(usage.billing_period_end).toLocaleDateString()
              : '—'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex justify-between text-sm">
            <span>Pages used</span>
            <span>
              {usage?.pages_used.toLocaleString() ?? 0} /{' '}
              {usage?.pages_limit === -1
                ? 'unlimited'
                : usage?.pages_limit?.toLocaleString() ?? 0}
            </span>
          </div>
          <div className="h-2 bg-muted rounded overflow-hidden">
            <div
              className={`h-full ${usageColor} transition-all`}
              style={{ width: `${Math.min(100, pct)}%` }}
            />
          </div>
        </CardContent>
      </Card>
    </>
  );
}

function ApiKeysTab() {
  const { data: keys, isLoading } = useApiKeys();
  const deleteKey = useDeleteApiKey();
  const [createOpen, setCreateOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6 text-muted-foreground">Loading…</CardContent>
      </Card>
    );
  }

  const activeKeys = (keys ?? []).filter((k) => k.is_active);
  const revokedKeys = (keys ?? []).filter((k) => !k.is_active);

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>API keys</CardTitle>
              <CardDescription>Programmatic access to SnowScrape</CardDescription>
            </div>
            <Button onClick={() => setCreateOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Create API key
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {activeKeys.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Key className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-medium mb-2">No API keys</p>
              <p className="text-sm">Create your first API key to get started</p>
            </div>
          ) : (
            <div className="space-y-3">
              {activeKeys.map((k) => (
                <div
                  key={k.api_key_id}
                  className="rounded-lg border border-border bg-card p-4"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h4 className="font-medium">{k.name}</h4>
                      <p className="text-sm text-muted-foreground">
                        Created {new Date(k.created_at).toLocaleDateString()}
                      </p>
                      {k.last_used_at && (
                        <p className="text-xs text-muted-foreground">
                          Last used {new Date(k.last_used_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                    <Badge>Active</Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <Input
                      value={`${k.key_prefix}…`}
                      readOnly
                      className="font-mono text-sm"
                    />
                    <Button
                      variant="destructive"
                      size="icon"
                      onClick={() => setConfirmDelete(k.api_key_id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {revokedKeys.length > 0 && (
            <details className="mt-6">
              <summary className="text-sm text-muted-foreground cursor-pointer">
                Revoked keys ({revokedKeys.length})
              </summary>
              <div className="space-y-2 mt-3 opacity-60">
                {revokedKeys.map((k) => (
                  <div
                    key={k.api_key_id}
                    className="rounded border border-border p-3 text-sm"
                  >
                    <span className="font-medium">{k.name}</span>
                    <span className="ml-2 text-muted-foreground font-mono">
                      {k.key_prefix}…
                    </span>
                    <Badge variant="outline" className="ml-2">
                      Revoked
                    </Badge>
                  </div>
                ))}
              </div>
            </details>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Authentication</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-sm text-muted-foreground">
            Include the key in the Authorization header:
          </p>
          <code className="block rounded bg-muted p-3 text-xs">
            Authorization: Bearer YOUR_API_KEY
          </code>
        </CardContent>
      </Card>

      <CreateApiKeyDialog open={createOpen} onOpenChange={setCreateOpen} />

      <Dialog
        open={!!confirmDelete}
        onOpenChange={(o) => !o && setConfirmDelete(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Revoke API key?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            This will immediately invalidate the key. Any service using it will
            start receiving 401 errors.
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmDelete(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={deleteKey.isPending}
              onClick={async () => {
                if (!confirmDelete) return;
                try {
                  await deleteKey.mutateAsync(confirmDelete);
                } finally {
                  setConfirmDelete(null);
                }
              }}
            >
              {deleteKey.isPending ? 'Revoking…' : 'Revoke'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

export default function SettingsPage() {
  const { user, isLoaded } = useUser();

  // Notification preferences
  const [emailNotifications, setEmailNotifications] = useState({
    jobCompleted: true,
    jobFailed: true,
    weeklyReport: false,
    securityAlerts: true,
  });

  // General preferences
  const [preferences, setPreferences] = useState({
    timezone: 'America/New_York',
    dateFormat: 'MM/DD/YYYY',
    resultsPerPage: '20',
    theme: 'dark',
  });

  const handleSaveNotifications = () => {
    // In production, save to backend
    toast.success('Notification preferences saved');
  };

  const handleSavePreferences = () => {
    // In production, save to backend
    toast.success('Preferences saved');
  };

  if (!isLoaded) {
    return (
      <AppLayout>
        <div className="flex min-h-[60vh] items-center justify-center">
          <p className="text-muted-foreground">Loading settings...</p>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6 p-6">
        <PageHeader
          title="Settings"
          description="Manage your account settings, API keys, and preferences"
        />

        <Tabs defaultValue="account" className="space-y-6">
          <TabsList>
            <TabsTrigger value="account">
              <User className="mr-2 h-4 w-4" />
              Account
            </TabsTrigger>
            <TabsTrigger value="api-keys">
              <Key className="mr-2 h-4 w-4" />
              API Keys
            </TabsTrigger>
            <TabsTrigger value="billing">
              <CreditCard className="mr-2 h-4 w-4" />
              Billing
            </TabsTrigger>
            <TabsTrigger value="notifications">
              <Bell className="mr-2 h-4 w-4" />
              Notifications
            </TabsTrigger>
            <TabsTrigger value="preferences">
              <SettingsIcon className="mr-2 h-4 w-4" />
              Preferences
            </TabsTrigger>
          </TabsList>

          {/* Account Tab */}
          <TabsContent value="account" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Account Information</CardTitle>
                <CardDescription>
                  Your account details are managed through Clerk authentication
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <Label>Email</Label>
                    <Input
                      value={user?.primaryEmailAddress?.emailAddress || ''}
                      disabled
                      className="mt-2"
                    />
                  </div>
                  <div>
                    <Label>Full Name</Label>
                    <Input
                      value={user?.fullName || ''}
                      disabled
                      className="mt-2"
                    />
                  </div>
                  <div>
                    <Label>User ID</Label>
                    <Input value={user?.id || ''} disabled className="mt-2" />
                  </div>
                  <div>
                    <Label>Account Created</Label>
                    <Input
                      value={
                        user?.createdAt
                          ? new Date(user.createdAt).toLocaleDateString()
                          : ''
                      }
                      disabled
                      className="mt-2"
                    />
                  </div>
                </div>
                <div className="pt-4">
                  <Button variant="outline">Manage Account in Clerk</Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Danger Zone</CardTitle>
                <CardDescription>
                  Irreversible actions that affect your account
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between rounded-lg border border-destructive p-4">
                  <div>
                    <h4 className="font-medium text-destructive">Delete Account</h4>
                    <p className="text-sm text-muted-foreground">
                      Permanently delete your account and all associated data
                    </p>
                  </div>
                  <Button variant="destructive">Delete Account</Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* API Keys Tab */}
          <TabsContent value="api-keys" className="space-y-6">
            <ApiKeysTab />
          </TabsContent>

          {/* Billing Tab */}
          <TabsContent value="billing" className="space-y-6">
            <BillingTab />
          </TabsContent>

          {/* Notifications Tab */}
          <TabsContent value="notifications" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Email Notifications</CardTitle>
                <CardDescription>
                  Configure which email notifications you want to receive
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between py-3 border-b border-border">
                  <div>
                    <p className="font-medium">Job Completed</p>
                    <p className="text-sm text-muted-foreground">
                      Receive an email when a job finishes successfully
                    </p>
                  </div>
                  <Switch
                    checked={emailNotifications.jobCompleted}
                    onCheckedChange={(checked) =>
                      setEmailNotifications({
                        ...emailNotifications,
                        jobCompleted: checked,
                      })
                    }
                  />
                </div>

                <div className="flex items-center justify-between py-3 border-b border-border">
                  <div>
                    <p className="font-medium">Job Failed</p>
                    <p className="text-sm text-muted-foreground">
                      Receive an email when a job fails
                    </p>
                  </div>
                  <Switch
                    checked={emailNotifications.jobFailed}
                    onCheckedChange={(checked) =>
                      setEmailNotifications({
                        ...emailNotifications,
                        jobFailed: checked,
                      })
                    }
                  />
                </div>

                <div className="flex items-center justify-between py-3 border-b border-border">
                  <div>
                    <p className="font-medium">Weekly Report</p>
                    <p className="text-sm text-muted-foreground">
                      Receive a weekly summary of your jobs
                    </p>
                  </div>
                  <Switch
                    checked={emailNotifications.weeklyReport}
                    onCheckedChange={(checked) =>
                      setEmailNotifications({
                        ...emailNotifications,
                        weeklyReport: checked,
                      })
                    }
                  />
                </div>

                <div className="flex items-center justify-between py-3">
                  <div>
                    <p className="font-medium">Security Alerts</p>
                    <p className="text-sm text-muted-foreground">
                      Receive alerts about security events (always enabled)
                    </p>
                  </div>
                  <Switch
                    checked={emailNotifications.securityAlerts}
                    onCheckedChange={(checked) =>
                      setEmailNotifications({
                        ...emailNotifications,
                        securityAlerts: checked,
                      })
                    }
                    disabled
                  />
                </div>

                <div className="pt-4">
                  <Button onClick={handleSaveNotifications}>
                    Save Notification Preferences
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Preferences Tab */}
          <TabsContent value="preferences" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>General Preferences</CardTitle>
                <CardDescription>
                  Customize your SnowScrape experience
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="timezone">Timezone</Label>
                  <Select
                    value={preferences.timezone}
                    onValueChange={(value) =>
                      setPreferences({ ...preferences, timezone: value })
                    }
                  >
                    <SelectTrigger id="timezone" className="mt-2">
                      <SelectValue placeholder="Select timezone" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="America/New_York">
                        Eastern Time (ET)
                      </SelectItem>
                      <SelectItem value="America/Chicago">
                        Central Time (CT)
                      </SelectItem>
                      <SelectItem value="America/Denver">
                        Mountain Time (MT)
                      </SelectItem>
                      <SelectItem value="America/Los_Angeles">
                        Pacific Time (PT)
                      </SelectItem>
                      <SelectItem value="UTC">UTC</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="dateFormat">Date Format</Label>
                  <Select
                    value={preferences.dateFormat}
                    onValueChange={(value) =>
                      setPreferences({ ...preferences, dateFormat: value })
                    }
                  >
                    <SelectTrigger id="dateFormat" className="mt-2">
                      <SelectValue placeholder="Select date format" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="MM/DD/YYYY">MM/DD/YYYY</SelectItem>
                      <SelectItem value="DD/MM/YYYY">DD/MM/YYYY</SelectItem>
                      <SelectItem value="YYYY-MM-DD">YYYY-MM-DD</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="resultsPerPage">Results Per Page</Label>
                  <Select
                    value={preferences.resultsPerPage}
                    onValueChange={(value) =>
                      setPreferences({ ...preferences, resultsPerPage: value })
                    }
                  >
                    <SelectTrigger id="resultsPerPage" className="mt-2">
                      <SelectValue placeholder="Select results per page" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="10">10</SelectItem>
                      <SelectItem value="20">20</SelectItem>
                      <SelectItem value="50">50</SelectItem>
                      <SelectItem value="100">100</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="theme">Theme</Label>
                  <Select
                    value={preferences.theme}
                    onValueChange={(value) =>
                      setPreferences({ ...preferences, theme: value })
                    }
                  >
                    <SelectTrigger id="theme" className="mt-2">
                      <SelectValue placeholder="Select theme" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="light">Light</SelectItem>
                      <SelectItem value="dark">Dark</SelectItem>
                      <SelectItem value="system">System</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="pt-4">
                  <Button onClick={handleSavePreferences}>Save Preferences</Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

    </AppLayout>
  );
}
