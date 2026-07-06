import { describe, it, expect } from 'vitest';
import { jobFormSchema } from '@/lib/schemas/jobFormSchema';

// Characterization tests for the job-creation form-validation contract.
// jobFormSchema is the client-side gate on what a user is allowed to submit as a
// scrape job: a discriminated union on `source_type` ('csv' vs 'direct_url') over a
// shared base (name/rate_limit/queries/scheduling + optional proxy/render/export/
// notification configs). These tests pin the rules so a silent loosening (a dropped
// `.min`, a widened enum, a removed refine) fails loudly. No source change.

type Obj = Record<string, unknown>;
type Result = ReturnType<typeof jobFormSchema.safeParse>;

const validFileMapping = (over: Obj = {}): Obj => ({
  delimiter: ',',
  enclosure: '"',
  escape: '\\',
  url_column: 'url',
  ...over,
});

const validQuery = (over: Obj = {}): Obj => ({
  name: 'price',
  type: 'xpath',
  query: '//span[@class="price"]',
  join: false,
  ...over,
});

// The shared base fields required by BOTH job variants.
const validBase = (over: Obj = {}): Obj => ({
  name: 'My Job',
  rate_limit: 4,
  timezone: 'UTC',
  scheduling: { days: [], hours: [], minutes: [] },
  queries: [validQuery()],
  ...over,
});

const validCsvJob = (over: Obj = {}): Obj => ({
  source_type: 'csv',
  source: 'https://example.com/list.csv',
  url_template: '',
  file_mapping: validFileMapping(),
  ...validBase(),
  ...over,
});

const validDirectUrlJob = (over: Obj = {}): Obj => ({
  source_type: 'direct_url',
  source: '',
  url_template: 'https://example.com/{id}',
  file_mapping: validFileMapping(),
  ...validBase(),
  ...over,
});

const messages = (res: Result): string[] =>
  res.success ? [] : res.error.issues.map((i) => i.message);

const issueAtPath = (res: Result, path: string) =>
  res.success ? undefined : res.error.issues.find((i) => i.path.join('.') === path);

describe('jobFormSchema', () => {
  describe('the source_type discriminator', () => {
    it('accepts a fully-valid csv job', () => {
      const res = jobFormSchema.safeParse(validCsvJob());
      expect(res.success).toBe(true);
    });

    it('accepts a fully-valid direct_url job', () => {
      const res = jobFormSchema.safeParse(validDirectUrlJob());
      expect(res.success).toBe(true);
    });

    it('rejects an unknown source_type and blames the discriminator field', () => {
      const res = jobFormSchema.safeParse({ ...validCsvJob(), source_type: 'api' });
      expect(res.success).toBe(false);
      expect(issueAtPath(res, 'source_type')).toBeDefined();
    });

    it('rejects a missing source_type', () => {
      const job = validCsvJob();
      delete (job as Obj).source_type;
      const res = jobFormSchema.safeParse(job);
      expect(res.success).toBe(false);
      expect(issueAtPath(res, 'source_type')).toBeDefined();
    });

    it('preserves the discriminant on the parsed value', () => {
      const res = jobFormSchema.safeParse(validDirectUrlJob());
      expect(res.success).toBe(true);
      if (res.success) expect(res.data.source_type).toBe('direct_url');
    });
  });

  describe('csv variant', () => {
    it('requires a non-empty source', () => {
      const res = jobFormSchema.safeParse(validCsvJob({ source: '' }));
      expect(res.success).toBe(false);
      expect(issueAtPath(res, 'source')?.message).toBe('Source URL is required');
    });

    it('allows an empty url_template (csv derives URLs from the file, not a template)', () => {
      const res = jobFormSchema.safeParse(validCsvJob({ url_template: '' }));
      expect(res.success).toBe(true);
    });

    it('requires file_mapping.url_column to be non-empty (the csv-only refine)', () => {
      const res = jobFormSchema.safeParse(
        validCsvJob({ file_mapping: validFileMapping({ url_column: '' }) })
      );
      expect(res.success).toBe(false);
      expect(issueAtPath(res, 'file_mapping.url_column')?.message).toBe(
        'URL column is required'
      );
    });

    it('passes once url_column is supplied', () => {
      const res = jobFormSchema.safeParse(
        validCsvJob({ file_mapping: validFileMapping({ url_column: 'product_url' }) })
      );
      expect(res.success).toBe(true);
    });

    it('requires every file_mapping field to be present', () => {
      const res = jobFormSchema.safeParse(
        validCsvJob({ file_mapping: { url_column: 'url' } })
      );
      expect(res.success).toBe(false);
    });
  });

  describe('direct_url variant', () => {
    it('requires a non-empty url_template', () => {
      const res = jobFormSchema.safeParse(validDirectUrlJob({ url_template: '' }));
      expect(res.success).toBe(false);
      expect(issueAtPath(res, 'url_template')?.message).toBe('URL template is required');
    });

    it('allows an empty source (the template, not a file, drives the URLs)', () => {
      const res = jobFormSchema.safeParse(validDirectUrlJob({ source: '' }));
      expect(res.success).toBe(true);
    });

    it('does NOT require url_column (the url_column refine is csv-only)', () => {
      const res = jobFormSchema.safeParse(
        validDirectUrlJob({ file_mapping: validFileMapping({ url_column: '' }) })
      );
      expect(res.success).toBe(true);
    });
  });

  describe('shared base fields', () => {
    it('requires a non-empty job name', () => {
      const res = jobFormSchema.safeParse(validCsvJob({ name: '' }));
      expect(res.success).toBe(false);
      expect(messages(res)).toContain('Job name is required');
    });

    it('rejects a rate_limit below 1', () => {
      const res = jobFormSchema.safeParse(validCsvJob({ rate_limit: 0 }));
      expect(res.success).toBe(false);
      expect(messages(res)).toContain('Min rate limit is 1');
    });

    it('rejects a rate_limit above 8', () => {
      const res = jobFormSchema.safeParse(validCsvJob({ rate_limit: 9 }));
      expect(res.success).toBe(false);
      expect(messages(res)).toContain('Max rate limit is 8');
    });

    it('accepts the rate_limit boundaries 1 and 8', () => {
      expect(jobFormSchema.safeParse(validCsvJob({ rate_limit: 1 })).success).toBe(true);
      expect(jobFormSchema.safeParse(validCsvJob({ rate_limit: 8 })).success).toBe(true);
    });

    it('requires at least one query', () => {
      const res = jobFormSchema.safeParse(validCsvJob({ queries: [] }));
      expect(res.success).toBe(false);
      expect(messages(res)).toContain('At least one query is required');
    });

    it('requires each query to have a non-empty name', () => {
      const res = jobFormSchema.safeParse(
        validCsvJob({ queries: [validQuery({ name: '' })] })
      );
      expect(res.success).toBe(false);
      expect(messages(res)).toContain('Field name is required');
    });

    it('rejects an unknown query type and blames the offending query field', () => {
      const res = jobFormSchema.safeParse(
        validCsvJob({ queries: [validQuery({ type: 'css' })] })
      );
      expect(res.success).toBe(false);
      expect(issueAtPath(res, 'queries.0.type')).toBeDefined();
    });

    it('accepts every documented query type', () => {
      for (const type of [
        'xpath',
        'regex',
        'jsonpath',
        'pdf_text',
        'pdf_table',
        'pdf_metadata',
        'ai',
      ]) {
        const res = jobFormSchema.safeParse(
          validCsvJob({ queries: [validQuery({ type })] })
        );
        expect(res.success, `type ${type} should be valid`).toBe(true);
      }
    });

    it('caps export_destination_ids at 10', () => {
      const eleven = Array.from({ length: 11 }, (_, i) => `dest-${i}`);
      const res = jobFormSchema.safeParse(
        validCsvJob({ export_destination_ids: eleven })
      );
      expect(res.success).toBe(false);
      expect(issueAtPath(res, 'export_destination_ids')).toBeDefined();
    });

    it('accepts exactly 10 export_destination_ids', () => {
      const ten = Array.from({ length: 10 }, (_, i) => `dest-${i}`);
      const res = jobFormSchema.safeParse(validCsvJob({ export_destination_ids: ten }));
      expect(res.success).toBe(true);
    });
  });

  describe('optional nested configs', () => {
    it('is valid with all optional configs omitted', () => {
      // validBase() deliberately sets none of proxy/render/export/notification.
      const res = jobFormSchema.safeParse(validCsvJob());
      expect(res.success).toBe(true);
    });

    it('rejects proxy_config.max_retries above 10', () => {
      const res = jobFormSchema.safeParse(
        validCsvJob({ proxy_config: { enabled: true, max_retries: 11 } })
      );
      expect(res.success).toBe(false);
      expect(issueAtPath(res, 'proxy_config.max_retries')).toBeDefined();
    });

    it('requires proxy_config.enabled when proxy_config is present', () => {
      const res = jobFormSchema.safeParse(
        validCsvJob({ proxy_config: { max_retries: 3 } })
      );
      expect(res.success).toBe(false);
      expect(issueAtPath(res, 'proxy_config.enabled')).toBeDefined();
    });

    it('rejects render_config.wait_timeout_ms below 5000', () => {
      const res = jobFormSchema.safeParse(
        validCsvJob({ render_config: { enabled: true, wait_timeout_ms: 4999 } })
      );
      expect(res.success).toBe(false);
      expect(issueAtPath(res, 'render_config.wait_timeout_ms')).toBeDefined();
    });

    it('accepts the render_config.wait_timeout_ms boundary 5000', () => {
      const res = jobFormSchema.safeParse(
        validCsvJob({ render_config: { enabled: true, wait_timeout_ms: 5000 } })
      );
      expect(res.success).toBe(true);
    });

    it('rejects an export_config format outside json/csv/xlsx', () => {
      const res = jobFormSchema.safeParse(
        validCsvJob({ export_config: { enabled: true, formats: ['parquet'] } })
      );
      expect(res.success).toBe(false);
      expect(issueAtPath(res, 'export_config.formats.0')).toBeDefined();
    });

    it('accepts the json/csv/xlsx export_config formats', () => {
      const res = jobFormSchema.safeParse(
        validCsvJob({ export_config: { enabled: true, formats: ['json', 'csv', 'xlsx'] } })
      );
      expect(res.success).toBe(true);
    });
  });

  describe('unknown-key handling', () => {
    it('strips an unknown top-level key rather than rejecting it', () => {
      const res = jobFormSchema.safeParse(validCsvJob({ totally_made_up: 'x' }));
      expect(res.success).toBe(true);
      if (res.success) expect('totally_made_up' in res.data).toBe(false);
    });
  });
});
