/**
 * WebSocket Hook for Real-time Updates
 *
 * Connects to AWS API Gateway WebSocket API with Clerk authentication.
 * Supports channel subscriptions for receiving targeted messages.
 *
 * Usage:
 * const { isConnected, isAuthenticated, messages, subscribe, unsubscribe } = useWebSocket();
 *
 * // Subscribe to a channel (wait for authentication, not just connection)
 * useEffect(() => {
 *   if (isAuthenticated) {
 *     subscribe('scraper:task-id-here');
 *   }
 * }, [isAuthenticated, subscribe]);
 */

import { useAuth } from '@clerk/nextjs';
import { useCallback, useEffect, useRef, useState } from 'react';

export interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export interface UseWebSocketReturn {
  isConnected: boolean;
  isAuthenticated: boolean;
  messages: WebSocketMessage[];
  subscribe: (channel: string) => void;
  unsubscribe: (channel: string) => void;
  clearMessages: () => void;
  connectionError: Error | null;
}

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'wss://p3x9vdmf4h.execute-api.us-east-2.amazonaws.com/dev';
const RECONNECT_DELAY = 3000; // 3 seconds
const MAX_RECONNECT_ATTEMPTS = 5;
const MAX_MESSAGE_BUFFER_SIZE = 100;

export function useWebSocket(autoConnect = true): UseWebSocketReturn {
  const { getToken } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const [connectionError, setConnectionError] = useState<Error | null>(null);

  const ws = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  const subscribedChannels = useRef<Set<string>>(new Set());
  const isAuthenticatedRef = useRef(false);

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

      // Connect WITHOUT the token in the URL to avoid token exposure in logs/history
      console.log('[WebSocket] Connecting to:', WS_URL);
      ws.current = new WebSocket(WS_URL);

      ws.current.onopen = () => {
        console.log('[WebSocket] Connected, authenticating...');
        setIsConnected(true);
        setConnectionError(null);
        reconnectAttempts.current = 0;

        // Send auth token as the first message instead of in the URL
        ws.current?.send(JSON.stringify({
          action: 'authenticate',
          token: token
        }));
      };

      ws.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage;

          // Handle authentication response
          if (message.type === 'auth_success') {
            console.log('[WebSocket] Authenticated successfully');
            isAuthenticatedRef.current = true;
            setIsAuthenticated(true);

            // Now that we are authenticated, resubscribe to all channels
            subscribedChannels.current.forEach(channel => {
              ws.current?.send(JSON.stringify({
                type: 'subscribe',
                channel: channel
              }));
              console.log('[WebSocket] Resubscribed to:', channel);
            });
            return;
          }

          if (message.type === 'auth_error') {
            console.error('[WebSocket] Authentication failed:', message.message);
            isAuthenticatedRef.current = false;
            setIsAuthenticated(false);
            setConnectionError(new Error(`Authentication failed: ${message.message}`));
            ws.current?.close(4001, 'Authentication failed');
            return;
          }

          // Only process other messages after authentication is confirmed
          if (!isAuthenticatedRef.current) {
            console.warn('[WebSocket] Ignoring message before authentication:', message.type);
            return;
          }

          console.log('[WebSocket] Message received:', message.type, message);
          setMessages(prev => {
            const updated = [...prev, message];
            // Cap the buffer to prevent unbounded memory growth
            if (updated.length > MAX_MESSAGE_BUFFER_SIZE) {
              return updated.slice(updated.length - MAX_MESSAGE_BUFFER_SIZE);
            }
            return updated;
          });
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
        isAuthenticatedRef.current = false;
        setIsAuthenticated(false);

        // Attempt to reconnect if not a normal closure, not an auth failure,
        // and under max attempts
        if (
          event.code !== 1000 &&
          event.code !== 4001 &&
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

    if (ws.current && isAuthenticated) {
      ws.current.send(JSON.stringify({
        type: 'subscribe',
        channel: channel
      }));
      console.log('[WebSocket] Subscribed to:', channel);
    } else {
      console.log('[WebSocket] Queued subscription for:', channel);
    }
  }, [isAuthenticated]);

  const unsubscribe = useCallback((channel: string) => {
    subscribedChannels.current.delete(channel);

    if (ws.current && isAuthenticated) {
      ws.current.send(JSON.stringify({
        type: 'unsubscribe',
        channel: channel
      }));
      console.log('[WebSocket] Unsubscribed from:', channel);
    }
  }, [isAuthenticated]);

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
    isAuthenticated,
    messages,
    subscribe,
    unsubscribe,
    clearMessages,
    connectionError
  };
}
