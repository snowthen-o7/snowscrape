'use client';

import { useFormContext } from 'react-hook-form';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@snowforge/ui';
import { Label } from '@snowforge/ui';
import { Checkbox } from '@snowforge/ui';
import type { JobFormValues } from '@/lib/schemas/jobFormSchema';

const daysOfWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const hours = Array.from({ length: 24 }, (_, i) => i);
const minutes = Array.from({ length: 12 }, (_, i) => i * 5);

export function SchedulingTab() {
  const { watch, setValue } = useFormContext<JobFormValues>();
  const scheduling = watch('scheduling');

  const handleSchedulingChange = (field: 'days' | 'hours' | 'minutes', value: string[] | number[]) => {
    const updated = { ...scheduling };
    if (field === 'days') {
      const daysValue = value as string[];
      updated.days = daysValue.includes('Every Day')
        ? ['Every Day']
        : daysValue.filter((d) => d !== 'Every Day');
    }
    if (field === 'hours') {
      const hoursValue = value as number[];
      updated.hours = hoursValue.includes(24)
        ? [24]
        : hoursValue.filter((h) => h !== 24);
    }
    if (field === 'minutes') {
      updated.minutes = value as number[];
    }
    setValue('scheduling', updated, { shouldDirty: true });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Schedule</CardTitle>
        <CardDescription>Configure when the job should run automatically</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-3">
          <Label>Days</Label>
          <div className="flex flex-wrap gap-2">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="everyDay"
                checked={scheduling.days.includes('Every Day')}
                onCheckedChange={(checked) => {
                  handleSchedulingChange('days', checked ? ['Every Day'] : []);
                }}
              />
              <Label htmlFor="everyDay" className="font-medium">Every Day</Label>
            </div>
            {daysOfWeek.map(day => (
              <div key={day} className="flex items-center space-x-2">
                <Checkbox
                  id={day.toLowerCase()}
                  onCheckedChange={(checked) => {
                    const newDays = checked
                      ? [...scheduling.days, day]
                      : scheduling.days.filter(d => d !== day);
                    handleSchedulingChange('days', newDays);
                  }}
                  checked={scheduling.days.includes(day)}
                  disabled={scheduling.days.includes('Every Day')}
                />
                <Label htmlFor={day.toLowerCase()}>{day.slice(0, 3)}</Label>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          <Label>Hours</Label>
          <div className="flex flex-wrap gap-2">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="everyHour"
                checked={scheduling.hours.includes(24)}
                onCheckedChange={(checked) => {
                  handleSchedulingChange('hours', checked ? [24] : []);
                }}
              />
              <Label htmlFor="everyHour" className="font-medium">Every Hour</Label>
            </div>
            {hours.map(hour => (
              <div key={hour} className="flex items-center space-x-2">
                <Checkbox
                  id={`hour-${hour}`}
                  onCheckedChange={(checked) => {
                    const newHours = checked
                      ? [...scheduling.hours, hour]
                      : scheduling.hours.filter(h => h !== hour);
                    handleSchedulingChange('hours', newHours);
                  }}
                  checked={scheduling.hours.includes(hour)}
                  disabled={scheduling.hours.includes(24)}
                />
                <Label htmlFor={`hour-${hour}`}>{`${hour.toString().padStart(2, '0')}:00`}</Label>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          <Label>Minutes</Label>
          <div className="flex flex-wrap gap-2">
            {minutes.map(minute => (
              <div key={minute} className="flex items-center space-x-2">
                <Checkbox
                  id={`minute-${minute}`}
                  checked={scheduling.minutes.includes(minute)}
                  onCheckedChange={(checked) => {
                    const newMinutes = checked
                      ? [...scheduling.minutes, minute]
                      : scheduling.minutes.filter(m => m !== minute);
                    handleSchedulingChange('minutes', newMinutes);
                  }}
                />
                <Label htmlFor={`minute-${minute}`}>{`:${minute.toString().padStart(2, '0')}`}</Label>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
