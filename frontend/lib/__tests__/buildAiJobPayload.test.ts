import { describe, it, expect } from 'vitest';
import { buildAiJobPayload, type AiSuggestionField } from '@/lib/jobs/buildAiJobPayload';

const field = (over: Partial<AiSuggestionField> = {}): AiSuggestionField => ({
  name: 'price',
  type: 'xpath',
  query: '//span[@class="price"]',
  description: 'the product price',
  accepted: true,
  useAi: false,
  ...over,
});

describe('buildAiJobPayload', () => {
  it('includes only accepted fields as queries', () => {
    const payload = buildAiJobPayload({
      name: 'Test',
      url: 'https://example.com',
      rateLimit: 2,
      fields: [
        field({ name: 'price' }),
        field({ name: 'sku', accepted: false }),
      ],
      destinationIds: [],
    });

    expect(payload.queries).toHaveLength(1);
    expect(payload.queries[0].name).toBe('price');
  });

  it('passes export_destination_ids through to the payload', () => {
    const payload = buildAiJobPayload({
      name: 'Test',
      url: 'https://example.com',
      rateLimit: 2,
      fields: [field()],
      destinationIds: ['d-1', 'd-2'],
    });

    expect(payload.export_destination_ids).toEqual(['d-1', 'd-2']);
  });

  it('defaults export_destination_ids to an empty array', () => {
    const payload = buildAiJobPayload({
      name: 'Test',
      url: 'https://example.com',
      rateLimit: 2,
      fields: [field()],
      destinationIds: [],
    });

    expect(payload.export_destination_ids).toEqual([]);
  });

  it('uses the description as the query and ai type when useAi is set', () => {
    const payload = buildAiJobPayload({
      name: 'Test',
      url: 'https://example.com',
      rateLimit: 2,
      fields: [field({ useAi: true, description: 'extract the price', query: '//ignored' })],
      destinationIds: [],
    });

    expect(payload.queries[0].type).toBe('ai');
    expect(payload.queries[0].query).toBe('extract the price');
  });

  it('translates css selectors to real XPath (AI suggest returns css but backend job runs xpath)', () => {
    const payload = buildAiJobPayload({
      name: 'Test',
      url: 'https://example.com',
      rateLimit: 2,
      fields: [field({ type: 'css', useAi: false, query: 'span.price' })],
      destinationIds: [],
    });

    expect(payload.queries[0].type).toBe('xpath');
    expect(payload.queries[0].query).toBe(
      "//span[contains(concat(' ',normalize-space(@class),' '),' price ')]"
    );
  });

  it('throws a clear error when a css selector cannot be translated to XPath', () => {
    expect(() =>
      buildAiJobPayload({
        name: 'Test',
        url: 'https://example.com',
        rateLimit: 2,
        fields: [field({ name: 'odd', type: 'css', useAi: false, query: 'li:nth-child(2)' })],
        destinationIds: [],
      })
    ).toThrow(/could not be converted to XPath/);
  });

  it('does not translate css when the field is flipped to AI (useAi wins)', () => {
    const payload = buildAiJobPayload({
      name: 'Test',
      url: 'https://example.com',
      rateLimit: 2,
      fields: [
        field({ type: 'css', useAi: true, description: 'the price text', query: 'li:nth-child(2)' }),
      ],
      destinationIds: [],
    });

    expect(payload.queries[0].type).toBe('ai');
    expect(payload.queries[0].query).toBe('the price text');
  });

  it('sets source, source_type and url_template from the url', () => {
    const payload = buildAiJobPayload({
      name: 'My Job',
      url: 'https://example.com/products',
      rateLimit: 3,
      fields: [field()],
      destinationIds: [],
    });

    expect(payload.name).toBe('My Job');
    expect(payload.source).toBe('https://example.com/products');
    expect(payload.source_type).toBe('direct_url');
    expect(payload.url_template).toBe('https://example.com/products');
    expect(payload.rate_limit).toBe(3);
  });
});
