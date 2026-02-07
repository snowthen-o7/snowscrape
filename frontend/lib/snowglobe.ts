/**
 * Snowglobe Analytics Service
 * Sends events, metrics, and health status to the Snowglobe Observatory
 */

interface SnowglobeConfig {
  siteId: string;
  apiKey: string;
  apiUrl: string;
  enabled: boolean;
}

interface EventData {
  [key: string]: unknown;
}

const config: SnowglobeConfig = {
  siteId: process.env.SNOWGLOBE_SITE_ID || 'snowscrape',
  apiKey: process.env.SNOWGLOBE_API_KEY || '',
  apiUrl: process.env.SNOWGLOBE_URL || 'https://snowglobe.alexdiaz.me',
  enabled: !!process.env.SNOWGLOBE_API_KEY,
};

async function request(
  endpoint: string,
  method: 'GET' | 'POST',
  body?: unknown
): Promise<unknown> {
  if (!config.enabled) {
    return null;
  }

  try {
    const response = await fetch(`${config.apiUrl}${endpoint}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': config.apiKey,
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      console.error(
        `[Snowglobe] Request failed: ${response.status} ${response.statusText}`
      );
      return null;
    }

    return response.json();
  } catch (error) {
    console.error('[Snowglobe] Request error:', error);
    return null;
  }
}

/**
 * Track an analytics event
 */
export async function trackEvent(
  eventType: string,
  data?: EventData
): Promise<void> {
  await request('/api/events', 'POST', {
    siteId: config.siteId,
    eventType,
    data: {
      ...data,
      timestamp: new Date().toISOString(),
    },
  });
}

/**
 * Report health status
 */
export async function reportHealth(
  status: 'healthy' | 'degraded' | 'down',
  details?: { responseTimeMs?: number; error?: string }
): Promise<void> {
  await request(`/api/sites/${config.siteId}/health`, 'POST', {
    status,
    ...details,
  });
}

/**
 * Send metrics snapshot
 */
export async function sendMetrics(
  metrics: Record<string, number | string>
): Promise<void> {
  await request('/api/metrics', 'POST', {
    siteId: config.siteId,
    metrics,
  });
}

/**
 * Register this site with Snowglobe
 */
export async function register(): Promise<void> {
  await request('/api/sites', 'POST', {
    siteId: config.siteId,
    name: 'SnowScrape',
    type: 'app',
    platform: 'Vercel',
    description: 'Web scraping and data extraction tool',
  });
}

export { config as snowglobeConfig };
