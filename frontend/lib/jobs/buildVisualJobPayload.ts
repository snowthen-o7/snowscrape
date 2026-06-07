/**
 * buildVisualJobPayload
 * Pure helper that turns the Visual Scraper Builder's extracted fields into a
 * CreateJobDTO. Extracted (mirroring buildAiJobPayload) so the payload shape is
 * unit-testable independently of the React page.
 *
 * The Visual builder scrapes a single target URL, so it must create a
 * `direct_url` job (source_type + url_template). Without source_type the backend
 * defaults to 'csv' and then requires a file_mapping the Visual builder never
 * sends, so job creation was rejected outright.
 */

import type { CreateJobDTO } from '@/lib/api/jobs';

export interface VisualExtractedField {
  name: string;
  selector: string;
  type: 'xpath' | 'css' | 'regex';
}

interface BuildVisualJobPayloadParams {
  name: string;
  url: string;
  rateLimit: number;
  fields: VisualExtractedField[];
  destinationIds: string[];
}

export function buildVisualJobPayload({
  name,
  url,
  rateLimit,
  fields,
  destinationIds,
}: BuildVisualJobPayloadParams): CreateJobDTO {
  const queries = fields.map((field) => ({
    name: field.name,
    // The backend job runner supports xpath/regex (not raw css), so a css
    // selector is downgraded to xpath, matching the AI flow (buildAiJobPayload).
    type: field.type === 'css' ? 'xpath' : field.type,
    query: field.selector,
    join: false,
  }));

  return {
    name,
    source: url,
    source_type: 'direct_url',
    url_template: url,
    rate_limit: rateLimit,
    queries,
    export_destination_ids: destinationIds,
  };
}
