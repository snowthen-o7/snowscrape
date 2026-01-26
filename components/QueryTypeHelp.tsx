'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {  } from '@snowforge/ui';
import { HelpCircle, Code, FileText, FileJson, Table, Type, Info } from 'lucide-react';

export function QueryTypeHelpButton() {
  const [open, setOpen] = useState(false);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-1 text-muted-foreground">
          <HelpCircle className="h-4 w-4" />
          Query Help
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Query Types Guide</DialogTitle>
          <DialogDescription>
            Learn how to use each query type to extract data from different content formats.
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="xpath" className="mt-4">
          <TabsList className="grid w-full grid-cols-6">
            <TabsTrigger value="xpath" className="text-xs">XPath</TabsTrigger>
            <TabsTrigger value="regex" className="text-xs">Regex</TabsTrigger>
            <TabsTrigger value="jsonpath" className="text-xs">JSONPath</TabsTrigger>
            <TabsTrigger value="pdf_table" className="text-xs">PDF Table</TabsTrigger>
            <TabsTrigger value="pdf_text" className="text-xs">PDF Text</TabsTrigger>
            <TabsTrigger value="pdf_meta" className="text-xs">PDF Meta</TabsTrigger>
          </TabsList>

          {/* XPath Tab */}
          <TabsContent value="xpath" className="space-y-4 mt-4">
            <div className="flex items-center gap-2 text-lg font-semibold">
              <Code className="h-5 w-5" />
              XPath (HTML/XML)
            </div>
            <p className="text-sm text-muted-foreground">
              XPath is a query language for selecting nodes from HTML or XML documents.
              Use it to extract specific elements from web pages.
            </p>

            <div className="space-y-3">
              <h4 className="font-medium">Common Examples</h4>
              <div className="space-y-2 text-sm">
                <div className="bg-muted p-3 rounded-lg font-mono">
                  <p className="text-xs text-muted-foreground mb-1">Get all product titles:</p>
                  <code>//h2[@class=&quot;product-title&quot;]/text()</code>
                </div>
                <div className="bg-muted p-3 rounded-lg font-mono">
                  <p className="text-xs text-muted-foreground mb-1">Get all links:</p>
                  <code>//a/@href</code>
                </div>
                <div className="bg-muted p-3 rounded-lg font-mono">
                  <p className="text-xs text-muted-foreground mb-1">Get price from a specific div:</p>
                  <code>//div[@id=&quot;price&quot;]/span/text()</code>
                </div>
                <div className="bg-muted p-3 rounded-lg font-mono">
                  <p className="text-xs text-muted-foreground mb-1">Get table cells:</p>
                  <code>//table//tr/td[2]/text()</code>
                </div>
              </div>

              <h4 className="font-medium mt-4">Quick Reference</h4>
              <div className="text-sm space-y-1">
                <p><code className="bg-muted px-1 rounded">//</code> - Select from anywhere in document</p>
                <p><code className="bg-muted px-1 rounded">/</code> - Select from root/current node</p>
                <p><code className="bg-muted px-1 rounded">[@attr=&quot;value&quot;]</code> - Filter by attribute</p>
                <p><code className="bg-muted px-1 rounded">/text()</code> - Get text content</p>
                <p><code className="bg-muted px-1 rounded">/@href</code> - Get attribute value</p>
                <p><code className="bg-muted px-1 rounded">[1]</code> - Get first match (1-indexed)</p>
              </div>
            </div>
          </TabsContent>

          {/* Regex Tab */}
          <TabsContent value="regex" className="space-y-4 mt-4">
            <div className="flex items-center gap-2 text-lg font-semibold">
              <Type className="h-5 w-5" />
              Regex (Text Patterns)
            </div>
            <p className="text-sm text-muted-foreground">
              Regular expressions match text patterns. Use for extracting specific formats
              like prices, dates, emails, or any structured text.
            </p>

            <div className="space-y-3">
              <h4 className="font-medium">Common Examples</h4>
              <div className="space-y-2 text-sm">
                <div className="bg-muted p-3 rounded-lg font-mono">
                  <p className="text-xs text-muted-foreground mb-1">Extract prices ($XX.XX):</p>
                  <code>\$[\d,]+\.?\d*</code>
                </div>
                <div className="bg-muted p-3 rounded-lg font-mono">
                  <p className="text-xs text-muted-foreground mb-1">Extract email addresses:</p>
                  <code>[\w.-]+@[\w.-]+\.\w+</code>
                </div>
                <div className="bg-muted p-3 rounded-lg font-mono">
                  <p className="text-xs text-muted-foreground mb-1">Extract dates (MM/DD/YYYY):</p>
                  <code>\d{2}/\d{2}/\d{4}</code>
                </div>
                <div className="bg-muted p-3 rounded-lg font-mono">
                  <p className="text-xs text-muted-foreground mb-1">Extract phone numbers:</p>
                  <code>\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}</code>
                </div>
              </div>

              <h4 className="font-medium mt-4">Quick Reference</h4>
              <div className="text-sm space-y-1">
                <p><code className="bg-muted px-1 rounded">\d</code> - Any digit (0-9)</p>
                <p><code className="bg-muted px-1 rounded">\w</code> - Any word character (a-z, A-Z, 0-9, _)</p>
                <p><code className="bg-muted px-1 rounded">.</code> - Any character</p>
                <p><code className="bg-muted px-1 rounded">+</code> - One or more</p>
                <p><code className="bg-muted px-1 rounded">*</code> - Zero or more</p>
                <p><code className="bg-muted px-1 rounded">{`{n}`}</code> - Exactly n times</p>
                <p><code className="bg-muted px-1 rounded">[abc]</code> - Any character in set</p>
                <p><code className="bg-muted px-1 rounded">(group)</code> - Capture group</p>
              </div>
            </div>
          </TabsContent>

          {/* JSONPath Tab */}
          <TabsContent value="jsonpath" className="space-y-4 mt-4">
            <div className="flex items-center gap-2 text-lg font-semibold">
              <FileJson className="h-5 w-5" />
              JSONPath (JSON APIs)
            </div>
            <p className="text-sm text-muted-foreground">
              JSONPath queries JSON data structures. Use for extracting data from
              REST APIs or any JSON response.
            </p>

            <div className="space-y-3">
              <h4 className="font-medium">Common Examples</h4>
              <div className="space-y-2 text-sm">
                <div className="bg-muted p-3 rounded-lg font-mono">
                  <p className="text-xs text-muted-foreground mb-1">Get all product names:</p>
                  <code>$.products[*].name</code>
                </div>
                <div className="bg-muted p-3 rounded-lg font-mono">
                  <p className="text-xs text-muted-foreground mb-1">Get first item&apos;s price:</p>
                  <code>$.items[0].price</code>
                </div>
                <div className="bg-muted p-3 rounded-lg font-mono">
                  <p className="text-xs text-muted-foreground mb-1">Get nested data:</p>
                  <code>$.data.results[*].attributes.title</code>
                </div>
                <div className="bg-muted p-3 rounded-lg font-mono">
                  <p className="text-xs text-muted-foreground mb-1">Filter by condition:</p>
                  <code>$.products[?(@.price &lt; 100)].name</code>
                </div>
              </div>

              <h4 className="font-medium mt-4">Quick Reference</h4>
              <div className="text-sm space-y-1">
                <p><code className="bg-muted px-1 rounded">$</code> - Root object</p>
                <p><code className="bg-muted px-1 rounded">.key</code> - Access property</p>
                <p><code className="bg-muted px-1 rounded">[0]</code> - Array index (0-based)</p>
                <p><code className="bg-muted px-1 rounded">[*]</code> - All array elements</p>
                <p><code className="bg-muted px-1 rounded">..</code> - Recursive descent</p>
                <p><code className="bg-muted px-1 rounded">[?(@.x)]</code> - Filter expression</p>
              </div>
            </div>
          </TabsContent>

          {/* PDF Table Tab */}
          <TabsContent value="pdf_table" className="space-y-4 mt-4">
            <div className="flex items-center gap-2 text-lg font-semibold">
              <Table className="h-5 w-5" />
              PDF Table Extraction
            </div>
            <p className="text-sm text-muted-foreground">
              Extracts tables from PDF documents. Automatically detects table structures
              and returns data with headers and rows.
            </p>

            <div className="space-y-3">
              <h4 className="font-medium">How It Works</h4>
              <div className="text-sm space-y-2">
                <p>1. The scraper automatically detects tables in the PDF</p>
                <p>2. First row is treated as column headers</p>
                <p>3. Data is returned as structured JSON with headers and rows</p>
              </div>

              <h4 className="font-medium mt-4">Expression Field (Optional)</h4>
              <div className="space-y-2 text-sm">
                <div className="bg-muted p-3 rounded-lg">
                  <p className="text-xs text-muted-foreground mb-1">Leave empty:</p>
                  <p>Returns all columns from all tables</p>
                </div>
                <div className="bg-muted p-3 rounded-lg">
                  <p className="text-xs text-muted-foreground mb-1">Enter a column name:</p>
                  <p>Returns only values from that specific column</p>
                  <code className="block mt-1">Player Name</code>
                </div>
              </div>

              <h4 className="font-medium mt-4">Example Output</h4>
              <div className="bg-muted p-3 rounded-lg font-mono text-xs overflow-x-auto">
                <pre>{`{
  "headers": ["Team", "Player", "Status"],
  "rows": [
    { "Team": "LAL", "Player": "LeBron James", "Status": "Probable" },
    { "Team": "LAL", "Player": "Anthony Davis", "Status": "Questionable" }
  ]
}`}</pre>
              </div>

              <div className="bg-blue-500/10 border border-blue-500/30 p-3 rounded-lg mt-4">
                <div className="flex gap-2">
                  <Info className="h-4 w-4 text-blue-500 mt-0.5" />
                  <p className="text-sm">Perfect for NBA injury reports, financial statements,
                  schedules, and any PDF with tabular data.</p>
                </div>
              </div>
            </div>
          </TabsContent>

          {/* PDF Text Tab */}
          <TabsContent value="pdf_text" className="space-y-4 mt-4">
            <div className="flex items-center gap-2 text-lg font-semibold">
              <FileText className="h-5 w-5" />
              PDF Text Extraction
            </div>
            <p className="text-sm text-muted-foreground">
              Extracts all text content from a PDF. Optionally apply a regex pattern
              to extract specific information from the text.
            </p>

            <div className="space-y-3">
              <h4 className="font-medium">Expression Field (Optional)</h4>
              <div className="space-y-2 text-sm">
                <div className="bg-muted p-3 rounded-lg">
                  <p className="text-xs text-muted-foreground mb-1">Leave empty:</p>
                  <p>Returns all text from the PDF as a single string</p>
                </div>
                <div className="bg-muted p-3 rounded-lg">
                  <p className="text-xs text-muted-foreground mb-1">Enter a regex pattern:</p>
                  <p>Extracts all matches of the pattern from the text</p>
                  <code className="block mt-1">Report Date: (\d{2}/\d{2}/\d{4})</code>
                </div>
              </div>

              <h4 className="font-medium mt-4">Use Cases</h4>
              <div className="text-sm space-y-1">
                <p>- Extract all text for full-text search</p>
                <p>- Find specific dates, numbers, or IDs with regex</p>
                <p>- Extract paragraphs matching a pattern</p>
                <p>- Get document content when tables aren&apos;t present</p>
              </div>

              <h4 className="font-medium mt-4">Example with Regex</h4>
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">To extract all dates from a PDF:</p>
                <div className="bg-muted p-3 rounded-lg font-mono text-sm">
                  <code>\d{2}/\d{2}/\d{4}</code>
                </div>
                <p className="text-sm text-muted-foreground">Returns: [&quot;01/23/2026&quot;, &quot;01/24/2026&quot;, ...]</p>
              </div>
            </div>
          </TabsContent>

          {/* PDF Metadata Tab */}
          <TabsContent value="pdf_meta" className="space-y-4 mt-4">
            <div className="flex items-center gap-2 text-lg font-semibold">
              <Info className="h-5 w-5" />
              PDF Metadata
            </div>
            <p className="text-sm text-muted-foreground">
              Extracts metadata from the PDF file itself, such as title, author,
              creation date, and page count.
            </p>

            <div className="space-y-3">
              <h4 className="font-medium">Expression Field</h4>
              <p className="text-sm">Not used - leave empty. All metadata is returned automatically.</p>

              <h4 className="font-medium mt-4">Returned Fields</h4>
              <div className="bg-muted p-3 rounded-lg font-mono text-xs overflow-x-auto">
                <pre>{`{
  "title": "Injury Report",
  "author": "NBA",
  "subject": "",
  "creator": "Adobe Acrobat",
  "producer": "Adobe PDF Library",
  "creation_date": "D:20260123120000",
  "modification_date": "D:20260123120000",
  "page_count": 3
}`}</pre>
              </div>

              <h4 className="font-medium mt-4">Use Cases</h4>
              <div className="text-sm space-y-1">
                <p>- Verify document authenticity</p>
                <p>- Track document versions by modification date</p>
                <p>- Get page count for large documents</p>
                <p>- Extract author/creator information</p>
              </div>
            </div>
          </TabsContent>
        </Tabs>

        <div className="mt-6 pt-4 border-t">
          <h4 className="font-medium mb-2">Tips</h4>
          <ul className="text-sm text-muted-foreground space-y-1">
            <li>- <strong>Field Name</strong> is always required - it&apos;s the key for your extracted data</li>
            <li>- Enable <strong>Join</strong> to combine multiple results into a single pipe-separated string</li>
            <li>- For PDFs, the scraper auto-detects the content type - no special setup needed</li>
            <li>- Test your queries on a single URL before scheduling recurring jobs</li>
          </ul>
        </div>
      </DialogContent>
    </Dialog>
  );
}
