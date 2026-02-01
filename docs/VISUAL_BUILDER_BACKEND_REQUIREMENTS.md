# Visual Scraper Builder - Backend Requirements

The Visual Scraper Builder requires two backend endpoints to function properly.

## Required Endpoints

### 1. POST /scraper/preview

Fetches a URL and returns a simplified DOM structure for visual selection.

**Request Body:**
```json
{
  "url": "https://example.com/page"
}
```

**Response:**
```json
{
  "url": "https://example.com/page",
  "title": "Page Title",
  "elements": [
    {
      "id": "el-1",
      "type": "h1",
      "text": "Sample Heading",
      "xpath": "//h1[@class='heading']",
      "css": ".heading",
      "path": "body > div > h1.heading"
    },
    {
      "id": "el-2",
      "type": "span",
      "text": "$99.99",
      "xpath": "//span[@class='price']",
      "css": ".price",
      "path": "body > div > span.price"
    }
  ]
}
```

**Backend Implementation Notes:**
- Fetch the target URL
- Parse the HTML/DOM
- Extract text-containing elements (headings, paragraphs, spans, divs with text, etc.)
- Generate XPath, CSS selectors, and DOM path for each element
- Limit text preview to ~100 characters
- Return up to 50-100 most relevant elements (filter out empty/whitespace-only elements)
- Handle JavaScript-rendered content if possible

### 2. POST /scraper/test

Tests extraction with given selectors on a URL and returns the extracted data.

**Request Body:**
```json
{
  "url": "https://example.com/page",
  "selectors": [
    {
      "name": "title",
      "type": "xpath",
      "selector": "//h1[@class='product-title']"
    },
    {
      "name": "price",
      "type": "css",
      "selector": ".price"
    },
    {
      "name": "description",
      "type": "regex",
      "selector": "Description:\\s*(.+)"
    }
  ]
}
```

**Response:**
```json
[
  {
    "title": "Premium Wireless Headphones",
    "price": "$299.99",
    "description": "High-quality noise-cancelling headphones..."
  }
]
```

**Backend Implementation Notes:**
- Fetch the target URL
- Apply each selector based on its type (xpath, css, regex)
- Extract the matched text/data
- Return as an array with field names as keys
- Handle errors gracefully (return null/empty string for failed selectors)
- Support JavaScript rendering if selector type requires it

## Error Handling

Both endpoints should return appropriate error responses:

**400 Bad Request:**
- Invalid URL format
- Missing required fields
- Invalid selector syntax

**404 Not Found:**
- URL doesn't exist or returns 404

**500 Internal Server Error:**
- Network errors
- Parsing errors
- Unexpected server errors

**Response Format:**
```json
{
  "error": "Error message here",
  "details": "Additional context if available"
}
```

## Authentication

Both endpoints require Bearer token authentication:
```
Authorization: Bearer {clerk_jwt_token}
```

## Rate Limiting

Consider implementing rate limiting for these endpoints:
- Max 10 requests per minute per user for `/scraper/preview`
- Max 20 requests per minute per user for `/scraper/test`

## Timeout

Both endpoints should have reasonable timeouts:
- `/scraper/preview`: 10 seconds
- `/scraper/test`: 10 seconds

If the target URL takes longer to load, return a timeout error.
