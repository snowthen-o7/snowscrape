import { describe, it, expect, vi, beforeEach } from 'vitest';

// Hoist env setup so the apiClient singleton (constructed at import of
// '@/lib/api/client') reads a configured baseURL before the module graph runs.
const { setEnv } = vi.hoisted(() => {
  process.env.NEXT_PUBLIC_API_BASE_URL = 'https://api.test';
  return {
    setEnv: () => {
      process.env.NEXT_PUBLIC_API_BASE_URL = 'https://api.test';
    },
  };
});

import { webhooksAPI, type CreateWebhookDTO, type UpdateWebhookDTO } from '@/lib/api/webhooks';

beforeEach(() => {
  setEnv();
  vi.restoreAllMocks();
});

// A complete, valid create payload exercised by several tests.
const fullCreate: CreateWebhookDTO = {
  name: 'Job done',
  url: 'https://hooks.example.com/sink',
  events: ['job.completed', 'job.failed'],
  headers: { 'X-Token': 'abc' },
  secret: 'shhh',
};

function mockFetchJson(body: unknown, ok = true, status = 200) {
  global.fetch = vi.fn().mockResolvedValue({
    ok,
    status,
    headers: { get: () => 'application/json' },
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as any);
}

function lastCall() {
  return (global.fetch as any).mock.calls[0] as [string, any];
}

describe('webhooksAPI.list', () => {
  it('requests /webhooks with the bearer token, no explicit method, and no body', async () => {
    const payload = [
      {
        id: 'w1',
        name: 'Hook',
        url: 'https://x',
        events: ['job.completed'],
        enabled: true,
        created_at: '2026-06-01T00:00:00Z',
        updated_at: '2026-06-01T00:00:00Z',
      },
    ];
    mockFetchJson(payload);

    const result = await webhooksAPI.list('tok-list');

    // The wrapper returns the array verbatim (no unwrap/transform).
    expect(result).toEqual(payload);

    expect(global.fetch).toHaveBeenCalledTimes(1);
    const [url, init] = lastCall();
    expect(url).toBe('https://api.test/webhooks');
    // list() calls client.request with no options, so fetch's default verb is
    // used: method is undefined (NOT the string 'GET').
    expect(init.method).toBeUndefined();
    expect(init.body).toBeUndefined();
    expect(init.headers).toEqual(
      expect.objectContaining({
        Authorization: 'Bearer tok-list',
        'Content-Type': 'application/json',
      })
    );
  });

  it('returns an empty array verbatim', async () => {
    mockFetchJson([]);
    const result = await webhooksAPI.list('tok');
    expect(result).toEqual([]);
  });

  it('propagates an APIError on a non-ok response (not swallowed)', async () => {
    mockFetchJson({ error: 'nope' }, false, 401);
    await expect(webhooksAPI.list('tok')).rejects.toMatchObject({
      name: 'APIError',
      status: 401,
      message: 'nope',
    });
  });
});

describe('webhooksAPI.get', () => {
  it('GET-style requests /webhooks/<id> with no body and interpolates the id', async () => {
    mockFetchJson({ id: 'w-42', name: 'H', url: 'https://x', events: [], enabled: false, created_at: 'a', updated_at: 'b' });

    await webhooksAPI.get('w-42', 'tok-get');

    const [url, init] = lastCall();
    expect(url).toBe('https://api.test/webhooks/w-42');
    expect(init.method).toBeUndefined();
    expect(init.body).toBeUndefined();
    expect(init.headers).toEqual(
      expect.objectContaining({ Authorization: 'Bearer tok-get' })
    );
  });

  it('propagates an APIError on a missing webhook (404)', async () => {
    mockFetchJson({ error: 'not found' }, false, 404);
    await expect(webhooksAPI.get('gone', 'tok')).rejects.toMatchObject({
      name: 'APIError',
      status: 404,
    });
  });
});

describe('webhooksAPI.create', () => {
  it('POSTs /webhooks with the DTO as the JSON body and returns the created webhook', async () => {
    const created = { id: 'w-new', enabled: true, created_at: 'x', updated_at: 'x', ...fullCreate };
    mockFetchJson(created);

    const result = await webhooksAPI.create(fullCreate, 'tok-create');
    expect(result).toEqual(created);

    const [url, init] = lastCall();
    expect(url).toBe('https://api.test/webhooks');
    expect(init.method).toBe('POST');
    expect(init.headers).toEqual(
      expect.objectContaining({
        Authorization: 'Bearer tok-create',
        'Content-Type': 'application/json',
      })
    );
    // Body round-trips to exactly the DTO: nothing dropped, nothing added.
    expect(JSON.parse(init.body)).toEqual(fullCreate);
  });

  it('preserves all five CreateWebhookDTO fields verbatim in the body', async () => {
    mockFetchJson({ id: 'w', enabled: true, created_at: 'x', updated_at: 'x', ...fullCreate });
    await webhooksAPI.create(fullCreate, 'tok');
    const body = JSON.parse(lastCall()[1].body);
    expect(Object.keys(body).sort()).toEqual(
      ['events', 'headers', 'name', 'secret', 'url'].sort()
    );
    expect(body.events).toEqual(['job.completed', 'job.failed']);
    expect(body.headers).toEqual({ 'X-Token': 'abc' });
  });

  it('round-trips a minimal DTO (optional headers/secret omitted)', async () => {
    const minimal: CreateWebhookDTO = {
      name: 'Min',
      url: 'https://min',
      events: ['job.completed'],
    };
    mockFetchJson({ id: 'w', enabled: true, created_at: 'x', updated_at: 'x', ...minimal });
    await webhooksAPI.create(minimal, 'tok');
    const body = JSON.parse(lastCall()[1].body);
    expect(body).toEqual(minimal);
    expect('headers' in body).toBe(false);
    expect('secret' in body).toBe(false);
  });
});

describe('webhooksAPI.update', () => {
  it('PUTs /webhooks/<id> with the partial DTO as the JSON body', async () => {
    const patch: UpdateWebhookDTO = { name: 'Renamed', events: ['job.failed'] };
    mockFetchJson({ id: 'w-7', enabled: true, created_at: 'x', updated_at: 'y', name: 'Renamed', url: 'https://x', events: ['job.failed'] });

    await webhooksAPI.update('w-7', patch, 'tok-up');

    const [url, init] = lastCall();
    expect(url).toBe('https://api.test/webhooks/w-7');
    expect(init.method).toBe('PUT');
    expect(JSON.parse(init.body)).toEqual(patch);
    expect(init.headers).toEqual(
      expect.objectContaining({ Authorization: 'Bearer tok-up' })
    );
  });

  it('serializes an empty patch as {} (not undefined)', async () => {
    mockFetchJson({ id: 'w', enabled: true, created_at: 'x', updated_at: 'y', name: 'n', url: 'u', events: [] });
    await webhooksAPI.update('w', {}, 'tok');
    // update() passes body: JSON.stringify(data) directly, so an empty object
    // is still stringified to '{}' (unlike the client.post wrapper's
    // data ? ... : undefined guard).
    expect(lastCall()[1].body).toBe('{}');
  });
});

describe('webhooksAPI.delete', () => {
  it('DELETEs /webhooks/<id> with no body and returns {} for a null content-type', async () => {
    // Delete responses are non-JSON; the client returns {} for a null content-type.
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: { get: () => null },
      json: async () => {
        throw new Error('should not be called');
      },
      text: async () => '',
    } as any);

    const result = await webhooksAPI.delete('w-42', 'tok-del');
    // delete() is typed Promise<void>, but the client returns the {} cast at
    // runtime for a null content-type, so the resolved value is an empty object.
    expect(result).toEqual({});

    const [url, init] = lastCall();
    expect(url).toBe('https://api.test/webhooks/w-42');
    expect(init.method).toBe('DELETE');
    expect(init.body).toBeUndefined();
    expect(init.headers).toEqual(
      expect.objectContaining({ Authorization: 'Bearer tok-del' })
    );
  });

  it('propagates an APIError on a non-ok delete (e.g. 404)', async () => {
    mockFetchJson({ error: 'not found' }, false, 404);
    await expect(webhooksAPI.delete('missing', 'tok')).rejects.toMatchObject({
      name: 'APIError',
      status: 404,
    });
  });
});

describe('webhooksAPI.test', () => {
  it('POSTs /webhooks/<id>/test with no body', async () => {
    mockFetchJson({
      id: 'del-1',
      webhook_id: 'w-9',
      event: 'test',
      payload: {},
      status: 'success',
      attempts: 1,
      created_at: 'x',
    });

    await webhooksAPI.test('w-9', 'tok-test');

    const [url, init] = lastCall();
    expect(url).toBe('https://api.test/webhooks/w-9/test');
    expect(init.method).toBe('POST');
    expect(init.body).toBeUndefined();
  });
});

describe('webhooksAPI.deliveries', () => {
  it('GET-style requests deliveries with the default limit of 50', async () => {
    mockFetchJson([]);
    await webhooksAPI.deliveries('w-1', 'tok');
    const [url, init] = lastCall();
    expect(url).toBe('https://api.test/webhooks/w-1/deliveries?limit=50');
    expect(init.method).toBeUndefined();
    expect(init.body).toBeUndefined();
  });

  it('forwards a custom limit into the query string', async () => {
    mockFetchJson([]);
    await webhooksAPI.deliveries('w-1', 'tok', 5);
    expect(lastCall()[0]).toBe('https://api.test/webhooks/w-1/deliveries?limit=5');
  });

  it('returns the delivery array verbatim', async () => {
    const rows = [
      { id: 'd1', webhook_id: 'w-1', event: 'job.completed', payload: {}, status: 'failed', attempts: 3, created_at: 'x' },
    ];
    mockFetchJson(rows);
    const result = await webhooksAPI.deliveries('w-1', 'tok');
    expect(result).toEqual(rows);
  });
});

describe('webhooksAPI.enable / disable', () => {
  it('enable POSTs /webhooks/<id>/enable with no body', async () => {
    mockFetchJson({ id: 'w-3', name: 'H', url: 'u', events: [], enabled: true, created_at: 'x', updated_at: 'y' });
    await webhooksAPI.enable('w-3', 'tok');
    const [url, init] = lastCall();
    expect(url).toBe('https://api.test/webhooks/w-3/enable');
    expect(init.method).toBe('POST');
    expect(init.body).toBeUndefined();
  });

  it('disable POSTs /webhooks/<id>/disable with no body', async () => {
    mockFetchJson({ id: 'w-3', name: 'H', url: 'u', events: [], enabled: false, created_at: 'x', updated_at: 'y' });
    await webhooksAPI.disable('w-3', 'tok');
    const [url, init] = lastCall();
    expect(url).toBe('https://api.test/webhooks/w-3/disable');
    expect(init.method).toBe('POST');
    expect(init.body).toBeUndefined();
  });
});

describe('webhooksAPI auth guard', () => {
  it('throws APIError(401) before any fetch when the token is empty', async () => {
    global.fetch = vi.fn();
    await expect(webhooksAPI.list('')).rejects.toMatchObject({
      name: 'APIError',
      status: 401,
      message: 'Not authenticated',
    });
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('guards every method before fetch when the token is empty', async () => {
    global.fetch = vi.fn();
    await Promise.all([
      expect(webhooksAPI.get('w', '')).rejects.toMatchObject({ status: 401 }),
      expect(webhooksAPI.create(fullCreate, '')).rejects.toMatchObject({ status: 401 }),
      expect(webhooksAPI.update('w', {}, '')).rejects.toMatchObject({ status: 401 }),
      expect(webhooksAPI.delete('w', '')).rejects.toMatchObject({ status: 401 }),
      expect(webhooksAPI.test('w', '')).rejects.toMatchObject({ status: 401 }),
      expect(webhooksAPI.deliveries('w', '')).rejects.toMatchObject({ status: 401 }),
      expect(webhooksAPI.enable('w', '')).rejects.toMatchObject({ status: 401 }),
      expect(webhooksAPI.disable('w', '')).rejects.toMatchObject({ status: 401 }),
    ]);
    expect(global.fetch).not.toHaveBeenCalled();
  });
});
