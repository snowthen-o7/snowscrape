# API Client Documentation

Centralized API client for all backend communication with the SnowScrape API.

## Architecture

The API client is organized into domain-specific modules:

```
lib/api/
├── client.ts      # Base APIClient class with auth & error handling
├── jobs.ts        # Jobs API (CRUD, pause, resume, run, results)
├── templates.ts   # Templates API (CRUD, public templates)
├── webhooks.ts    # Webhooks API (CRUD, test, deliveries)
├── analytics.ts   # Analytics API (usage, cost, performance)
└── index.ts       # Unified exports
```

## Base Client (`client.ts`)

### APIClient

Base client class handling authentication, request formatting, and error handling.

```tsx
import { apiClient } from '@/lib/api/client';

// All requests require a Clerk session token
const token = await session.getToken();

const response = await apiClient.request<ResponseType>(
  '/endpoint',
  token,
  {
    method: 'POST',
    body: JSON.stringify(data)
  }
);
```

#### Methods

**`request<T>(endpoint, token, options): Promise<T>`**
- Makes authenticated API request
- Automatically adds `Authorization` header with Bearer token
- Handles JSON parsing and error responses
- Throws `APIError` on failure

**`get<T>(endpoint, token): Promise<T>`**
- Convenience method for GET requests

**`post<T>(endpoint, token, data?): Promise<T>`**
- Convenience method for POST requests
- Automatically serializes data to JSON

**`put<T>(endpoint, token, data?): Promise<T>`**
- Convenience method for PUT requests

**`delete<T>(endpoint, token): Promise<T>`**
- Convenience method for DELETE requests

### APIError

Custom error class for API errors:

```tsx
try {
  await apiClient.get('/endpoint', token);
} catch (error) {
  if (error instanceof APIError) {
    console.error(`API Error ${error.status}: ${error.message}`);
    console.error('Data:', error.data);
  }
}
```

**Properties:**
- `status: number` - HTTP status code (0 for network errors)
- `message: string` - Error message
- `data?: any` - Additional error data from API response

## Jobs API (`jobs.ts`)

Manage scraping jobs (create, update, delete, pause, resume, run, results).

### Usage with React Query

```tsx
import { jobsAPI } from '@/lib/api';
import { useSession } from '@clerk/nextjs';

const { session } = useSession();
const token = await session?.getToken();

// List all jobs
const jobs = await jobsAPI.list(token);

// Get single job
const job = await jobsAPI.get('job-123', token);

// Create job
const newJob = await jobsAPI.create({
  name: 'My Job',
  source: 'https://example.com/data.csv',
  queries: [
    { name: 'title', type: 'xpath', query: '//h1', join: false }
  ],
  rate_limit: 1,
  scheduling: { days: [1,2,3,4,5], hours: [9], minutes: [0] }
}, token);

// Update job
const updatedJob = await jobsAPI.update('job-123', {
  name: 'Updated Name',
  rate_limit: 2
}, token);

// Delete job
await jobsAPI.delete('job-123', token);

// Pause job
const pausedJob = await jobsAPI.pause('job-123', token);

// Resume job
const resumedJob = await jobsAPI.resume('job-123', token);

// Run job immediately
const runningJob = await jobsAPI.run('job-123', token);

// Get job results
const results = await jobsAPI.results('job-123', token, 100);

// Download results
const downloadData = await jobsAPI.download('job-123', 'json', token);
```

### DTOs

**CreateJobDTO:**
```tsx
interface CreateJobDTO {
  name: string;
  source: string;              // URL to CSV file or single URL
  rate_limit?: number;          // Requests per second (default: 1)
  queries: Array<{
    name: string;               // Field name
    type: 'xpath' | 'regex' | 'jsonpath';
    query: string;              // Extraction query
    join?: boolean;             // Join multiple results
  }>;
  scheduling?: {
    days: number[];             // 0-6 (Sun-Sat)
    hours: number[];            // 0-23
    minutes: number[];          // 0-59
  };
  file_mapping?: {
    delimiter: string;          // CSV delimiter
    enclosure: string;
    escape: string;
    url_column: string;         // Column name with URLs
  };
  proxy_config?: {
    enabled: boolean;
    geo_targeting?: string;     // 'any', 'US', 'EU', etc.
    rotation_strategy?: string; // 'random', 'round-robin'
    max_retries?: number;
    fallback_to_direct?: boolean;
  };
  render_config?: {
    enabled: boolean;
    wait_strategy?: string;     // 'networkidle', 'domcontentloaded'
    wait_timeout_ms?: number;
    wait_for_selector?: string | null;
    capture_screenshot?: boolean;
    screenshot_full_page?: boolean;
    block_resources?: string[]; // ['image', 'stylesheet', 'font']
    fallback_to_standard?: boolean;
  };
}
```

**UpdateJobDTO:**
```tsx
type UpdateJobDTO = Partial<CreateJobDTO>;
```

All fields optional - only include fields to update.

### API Methods

| Method | Endpoint | Description |
|--------|----------|-------------|
| `list(token)` | `GET /jobs/status` | List all jobs |
| `get(id, token)` | `GET /jobs/{id}` | Get single job |
| `create(data, token)` | `POST /jobs` | Create new job |
| `update(id, data, token)` | `PUT /jobs/{id}` | Update job |
| `delete(id, token)` | `DELETE /jobs/{id}` | Delete job |
| `pause(id, token)` | `PATCH /jobs/{id}/pause` | Pause job |
| `resume(id, token)` | `PATCH /jobs/{id}/resume` | Resume job |
| `run(id, token)` | `POST /jobs/{id}/run` | Run job immediately |
| `download(id, format, token)` | `GET /jobs/{id}/download` | Download results |
| `history(id, token)` | `GET /jobs/{id}/history` | Get run history |
| `results(id, token, limit?)` | `GET /jobs/{id}/results` | Get job results |

## Templates API (`templates.ts`)

Manage job templates for quick job creation.

### Usage

```tsx
import { templatesAPI } from '@/lib/api';

// List all templates (user + public)
const templates = await templatesAPI.list(token);

// List public templates only
const publicTemplates = await templatesAPI.listPublic(token);

// Get single template
const template = await templatesAPI.get('template-123', token);

// Create template
const newTemplate = await templatesAPI.create({
  name: 'Amazon Product Scraper',
  description: 'Scrape product data from Amazon',
  category: 'ecommerce',
  is_public: false,
  config: {
    queries: [
      { name: 'title', type: 'xpath', query: '//h1', join: false },
      { name: 'price', type: 'xpath', query: '//span[@class="price"]', join: false }
    ],
    rate_limit: 1
  }
}, token);

// Update template
const updatedTemplate = await templatesAPI.update('template-123', {
  description: 'Updated description'
}, token);

// Delete template
await templatesAPI.delete('template-123', token);

// Use template to create job
const job = await templatesAPI.use('template-123', {
  name: 'My Amazon Scrape',
  source: 'https://example.com/products.csv'
}, token);
```

### DTOs

**CreateTemplateDTO:**
```tsx
interface CreateTemplateDTO {
  name: string;
  description?: string;
  category?: string;          // 'ecommerce', 'social-media', 'news', etc.
  is_public?: boolean;
  config: {
    queries: Array<{
      name: string;
      type: 'xpath' | 'regex' | 'jsonpath';
      query: string;
      join?: boolean;
    }>;
    rate_limit?: number;
    proxy_config?: ProxyConfig;
    render_config?: RenderConfig;
  };
}
```

**UpdateTemplateDTO:**
```tsx
type UpdateTemplateDTO = Partial<CreateTemplateDTO>;
```

### API Methods

| Method | Endpoint | Description |
|--------|----------|-------------|
| `list(token)` | `GET /templates` | List all templates |
| `listPublic(token)` | `GET /templates/public` | List public templates |
| `get(id, token)` | `GET /templates/{id}` | Get single template |
| `create(data, token)` | `POST /templates` | Create template |
| `update(id, data, token)` | `PUT /templates/{id}` | Update template |
| `delete(id, token)` | `DELETE /templates/{id}` | Delete template |
| `use(id, jobData, token)` | `POST /templates/{id}/use` | Create job from template |

## Webhooks API (`webhooks.ts`)

Manage webhook notifications for job events.

### Usage

```tsx
import { webhooksAPI } from '@/lib/api';

// List webhooks
const webhooks = await webhooksAPI.list(token);

// Get single webhook
const webhook = await webhooksAPI.get('webhook-123', token);

// Create webhook
const newWebhook = await webhooksAPI.create({
  url: 'https://myapp.com/webhook',
  events: ['job.completed', 'job.failed'],
  secret: 'my-secret-key',
  enabled: true
}, token);

// Update webhook
const updatedWebhook = await webhooksAPI.update('webhook-123', {
  enabled: false
}, token);

// Delete webhook
await webhooksAPI.delete('webhook-123', token);

// Test webhook
const testResult = await webhooksAPI.test('webhook-123', token);

// Get webhook deliveries (history)
const deliveries = await webhooksAPI.deliveries('webhook-123', token, 50);

// Enable webhook
await webhooksAPI.enable('webhook-123', token);

// Disable webhook
await webhooksAPI.disable('webhook-123', token);
```

### DTOs

**CreateWebhookDTO:**
```tsx
interface CreateWebhookDTO {
  url: string;                      // Webhook URL
  events: string[];                  // ['job.completed', 'job.failed', etc.]
  secret?: string;                   // HMAC secret for verification
  enabled?: boolean;
  retry_config?: {
    max_retries: number;
    backoff_strategy: 'linear' | 'exponential';
  };
}
```

**UpdateWebhookDTO:**
```tsx
type UpdateWebhookDTO = Partial<CreateWebhookDTO>;
```

### Webhook Events

- `job.created` - Job created
- `job.started` - Job started running
- `job.completed` - Job completed successfully
- `job.failed` - Job failed
- `job.paused` - Job paused
- `job.resumed` - Job resumed

### Webhook Payload

```json
{
  "event": "job.completed",
  "timestamp": "2025-01-19T12:00:00Z",
  "data": {
    "job_id": "job-123",
    "name": "My Job",
    "status": "success",
    "results_count": 1000,
    "s3_key": "results/job-123/output.json"
  }
}
```

### API Methods

| Method | Endpoint | Description |
|--------|----------|-------------|
| `list(token)` | `GET /webhooks` | List webhooks |
| `get(id, token)` | `GET /webhooks/{id}` | Get single webhook |
| `create(data, token)` | `POST /webhooks` | Create webhook |
| `update(id, data, token)` | `PUT /webhooks/{id}` | Update webhook |
| `delete(id, token)` | `DELETE /webhooks/{id}` | Delete webhook |
| `test(id, token)` | `POST /webhooks/{id}/test` | Send test payload |
| `deliveries(id, token, limit?)` | `GET /webhooks/{id}/deliveries` | Get delivery history |
| `enable(id, token)` | `PATCH /webhooks/{id}/enable` | Enable webhook |
| `disable(id, token)` | `PATCH /webhooks/{id}/disable` | Disable webhook |

## Analytics API (`analytics.ts`)

Fetch usage, cost, and performance analytics.

### Usage

```tsx
import { analyticsAPI } from '@/lib/api';

// Get usage metrics
const usage = await analyticsAPI.usage('7d', token);
// Returns: { api_calls, data_volume, active_jobs, ... }

// Get cost metrics
const cost = await analyticsAPI.cost('30d', token);
// Returns: { total_cost, cost_breakdown, projected_cost, ... }

// Get performance metrics
const performance = await analyticsAPI.performance('7d', token);
// Returns: { avg_runtime, success_rate, error_rate, ... }

// Get job-specific analytics
const jobAnalytics = await analyticsAPI.jobAnalytics('job-123', token);
// Returns: { runs, success_rate, avg_runtime, cost, ... }

// Get trends
const trends = await analyticsAPI.trends('30d', token);
// Returns: { daily_api_calls[], daily_cost[], ... }
```

### Time Periods

- `'24h'` - Last 24 hours
- `'7d'` - Last 7 days
- `'30d'` - Last 30 days
- `'90d'` - Last 90 days

### API Methods

| Method | Endpoint | Description |
|--------|----------|-------------|
| `usage(period, token)` | `GET /analytics/usage` | Usage metrics |
| `cost(period, token)` | `GET /analytics/cost` | Cost metrics |
| `performance(period, token)` | `GET /analytics/performance` | Performance metrics |
| `jobAnalytics(jobId, token)` | `GET /analytics/jobs/{id}` | Job-specific analytics |
| `trends(period, token)` | `GET /analytics/trends` | Historical trends |

## Unified API Export

For convenience, all APIs are available through a unified export:

```tsx
import { api } from '@/lib/api';

const jobs = await api.jobs.list(token);
const templates = await api.templates.listPublic(token);
const webhooks = await api.webhooks.list(token);
const usage = await api.analytics.usage('7d', token);
```

## Using with React Query Hooks

All API methods are wrapped in React Query hooks located in `lib/hooks/`:

```tsx
import {
  useJobs,
  useJob,
  useCreateJob,
  useDeleteJob,
} from '@/lib/hooks/useJobs';

function MyComponent() {
  // Fetch jobs (with automatic caching and refetching)
  const { data: jobs, isLoading, error } = useJobs();

  // Create job mutation
  const createJob = useCreateJob();

  const handleCreate = async () => {
    try {
      await createJob.mutateAsync({
        name: 'My Job',
        source: 'https://example.com/data.csv',
        queries: [/* ... */]
      });
      // Automatically invalidates 'jobs' query and shows success toast
    } catch (error) {
      // Error handled by mutation, shows error toast
    }
  };

  return (
    <div>
      {isLoading && <LoadingSpinner />}
      {error && <ErrorMessage />}
      {jobs?.map(job => <JobCard key={job.job_id} job={job} />)}
    </div>
  );
}
```

**Benefits:**
- Automatic caching (30s stale time)
- Automatic refetching (30s interval for jobs)
- Optimistic updates
- Error handling with toast notifications
- Loading states
- Cache invalidation

See `lib/hooks/README.md` for detailed hook documentation (if exists).

## Error Handling

All API methods throw `APIError` on failure. Handle errors appropriately:

```tsx
try {
  const job = await jobsAPI.get('job-123', token);
} catch (error) {
  if (error instanceof APIError) {
    if (error.status === 404) {
      console.error('Job not found');
    } else if (error.status === 401) {
      console.error('Not authenticated');
    } else {
      console.error('API error:', error.message);
    }
  } else {
    console.error('Unexpected error:', error);
  }
}
```

When using React Query hooks, errors are handled automatically with toast notifications.

## Authentication

All API methods require a Clerk session token:

```tsx
import { useSession } from '@clerk/nextjs';

function MyComponent() {
  const { session } = useSession();

  const fetchData = async () => {
    const token = await session?.getToken();
    if (!token) {
      throw new Error('Not authenticated');
    }

    const jobs = await jobsAPI.list(token);
  };
}
```

React Query hooks handle authentication automatically.

## Environment Variables

The API client uses the following environment variables:

```bash
NEXT_PUBLIC_API_BASE_URL=https://api.snowscrape.com
NEXT_PUBLIC_API_KEY=your-api-key  # Optional
```

Set these in `.env.local` for local development.

## Best Practices

1. **Use React Query hooks** instead of calling API methods directly
2. **Handle authentication errors** gracefully (redirect to sign-in)
3. **Use TypeScript types** provided by DTOs for type safety
4. **Don't retry authentication errors** (401, 403) automatically
5. **Cache aggressively** for read operations, invalidate on mutations
6. **Use optimistic updates** for better UX (handled by hooks)
7. **Show loading states** while data is being fetched
8. **Display error messages** to users when operations fail
9. **Implement retry logic** for transient network errors (handled by React Query)
10. **Log errors** to error tracking service (Sentry, LogRocket, etc.)

## Testing

To mock API responses in tests:

```tsx
import { apiClient } from '@/lib/api/client';

// Mock the request method
jest.spyOn(apiClient, 'request').mockResolvedValue({
  job_id: 'job-123',
  name: 'Test Job',
  status: 'running'
});

// Test your component
const { result } = renderHook(() => useJobs());
await waitFor(() => expect(result.current.isSuccess).toBe(true));
```

See `lib/__tests__/` for example tests.

## Resources

- [React Query Documentation](https://tanstack.com/query/latest)
- [Clerk Authentication](https://clerk.com/docs)
- [Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API)
