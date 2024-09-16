import Papa from 'papaparse';
import { Query } from '@/lib/types';

/**
 * Detects CSV settings using PapaParse and extracts headers
 * @param fileContent - The content of the CSV file
 * @returns Detected CSV settings: delimiter, enclosure, escape, and headers
 */
export const detectCSVSettings = (fileContent: string) => {
  const detected = {
    delimiter: ',',
    enclosure: '"',
    escape: '\\',
    headers: [] as string[],
  };

  Papa.parse(fileContent, {
    delimiter: '', // Auto-detect delimiter
    skipEmptyLines: true,
    preview: 1, // Only parse the first row to detect headers and settings
    complete: (results: Papa.ParseResult<string[]>) => {
      const firstRow: string[] = results.data[0];

      // Set detected delimiter, enclosure, escape if found
      detected.delimiter = results.meta.delimiter || ',';
      detected.headers = firstRow || [];

      // PapaParse doesn't directly detect enclosure and escape, so we'll estimate them
      detected.enclosure = fileContent.includes('"') ? '"' : fileContent.includes("'") ? "'" : '';
      detected.escape = fileContent.includes('\\') ? '\\' : fileContent.includes('/') ? '/' : '';
    },
  });

  return detected;
};

/**
 * Function to extract headers from a CSV file
 * @param fileContent - The content of the file as a string
 * @param delimiter - The delimiter used to separate the fields (default is comma)
 * @returns An array of headers extracted from the first row of the file
 */
export const extractHeadersFromFile = (fileContent: string, delimiter: string = ','): string[] => {
  const rows = fileContent.split('\n');
  const headerRow = rows[0];
  return headerRow.split(delimiter).map(header => header.trim());
};

// Function to validate JSONPath expressions
const validateJSONPath = async (expression: string): Promise<boolean> => {
  if (typeof window === 'undefined') {
    // Skip validation in server-side rendering
    return false;
  }

  try {
    const jsonpath = (await import('jsonpath')).default; // Dynamically import jsonpath
    jsonpath.parse(expression); // Validate the expression
    return true;
  } catch (error) {
    return false;
  }
};


// Function to validate XPath expressions
const validateXPath = (expression: string): boolean => {
  if (typeof window === 'undefined') {
    // Skip validation in server-side rendering
    return false;
  }

  try {
    document.evaluate(expression, document, null, XPathResult.ANY_TYPE, null);
    return true;
  } catch (error) {
    return false;
  }
};

// Function to validate all queries on submit
export const validateQueries = async (queries: Query[]): Promise<(string | null)[]> => {
  const errors: (string | null)[] = [];

  for (const query of queries) {
    if (query.type === 'xpath' && !validateXPath(query.query)) {
      errors.push(`Invalid XPath expression in query: ${query.name}`);
    } else if (query.type === 'jsonpath') {
      const isValid = await validateJSONPath(query.query); // Await the asynchronous validation
      if (!isValid) {
        errors.push(`Invalid JSONPath expression in query: ${query.name}`);
      } else {
        errors.push(null);
      }
    } else {
      errors.push(null); // No error for this query
    }
  }

  return errors;
};

