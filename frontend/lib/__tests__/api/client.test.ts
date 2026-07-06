import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Hoist env setup so the module-level singleton (constructed at import time)
// picks up a configured base URL.
const { setEnv } = vi.hoisted(() => {
  process.env.NEXT_PUBLIC_API_BASE_URL = 'https://api.test';
  return {
    setEnv: () => {
      process.env.NEXT_PUBLIC_API_BASE_URL = 'https://api.test';
    },
  };
});

import { APIClient, APIError, apiClient } from '@/lib/api/client';

/** Build a minimal Response-like stub for the fetch mock. */
function mockResponse(opts: {
  ok: boolean;
  status?: number;
  contentType?: string | null;
  json?: unknown;
  text?: string;
}) {
  return {
    ok: opts.ok,
    status: opts.status ?? (opts.ok ? 200 : 500),
    headers: {
      get: (h: string) =>
        h.toLowerCase() === 'content-type'
          ? opts.contentType === undefined
            ? 'application/json'
            : opts.contentType
          : null,
    },
    json: async () => opts.json,
    text: async () => opts.text ?? '',
  } as unknown as Response;
}

beforeEach(() => {
  setEnv();
  vi.restoreAllMocks();
});

afterEach(() => {
  setEnv();
});

describe('APIError', () => {
  it('carries status, message and optional data, and is an Error subclass', () => {
    const err = new APIError(404, 'nope', { detail: 'x' });
    expect(err).toBeInstanceOf(Error);
    expect(err).toBeInstanceOf(APIError);
    expect(err.name).toBe('APIError');
    expect(err.status).toBe(404);
    expect(err.message).toBe('nope');
    expect(err.data).toEqual({ detail: 'x' });
  });

  it('leaves data undefined when not provided', () => {
    const err = new APIError(500, 'boom');
    expect(err.data).toBeUndefined();
  });
});

describe('APIClient.request - guards', () => {
  it('throws 401 "Not authenticated" without calling fetch when token is empty', async () => {
    const fetchSpy = vi.fn();
    global.fetch = fetchSpy as any;
    const client = new APIClient();

    await expect(client.request('/jobs', '')).rejects.toMatchObject({
      name: 'APIError',
      status: 401,
      message: 'Not authenticated',
    });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('throws status 0 with the configuration hint when base URL is unset (token present)', async () => {
    const fetchSpy = vi.fn();
    global.fetch = fetchSpy as any;
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    // baseURL is read in the constructor, so construct after clearing the env.
    const client = new APIClient();

    await expect(client.request('/jobs', 'tok')).rejects.toMatchObject({
      name: 'APIError',
      status: 0,
    });
    await expect(client.request('/jobs', 'tok')).rejects.toThrow(
      /NEXT_PUBLIC_API_BASE_URL/
    );
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});

describe('APIClient.request - URL + headers', () => {
  it('concatenates baseURL + endpoint verbatim (no slash normalization) and sets default headers', async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      mockResponse({ ok: true, json: { ok: 1 } })
    );
    global.fetch = fetchSpy as any;
    const client = new APIClient();

    await client.request('/jobs', 'tok');
    expect(fetchSpy).toHaveBeenCalledWith(
      'https://api.test/jobs',
      expect.objectContaining({
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          Authorization: 'Bearer tok',
        }),
      })
    );

    // No normalization: a missing leading slash is NOT inserted.
    await client.request('jobs', 'tok');
    expect(fetchSpy).toHaveBeenLastCalledWith(
      'https://api.testjobs',
      expect.anything()
    );
  });

  it('lets caller-supplied options.headers override the defaults (spread last wins)', async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      mockResponse({ ok: true, json: {} })
    );
    global.fetch = fetchSpy as any;
    const client = new APIClient();

    await client.request('/x', 'tok', {
      headers: { Authorization: 'Bearer override', 'X-Custom': 'v' },
    });

    const headers = (fetchSpy.mock.calls[0][1] as RequestInit).headers as Record<
      string,
      string
    >;
    expect(headers.Authorization).toBe('Bearer override');
    expect(headers['X-Custom']).toBe('v');
    expect(headers['Content-Type']).toBe('application/json');
  });

  it('forwards arbitrary RequestInit options (e.g. method) to fetch', async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      mockResponse({ ok: true, json: {} })
    );
    global.fetch = fetchSpy as any;
    const client = new APIClient();

    await client.request('/x', 'tok', { method: 'PATCH' });
    expect(fetchSpy.mock.calls[0][1]).toMatchObject({ method: 'PATCH' });
  });
});

describe('APIClient.request - success body handling', () => {
  it('returns the parsed JSON body when content-type is application/json', async () => {
    const body = { id: '1', nested: { a: true } };
    global.fetch = vi.fn().mockResolvedValue(
      mockResponse({ ok: true, contentType: 'application/json; charset=utf-8', json: body })
    ) as any;
    const client = new APIClient();

    await expect(client.request('/jobs', 'tok')).resolves.toEqual(body);
  });

  it('returns an empty object (not the parsed body) when content-type is missing', async () => {
    const jsonSpy = vi.fn();
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: { get: () => null },
      json: jsonSpy,
      text: async () => '',
    } as unknown as Response) as any;
    const client = new APIClient();

    await expect(client.request('/x', 'tok')).resolves.toEqual({});
    expect(jsonSpy).not.toHaveBeenCalled();
  });

  it('returns an empty object when content-type is non-JSON (e.g. text/plain)', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      mockResponse({ ok: true, contentType: 'text/plain', json: { should: 'not parse' } })
    ) as any;
    const client = new APIClient();

    await expect(client.request('/x', 'tok')).resolves.toEqual({});
  });
});

describe('APIClient.request - error body handling', () => {
  it('prefers the JSON "error" field for the message and passes parsed data', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      mockResponse({
        ok: false,
        status: 422,
        text: JSON.stringify({ error: 'detailed error', message: 'summary' }),
      })
    ) as any;
    const client = new APIClient();

    await expect(client.request('/x', 'tok')).rejects.toMatchObject({
      status: 422,
      message: 'detailed error',
      data: { error: 'detailed error', message: 'summary' },
    });
  });

  it('falls back to the JSON "message" field when "error" is absent', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      mockResponse({ ok: false, status: 400, text: JSON.stringify({ message: 'just summary' }) })
    ) as any;
    const client = new APIClient();

    await expect(client.request('/x', 'tok')).rejects.toMatchObject({
      status: 400,
      message: 'just summary',
    });
  });

  it('falls back to "Request failed: <status>" when JSON has neither error nor message', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      mockResponse({ ok: false, status: 503, text: JSON.stringify({ other: 'field' }) })
    ) as any;
    const client = new APIClient();

    await expect(client.request('/x', 'tok')).rejects.toMatchObject({
      status: 503,
      message: 'Request failed: 503',
      data: { other: 'field' },
    });
  });

  it('uses the default message and the raw text as data when the error body is not JSON', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      mockResponse({ ok: false, status: 500, text: 'Internal Server Error' })
    ) as any;
    const client = new APIClient();

    await expect(client.request('/x', 'tok')).rejects.toMatchObject({
      status: 500,
      message: 'Request failed: 500',
      data: 'Internal Server Error',
    });
  });

  it('preserves the original status (does not rewrap to 0) for an error response', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      mockResponse({ ok: false, status: 404, text: JSON.stringify({ error: 'missing' }) })
    ) as any;
    const client = new APIClient();

    const err = await client.request('/x', 'tok').catch((e) => e);
    expect(err).toBeInstanceOf(APIError);
    expect(err.status).toBe(404);
  });
});

describe('APIClient.request - network / unexpected errors', () => {
  it('wraps a rejecting fetch (network error) in APIError status 0 with the original message', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('network down')) as any;
    const client = new APIClient();

    await expect(client.request('/x', 'tok')).rejects.toMatchObject({
      name: 'APIError',
      status: 0,
      message: 'network down',
    });
  });

  it('wraps a non-Error rejection in APIError status 0 with the generic message', async () => {
    global.fetch = vi.fn().mockRejectedValue('weird string') as any;
    const client = new APIClient();

    await expect(client.request('/x', 'tok')).rejects.toMatchObject({
      status: 0,
      message: 'Unknown error occurred',
    });
  });
});

describe('APIClient verb helpers', () => {
  beforeEach(() => {
    global.fetch = vi.fn().mockResolvedValue(
      mockResponse({ ok: true, json: { ok: true } })
    ) as any;
  });

  it('get() issues a GET with no body and returns the parsed result', async () => {
    const client = new APIClient();
    await expect(client.get('/jobs', 'tok')).resolves.toEqual({ ok: true });
    const opts = (global.fetch as any).mock.calls[0][1] as RequestInit;
    expect(opts.method).toBe('GET');
    expect(opts.body).toBeUndefined();
  });

  it('post() serializes the data argument as a JSON body', async () => {
    const client = new APIClient();
    await client.post('/jobs', 'tok', { name: 'j', count: 2 });
    const opts = (global.fetch as any).mock.calls[0][1] as RequestInit;
    expect(opts.method).toBe('POST');
    expect(JSON.parse(opts.body as string)).toEqual({ name: 'j', count: 2 });
  });

  it('post() sends an undefined body when no data is given', async () => {
    const client = new APIClient();
    await client.post('/jobs', 'tok');
    const opts = (global.fetch as any).mock.calls[0][1] as RequestInit;
    expect(opts.method).toBe('POST');
    expect(opts.body).toBeUndefined();
  });

  it('put() serializes the data argument as a JSON body', async () => {
    const client = new APIClient();
    await client.put('/jobs/1', 'tok', { name: 'updated' });
    const opts = (global.fetch as any).mock.calls[0][1] as RequestInit;
    expect(opts.method).toBe('PUT');
    expect(JSON.parse(opts.body as string)).toEqual({ name: 'updated' });
  });

  it('put() sends an undefined body when no data is given', async () => {
    const client = new APIClient();
    await client.put('/jobs/1', 'tok');
    const opts = (global.fetch as any).mock.calls[0][1] as RequestInit;
    expect(opts.body).toBeUndefined();
  });

  it('delete() issues a DELETE with no body', async () => {
    const client = new APIClient();
    await client.delete('/jobs/1', 'tok');
    const opts = (global.fetch as any).mock.calls[0][1] as RequestInit;
    expect(opts.method).toBe('DELETE');
    expect(opts.body).toBeUndefined();
  });
});

describe('exported singleton', () => {
  it('apiClient is an APIClient instance', () => {
    expect(apiClient).toBeInstanceOf(APIClient);
  });
});
