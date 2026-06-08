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
import { cssSelectorToXPath } from '@/lib/jobs/cssToXpath';

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
  const queries = fields.map((field) => {
    if (field.type === 'css') {
      // The backend job runner only evaluates xpath/regex/jsonpath, not raw css.
      // Translate the css selector to XPath so the field actually extracts at
      // scrape time. If it cannot be translated faithfully, fail loudly rather
      // than silently shipping an XPath-labeled css string that extracts nothing
      // (issue #26).
      const xpath = cssSelectorToXPath(field.selector);
      if (xpath === null) {
        throw new Error(
          `Field "${field.name}": the CSS selector "${field.selector}" could not be converted to XPath. Rewrite it as an XPath expression and set the field type to XPath.`
        );
      }
      return { name: field.name, type: 'xpath', query: xpath, join: false };
    }
    return { name: field.name, type: field.type, query: field.selector, join: false };
  });

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
