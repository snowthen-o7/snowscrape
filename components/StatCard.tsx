import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@snowforge/ui';
import { cn } from '@snowforge/ui';
import { ArrowUpIcon, ArrowDownIcon, MinusIcon } from 'lucide-react';

export interface StatCardProps {
  title: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon?: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  className?: string;
}

export function StatCard({
  title,
  value,
  change,
  changeLabel,
  icon,
  trend,
  className,
}: StatCardProps) {
  const getTrendIcon = () => {
    if (!trend || trend === 'neutral') {
      return <MinusIcon className="h-4 w-4" />;
    }
    return trend === 'up' ? (
      <ArrowUpIcon className="h-4 w-4" />
    ) : (
      <ArrowDownIcon className="h-4 w-4" />
    );
  };

  const getTrendColor = () => {
    if (!trend || trend === 'neutral') return 'text-muted-foreground';
    return trend === 'up' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400';
  };

  return (
    <Card className={cn('', className)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        {icon && (
          <div className="h-4 w-4 text-muted-foreground">
            {icon}
          </div>
        )}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {(change !== undefined || changeLabel) && (
          <div className={cn('flex items-center gap-1 text-xs mt-1', getTrendColor())}>
            {change !== undefined && (
              <>
                {getTrendIcon()}
                <span className="font-medium">
                  {change > 0 ? '+' : ''}{change}%
                </span>
              </>
            )}
            {changeLabel && (
              <span className="text-muted-foreground ml-1">{changeLabel}</span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
