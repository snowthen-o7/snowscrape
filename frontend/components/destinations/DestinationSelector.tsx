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

// Mirrors the backend cap in backend/utils.py ("Maximum 10 export destinations per job").
// Keep in sync if the server limit changes.
const MAX_DESTINATIONS = 10;

export function DestinationSelector({ value, onChange }: Props) {
  const { data: destinations, isLoading } = useDestinations();
  const atCap = value.length >= MAX_DESTINATIONS;

  function toggle(id: string, checked: boolean) {
    if (checked) {
      // Guard the cap even if a disabled control is somehow toggled.
      if (value.includes(id) || value.length >= MAX_DESTINATIONS) return;
      onChange([...value, id]);
    } else {
      onChange(value.filter((x) => x !== id));
    }
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
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          {value.length} / {MAX_DESTINATIONS} selected
        </span>
        {atCap && (
          <span role="status" aria-live="polite">
            Maximum {MAX_DESTINATIONS} destinations per job
          </span>
        )}
      </div>
      {destinations.map((d) => {
        const isChecked = value.includes(d.destination_id);
        const isDisabled = atCap && !isChecked;
        return (
        <label
          key={d.destination_id}
          className={`flex items-center gap-3 rounded-md border p-3 ${
            isDisabled
              ? 'cursor-not-allowed opacity-50'
              : 'hover:bg-muted/50 cursor-pointer'
          }`}
          htmlFor={`dest-${d.destination_id}`}
        >
          <Checkbox
            id={`dest-${d.destination_id}`}
            checked={isChecked}
            disabled={isDisabled}
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
        );
      })}
    </div>
  );
}
