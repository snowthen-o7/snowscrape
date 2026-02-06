'use client';

import { Controller, useFormContext } from 'react-hook-form';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@snowforge/ui';
import { Input } from '@snowforge/ui';
import { Label } from '@snowforge/ui';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@snowforge/ui';
import { Switch } from '@snowforge/ui';
import { Checkbox } from '@snowforge/ui';
import type { JobFormValues } from '@/lib/schemas/jobFormSchema';

export function ExportTab() {
  const { control, watch, setValue, getValues } = useFormContext<JobFormValues>();
  const exportEnabled = watch('export_config.enabled');
  const notificationEnabled = watch('notification_config.enabled');

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Export Settings</CardTitle>
              <CardDescription>Configure how and where to export results</CardDescription>
            </div>
            <Controller
              control={control}
              name="export_config.enabled"
              render={({ field }) => (
                <Switch
                  checked={field.value || false}
                  onCheckedChange={field.onChange}
                />
              )}
            />
          </div>
        </CardHeader>
        {exportEnabled && (
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Export Formats</Label>
                <div className="space-y-2">
                  {(['json', 'csv', 'xlsx'] as const).map((format) => (
                    <div key={format} className="flex items-center space-x-2">
                      <Checkbox
                        id={`format-${format}`}
                        checked={getValues('export_config.formats')?.includes(format) || false}
                        onCheckedChange={(checked) => {
                          const currentFormats = getValues('export_config.formats') || [];
                          const newFormats = checked
                            ? [...currentFormats, format]
                            : currentFormats.filter(f => f !== format);
                          setValue('export_config.formats', newFormats.length > 0 ? newFormats : ['json'], { shouldDirty: true });
                        }}
                      />
                      <Label htmlFor={`format-${format}`} className="uppercase">{format}</Label>
                    </div>
                  ))}
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="exportDestination">Destination</Label>
                <Controller
                  control={control}
                  name="export_config.destination"
                  render={({ field }) => (
                    <Select value={field.value || 's3'} onValueChange={field.onChange}>
                      <SelectTrigger id="exportDestination">
                        <SelectValue placeholder="Select destination" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="s3">S3 Bucket</SelectItem>
                        <SelectItem value="local">Local Storage</SelectItem>
                        <SelectItem value="webhook">Webhook POST</SelectItem>
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>
              <div className="flex items-center space-x-2">
                <Controller
                  control={control}
                  name="export_config.compress"
                  render={({ field }) => (
                    <Switch
                      id="compressExport"
                      checked={field.value || false}
                      onCheckedChange={field.onChange}
                    />
                  )}
                />
                <Label htmlFor="compressExport">Compress files (ZIP)</Label>
              </div>
            </div>
          </CardContent>
        )}
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Notifications</CardTitle>
              <CardDescription>Get notified when jobs complete or fail</CardDescription>
            </div>
            <Controller
              control={control}
              name="notification_config.enabled"
              render={({ field }) => (
                <Switch
                  checked={field.value || false}
                  onCheckedChange={field.onChange}
                />
              )}
            />
          </div>
        </CardHeader>
        {notificationEnabled && (
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center space-x-2">
                <Controller
                  control={control}
                  name="notification_config.email_on_success"
                  render={({ field }) => (
                    <Switch
                      id="emailOnSuccess"
                      checked={field.value || false}
                      onCheckedChange={field.onChange}
                    />
                  )}
                />
                <Label htmlFor="emailOnSuccess">Email on success</Label>
              </div>
              <div className="flex items-center space-x-2">
                <Controller
                  control={control}
                  name="notification_config.email_on_failure"
                  render={({ field }) => (
                    <Switch
                      id="emailOnFailure"
                      checked={field.value !== false}
                      onCheckedChange={field.onChange}
                    />
                  )}
                />
                <Label htmlFor="emailOnFailure">Email on failure</Label>
              </div>
              <div className="md:col-span-2 space-y-2">
                <Label htmlFor="emailAddresses">Email Addresses</Label>
                <Input
                  id="emailAddresses"
                  type="text"
                  placeholder="email1@example.com, email2@example.com"
                  value={watch('notification_config.email_addresses')?.join(', ') || ''}
                  onChange={(e) =>
                    setValue(
                      'notification_config.email_addresses',
                      e.target.value.split(',').map(email => email.trim()).filter(email => email.length > 0),
                      { shouldDirty: true }
                    )
                  }
                />
              </div>
            </div>
          </CardContent>
        )}
      </Card>
    </div>
  );
}
