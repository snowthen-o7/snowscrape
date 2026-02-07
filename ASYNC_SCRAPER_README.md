# Async Scraper with WebSocket Updates

Complete implementation of async scraping pattern to handle sites that exceed API Gateway's 30-second timeout limit.

## ✅ Backend Implementation (COMPLETE)

### Architecture

```
Client (Frontend)
    ↓ POST /scraper/preview/async
    ↓ (returns immediately: 202 Accepted + task_id)
Lambda Start Handler (10s timeout)
    ↓ InvokeAsync
Lambda Worker (120s timeout)
    ↓ sends progress updates
WebSocket API
    ↓ broadcasts to client
Client receives real-time updates
```

### Deployed Endpoints

**Async Scraper:**
- `POST https://68i4rosq00.execute-api.us-east-2.amazonaws.com/dev/scraper/preview/async`
  - Returns: `{ task_id, status: "started", websocket_channel, websocket_url }`
  - Status Code: 202 Accepted

**WebSocket:**
- `wss://p3x9vdmf4h.execute-api.us-east-2.amazonaws.com/dev`
  - Connect with `?token=<clerk_jwt>`
  - Subscribe to channel: `scraper:{task_id}`

### Lambda Functions

1. **scraperPreviewAsyncStart** (186 kB, 10s timeout)
   - Handler: `handler.scraper_preview_async_start_handler`
   - Validates auth, generates task_id
   - Invokes worker Lambda asynchronously
   - Returns immediately

2. **scraperPreviewAsyncWorker** (186 kB, 120s timeout)
   - Handler: `handler.scraper_preview_async_worker_handler`
   - Performs actual scraping with tier escalation
   - Sends WebSocket updates during process
   - No HTTP endpoint (invoked directly)

### WebSocket Message Types

**Progress Update:**
```json
{
  "type": "scraper:progress",
  "task_id": "uuid",
  "status": "starting" | "escalating" | "escalated",
  "message": "Starting scrape for https://...",
  "tier": 1,
  "tier_name": "Lightweight" | "IP Rotation",
  "cost_per_page": 0.0001,
  "escalation_log": ["..."]
}
```

**Completion:**
```json
{
  "type": "scraper:complete",
  "task_id": "uuid",
  "status": "completed",
  "data": {
    "url": "https://...",
    "title": "Page Title",
    "elements": [...],
    "tier_info": {
      "tier_used": 2,
      "tier_name": "IP Rotation",
      "cost_per_page": 0.005,
      "escalation_log": [...]
    }
  }
}
```

**Error:**
```json
{
  "type": "scraper:error",
  "task_id": "uuid",
  "status": "failed",
  "error": "Error message"
}
```

### Code Structure

**`scraper_preview_async.py`** (NEW)
```python
# Main functions:
- start_async_scrape(user_id, url, min_tier, max_tier)
  → Returns task_id immediately
  → Invokes worker Lambda async

- scrape_with_websocket_updates(task_id, user_id, url, ...)
  → Worker function (runs in separate Lambda)
  → Sends WS updates during scraping
  → Uses tiered_scraper.smart_scrape()

- invoke_scraper_async(user_id, url, task_id, ...)
  → Invokes worker Lambda with Event invocation type
```

**`handler.py`** (MODIFIED)
```python
# Added handlers:
- scraper_preview_async_start_handler(event, context)
  → API Gateway endpoint
  → Auth validation
  → Calls start_async_scrape()

- scraper_preview_async_worker_handler(event, context)
  → Worker Lambda (direct invocation)
  → Calls scrape_with_websocket_updates()
  → Error handling with WS notifications
```

**`serverless.yml`** (MODIFIED)
```yaml
# Added functions:
  scraperPreviewAsyncStart:
    handler: handler.scraper_preview_async_start_handler
    timeout: 10
    events: [http: POST /scraper/preview/async]

  scraperPreviewAsyncWorker:
    handler: handler.scraper_preview_async_worker_handler
    timeout: 120
    # No HTTP event - invoked directly

# Added IAM permissions:
  - Effect: Allow
    Action: [lambda:InvokeFunction, lambda:InvokeAsync]
    Resource: arn:aws:lambda:...:snowscrape-scraper-preview-async-worker
```

## ⏳ Frontend Implementation (TODO)

### Required Changes

**1. WebSocket Connection Hook** (`lib/useWebSocket.ts`)
```typescript
import { useAuth } from '@clerk/nextjs';
import { useEffect, useRef, useState } from 'react';

export function useWebSocket(channel?: string) {
  const { getToken } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<any[]>([]);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    const connectWebSocket = async () => {
      const token = await getToken();
      const wsUrl = `wss://p3x9vdmf4h.execute-api.us-east-2.amazonaws.com/dev?token=${token}`;

      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        setIsConnected(true);

        // Subscribe to channel if provided
        if (channel) {
          ws.current?.send(JSON.stringify({
            type: 'subscribe',
            channel: channel
          }));
        }
      };

      ws.current.onmessage = (event) => {
        const message = JSON.parse(event.data);
        setMessages(prev => [...prev, message]);
      };

      ws.current.onclose = () => {
        setIsConnected(false);
      };
    };

    connectWebSocket();

    return () => {
      ws.current?.close();
    };
  }, [channel, getToken]);

  return { isConnected, messages };
}
```

**2. Update Visual Builder** (`app/(application)/dashboard/jobs/new/visual/page.tsx`)

Add async scraper call:
```typescript
// Add state for async task
const [asyncTaskId, setAsyncTaskId] = useState<string | null>(null);
const [isAsyncLoading, setIsAsyncLoading] = useState(false);

// WebSocket hook (only when async task is running)
const { isConnected, messages } = useWebSocket(
  asyncTaskId ? `scraper:${asyncTaskId}` : undefined
);

// Handle WebSocket messages
useEffect(() => {
  if (!asyncTaskId) return;

  for (const message of messages) {
    if (message.task_id !== asyncTaskId) continue;

    switch (message.type) {
      case 'scraper:progress':
        toast.info(`${message.message} (Tier ${message.tier})`);
        break;

      case 'scraper:complete':
        // Same as sync success handler
        setPageStructure(message.data);
        setPageLoaded(true);
        setIsAsyncLoading(false);
        setAsyncTaskId(null);
        toast.success(`Loaded ${message.data.elements.length} elements using ${message.data.tier_info.tier_name}`);
        break;

      case 'scraper:error':
        setIsAsyncLoading(false);
        setAsyncTaskId(null);
        toast.error(`Failed to load page: ${message.error}`);
        break;
    }
  }
}, [messages, asyncTaskId]);

// Modify handleLoadPage to use async endpoint
const handleLoadPage = async () => {
  if (!url) {
    toast.error('Please enter a URL');
    return;
  }

  setLoading(true);
  setPageLoaded(false);

  try {
    // Try sync first
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/scraper/preview`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${await getToken()}`
        },
        body: JSON.stringify({ url })
      }
    );

    if (response.ok) {
      // Sync succeeded
      const result = await response.json();
      setPageStructure(result);
      setPageLoaded(true);
      // ... existing success handling
    } else {
      // Sync failed - try async
      const asyncResponse = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/scraper/preview/async`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${await getToken()}`
          },
          body: JSON.dumps({ url })
        }
      );

      if (asyncResponse.ok) {
        const { task_id, message } = await asyncResponse.json();
        setAsyncTaskId(task_id);
        setIsAsyncLoading(true);
        toast.info(message);
      } else {
        throw new Error('Both sync and async scraping failed');
      }
    }
  } catch (error) {
    console.error('Error loading page:', error);
    toast.error('Failed to load page');
  } finally {
    setLoading(false);
  }
};
```

**3. Loading State UI**
```tsx
{isAsyncLoading && (
  <Card className="border-blue-500 bg-blue-900/10">
    <CardContent className="pt-6">
      <div className="flex items-center gap-3">
        <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
        <div>
          <p className="font-medium text-blue-300">Scraping in progress...</p>
          <p className="text-sm text-muted-foreground">
            This site is taking longer than usual. You'll receive updates in real-time.
          </p>
          {!isConnected && (
            <p className="text-xs text-yellow-400 mt-1">
              Connecting to WebSocket...
            </p>
          )}
        </div>
      </div>
    </CardContent>
  </Card>
)}
```

## Testing

### Test Async Scraper (Backend Only)

```bash
# Get Clerk token
TOKEN="your_clerk_jwt_token"

# Start async scrape
curl -X POST https://68i4rosq00.execute-api.us-east-2.amazonaws.com/dev/scraper/preview/async \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"url": "https://www.bestbuy.com/"}'

# Response (immediate):
{
  "task_id": "uuid-here",
  "status": "started",
  "url": "https://www.bestbuy.com/",
  "message": "Scrape started. Connect to WebSocket...",
  "websocket_channel": "scraper:uuid-here",
  "websocket_url": "wss://p3x9vdmf4h.execute-api.us-east-2.amazonaws.com/dev"
}
```

### Test WebSocket (wscat)

```bash
# Install wscat
npm install -g wscat

# Connect with token
wscat -c "wss://p3x9vdmf4h.execute-api.us-east-2.amazonaws.com/dev?token=YOUR_TOKEN"

# Subscribe to channel
> {"type": "subscribe", "channel": "scraper:uuid-here"}

# Wait for messages...
< {"type": "scraper:progress", ...}
< {"type": "scraper:complete", ...}
```

## Use Cases

### When to Use Async vs Sync

**Use Sync (`/scraper/preview`):**
- Forever21, Target, most sites
- Expected response time < 20 seconds
- Tier 1 or quick Tier 2

**Use Async (`/scraper/preview/async`):**
- Best Buy, slow-loading sites
- Sites requiring Tier 2+ with heavy content
- Sites that previously timed out
- Future: All Tier 3 (browser mode) requests

### Smart Fallback Pattern

Recommended frontend pattern:
1. Try sync endpoint first
2. If timeout (30s) or 504 error → fallback to async
3. Connect WebSocket for progress updates
4. Same UI for both paths (seamless to user)

## Future Enhancements

1. **Retry Logic**: Automatic retry on worker failure
2. **Task Status API**: GET `/scraper/task/{task_id}` for polling fallback
3. **Task Cancellation**: DELETE `/scraper/task/{task_id}` to cancel running job
4. **Rate Limiting**: Per-user concurrent task limits
5. **Progress Percentage**: More granular progress updates (10%, 50%, 90%)
6. **Task History**: Store completed tasks in DynamoDB for retrieval

## Cost Implications

**Sync Scraper:**
- Lambda: 1 invocation × memory × duration
- API Gateway: 1 request

**Async Scraper:**
- Lambda Start: 1 invocation × 256MB × ~1s = $0.000002
- Lambda Worker: 1 invocation × 512MB × 30-120s = $0.00001-0.00004
- API Gateway: 1 request = $0.0000035
- WebSocket: connections + messages (minimal cost)

**Total overhead: ~$0.00005 per async scrape** (negligible compared to Tier 2+ costs)

## Monitoring

**CloudWatch Logs:**
- `snowscrape-scraper-preview-async-start`: Start handler logs
- `snowscrape-scraper-preview-async-worker`: Worker execution logs

**Metrics to Watch:**
- Worker duration (should be < 120s)
- Worker success rate
- WebSocket message delivery rate
- Concurrent async tasks

## Summary

✅ **Backend: 100% Complete**
- Async endpoint deployed
- Worker Lambda with 120s timeout
- WebSocket integration ready
- Tier escalation supported
- Error handling with WS notifications

⏳ **Frontend: Needs Implementation**
- WebSocket hook
- Async API call integration
- Loading state UI
- Message handling

**Estimated Frontend Work: 2-3 hours**
