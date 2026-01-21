/**
 * React Hook for Real-time Job Updates
 * Uses WebSocket with polling fallback
 */

'use client';

import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@clerk/nextjs';
import { getRealtimeClient, cleanupRealtimeClient } from '@/lib/websocket';
import { Job } from '@/lib/types';

interface UseRealtimeJobsOptions {
  enabled?: boolean;
  jobId?: string; // Subscribe to specific job
}

interface RealtimeStatus {
  isConnected: boolean;
  isPolling: boolean;
  connectionType: 'websocket' | 'polling' | 'disconnected';
}

export function useRealtimeJobs(options: UseRealtimeJobsOptions = {}) {
  const { enabled = true, jobId } = options;
  const { getToken } = useAuth();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [status, setStatus] = useState<RealtimeStatus>({
    isConnected: false,
    isPolling: false,
    connectionType: 'disconnected',
  });

  // Initialize realtime client
  useEffect(() => {
    if (!enabled) return;

    let mounted = true;

    const init = async () => {
      try {
        const token = await getToken();
        if (!token || !mounted) return;

        // Get or create realtime client
        const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';
        const client = getRealtimeClient({
          url: wsUrl,
          token,
          pollingInterval: 30000,
          reconnectInterval: 5000,
          maxReconnectAttempts: 3,
        });

        // Connection handlers
        const unsubConnection = client.onConnection(() => {
          if (!mounted) return;
          setStatus({
            isConnected: true,
            isPolling: false,
            connectionType: 'websocket',
          });
        });

        const unsubDisconnection = client.onDisconnection(() => {
          if (!mounted) return;
          setStatus({
            isConnected: false,
            isPolling: client.isUsingPolling(),
            connectionType: client.isUsingPolling() ? 'polling' : 'disconnected',
          });
        });

        // Message handler
        const unsubMessage = client.onMessage((message) => {
          if (!mounted) return;

          if (message.type === 'jobs:update') {
            setJobs(message.data);
          } else if (message.type === 'job:status' && message.data) {
            // Update specific job
            setJobs((prevJobs) =>
              prevJobs.map((job) =>
                job.job_id === message.data.job_id ? { ...job, ...message.data } : job
              )
            );
          } else if (message.type === 'job:created' && message.data) {
            // Add new job
            setJobs((prevJobs) => [message.data, ...prevJobs]);
          } else if (message.type === 'job:deleted' && message.data?.job_id) {
            // Remove job
            setJobs((prevJobs) => prevJobs.filter((job) => job.job_id !== message.data.job_id));
          }

          // Update status
          setStatus({
            isConnected: client.isConnected(),
            isPolling: client.isUsingPolling(),
            connectionType: client.isConnected()
              ? 'websocket'
              : client.isUsingPolling()
              ? 'polling'
              : 'disconnected',
          });
        });

        // Connect
        client.connect();

        // Subscribe to updates
        if (jobId) {
          client.subscribeToJob(jobId);
        } else {
          client.subscribeToAllJobs();
        }

        // Cleanup
        return () => {
          unsubConnection();
          unsubDisconnection();
          unsubMessage();
          if (jobId) {
            client.unsubscribeFromJob(jobId);
          }
        };
      } catch (error) {
        console.error('[useRealtimeJobs] Initialization error:', error);
      }
    };

    init();

    return () => {
      mounted = false;
    };
  }, [enabled, jobId, getToken]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (!enabled) {
        cleanupRealtimeClient();
      }
    };
  }, [enabled]);

  // Manual refresh (useful for polling mode)
  const refresh = useCallback(async () => {
    try {
      const token = await getToken();
      if (!token) return;

      const response = await fetch('/api/jobs', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setJobs(data);
      }
    } catch (error) {
      console.error('[useRealtimeJobs] Refresh error:', error);
    }
  }, [getToken]);

  return {
    jobs,
    status,
    refresh,
  };
}

/**
 * Hook for real-time updates of a specific job
 */
export function useRealtimeJob(jobId: string | undefined, options: { enabled?: boolean } = {}) {
  const { enabled = true } = options;
  const { jobs, status, refresh } = useRealtimeJobs({
    enabled: enabled && !!jobId,
    jobId,
  });

  const job = jobs.find((j) => j.job_id === jobId) || null;

  return {
    job,
    status,
    refresh,
  };
}
