import { describe, it, expect } from 'vitest';
import { EXPORT_FORMATS } from '@/lib/jobs/exportFormats';

describe('EXPORT_FORMATS', () => {
  it('offers exactly JSON, CSV, XLSX, SQL (the formats that work in prod)', () => {
    expect(EXPORT_FORMATS.map((f) => f.value)).toEqual([
      'json',
      'csv',
      'xlsx',
      'sql',
    ]);
  });

  it('does NOT offer Parquet (pyarrow is not bundled in the Lambda, so it 100%-fails)', () => {
    expect(EXPORT_FORMATS.some((f) => f.value === ('parquet' as string))).toBe(
      false
    );
  });

  it('gives every offered format a non-empty label and description', () => {
    for (const f of EXPORT_FORMATS) {
      expect(f.label.trim().length).toBeGreaterThan(0);
      expect(f.description.trim().length).toBeGreaterThan(0);
    }
  });
});
