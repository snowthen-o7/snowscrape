import { describe, it, expect } from 'vitest';
import {
  buildVisualJobPayload,
  type VisualExtractedField,
} from '@/lib/jobs/buildVisualJobPayload';

const field = (over: Partial<VisualExtractedField> = {}): VisualExtractedField => ({
  name: 'price',
  selector: '//span[@class="price"]',
  type: 'xpath',
  ...over,
});

describe('buildVisualJobPayload', () => {
  it('creates a direct_url job (source_type + url_template) so backend validation passes', () => {
    const payload = buildVisualJobPayload({
      name: 'My Job',
      url: 'https://example.com/products',
      rateLimit: 10,
      fields: [field()],
      destinationIds: [],
    });

    expect(payload.name).toBe('My Job');
    expect(payload.source).toBe('https://example.com/products');
    expect(payload.source_type).toBe('direct_url');
    expect(payload.url_template).toBe('https://example.com/products');
    expect(payload.rate_limit).toBe(10);
  });

  it('maps each extracted field to a query (name, type, selector as query)', () => {
    const payload = buildVisualJobPayload({
      name: 'Test',
      url: 'https://example.com',
      rateLimit: 10,
      fields: [
        field({ name: 'price', selector: '//p', type: 'xpath' }),
        field({ name: 'title', selector: 'h1.title', type: 'regex' }),
      ],
      destinationIds: [],
    });

    expect(payload.queries).toHaveLength(2);
    expect(payload.queries[0]).toMatchObject({ name: 'price', type: 'xpath', query: '//p', join: false });
    expect(payload.queries[1]).toMatchObject({ name: 'title', type: 'regex', query: 'h1.title', join: false });
  });

  it('downgrades css selectors to xpath (backend job runner does not support raw css)', () => {
    const payload = buildVisualJobPayload({
      name: 'Test',
      url: 'https://example.com',
      rateLimit: 10,
      fields: [field({ type: 'css' })],
      destinationIds: [],
    });

    expect(payload.queries[0].type).toBe('xpath');
  });

  it('passes export_destination_ids through to the payload', () => {
    const payload = buildVisualJobPayload({
      name: 'Test',
      url: 'https://example.com',
      rateLimit: 10,
      fields: [field()],
      destinationIds: ['d-1', 'd-2'],
    });

    expect(payload.export_destination_ids).toEqual(['d-1', 'd-2']);
  });

  it('passes an empty export_destination_ids array through unchanged', () => {
    const payload = buildVisualJobPayload({
      name: 'Test',
      url: 'https://example.com',
      rateLimit: 10,
      fields: [field()],
      destinationIds: [],
    });

    expect(payload.export_destination_ids).toEqual([]);
  });
});
