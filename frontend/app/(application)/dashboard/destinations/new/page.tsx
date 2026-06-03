/**
 * New Destination Page
 * Form to create a Google Docs export destination.
 */

'use client';

import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';

import { AppLayout } from '@/components/layout';
import {
  PageHeader,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Button,
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@snowforge/ui';
import { useGoogleAccounts } from '@/lib/hooks/useGoogleAccount';
import { useCreateDestination } from '@/lib/hooks/useDestinations';

const schema = z.object({
  name: z.string().min(1, 'Required').max(100),
  drive_folder_id: z.string().min(1, 'Paste a Google Drive folder ID'),
  naming_template: z.string().min(1).max(200),
  mode: z.enum(['new_doc_per_run', 'one_doc_per_row']),
  format_template: z.enum(['structured_log', 'compact_list', 'narrative']),
});

type FormValues = z.infer<typeof schema>;

export default function NewDestinationPage() {
  const router = useRouter();
  const create = useCreateDestination();
  const { data: accounts, isLoading: accountsLoading } = useGoogleAccounts();
  const hasAccount = !!accounts?.length;

  const { register, handleSubmit, setValue, watch, formState } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      mode: 'new_doc_per_run',
      format_template: 'structured_log',
      naming_template: '{{job_name}} — {{date}}',
    },
  });

  async function onSubmit(values: FormValues) {
    await create.mutateAsync({ ...values, type: 'google_docs' });
    router.push('/dashboard/destinations');
  }

  if (accountsLoading) {
    return (
      <AppLayout>
        <div className="space-y-6 p-6">
          <Card>
            <CardContent className="p-6 text-muted-foreground">Loading…</CardContent>
          </Card>
        </div>
      </AppLayout>
    );
  }

  if (!hasAccount) {
    return (
      <AppLayout>
        <div className="space-y-6 p-6">
          <PageHeader
            title="No Google account connected"
            description="Connect one before creating a destination."
          />
          <Card>
            <CardContent className="p-6 space-y-4">
              <p className="text-muted-foreground">
                Destinations require an authorized Google account so exports can write to your
                Drive.
              </p>
              <Link href="/dashboard/integrations" className="text-primary underline">
                Go to Integrations
              </Link>
            </CardContent>
          </Card>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6 p-6">
        <PageHeader
          title="New Destination"
          description="Create a destination to send job results to Google Docs."
        />

        <Card className="max-w-2xl">
          <CardHeader>
            <CardTitle>Destination details</CardTitle>
            <CardDescription>
              Configure where and how scraped results will be written.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input id="name" placeholder="My LinkedIn export" {...register('name')} />
                {formState.errors.name && (
                  <p className="text-sm text-destructive">{formState.errors.name.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="drive_folder_id">Google Drive folder ID</Label>
                <Input
                  id="drive_folder_id"
                  placeholder="Paste the folder ID from your Drive URL"
                  {...register('drive_folder_id')}
                />
                <p className="text-xs text-muted-foreground">
                  Find the folder in Google Drive — the ID is in the URL after
                  <code className="mx-1 rounded bg-muted px-1 py-0.5 text-xs">folders/</code>.
                  Picker UI coming in a future release.
                </p>
                {formState.errors.drive_folder_id && (
                  <p className="text-sm text-destructive">
                    {formState.errors.drive_folder_id.message}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="naming_template">Document name template</Label>
                <Input id="naming_template" {...register('naming_template')} />
                <p className="text-xs text-muted-foreground">
                  Variables:{' '}
                  <code className="rounded bg-muted px-1 py-0.5 text-xs">{`{{job_name}}`}</code>{' '}
                  <code className="rounded bg-muted px-1 py-0.5 text-xs">{`{{date}}`}</code>
                </p>
                {formState.errors.naming_template && (
                  <p className="text-sm text-destructive">
                    {formState.errors.naming_template.message}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label>Mode</Label>
                <Select
                  value={watch('mode')}
                  onValueChange={(v) => setValue('mode', v as FormValues['mode'])}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="new_doc_per_run">New doc per run</SelectItem>
                    <SelectItem value="one_doc_per_row">One doc per row</SelectItem>
                  </SelectContent>
                </Select>
                {watch('mode') === 'one_doc_per_row' && (
                  <p className="text-xs text-muted-foreground">
                    Creates a separate Google Doc for each result row (e.g. one doc per
                    profile). Limited to 25 rows per run — larger jobs should use
                    &ldquo;New doc per run&rdquo; or be split.
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label>Format</Label>
                <Select
                  value={watch('format_template')}
                  onValueChange={(v) =>
                    setValue('format_template', v as FormValues['format_template'])
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="structured_log">Structured log</SelectItem>
                    <SelectItem value="compact_list">Compact list</SelectItem>
                    <SelectItem value="narrative">Narrative</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex gap-2 pt-2">
                <Button type="submit" disabled={create.isPending}>
                  {create.isPending ? 'Creating…' : 'Create destination'}
                </Button>
                <Button type="button" variant="outline" onClick={() => router.back()}>
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  );
}
