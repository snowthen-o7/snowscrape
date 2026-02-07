'use client';

import { Controller, useFormContext } from 'react-hook-form';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@snowforge/ui';
import { Button } from '@snowforge/ui';
import { Input } from '@snowforge/ui';
import { Label } from '@snowforge/ui';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@snowforge/ui';
import {
  Loader2,
  FileText,
  Link,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';
import { COMMON_TIMEZONES, type URLPreviewResponse } from '@/lib/types';
import type { JobFormValues } from '@/lib/schemas/jobFormSchema';

interface BasicsTabProps {
  sourceError: string | null;
  sourceLoading: boolean;
  headers: string[];
  urlPreview: URLPreviewResponse | null;
  urlPreviewLoading: boolean;
  onValidateSource: () => void;
  onPreviewUrlTemplate: () => void;
  onSourceErrorClear: () => void;
  onUrlPreviewClear: () => void;
}

export function BasicsTab({
  sourceError,
  sourceLoading,
  headers,
  urlPreview,
  urlPreviewLoading,
  onValidateSource,
  onPreviewUrlTemplate,
  onSourceErrorClear,
  onUrlPreviewClear,
}: BasicsTabProps) {
  const { control, register, watch, setValue, formState: { errors } } = useFormContext<JobFormValues>();
  const sourceType = watch('source_type');

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>General Information</CardTitle>
          <CardDescription>Basic job settings and source configuration</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name">Job Name</Label>
              <Input
                id="name"
                placeholder="My Scraping Job"
                {...register('name')}
                className={errors.name ? 'border-red-500 focus-visible:ring-red-500' : ''}
              />
              {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="rateLimit">Rate Limit (requests/second)</Label>
              <Input
                id="rateLimit"
                type="number"
                min={1}
                max={8}
                placeholder="1-8"
                {...register('rate_limit', { valueAsNumber: true })}
              />
              {errors.rate_limit && <p className="text-sm text-destructive">{errors.rate_limit.message}</p>}
            </div>
          </div>

          {/* Source Type Toggle */}
          <div className="space-y-3">
            <Label>Source Type</Label>
            <div className="flex gap-2">
              <Button
                type="button"
                variant={sourceType === 'csv' ? 'default' : 'outline'}
                className="flex items-center gap-2"
                onClick={() => {
                  setValue('source_type', 'csv', { shouldValidate: false });
                  onSourceErrorClear();
                  onUrlPreviewClear();
                }}
              >
                <FileText className="h-4 w-4" />
                CSV File
              </Button>
              <Button
                type="button"
                variant={sourceType === 'direct_url' ? 'default' : 'outline'}
                className="flex items-center gap-2"
                onClick={() => {
                  setValue('source_type', 'direct_url', { shouldValidate: false });
                  onSourceErrorClear();
                }}
              >
                <Link className="h-4 w-4" />
                Direct URL
              </Button>
            </div>
            <p className="text-sm text-muted-foreground">
              {sourceType === 'csv'
                ? 'Parse URLs from a CSV file hosted on HTTP/HTTPS or SFTP'
                : 'Use a single URL with optional date/time variables (e.g., {{date:Y-m-d}})'}
            </p>
          </div>

          {/* CSV Source Mode */}
          {sourceType === 'csv' && (
            <div className="space-y-2">
              <Label htmlFor="sourceUrl">Source URL</Label>
              <div className="relative">
                <Input
                  id="sourceUrl"
                  placeholder="https://example.com/data.csv or sftp://..."
                  {...register('source')}
                  onBlur={onValidateSource}
                  className={errors.source ? 'border-red-500 focus-visible:ring-red-500' : ''}
                />
                {sourceLoading && (
                  <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                    <Loader2 className="h-4 w-4 text-accent-foreground animate-spin" />
                  </div>
                )}
              </div>
              {errors.source && <p className="text-sm text-destructive">{errors.source.message}</p>}
              {sourceError && <p className="text-sm text-destructive">{sourceError}</p>}
              {sourceLoading && <p className="text-sm text-muted-foreground">Validating source URL...</p>}
            </div>
          )}

          {/* Direct URL Mode */}
          {sourceType === 'direct_url' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2 md:col-span-2">
                  <Label htmlFor="urlTemplate">URL Template</Label>
                  <div className="relative">
                    <Input
                      id="urlTemplate"
                      placeholder="https://example.com/report_{{date:Y-m-d}}.pdf"
                      {...register('url_template', {
                        onChange: () => onUrlPreviewClear(),
                      })}
                      onBlur={onPreviewUrlTemplate}
                      className={errors.url_template ? 'border-red-500 focus-visible:ring-red-500' : ''}
                    />
                    {urlPreviewLoading && (
                      <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                        <Loader2 className="h-4 w-4 text-accent-foreground animate-spin" />
                      </div>
                    )}
                  </div>
                  {errors.url_template && <p className="text-sm text-destructive">{errors.url_template.message}</p>}
                  {sourceError && <p className="text-sm text-destructive">{sourceError}</p>}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="timezone">Timezone</Label>
                  <Controller
                    control={control}
                    name="timezone"
                    render={({ field }) => (
                      <Select
                        value={field.value}
                        onValueChange={(value) => {
                          field.onChange(value);
                          onUrlPreviewClear();
                          if (watch('url_template')) {
                            setTimeout(onPreviewUrlTemplate, 100);
                          }
                        }}
                      >
                        <SelectTrigger id="timezone">
                          <SelectValue placeholder="Select timezone" />
                        </SelectTrigger>
                        <SelectContent>
                          {COMMON_TIMEZONES.map((tz) => (
                            <SelectItem key={tz} value={tz}>{tz}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  />
                  <p className="text-xs text-muted-foreground">
                    Date/time variables will be resolved in this timezone
                  </p>
                </div>
              </div>

              {/* URL Preview */}
              {urlPreview && (
                <div className={`p-4 rounded-lg border ${urlPreview.valid ? 'border-green-500/30 bg-green-500/5' : 'border-red-500/30 bg-red-500/5'}`}>
                  <div className="flex items-start gap-2">
                    {urlPreview.valid ? (
                      <CheckCircle2 className="h-5 w-5 text-green-500 mt-0.5" />
                    ) : (
                      <AlertCircle className="h-5 w-5 text-red-500 mt-0.5" />
                    )}
                    <div className="space-y-1 flex-1">
                      <p className="text-sm font-medium">
                        {urlPreview.valid ? 'URL Preview' : 'Invalid Template'}
                      </p>
                      {urlPreview.valid ? (
                        <>
                          <p className="text-sm text-muted-foreground break-all">
                            {urlPreview.resolved}
                          </p>
                          {urlPreview.variables && urlPreview.variables.length > 0 && (
                            <p className="text-xs text-muted-foreground mt-2">
                              Variables: {urlPreview.variables.map(v =>
                                `{{${v.type}${v.offset || ''}${v.format ? ':' + v.format : ''}}}`
                              ).join(', ')}
                            </p>
                          )}
                        </>
                      ) : (
                        <p className="text-sm text-red-500">{urlPreview.error}</p>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Variable Syntax Help */}
              <div className="p-4 rounded-lg bg-muted/50 border">
                <p className="text-sm font-medium mb-2">Supported Variables</p>
                <div className="text-xs text-muted-foreground space-y-1">
                  <p><code className="bg-muted px-1 rounded">{`{{date}}`}</code> - Current date (YYYY-MM-DD)</p>
                  <p><code className="bg-muted px-1 rounded">{`{{date:Y-m-d}}`}</code> - Custom format (2026-01-22)</p>
                  <p><code className="bg-muted px-1 rounded">{`{{date:m/d/Y}}`}</code> - US format (01/22/2026)</p>
                  <p><code className="bg-muted px-1 rounded">{`{{date+1d:Y-m-d}}`}</code> - Tomorrow&apos;s date</p>
                  <p><code className="bg-muted px-1 rounded">{`{{date-1d:Y-m-d}}`}</code> - Yesterday&apos;s date</p>
                  <p><code className="bg-muted px-1 rounded">{`{{time:H_i}}`}</code> - Current time (20_00)</p>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* File Mapping - Only shown for CSV mode */}
      {sourceType === 'csv' && (
        <Card>
          <CardHeader>
            <CardTitle>File Mapping</CardTitle>
            <CardDescription>Configure how to parse the source file</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="delimiter">Delimiter</Label>
                <Controller
                  control={control}
                  name="file_mapping.delimiter"
                  render={({ field }) => (
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger id="delimiter">
                        <SelectValue placeholder="Select delimiter" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value=",">,</SelectItem>
                        <SelectItem value=";">;</SelectItem>
                        <SelectItem value="|">|</SelectItem>
                        <SelectItem value="\t">Tab</SelectItem>
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="enclosure">Enclosure</Label>
                <Controller
                  control={control}
                  name="file_mapping.enclosure"
                  render={({ field }) => (
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger id="enclosure">
                        <SelectValue placeholder="Select enclosure" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value='"'>&quot;</SelectItem>
                        <SelectItem value="'">&apos;</SelectItem>
                        <SelectItem value="none">None</SelectItem>
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="escape">Escape Character</Label>
                <Controller
                  control={control}
                  name="file_mapping.escape"
                  render={({ field }) => (
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger id="escape">
                        <SelectValue placeholder="Select escape" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="\\">\\</SelectItem>
                        <SelectItem value="/">/</SelectItem>
                        <SelectItem value='"'>&quot;</SelectItem>
                        <SelectItem value="none">None</SelectItem>
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="urlColumn">URL Column</Label>
                <Controller
                  control={control}
                  name="file_mapping.url_column"
                  render={({ field }) => (
                    <Select
                      value={field.value}
                      onValueChange={field.onChange}
                    >
                      <SelectTrigger
                        id="urlColumn"
                        className={errors.file_mapping && 'url_column' in (errors.file_mapping || {}) ? 'border-red-500 focus:ring-red-500' : ''}
                      >
                        <SelectValue placeholder="Select URL column" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="default">Default (Auto-detect)</SelectItem>
                        {headers.map((header, index) => (
                          <SelectItem key={index} value={header}>{header}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
