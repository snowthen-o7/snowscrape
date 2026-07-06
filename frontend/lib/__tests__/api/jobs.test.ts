import { describe, it, expect, vi, beforeEach } from 'vitest';

// Hoist env setup so it runs before the module graph is evaluated:
// client.ts reads NEXT_PUBLIC_API_BASE_URL in the APIClient constructor, and
// jobs.ts constructs the singleton `jobsAPI` at import time.
const { setEnv } = vi.hoisted(() => {
  process.env.NEXT_PUBLIC_API_BASE_URL = 'https://api.test';
  return {
    setEnv: () => {
      process.env.NEXT_PUBLIC_API_BASE_URL = 'https://api.test';
    },
  };
});

import { jobsAPI } from '@/lib/api/jobs';
import { APIError } from '@/lib/api/client';

const BASE = 'https://api.test';
const TOKEN = 'test-token';

// A successful JSON response: the client returns response.json().
function mockFetchJson(body: unknown) {
  const fn = vi.fn().mockResolvedValue({
    ok: true,
    headers: { get: () => 'application/json' },
    json: async () => body,
  } as any);
  global.fetch = fn;
  return fn;
}

// A successful non-JSON response (e.g. an empty 200/204): the client returns {}.
function mockFetchEmpty() {
  const fn = vi.fn().mockResolvedValue({
    ok: true,
    headers: { get: () => null },
    text: async () => '',
  } as any);
  global.fetch = fn;
  return fn;
}

// [url, init] of the first fetch call.
function call(fn: ReturnType<typeof vi.fn>): [string, RequestInit] {
  return (fn as any).mock.calls[0];
}

beforeEach(() => {
  setEnv();
  vi.restoreAllMocks();
});

describe('jobsAPI.list', () => {
  it('GETs /jobs/status and unwraps the jobs array', async () => {
    const jobs = [{ id: 'j1' }, { id: 'j2' }];
    const fetchFn = mockFetchJson({ jobs, count: 2 });

    const result = await jobsAPI.list(TOKEN);

    expect(result).toEqual(jobs);
    const [url, init] = call(fetchFn);
    expect(url).toBe(`${BASE}/jobs/status`);
    // list() passes no options, so it relies on fetch's default GET (no method key).
    expect(init.method).toBeUndefined();
    expect(init.body).toBeUndefined();
    expect(init.headers).toMatchObject({
      Authorization: `Bearer ${TOKEN}`,
      'Content-Type': 'application/json',
    });
  });

  it('falls back to [] when the response has no jobs field (|| [])', async () => {
    mockFetchJson({ count: 0 });
    expect(await jobsAPI.list(TOKEN)).toEqual([]);
  });

  it('falls back to [] when jobs is null', async () => {
    mockFetchJson({ jobs: null, count: 0 });
    expect(await jobsAPI.list(TOKEN)).toEqual([]);
  });
});

describe('jobsAPI.get', () => {
  it('GETs /jobs/:id and returns the job verbatim', async () => {
    const job = { id: 'abc', name: 'n' };
    const fetchFn = mockFetchJson(job);

    const result = await jobsAPI.get('abc', TOKEN);

    expect(result).toEqual(job);
    const [url, init] = call(fetchFn);
    expect(url).toBe(`${BASE}/jobs/abc`);
    expect(init.method).toBeUndefined();
    expect(init.body).toBeUndefined();
  });
});

describe('jobsAPI.create', () => {
  it('POSTs /jobs with the job payload and bearer auth', async () => {
    const created = { id: 'new' };
    const fetchFn = mockFetchJson(created);
    const dto = {
      name: 'J',
      source: 'https://x',
      queries: [{ name: 'a', type: 'xpath', query: '//a' }],
    };

    const result = await jobsAPI.create(dto as any, TOKEN);

    expect(result).toEqual(created);
    const [url, init] = call(fetchFn);
    expect(url).toBe(`${BASE}/jobs`);
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body as string)).toEqual(dto);
    expect(init.headers).toMatchObject({ Authorization: `Bearer ${TOKEN}` });
  });
});

describe('jobsAPI.update', () => {
  it('PUTs /jobs/:id with the partial payload', async () => {
    const fetchFn = mockFetchJson({ id: 'abc' });
    const patch = { name: 'renamed' };

    await jobsAPI.update('abc', patch, TOKEN);

    const [url, init] = call(fetchFn);
    expect(url).toBe(`${BASE}/jobs/abc`);
    expect(init.method).toBe('PUT');
    expect(JSON.parse(init.body as string)).toEqual(patch);
  });
});

describe('jobsAPI.delete', () => {
  it('DELETEs /jobs/:id with no body and resolves on an empty response', async () => {
    const fetchFn = mockFetchEmpty();

    await expect(jobsAPI.delete('abc', TOKEN)).resolves.toEqual({});

    const [url, init] = call(fetchFn);
    expect(url).toBe(`${BASE}/jobs/abc`);
    expect(init.method).toBe('DELETE');
    expect(init.body).toBeUndefined();
  });
});

describe('jobsAPI lifecycle POST actions', () => {
  it.each([
    ['pause', (t: string) => jobsAPI.pause('abc', t), '/jobs/abc/pause'],
    ['resume', (t: string) => jobsAPI.resume('abc', t), '/jobs/abc/resume'],
    ['run', (t: string) => jobsAPI.run('abc', t), '/jobs/abc/run'],
  ])('%s POSTs %s with no body', async (_name, fn, endpoint) => {
    const fetchFn = mockFetchJson({ id: 'abc' });

    await fn(TOKEN);

    const [url, init] = call(fetchFn);
    expect(url).toBe(`${BASE}${endpoint}`);
    expect(init.method).toBe('POST');
    expect(init.body).toBeUndefined();
  });
});

describe('jobsAPI.download', () => {
  it.each(['csv', 'json', 'xlsx', 'sql'] as const)(
    'GETs the download URL for format=%s',
    async (fmt) => {
      const fetchFn = mockFetchJson({ url: 'https://s3/x', filename: `f.${fmt}` });

      const result = await jobsAPI.download('abc', fmt, TOKEN);

      expect(result).toEqual({ url: 'https://s3/x', filename: `f.${fmt}` });
      expect(call(fetchFn)[0]).toBe(`${BASE}/jobs/abc/download?format=${fmt}`);
    }
  );
});

describe('jobsAPI.history', () => {
  it('GETs /jobs/:id/history', async () => {
    const fetchFn = mockFetchJson([{ run: 1 }]);

    const result = await jobsAPI.history('abc', TOKEN);

    expect(result).toEqual([{ run: 1 }]);
    expect(call(fetchFn)[0]).toBe(`${BASE}/jobs/abc/history`);
  });
});

describe('jobsAPI.results', () => {
  it('GETs results with the default limit of 100', async () => {
    const fetchFn = mockFetchJson([{ a: 1 }]);

    await jobsAPI.results('abc', TOKEN);

    expect(call(fetchFn)[0]).toBe(`${BASE}/jobs/abc/results?limit=100`);
  });

  it('forwards a custom limit', async () => {
    const fetchFn = mockFetchJson([]);

    await jobsAPI.results('abc', TOKEN, 25);

    expect(call(fetchFn)[0]).toBe(`${BASE}/jobs/abc/results?limit=25`);
  });
});

describe('jobsAPI scraper helpers', () => {
  it('preview POSTs /scraper/preview with { url }', async () => {
    const fetchFn = mockFetchJson({ url: 'https://x', title: 't', elements: [] });

    await jobsAPI.preview('https://x', TOKEN);

    const [url, init] = call(fetchFn);
    expect(url).toBe(`${BASE}/scraper/preview`);
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body as string)).toEqual({ url: 'https://x' });
  });

  it('previewAsync POSTs /scraper/preview/async with { url }', async () => {
    const fetchFn = mockFetchJson({
      task_id: 'tid',
      status: 'queued',
      websocket_channel: 'c',
      websocket_url: 'w',
    });

    const result = await jobsAPI.previewAsync('https://x', TOKEN);

    expect(result.task_id).toBe('tid');
    const [url, init] = call(fetchFn);
    expect(url).toBe(`${BASE}/scraper/preview/async`);
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body as string)).toEqual({ url: 'https://x' });
  });

  it('testExtraction POSTs /scraper/test with { url, selectors }', async () => {
    const fetchFn = mockFetchJson([{ name: 'a', value: 'v' }]);
    const selectors = [{ name: 'a', type: 'xpath', selector: '//a' }];

    await jobsAPI.testExtraction('https://x', selectors, TOKEN);

    const [url, init] = call(fetchFn);
    expect(url).toBe(`${BASE}/scraper/test`);
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body as string)).toEqual({ url: 'https://x', selectors });
  });
});

describe('jobsAPI AI helpers', () => {
  it('aiExtract POSTs /ai/extract with url+description when no options are given', async () => {
    const fetchFn = mockFetchJson({ result: {} });

    await jobsAPI.aiExtract('https://x', 'desc', TOKEN);

    const [url, init] = call(fetchFn);
    expect(url).toBe(`${BASE}/ai/extract`);
    expect(init.method).toBe('POST');
    // ...options spreads nothing when options is undefined.
    expect(JSON.parse(init.body as string)).toEqual({ url: 'https://x', description: 'desc' });
  });

  it('aiExtract merges tier options into the body via the spread', async () => {
    const fetchFn = mockFetchJson({ result: {} });

    await jobsAPI.aiExtract('https://x', 'desc', TOKEN, { min_tier: 1, max_tier: 3 });

    expect(JSON.parse(call(fetchFn)[1].body as string)).toEqual({
      url: 'https://x',
      description: 'desc',
      min_tier: 1,
      max_tier: 3,
    });
  });

  it('aiSuggestQueries POSTs /ai/suggest-queries with { url, description }', async () => {
    const fetchFn = mockFetchJson({ url: 'https://x', suggestions: [] });

    await jobsAPI.aiSuggestQueries('https://x', 'desc', TOKEN);

    const [url, init] = call(fetchFn);
    expect(url).toBe(`${BASE}/ai/suggest-queries`);
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body as string)).toEqual({ url: 'https://x', description: 'desc' });
  });
});

describe('jobsAPI error propagation', () => {
  it('does not swallow a non-ok response: the APIError propagates with status + message', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      headers: { get: () => 'application/json' },
      text: async () => JSON.stringify({ error: 'not found' }),
    } as any);

    const err = await jobsAPI.get('missing', TOKEN).catch((e) => e);

    expect(err).toBeInstanceOf(APIError);
    expect(err.status).toBe(404);
    expect(err.message).toBe('not found');
  });

  it('prefers the error-body "error" field over "message" (error || message || default)', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      headers: { get: () => 'application/json' },
      text: async () => JSON.stringify({ error: 'E', message: 'M' }),
    } as any);

    const err = await jobsAPI.get('x', TOKEN).catch((e) => e);

    expect(err).toBeInstanceOf(APIError);
    expect(err.message).toBe('E');
  });
});
