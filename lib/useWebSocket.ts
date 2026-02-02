/**
 * WebSocket Hook for Real-time Updates
 *
 * Connects to AWS API Gateway WebSocket API with Clerk authentication.
 * Supports channel subscriptions for receiving targeted messages.
 *
 * Usage:
 * const { isConnected, messages, subscribe, unsubscribe } = useWebSocket();
 *
 * // Subscribe to a channel
 * useEffect(() => {
 *   if (isConnected) {
 *     subscribe('scraper:task-id-here');
 *   }
 * }, [isConnected, subscribe]);
 */

import { useAuth } from '@clerk/nextjs';
import { useCallback, useEffect, useRef, useState } from 'react';

export interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export interface UseWebSocketReturn {
  isConnected: boolean;
  messages: WebSocketMessage[];
  subscribe: (channel: string) => void;
  unsubscribe: (channel: string) => void;
  clearMessages: () => void;
  connectionError: Error | null;
}

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'wss://p3x9vdmf4h.execute-api.us-east-2.amazonaws.com/dev';
const RECONNECT_DELAY = 3000; // 3 seconds
const MAX_RECONNECT_ATTEMPTS = 5;

export function useWebSocket(autoConnect = true): UseWebSocketReturn {
  const { getToken } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const [connectionError, setConnectionError] = useState<Error | null>(null);

  const ws = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  const subscribedChannels = useRef<Set<string>>(new Set());

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  const connectWebSocket = useCallback(async () => {
    try {
      const token = await getToken();

      if (!token) {
        console.warn('[WebSocket] No auth token available, skipping connection');
        return;
      }

      // Close existing connection if any
      if (ws.current) {
        ws.current.close();
      }

      const wsUrl = `${WS_URL}?token=${token}`;
      console.log('[WebSocket] Connecting to:', WS_URL);

      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log('[WebSocket] Connected successfully');
        setIsConnected(true);
        setConnectionError(null);
        reconnectAttempts.current = 0;

        // Resubscribe to all channels
        subscribedChannels.current.forEach(channel => {
          ws.current?.send(JSON.stringify({
            type: 'subscribe',
            channel: channel
          }));
          console.log('[WebSocket] Resubscribed to:', channel);
        });
      };

      ws.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage;
          console.log('[WebSocket] Message received:', message.type, message);
          setMessages(prev => [...prev, message]);
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error);
        }
      };

      ws.current.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
        setConnectionError(new Error('WebSocket connection error'));
      };

      ws.current.onclose = (event) => {
        console.log('[WebSocket] Disconnected:', event.code, event.reason);
        setIsConnected(false);

        // Attempt to reconnect if not a normal closure and under max attempts
        if (
          event.code !== 1000 &&
          reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS &&
          autoConnect
        ) {
          reconnectAttempts.current += 1;
          console.log(
            `[WebSocket] Reconnecting (attempt ${reconnectAttempts.current}/${MAX_RECONNECT_ATTEMPTS})...`
          );

          reconnectTimeout.current = setTimeout(() => {
            connectWebSocket();
          }, RECONNECT_DELAY);
        } else if (reconnectAttempts.current >= MAX_RECONNECT_ATTEMPTS) {
          console.error('[WebSocket] Max reconnection attempts reached');
          setConnectionError(new Error('Failed to connect after multiple attempts'));
        }
      };

    } catch (error) {
      console.error('[WebSocket] Connection failed:', error);
      setConnectionError(error as Error);
    }
  }, [getToken, autoConnect]);

  const subscribe = useCallback((channel: string) => {
    if (!channel) {
      console.warn('[WebSocket] Cannot subscribe to empty channel');
      return;
    }

    subscribedChannels.current.add(channel);

    if (ws.current && isConnected) {
      ws.current.send(JSON.stringify({
        type: 'subscribe',
        channel: channel
      }));
      console.log('[WebSocket] Subscribed to:', channel);
    } else {
      console.log('[WebSocket] Queued subscription for:', channel);
    }
  }, [isConnected]);

  const unsubscribe = useCallback((channel: string) => {
    subscribedChannels.current.delete(channel);

    if (ws.current && isConnected) {
      ws.current.send(JSON.stringify({
        type: 'unsubscribe',
        channel: channel
      }));
      console.log('[WebSocket] Unsubscribed from:', channel);
    }
  }, [isConnected]);

  // Connect on mount
  useEffect(() => {
    if (autoConnect) {
      connectWebSocket();
    }

    // Cleanup on unmount
    return () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      if (ws.current) {
        ws.current.close(1000, 'Component unmounted');
      }
    };
  }, [connectWebSocket, autoConnect]);

  return {
    isConnected,
    messages,
    subscribe,
    unsubscribe,
    clearMessages,
    connectionError
  };
}
