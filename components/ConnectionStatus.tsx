/**
 * Connection Status Indicator
 * Shows WebSocket or polling connection status
 */

'use client';

import { Wifi, WifiOff, RefreshCw } from 'lucide-react';
import {
  Badge,
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@snowforge/ui';

interface ConnectionStatusProps {
  isConnected: boolean;
  isPolling: boolean;
  connectionType: 'websocket' | 'polling' | 'disconnected';
  className?: string;
}

export function ConnectionStatus({
  isConnected,
  isPolling,
  connectionType,
  className = '',
}: ConnectionStatusProps) {
  const getStatusConfig = () => {
    if (connectionType === 'websocket') {
      return {
        icon: <Wifi className="h-3 w-3" />,
        label: 'Real-time',
        variant: 'default' as const,
        color: 'text-green-600 dark:text-green-400',
        description: 'Connected via WebSocket. Updates in real-time.',
      };
    }

    if (connectionType === 'polling') {
      return {
        icon: <RefreshCw className="h-3 w-3" />,
        label: 'Polling',
        variant: 'secondary' as const,
        color: 'text-yellow-600 dark:text-yellow-400',
        description: 'Using polling fallback. Updates every 30 seconds.',
      };
    }

    return {
      icon: <WifiOff className="h-3 w-3" />,
      label: 'Offline',
      variant: 'outline' as const,
      color: 'text-red-600 dark:text-red-400',
      description: 'Not connected. Reconnecting...',
    };
  };

  const config = getStatusConfig();

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge variant={config.variant} className={`gap-1.5 ${className}`}>
            <span className={config.color}>{config.icon}</span>
            <span className="text-xs">{config.label}</span>
          </Badge>
        </TooltipTrigger>
        <TooltipContent>
          <p className="text-sm">{config.description}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
