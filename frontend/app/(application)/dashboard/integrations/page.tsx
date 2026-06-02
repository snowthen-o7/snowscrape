/**
 * Integrations Page
 * Connect/disconnect third-party services (currently: Google Drive + Docs).
 */

'use client';

import { useState } from 'react';
import { AppLayout } from '@/components/layout';
import {
  PageHeader,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Button,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@snowforge/ui';
import { Plug } from 'lucide-react';
import {
  useGoogleAccounts,
  useStartGoogleOAuth,
  useRevokeGoogleAccount,
} from '@/lib/hooks/useGoogleAccount';

export default function IntegrationsPage() {
  const { data: accounts, isLoading } = useGoogleAccounts();
  const start = useStartGoogleOAuth();
  const revoke = useRevokeGoogleAccount();
  const [confirmRevoke, setConfirmRevoke] = useState(false);

  const account = accounts?.[0];

  async function handleConnect() {
    try {
      const r = await start.mutateAsync();
      sessionStorage.setItem('google_oauth_state', r.state);
      window.location.href = r.auth_url;
    } catch {
      // toast handled by hook
    }
  }

  return (
    <AppLayout>
      <div className="space-y-6 p-6">
        <PageHeader
          title="Integrations"
          description="Connect external services to export your scrape results."
        />

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <CardTitle className="flex items-center gap-2">
                  <Plug className="h-5 w-5" />
                  Google
                </CardTitle>
                <CardDescription>
                  Export scrape results to Google Docs in your Drive.
                </CardDescription>
              </div>
              {isLoading ? (
                <span className="text-sm text-muted-foreground">Loading…</span>
              ) : account ? (
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <div className="text-sm font-medium">{account.email}</div>
                    <div className="text-xs text-muted-foreground">Connected</div>
                  </div>
                  <Button
                    variant="outline"
                    onClick={() => setConfirmRevoke(true)}
                    disabled={revoke.isPending}
                  >
                    Disconnect
                  </Button>
                </div>
              ) : (
                <Button onClick={handleConnect} disabled={start.isPending}>
                  {start.isPending ? 'Connecting…' : 'Connect Google'}
                </Button>
              )}
            </div>
          </CardHeader>
          {account && (
            <CardContent>
              <div className="text-sm text-muted-foreground">
                Existing destinations will stop receiving exports if you disconnect.
              </div>
            </CardContent>
          )}
        </Card>

        <Dialog open={confirmRevoke} onOpenChange={setConfirmRevoke}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Disconnect Google account?</DialogTitle>
              <DialogDescription>
                {account?.email} will be unlinked. Any export destinations targeting this account
                will stop working until you reconnect.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setConfirmRevoke(false)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                disabled={revoke.isPending}
                onClick={async () => {
                  try {
                    await revoke.mutateAsync();
                  } finally {
                    setConfirmRevoke(false);
                  }
                }}
              >
                {revoke.isPending ? 'Disconnecting…' : 'Disconnect'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </AppLayout>
  );
}
