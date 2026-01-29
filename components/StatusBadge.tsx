import React from 'react';
import { Badge } from '@snowforge/ui';
import { cn } from '@snowforge/ui';
import {
  PlayIcon,
  CheckCircle2Icon,
  XCircleIcon,
  PauseIcon,
  ClockIcon,
} from 'lucide-react';

export type JobStatus = 'running' | 'success' | 'failed' | 'paused' | 'scheduled';

export interface StatusBadgeProps {
  status: JobStatus;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  className?: string;
}

const statusConfig: Record<
  JobStatus,
  {
    label: string;
    icon: React.ElementType;
    className: string;
  }
> = {
  running: {
    label: 'Running',
    icon: PlayIcon,
    className: 'status-running',
  },
  success: {
    label: 'Success',
    icon: CheckCircle2Icon,
    className: 'status-success',
  },
  failed: {
    label: 'Failed',
    icon: XCircleIcon,
    className: 'status-failed',
  },
  paused: {
    label: 'Paused',
    icon: PauseIcon,
    className: 'status-paused',
  },
  scheduled: {
    label: 'Scheduled',
    icon: ClockIcon,
    className: 'status-scheduled',
  },
};

export function StatusBadge({
  status,
  size = 'md',
  showIcon = true,
  className,
}: StatusBadgeProps) {
  const config = statusConfig[status];
  const Icon = config.icon;

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-2.5 py-1',
    lg: 'text-base px-3 py-1.5',
  };

  const iconSizes = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5',
  };

  return (
    <Badge
      variant="outline"
      className={cn(
        'rounded-full font-medium inline-flex items-center gap-1.5',
        config.className,
        sizeClasses[size],
        className
      )}
    >
      {showIcon && <Icon className={iconSizes[size]} />}
      <span>{config.label}</span>
    </Badge>
  );
}
