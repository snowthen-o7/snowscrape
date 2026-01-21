/**
 * WebSocket Client
 * Real-time updates with automatic fallback to polling
 */

type MessageHandler = (data: any) => void;
type ConnectionHandler = () => void;

interface WebSocketConfig {
  url: string;
  token: string;
  pollingInterval?: number;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export class RealtimeClient {
  private ws: WebSocket | null = null;
  private config: WebSocketConfig;
  private messageHandlers: Set<MessageHandler> = new Set();
  private connectionHandlers: Set<ConnectionHandler> = new Set();
  private disconnectionHandlers: Set<ConnectionHandler> = new Set();
  private reconnectAttempts = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private pollingTimer: NodeJS.Timeout | null = null;
  private isPolling = false;
  private lastPollData: any = null;

  constructor(config: WebSocketConfig) {
    this.config = {
      pollingInterval: 30000, // 30 seconds
      reconnectInterval: 5000, // 5 seconds
      maxReconnectAttempts: 5,
      ...config,
    };
  }

  /**
   * Connect to WebSocket server
   * Falls back to polling if WebSocket is unavailable
   */
  connect() {
    // Try WebSocket first
    try {
      this.ws = new WebSocket(this.config.url);

      this.ws.onopen = () => {
        console.log('[WebSocket] Connected');
        this.reconnectAttempts = 0;
        this.stopPolling();

        // Send authentication
        this.send({
          type: 'auth',
          token: this.config.token,
        });

        this.connectionHandlers.forEach((handler) => handler());
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.messageHandlers.forEach((handler) => handler(data));
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
      };

      this.ws.onclose = () => {
        console.log('[WebSocket] Disconnected');
        this.disconnectionHandlers.forEach((handler) => handler());
        this.handleDisconnection();
      };
    } catch (error) {
      console.error('[WebSocket] Failed to connect:', error);
      this.startPolling();
    }
  }

  /**
   * Send message through WebSocket
   */
  send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('[WebSocket] Cannot send message: not connected');
    }
  }

  /**
   * Subscribe to job updates
   */
  subscribeToJob(jobId: string) {
    this.send({
      type: 'subscribe',
      channel: `job:${jobId}`,
    });
  }

  /**
   * Unsubscribe from job updates
   */
  unsubscribeFromJob(jobId: string) {
    this.send({
      type: 'unsubscribe',
      channel: `job:${jobId}`,
    });
  }

  /**
   * Subscribe to all jobs updates
   */
  subscribeToAllJobs() {
    this.send({
      type: 'subscribe',
      channel: 'jobs:all',
    });
  }

  /**
   * Register message handler
   */
  onMessage(handler: MessageHandler) {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  /**
   * Register connection handler
   */
  onConnection(handler: ConnectionHandler) {
    this.connectionHandlers.add(handler);
    return () => this.connectionHandlers.delete(handler);
  }

  /**
   * Register disconnection handler
   */
  onDisconnection(handler: ConnectionHandler) {
    this.disconnectionHandlers.add(handler);
    return () => this.disconnectionHandlers.delete(handler);
  }

  /**
   * Handle disconnection and attempt reconnection
   */
  private handleDisconnection() {
    if (this.reconnectAttempts < this.config.maxReconnectAttempts!) {
      console.log(
        `[WebSocket] Attempting reconnection (${this.reconnectAttempts + 1}/${
          this.config.maxReconnectAttempts
        })`
      );

      this.reconnectTimer = setTimeout(() => {
        this.reconnectAttempts++;
        this.connect();
      }, this.config.reconnectInterval);
    } else {
      console.log('[WebSocket] Max reconnection attempts reached, falling back to polling');
      this.startPolling();
    }
  }

  /**
   * Start polling as fallback
   */
  private startPolling() {
    if (this.isPolling) return;

    console.log('[Polling] Starting with interval:', this.config.pollingInterval);
    this.isPolling = true;

    const poll = async () => {
      try {
        // Fetch jobs data via REST API
        const response = await fetch('/api/jobs', {
          headers: {
            Authorization: `Bearer ${this.config.token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();

          // Check if data changed
          if (JSON.stringify(data) !== JSON.stringify(this.lastPollData)) {
            this.lastPollData = data;

            // Emit as message
            this.messageHandlers.forEach((handler) =>
              handler({
                type: 'jobs:update',
                data,
              })
            );
          }
        }
      } catch (error) {
        console.error('[Polling] Error:', error);
      }

      if (this.isPolling) {
        this.pollingTimer = setTimeout(poll, this.config.pollingInterval);
      }
    };

    poll();
  }

  /**
   * Stop polling
   */
  private stopPolling() {
    if (this.pollingTimer) {
      clearTimeout(this.pollingTimer);
      this.pollingTimer = null;
    }
    this.isPolling = false;
  }

  /**
   * Disconnect and cleanup
   */
  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    this.stopPolling();

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.messageHandlers.clear();
    this.connectionHandlers.clear();
    this.disconnectionHandlers.clear();
  }

  /**
   * Check if connected via WebSocket
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * Check if using polling fallback
   */
  isUsingPolling(): boolean {
    return this.isPolling;
  }
}

// Singleton instance
let realtimeClient: RealtimeClient | null = null;

/**
 * Get or create realtime client instance
 */
export function getRealtimeClient(config?: WebSocketConfig): RealtimeClient {
  if (!realtimeClient && config) {
    realtimeClient = new RealtimeClient(config);
  }

  if (!realtimeClient) {
    throw new Error('RealtimeClient not initialized. Pass config on first call.');
  }

  return realtimeClient;
}

/**
 * Cleanup realtime client
 */
export function cleanupRealtimeClient() {
  if (realtimeClient) {
    realtimeClient.disconnect();
    realtimeClient = null;
  }
}
