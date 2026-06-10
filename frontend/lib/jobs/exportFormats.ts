/**
 * exportFormats
 * Single source of truth for the download/export formats SnowScrape OFFERS to
 * users. Extracted from JobCard so the offered set is unit-testable independently
 * of the React component.
 *
 * Parquet is intentionally NOT offered. The backend Parquet converter needs
 * pyarrow, which is intentionally not bundled in the Lambda (size / cold-start
 * cost, see backend/format_converter.py), so a Parquet download fails 100% of
 * the time in prod. Offering it in the UI was a guaranteed dead end. The backend
 * still carries a dormant convert_to_parquet (raising a clear, handled error) so
 * re-enabling later is just bundling pyarrow + re-listing the format here.
 */

export type ExportFormat = 'json' | 'csv' | 'xlsx' | 'sql';

export interface ExportFormatOption {
  value: ExportFormat;
  label: string;
  description: string;
}

export const EXPORT_FORMATS: ExportFormatOption[] = [
  { value: 'json', label: 'JSON', description: 'JavaScript Object Notation' },
  { value: 'csv', label: 'CSV', description: 'Comma-Separated Values' },
  { value: 'xlsx', label: 'Excel (XLSX)', description: 'Microsoft Excel format' },
  { value: 'sql', label: 'SQL', description: 'SQL INSERT statements' },
];
