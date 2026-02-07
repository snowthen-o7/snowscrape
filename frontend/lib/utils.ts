import Papa from 'papaparse';
import { Query, Scheduling } from '@/lib/types';

// Re-export cn from shared package for backwards compatibility
export { cn } from '@snowforge/ui';

export const capitalize = (str: string) => {
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
};

// Helper function to calculate the time difference
const calculateTimeUntilNextRun = (nextRunTime: Date) => {
  const now = new Date();
  const diffInMilliseconds = nextRunTime.getTime() - now.getTime(); // Get timestamps for the operation
  const diffInMinutes = Math.floor(diffInMilliseconds / 1000 / 60);
  const diffInHours = Math.floor(diffInMinutes / 60);
  const diffInDays = Math.floor(diffInHours / 24);

  const remainingTime = [];

  if (diffInDays > 0) remainingTime.push(`${diffInDays} day(s)`);
  if (diffInHours % 24 > 0) remainingTime.push(`${diffInHours % 24} hour(s)`);
  if (diffInMinutes % 60 > 0) remainingTime.push(`${diffInMinutes % 60} minute(s)`);

  return remainingTime.length ? remainingTime.join(', ') : "Now";  // Concatenate and return
};

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

// Helper function to estimate next run based on scheduling
export const getNextRunTime = (scheduling: Scheduling, status: string) => {
  console.log(scheduling);
  if (status === "paused") {
    return "Paused";  // Show Paused if the job is paused
  }

  const now = new Date();
  const nextRunTime = new Date(now.getTime()); // Start with the current time

  // Calculate next minute (supporting multiples of 5)
  if (scheduling.minutes?.length) {
    const currentMinute = now.getMinutes();
    const nextMinute = scheduling.minutes.find(min => min > currentMinute) || scheduling.minutes[0];
    console.log(currentMinute);
    console.log(nextMinute);
    
    // Set the minute and keep the hour if minutes are greater than now, else move to next hour
    nextRunTime.setMinutes(nextMinute, 0, 0);

    // If the next minute has already passed in the current hour, go to the next hour
    if (nextMinute <= currentMinute) {
      nextRunTime.setHours(nextRunTime.getHours() + 1);
    }
  } else {
    nextRunTime.setMinutes(0, 0, 0);  // Default to the top of the hour if no minute is specified
  }

  // Calculate next hour
  if (scheduling.hours?.includes(24)) {
    // "Every Hour" means we leave the hour as it is (any hour is valid)
    // So we don't change the hour here, it will remain whatever is set after minute calculation
  } else if (scheduling.hours?.length) {
    const currentHour = now.getHours();
    const nextHour = scheduling.hours.find(hour => hour > currentHour) || scheduling.hours[0];  // Get the next hour
    nextRunTime.setHours(nextHour);

    // If the next hour is earlier than or equal to the current time, move to the next day
    if (nextHour <= currentHour) {
      nextRunTime.setDate(nextRunTime.getDate() + 1);
    }
  }

  // Calculate next day
  if (scheduling.days?.includes("Every Day")) {
    // "Every Day" means we don't need to change the day, as it can run daily
  } else if (scheduling.days?.length) {
    const currentDay = now.getDay();
    const daysOfWeek = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const nextDay = scheduling.days.map(day => daysOfWeek.indexOf(day))
      .find(dayIndex => dayIndex > currentDay) || daysOfWeek.indexOf(scheduling.days[0]);

    if (nextDay <= currentDay) {
      nextRunTime.setDate(nextRunTime.getDate() + (7 - (currentDay - nextDay)));  // Move to the next week if necessary
    } else {
      nextRunTime.setDate(nextRunTime.getDate() + (nextDay - currentDay));
    }
  }

  const timeUntilNextRun = calculateTimeUntilNextRun(nextRunTime);
  return `${timeUntilNextRun} (${nextRunTime.toLocaleString()})`;  // Return the time until the next run with the date
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

export const validateHTTP = async (sourceUrl: string): Promise<{ delimiter: string; enclosure: string; escape: string; headers: string[] }> => {
  try {
    const response = await fetch(sourceUrl);
    if (!response.ok) {
      throw new Error('Invalid URL or cannot reach the source.');
    }

    const fileText = await response.text();
    const detected = detectCSVSettings(fileText); // Detect CSV settings and headers
    return {
      delimiter: detected.delimiter || ',',
      enclosure: detected.enclosure || '',
      escape: detected.escape || '',
      headers: detected.headers || [],
    };
  } catch (error) {
    throw new Error(`HTTP validation error: ${(error as Error).message}`);
  }
};

/**
 * Validates an SFTP URL by making a POST request to the serverless API.
 * @param sftpUrl - The SFTP URL string
 * @returns A promise that resolves if valid, rejects if invalid
 */
export const validateSFTP = async (sftpUrl: string): Promise<{ delimiter: string; enclosure: string; escape: string; headers: string[] }> => {
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/validate-sftp-url`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ sftp_url: sftpUrl }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to validate SFTP URL');
    }

    const result = await response.json();
    if (result.message !== 'SFTP URL validated successfully') {
      throw new Error('Failed to validate SFTP URL');
    }

    // Return the file mapping data from the response
    return {
      delimiter: result.delimiter,
      enclosure: result.enclosure,
      escape: result.escape,
      headers: result.headers,
    };
  } catch (error) {
    throw new Error((error as Error).message);
  }
};