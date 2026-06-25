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

import { destinationsAPI, type CreateDestinationInput } from '@/lib/api/destinations';

beforeEach(() => {
  setEnv();
  vi.restoreAllMocks();
});

// A complete, valid create payload exercised by several tests.
const fullInput: CreateDestinationInput = {
  name: 'My Docs Export',
  type: 'google_docs',
  drive_folder_id: 'folder-123',
  naming_template: '{{job_name}} {{date}}',
  mode: 'new_doc_per_run',
  format_template: 'structured_log',
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

describe('destinationsAPI.list', () => {
  it('GETs /export-destinations with the bearer token and no body', async () => {
    const payload = {
      destinations: [
        {
          destination_id: 'd1',
          user_id: 'u1',
          name: 'Docs',
          type: 'google_docs',
          drive_folder_id: 'f1',
          naming_template: '{{job_name}}',
          mode: 'new_doc_per_run',
          format_template: 'structured_log',
          google_user_id: 'g1',
          created_at: '2026-06-01T00:00:00Z',
        },
      ],
    };
    mockFetchJson(payload);

    const result = await destinationsAPI.list('tok-list');

    // The wrapper returns the server envelope verbatim (no unwrap/transform).
    expect(result).toEqual(payload);

    expect(global.fetch).toHaveBeenCalledTimes(1);
    const [url, init] = (global.fetch as any).mock.calls[0];
    expect(url).toBe('https://api.test/export-destinations');
    expect(init.method).toBe('GET');
    expect(init.body).toBeUndefined();
    expect(init.headers).toEqual(
      expect.objectContaining({
        Authorization: 'Bearer tok-list',
        'Content-Type': 'application/json',
      })
    );
  });

  it('returns an empty-destinations envelope verbatim', async () => {
    mockFetchJson({ destinations: [] });
    const result = await destinationsAPI.list('tok');
    expect(result).toEqual({ destinations: [] });
  });

  it('propagates an APIError on a non-ok response (not swallowed)', async () => {
    mockFetchJson({ error: 'nope' }, false, 401);
    await expect(destinationsAPI.list('tok')).rejects.toMatchObject({
      name: 'APIError',
      status: 401,
      message: 'nope',
    });
  });
});

describe('destinationsAPI.create', () => {
  it('POSTs /export-destinations with the input as the JSON body and returns the created destination', async () => {
    const created = {
      destination_id: 'd-new',
      user_id: 'u1',
      ...fullInput,
      google_user_id: 'g1',
      created_at: '2026-06-25T00:00:00Z',
    };
    mockFetchJson(created);

    const result = await destinationsAPI.create('tok-create', fullInput);
    expect(result).toEqual(created);

    expect(global.fetch).toHaveBeenCalledTimes(1);
    const [url, init] = (global.fetch as any).mock.calls[0];
    expect(url).toBe('https://api.test/export-destinations');
    expect(init.method).toBe('POST');
    expect(init.headers).toEqual(
      expect.objectContaining({
        Authorization: 'Bearer tok-create',
        'Content-Type': 'application/json',
      })
    );
    // The body round-trips to exactly the input: nothing dropped, nothing added.
    expect(JSON.parse(init.body)).toEqual(fullInput);
  });

  it('preserves all six CreateDestinationInput fields verbatim in the body', async () => {
    mockFetchJson({ destination_id: 'd', user_id: 'u', ...fullInput, google_user_id: 'g', created_at: 'x' });
    await destinationsAPI.create('tok', fullInput);
    const body = JSON.parse((global.fetch as any).mock.calls[0][1].body);
    expect(Object.keys(body).sort()).toEqual(
      ['drive_folder_id', 'format_template', 'mode', 'name', 'naming_template', 'type'].sort()
    );
    expect(body.mode).toBe('new_doc_per_run');
    expect(body.format_template).toBe('structured_log');
  });
});

describe('destinationsAPI.delete', () => {
  it('DELETEs /export-destinations/<id> with no body', async () => {
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

    const result = await destinationsAPI.delete('tok-del', 'dest-42');
    expect(result).toEqual({});

    expect(global.fetch).toHaveBeenCalledTimes(1);
    const [url, init] = (global.fetch as any).mock.calls[0];
    expect(url).toBe('https://api.test/export-destinations/dest-42');
    expect(init.method).toBe('DELETE');
    expect(init.body).toBeUndefined();
    expect(init.headers).toEqual(
      expect.objectContaining({ Authorization: 'Bearer tok-del' })
    );
  });

  it('interpolates the destination id into the path', async () => {
    mockFetchJson({});
    await destinationsAPI.delete('tok', 'abc-123');
    expect((global.fetch as any).mock.calls[0][0]).toBe(
      'https://api.test/export-destinations/abc-123'
    );
  });

  it('propagates an APIError on a non-ok delete (e.g. 404)', async () => {
    mockFetchJson({ error: 'not found' }, false, 404);
    await expect(destinationsAPI.delete('tok', 'missing')).rejects.toMatchObject({
      name: 'APIError',
      status: 404,
    });
  });
});

describe('destinationsAPI auth guard', () => {
  it('throws APIError(401) before any fetch when the token is empty', async () => {
    global.fetch = vi.fn();
    await expect(destinationsAPI.list('')).rejects.toMatchObject({
      name: 'APIError',
      status: 401,
      message: 'Not authenticated',
    });
    expect(global.fetch).not.toHaveBeenCalled();
  });
});
