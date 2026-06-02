/**
 * Destinations Page
 * List of export destinations (Google Docs, etc.) with delete actions.
 */

'use client';

import { useState } from 'react';
import Link from 'next/link';
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
  Badge,
} from '@snowforge/ui';
import { Send, Plus } from 'lucide-react';
import { useDestinations, useDeleteDestination } from '@/lib/hooks/useDestinations';

export default function DestinationsPage() {
  const { data: destinations, isLoading } = useDestinations();
  const del = useDeleteDestination();
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const confirmDelete = destinations?.find((d) => d.destination_id === confirmDeleteId);

  return (
    <AppLayout>
      <div className="space-y-6 p-6">
        <div className="flex items-center justify-between">
          <PageHeader
            title="Export Destinations"
            description="Send job results to Google Docs in your Drive."
          />
          <Link href="/dashboard/destinations/new">
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              New Destination
            </Button>
          </Link>
        </div>

        {isLoading ? (
          <Card>
            <CardContent className="p-6 text-muted-foreground">Loading…</CardContent>
          </Card>
        ) : !destinations?.length ? (
          <Card>
            <CardContent className="p-6">
              <div className="flex flex-col items-center justify-center gap-3 py-8 text-center">
                <Send className="h-10 w-10 text-muted-foreground" />
                <p className="text-muted-foreground">
                  No destinations yet. Connect a Google account and create one.
                </p>
                <Link href="/dashboard/destinations/new">
                  <Button variant="outline">
                    <Plus className="mr-2 h-4 w-4" />
                    Create your first destination
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {destinations.map((d) => (
              <Card key={d.destination_id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <CardTitle className="flex items-center gap-2">
                        <Send className="h-4 w-4" />
                        {d.name}
                      </CardTitle>
                      <CardDescription className="flex items-center gap-2">
                        <Badge variant="outline">{d.format_template}</Badge>
                        <Badge variant="outline">{d.mode}</Badge>
                      </CardDescription>
                    </div>
                    <Button
                      variant="outline"
                      onClick={() => setConfirmDeleteId(d.destination_id)}
                      disabled={del.isPending}
                    >
                      Delete
                    </Button>
                  </div>
                </CardHeader>
              </Card>
            ))}
          </div>
        )}

        <Dialog
          open={!!confirmDeleteId}
          onOpenChange={(open) => !open && setConfirmDeleteId(null)}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Delete destination?</DialogTitle>
              <DialogDescription>
                {confirmDelete
                  ? `"${confirmDelete.name}" will be removed. Jobs configured to use it will stop sending exports to it.`
                  : ''}
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setConfirmDeleteId(null)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                disabled={del.isPending}
                onClick={async () => {
                  if (!confirmDeleteId) return;
                  try {
                    await del.mutateAsync(confirmDeleteId);
                  } finally {
                    setConfirmDeleteId(null);
                  }
                }}
              >
                {del.isPending ? 'Deleting…' : 'Delete'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </AppLayout>
  );
}
