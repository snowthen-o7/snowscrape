'use client';

import { Controller, useFormContext } from 'react-hook-form';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@snowforge/ui';
import { Input } from '@snowforge/ui';
import { Label } from '@snowforge/ui';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@snowforge/ui';
import { Switch } from '@snowforge/ui';
import type { JobFormValues } from '@/lib/schemas/jobFormSchema';

export function ProxyTab() {
  const { control, watch, setValue } = useFormContext<JobFormValues>();
  const proxyEnabled = watch('proxy_config.enabled');

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Proxy Configuration</CardTitle>
            <CardDescription>Configure proxy rotation for avoiding rate limits</CardDescription>
          </div>
          <Controller
            control={control}
            name="proxy_config.enabled"
            render={({ field }) => (
              <Switch
                checked={field.value || false}
                onCheckedChange={field.onChange}
              />
            )}
          />
        </div>
      </CardHeader>
      {proxyEnabled && (
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="geoTargeting">Geo-Targeting</Label>
              <Controller
                control={control}
                name="proxy_config.geo_targeting"
                render={({ field }) => (
                  <Select value={field.value || 'any'} onValueChange={field.onChange}>
                    <SelectTrigger id="geoTargeting">
                      <SelectValue placeholder="Select region" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="any">Any Region</SelectItem>
                      <SelectItem value="us">United States</SelectItem>
                      <SelectItem value="eu">Europe</SelectItem>
                      <SelectItem value="as">Asia</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="rotationStrategy">Rotation Strategy</Label>
              <Controller
                control={control}
                name="proxy_config.rotation_strategy"
                render={({ field }) => (
                  <Select value={field.value || 'random'} onValueChange={field.onChange}>
                    <SelectTrigger id="rotationStrategy">
                      <SelectValue placeholder="Select strategy" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="random">Random</SelectItem>
                      <SelectItem value="round-robin">Round Robin</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="maxRetries">Max Retries</Label>
              <Controller
                control={control}
                name="proxy_config.max_retries"
                render={({ field }) => (
                  <Input
                    id="maxRetries"
                    type="number"
                    min={1}
                    max={10}
                    value={field.value ?? 3}
                    onChange={(e) => field.onChange(parseInt(e.target.value))}
                  />
                )}
              />
            </div>
            <div className="flex items-center space-x-2 pt-6">
              <Controller
                control={control}
                name="proxy_config.fallback_to_direct"
                render={({ field }) => (
                  <Switch
                    id="fallbackToDirect"
                    checked={field.value !== false}
                    onCheckedChange={field.onChange}
                  />
                )}
              />
              <Label htmlFor="fallbackToDirect">Fallback to direct connection</Label>
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  );
}
