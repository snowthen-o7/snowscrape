/**
 * buildAiJobPayload
 * Pure helper that turns the AI-assisted creation wizard's state into a
 * CreateJobDTO. Extracted so the payload shape (including export destinations)
 * is unit-testable independently of the React page.
 */

import type { CreateJobDTO } from '@/lib/api/jobs';

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
    .map((field) => ({
      name: field.name,
      // The backend job runner supports xpath/regex/ai, not raw css, so a css
      // suggestion is downgraded to xpath unless the user flipped it to AI.
      type: field.useAi ? 'ai' : field.type === 'css' ? 'xpath' : field.type,
      query: field.useAi ? field.description : field.query,
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
