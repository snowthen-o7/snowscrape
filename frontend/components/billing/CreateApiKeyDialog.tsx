/**
 * CreateApiKeyDialog
 *
 * Two-step modal:
 * 1. Name input → submit
 * 2. Show raw key once (copyable) with required acknowledgment checkbox
 *    that gates closing.
 */

'use client';

import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@snowforge/ui';
import { Input } from '@snowforge/ui';
import { Button } from '@snowforge/ui';
import { Label } from '@snowforge/ui';
import { Checkbox } from '@snowforge/ui';
import { Alert, AlertDescription } from '@snowforge/ui';
import { Copy, CheckCircle2, AlertTriangle } from 'lucide-react';
import { useCreateApiKey } from '@/lib/hooks';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateApiKeyDialog({ open, onOpenChange }: Props) {
  const [name, setName] = useState('');
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);
  const [copied, setCopied] = useState(false);

  const createKey = useCreateApiKey();

  const reset = () => {
    setName('');
    setCreatedKey(null);
    setAcknowledged(false);
    setCopied(false);
  };

  const handleClose = (next: boolean) => {
    if (!next) {
      // Block close while raw key is shown and not yet acknowledged.
      if (createdKey && !acknowledged) return;
      reset();
    }
    onOpenChange(next);
  };

  const handleSubmit = async () => {
    if (!name.trim()) return;
    try {
      const result = await createKey.mutateAsync(name.trim());
      setCreatedKey(result.key);
    } catch {
      // toast already fired by hook
    }
  };

  const handleCopy = async () => {
    if (!createdKey) return;
    await navigator.clipboard.writeText(createdKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        {!createdKey ? (
          <>
            <DialogHeader>
              <DialogTitle>Create API key</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <Label htmlFor="api-key-name">Name</Label>
              <Input
                id="api-key-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Production server"
                maxLength={100}
              />
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => handleClose(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={!name.trim() || createKey.isPending}
              >
                {createKey.isPending ? 'Creating…' : 'Create key'}
              </Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Save your API key</DialogTitle>
            </DialogHeader>
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                This is the only time you&apos;ll see the full key. Save it
                somewhere safe now.
              </AlertDescription>
            </Alert>
            <div className="flex items-center gap-2">
              <Input
                value={createdKey}
                readOnly
                className="font-mono text-sm"
                onFocus={(e) => e.currentTarget.select()}
              />
              <Button variant="ghost" size="icon" onClick={handleCopy}>
                {copied ? (
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
            </div>
            <div className="flex items-center gap-2 pt-2">
              <Checkbox
                id="ack"
                checked={acknowledged}
                onCheckedChange={(v) => setAcknowledged(!!v)}
              />
              <Label htmlFor="ack" className="text-sm cursor-pointer">
                I&apos;ve saved this key.
              </Label>
            </div>
            <DialogFooter>
              <Button
                onClick={() => handleClose(false)}
                disabled={!acknowledged}
              >
                Done
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
