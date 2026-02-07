import { z } from 'zod';

const fileMappingSchema = z.object({
  delimiter: z.string(),
  enclosure: z.string(),
  escape: z.string(),
  url_column: z.string(),
});

const pdfConfigSchema = z.object({
  page_range: z.tuple([z.number(), z.number()]).optional(),
  table_index: z.number().optional(),
  flatten: z.boolean().optional(),
});

const querySchema = z.object({
  name: z.string().min(1, 'Field name is required'),
  type: z.enum(['xpath', 'regex', 'jsonpath', 'pdf_text', 'pdf_table', 'pdf_metadata']),
  query: z.string(),
  join: z.boolean(),
  pdf_config: pdfConfigSchema.optional(),
});

const schedulingSchema = z.object({
  days: z.array(z.string()),
  hours: z.array(z.number()),
  minutes: z.array(z.number()),
});

const proxyConfigSchema = z.object({
  enabled: z.boolean(),
  geo_targeting: z.enum(['us', 'eu', 'as', 'any']).optional(),
  rotation_strategy: z.enum(['random', 'round-robin']).optional(),
  max_retries: z.number().min(1).max(10).optional(),
  fallback_to_direct: z.boolean().optional(),
});

const renderConfigSchema = z.object({
  enabled: z.boolean(),
  wait_strategy: z.enum(['load', 'domcontentloaded', 'networkidle']).optional(),
  wait_timeout_ms: z.number().min(5000).max(120000).optional(),
  wait_for_selector: z.string().nullable().optional(),
  capture_screenshot: z.boolean().optional(),
  screenshot_full_page: z.boolean().optional(),
  block_resources: z.array(z.string()).optional(),
  fallback_to_standard: z.boolean().optional(),
});

const exportConfigSchema = z.object({
  enabled: z.boolean(),
  formats: z.array(z.enum(['json', 'csv', 'xlsx'])).optional(),
  destination: z.enum(['s3', 'local', 'webhook']).optional(),
  s3_bucket: z.string().nullable().optional(),
  webhook_url: z.string().nullable().optional(),
  include_screenshots: z.boolean().optional(),
  compress: z.boolean().optional(),
});

const notificationConfigSchema = z.object({
  enabled: z.boolean(),
  email_on_success: z.boolean().optional(),
  email_on_failure: z.boolean().optional(),
  email_addresses: z.array(z.string()).optional(),
  webhook_on_success: z.boolean().optional(),
  webhook_on_failure: z.boolean().optional(),
  webhook_url: z.string().nullable().optional(),
});

const baseJobFields = {
  name: z.string().min(1, 'Job name is required'),
  rate_limit: z.coerce.number().min(1, 'Min rate limit is 1').max(8, 'Max rate limit is 8'),
  timezone: z.string(),
  scheduling: schedulingSchema,
  queries: z.array(querySchema).min(1, 'At least one query is required'),
  proxy_config: proxyConfigSchema.optional(),
  render_config: renderConfigSchema.optional(),
  export_config: exportConfigSchema.optional(),
  notification_config: notificationConfigSchema.optional(),
};

const csvJobSchema = z.object({
  source_type: z.literal('csv'),
  source: z.string().min(1, 'Source URL is required'),
  url_template: z.string().optional().default(''),
  file_mapping: fileMappingSchema.refine(data => data.url_column.length > 0, {
    message: 'URL column is required',
    path: ['url_column'],
  }),
  ...baseJobFields,
});

const directUrlJobSchema = z.object({
  source_type: z.literal('direct_url'),
  source: z.string().optional().default(''),
  url_template: z.string().min(1, 'URL template is required'),
  file_mapping: fileMappingSchema,
  ...baseJobFields,
});

export const jobFormSchema = z.discriminatedUnion('source_type', [
  csvJobSchema,
  directUrlJobSchema,
]);

export type JobFormValues = z.infer<typeof jobFormSchema>;
