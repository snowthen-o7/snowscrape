'use client';

import { Controller, useFormContext } from 'react-hook-form';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@snowforge/ui';
import { Input } from '@snowforge/ui';
import { Label } from '@snowforge/ui';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@snowforge/ui';
import { Switch } from '@snowforge/ui';
import type { JobFormValues } from '@/lib/schemas/jobFormSchema';

export function RenderingTab() {
  const { control, watch } = useFormContext<JobFormValues>();
  const renderEnabled = watch('render_config.enabled');

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>JavaScript Rendering</CardTitle>
            <CardDescription>Enable for JavaScript-heavy websites (SPAs)</CardDescription>
          </div>
          <Controller
            control={control}
            name="render_config.enabled"
            render={({ field }) => (
              <Switch
                checked={field.value || false}
                onCheckedChange={field.onChange}
              />
            )}
          />
        </div>
      </CardHeader>
      {renderEnabled && (
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="waitStrategy">Wait Strategy</Label>
              <Controller
                control={control}
                name="render_config.wait_strategy"
                render={({ field }) => (
                  <Select value={field.value || 'networkidle'} onValueChange={field.onChange}>
                    <SelectTrigger id="waitStrategy">
                      <SelectValue placeholder="Select wait strategy" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="load">Load (fastest)</SelectItem>
                      <SelectItem value="domcontentloaded">DOM Content Loaded</SelectItem>
                      <SelectItem value="networkidle">Network Idle (recommended)</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="waitTimeout">Wait Timeout (ms)</Label>
              <Controller
                control={control}
                name="render_config.wait_timeout_ms"
                render={({ field }) => (
                  <Input
                    id="waitTimeout"
                    type="number"
                    min={5000}
                    max={120000}
                    step={1000}
                    value={field.value ?? 30000}
                    onChange={(e) => field.onChange(parseInt(e.target.value))}
                  />
                )}
              />
            </div>
            <div className="md:col-span-2 space-y-2">
              <Label htmlFor="waitForSelector">Wait for Selector (optional)</Label>
              <Controller
                control={control}
                name="render_config.wait_for_selector"
                render={({ field }) => (
                  <Input
                    id="waitForSelector"
                    type="text"
                    placeholder="e.g., .product-list, #content"
                    value={field.value || ''}
                    onChange={(e) => field.onChange(e.target.value || null)}
                  />
                )}
              />
            </div>
            <div className="flex items-center space-x-2">
              <Controller
                control={control}
                name="render_config.capture_screenshot"
                render={({ field }) => (
                  <Switch
                    id="captureScreenshot"
                    checked={field.value || false}
                    onCheckedChange={field.onChange}
                  />
                )}
              />
              <Label htmlFor="captureScreenshot">Capture screenshot</Label>
            </div>
            <div className="flex items-center space-x-2">
              <Controller
                control={control}
                name="render_config.fallback_to_standard"
                render={({ field }) => (
                  <Switch
                    id="fallbackToStandard"
                    checked={field.value !== false}
                    onCheckedChange={field.onChange}
                  />
                )}
              />
              <Label htmlFor="fallbackToStandard">Fallback to standard requests</Label>
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  );
}
