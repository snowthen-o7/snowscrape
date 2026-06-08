/**
 * buildAiJobPayload
 * Pure helper that turns the AI-assisted creation wizard's state into a
 * CreateJobDTO. Extracted so the payload shape (including export destinations)
 * is unit-testable independently of the React page.
 */

import type { CreateJobDTO } from '@/lib/api/jobs';
import { cssSelectorToXPath } from '@/lib/jobs/cssToXpath';

export interface AiSuggestionField {
  name: string;
  type: 'xpath' | 'css' | 'regex' | 'ai';
  query: string;
  description: string;
  accepted: boolean;
  useAi: boolean;
}

interface BuildAiJobPayloadParams {
  name: string;
  url: string;
  rateLimit: number;
  fields: AiSuggestionField[];
  destinationIds: string[];
}

export function buildAiJobPayload({
  name,
  url,
  rateLimit,
  fields,
  destinationIds,
}: BuildAiJobPayloadParams): CreateJobDTO {
  const queries = fields
    .filter((f) => f.accepted)
    .map((field) => {
      // The user can flip any suggestion to AI (natural-language extraction),
      // which takes precedence over the structured selector.
      if (field.useAi) {
        return { name: field.name, type: 'ai', query: field.description, join: false };
      }
      if (field.type === 'css') {
        // The backend job runner only evaluates xpath/regex/jsonpath, not raw
        // css. Translate the css selector to XPath so it actually extracts; if
        // it cannot be translated faithfully, fail loudly rather than silently
        // shipping an XPath-labeled css string that extracts nothing (issue #26).
        const xpath = cssSelectorToXPath(field.query);
        if (xpath === null) {
          throw new Error(
            `Field "${field.name}": the CSS selector "${field.query}" could not be converted to XPath. Edit it to an XPath expression, or switch the field to AI extraction.`
          );
        }
        return { name: field.name, type: 'xpath', query: xpath, join: false };
      }
      return { name: field.name, type: field.type, query: field.query, join: false };
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
