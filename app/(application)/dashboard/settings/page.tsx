/**
 * Settings Page
 * User preferences, API keys, billing, and account settings
 */

'use client';

import { useState, useEffect } from 'react';
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
  Copy,
  Eye,
  EyeOff,
  Trash2,
  Plus,
  CheckCircle2,
} from 'lucide-react';
import { toast } from '@/lib/toast';
import { ConfirmDialog } from '@snowforge/ui';

export default function SettingsPage() {
  const { user, isLoaded } = useUser();
  const [apiKeys, setApiKeys] = useState<any[]>([]);
  const [showApiKey, setShowApiKey] = useState<{ [key: string]: boolean }>({});
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [keyToDelete, setKeyToDelete] = useState<string | null>(null);

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

  useEffect(() => {
    // In production, fetch API keys from backend
    // For now, using mock data
    setApiKeys([
      {
        id: '1',
        name: 'Production API Key',
        key: 'sk_live_4eC39HqLyjWDarjtT1zdp7dc',
        created: '2026-01-15T10:00:00Z',
        lastUsed: '2026-01-19T14:30:00Z',
      },
    ]);
  }, []);

  const handleCreateApiKey = () => {
    const keyName = prompt('Enter a name for this API key:');
    if (!keyName) return;

    const newKey = {
      id: Date.now().toString(),
      name: keyName,
      key: `sk_live_${Math.random().toString(36).substring(2, 15)}${Math.random().toString(36).substring(2, 15)}`,
      created: new Date().toISOString(),
      lastUsed: null,
    };

    setApiKeys([...apiKeys, newKey]);
    toast.success('API key created successfully');
  };

  const handleDeleteApiKey = (keyId: string) => {
    setApiKeys(apiKeys.filter((k) => k.id !== keyId));
    setDeleteDialogOpen(false);
    setKeyToDelete(null);
    toast.success('API key deleted');
  };

  const copyApiKey = (key: string, keyId: string) => {
    navigator.clipboard.writeText(key);
    setCopiedKey(keyId);
    toast.success('API key copied to clipboard');
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const toggleShowKey = (keyId: string) => {
    setShowApiKey((prev) => ({ ...prev, [keyId]: !prev[keyId] }));
  };

  const maskApiKey = (key: string) => {
    return `${key.substring(0, 12)}${'•'.repeat(20)}`;
  };

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
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>API Keys</CardTitle>
                    <CardDescription>
                      Manage your API keys for programmatic access
                    </CardDescription>
                  </div>
                  <Button onClick={handleCreateApiKey}>
                    <Plus className="mr-2 h-4 w-4" />
                    Create API Key
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {apiKeys.length === 0 ? (
                  <div className="text-center py-12 text-muted-foreground">
                    <Key className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p className="text-lg font-medium mb-2">No API Keys</p>
                    <p className="text-sm">Create your first API key to get started</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {apiKeys.map((apiKey) => (
                      <div
                        key={apiKey.id}
                        className="rounded-lg border border-border bg-card p-4"
                      >
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <h4 className="font-medium">{apiKey.name}</h4>
                            <p className="text-sm text-muted-foreground">
                              Created {new Date(apiKey.created).toLocaleDateString()}
                            </p>
                            {apiKey.lastUsed && (
                              <p className="text-xs text-muted-foreground">
                                Last used {new Date(apiKey.lastUsed).toLocaleString()}
                              </p>
                            )}
                          </div>
                          <Badge variant="outline">Active</Badge>
                        </div>

                        <div className="flex items-center gap-2">
                          <Input
                            value={
                              showApiKey[apiKey.id]
                                ? apiKey.key
                                : maskApiKey(apiKey.key)
                            }
                            readOnly
                            className="font-mono text-sm"
                          />
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => toggleShowKey(apiKey.id)}
                          >
                            {showApiKey[apiKey.id] ? (
                              <EyeOff className="h-4 w-4" />
                            ) : (
                              <Eye className="h-4 w-4" />
                            )}
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => copyApiKey(apiKey.key, apiKey.id)}
                          >
                            {copiedKey === apiKey.id ? (
                              <CheckCircle2 className="h-4 w-4 text-green-600" />
                            ) : (
                              <Copy className="h-4 w-4" />
                            )}
                          </Button>
                          <Button
                            variant="destructive"
                            size="icon"
                            onClick={() => {
                              setKeyToDelete(apiKey.id);
                              setDeleteDialogOpen(true);
                            }}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>API Documentation</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-sm text-muted-foreground">
                  Use your API keys to authenticate requests to the SnowScrape API.
                </p>
                <p className="text-sm text-muted-foreground">
                  Include the key in the Authorization header:
                </p>
                <code className="block rounded bg-muted p-3 text-xs">
                  Authorization: Bearer YOUR_API_KEY
                </code>
                <Button variant="link" className="p-0 h-auto">
                  View Full API Documentation →
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Billing Tab */}
          <TabsContent value="billing" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Current Plan</CardTitle>
                <CardDescription>
                  Manage your subscription and billing information
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-lg border border-border bg-card p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-2xl font-bold">Pro Plan</h3>
                      <p className="text-muted-foreground">
                        $49/month - Billed monthly
                      </p>
                    </div>
                    <Badge>Active</Badge>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">API Calls</span>
                      <span>50,000 / 100,000</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Storage</span>
                      <span>2.5 GB / 10 GB</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Next billing date</span>
                      <span>February 1, 2026</span>
                    </div>
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button>Upgrade Plan</Button>
                  <Button variant="outline">View All Plans</Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Payment Method</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between rounded-lg border border-border p-4">
                  <div className="flex items-center gap-4">
                    <CreditCard className="h-8 w-8 text-muted-foreground" />
                    <div>
                      <p className="font-medium">•••• •••• •••• 4242</p>
                      <p className="text-sm text-muted-foreground">Expires 12/2027</p>
                    </div>
                  </div>
                  <Button variant="outline" size="sm">
                    Update
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Billing History</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {[
                    {
                      date: '2026-01-01',
                      amount: '$49.00',
                      status: 'Paid',
                      invoice: 'INV-2026-001',
                    },
                    {
                      date: '2025-12-01',
                      amount: '$49.00',
                      status: 'Paid',
                      invoice: 'INV-2025-012',
                    },
                    {
                      date: '2025-11-01',
                      amount: '$49.00',
                      status: 'Paid',
                      invoice: 'INV-2025-011',
                    },
                  ].map((item, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between py-3 border-b border-border last:border-0"
                    >
                      <div>
                        <p className="font-medium">{item.invoice}</p>
                        <p className="text-sm text-muted-foreground">
                          {new Date(item.date).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="flex items-center gap-4">
                        <Badge variant="outline">{item.status}</Badge>
                        <p className="font-medium">{item.amount}</p>
                        <Button variant="ghost" size="sm">
                          Download
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
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

      {/* Delete API Key Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        onConfirm={() => keyToDelete && handleDeleteApiKey(keyToDelete)}
        title="Delete API Key"
        description="Are you sure you want to delete this API key? This action cannot be undone and any applications using this key will stop working."
        confirmLabel="Delete"
        variant="destructive"
      />
    </AppLayout>
  );
}
