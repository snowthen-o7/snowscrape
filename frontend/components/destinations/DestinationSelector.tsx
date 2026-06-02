/**
 * DestinationSelector
 * Multi-select checklist of saved export destinations.
 * Used in job creation/edit forms to attach destinations to a job.
 */

'use client';

import Link from 'next/link';
import { Card, CardContent, Checkbox, Label, Badge } from '@snowforge/ui';
import { useDestinations } from '@/lib/hooks/useDestinations';

interface Props {
  value: string[];
  onChange: (ids: string[]) => void;
}

export function DestinationSelector({ value, onChange }: Props) {
  const { data: destinations, isLoading } = useDestinations();

  function toggle(id: string, checked: boolean) {
    onChange(checked ? [...value, id] : value.filter((x) => x !== id));
  }

  if (isLoading) {
    return <div className="text-sm text-muted-foreground">Loading destinations…</div>;
  }

  if (!destinations?.length) {
    return (
      <Card>
        <CardContent className="p-4">
          <p className="text-sm text-muted-foreground">
            No destinations yet.{' '}
            <Link className="text-primary underline" href="/dashboard/destinations/new">
              Create one
            </Link>{' '}
            to send results automatically to Google Docs.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-2">
      {destinations.map((d) => (
        <label
          key={d.destination_id}
          className="flex items-center gap-3 rounded-md border p-3 hover:bg-muted/50 cursor-pointer"
          htmlFor={`dest-${d.destination_id}`}
        >
          <Checkbox
            id={`dest-${d.destination_id}`}
            checked={value.includes(d.destination_id)}
            onCheckedChange={(c) => toggle(d.destination_id, Boolean(c))}
          />
          <div className="flex-1">
            <div className="font-medium text-sm">{d.name}</div>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="outline" className="text-xs">
                {d.format_template}
              </Badge>
              <Badge variant="outline" className="text-xs">
                {d.mode}
              </Badge>
            </div>
          </div>
        </label>
      ))}
    </div>
  );
}
