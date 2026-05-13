'use client';

import { useState } from 'react';
import { useClerk } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@snowforge/ui';
import { Button } from '@snowforge/ui';
import { Alert, AlertDescription } from '@snowforge/ui';
import { AlertTriangle } from 'lucide-react';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * DeleteAccountModal
 *
 * Confirmation dialog shown before a user deletes their Clerk account.
 * Lists all consequences of deletion so the user understands what "delete"
 * means before they confirm. On confirm, calls clerk.user.delete() then
 * redirects to the home page.
 */
export function DeleteAccountModal({ open, onOpenChange }: Props) {
  const { user } = useClerk();
  const router = useRouter();
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCancel = () => {
    if (isDeleting) return;
    setError(null);
    onOpenChange(false);
  };

  const handleConfirm = async () => {
    if (!user || isDeleting) return;
    setIsDeleting(true);
    setError(null);
    try {
      await user.delete();
      router.push('/');
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Failed to delete account. Please try again.'
      );
      setIsDeleting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleCancel}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete account</DialogTitle>
        </DialogHeader>

        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            This action is permanent and cannot be undone.
          </AlertDescription>
        </Alert>

        <div className="space-y-2 text-sm text-muted-foreground">
          <p className="font-medium text-foreground">Deleting your account will:</p>
          <ul className="space-y-1 list-disc list-inside">
            <li>Cancel your subscription immediately — you will not be charged again</li>
            <li>Permanently delete all your scrape jobs and their results</li>
            <li>Permanently delete all your API keys</li>
            <li>Permanently delete all your templates and webhooks</li>
          </ul>
        </div>

        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}

        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleCancel}
            disabled={isDeleting}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleConfirm}
            disabled={isDeleting}
          >
            {isDeleting ? 'Deleting…' : 'Yes, delete my account'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
