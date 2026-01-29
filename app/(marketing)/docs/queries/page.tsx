/**
 * Query Types Documentation Page
 */

import { DocLayout } from '@/components/docs';
import Link from 'next/link';

export default function QueriesPage() {
  return (
    <DocLayout
      title="Query Types"
      description="Master XPath, CSS selectors, and Regex patterns to extract exactly the data you need."
    >
      <section className="space-y-6">
        <p className="text-muted-foreground">
          SnowScrape supports three query types for data extraction. Each has its strengths, and you can mix
          them within a single job based on what works best for each data point.
        </p>

        <div className="grid gap-4 md:grid-cols-3 mt-6">
          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold text-accent-foreground">XPath</h4>
            <p className="text-sm text-muted-foreground mt-1">Best for complex DOM traversal</p>
          </div>
          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold text-accent-foreground">CSS</h4>
            <p className="text-sm text-muted-foreground mt-1">Simple and widely known</p>
          </div>
          <div className="rounded-lg border border-border p-4 bg-card">
            <h4 className="font-semibold text-accent-foreground">Regex</h4>
            <p className="text-sm text-muted-foreground mt-1">Pattern matching in text</p>
          </div>
        </div>

        <h2 className="text-2xl font-bold mt-8">XPath Selectors</h2>
        <p className="text-muted-foreground">
          XPath (XML Path Language) is a powerful query language for selecting nodes in XML/HTML documents.
          It excels at navigating complex document structures.
        </p>

        <h3 className="text-xl font-semibold mt-6">Basic Syntax</h3>
        <div className="overflow-x-auto mt-4">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left p-3 font-semibold">Expression</th>
                <th className="text-left p-3 font-semibold">Description</th>
                <th className="text-left p-3 font-semibold">Example</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">//tag</td>
                <td className="p-3 text-muted-foreground">Select all matching tags</td>
                <td className="p-3"><code className="bg-muted px-1 rounded">//div</code></td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">/tag</td>
                <td className="p-3 text-muted-foreground">Direct child only</td>
                <td className="p-3"><code className="bg-muted px-1 rounded">/html/body/div</code></td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">[@attr]</td>
                <td className="p-3 text-muted-foreground">Has attribute</td>
                <td className="p-3"><code className="bg-muted px-1 rounded">//a[@href]</code></td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">[@attr=&apos;value&apos;]</td>
                <td className="p-3 text-muted-foreground">Attribute equals value</td>
                <td className="p-3"><code className="bg-muted px-1 rounded">//div[@class=&apos;price&apos;]</code></td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">/text()</td>
                <td className="p-3 text-muted-foreground">Get text content</td>
                <td className="p-3"><code className="bg-muted px-1 rounded">//h1/text()</code></td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">/@attr</td>
                <td className="p-3 text-muted-foreground">Get attribute value</td>
                <td className="p-3"><code className="bg-muted px-1 rounded">//a/@href</code></td>
              </tr>
            </tbody>
          </table>
        </div>

        <h3 className="text-xl font-semibold mt-6">Advanced XPath</h3>
        <div className="rounded-lg border border-border bg-muted/30 p-4 mt-4">
          <h4 className="font-semibold mb-3">Common Patterns</h4>
          <div className="space-y-3 text-sm">
            <div>
              <code className="bg-card px-2 py-1 rounded border border-border block mb-1">
                //div[contains(@class, &apos;product&apos;)]
              </code>
              <span className="text-muted-foreground">Class contains &quot;product&quot;</span>
            </div>
            <div>
              <code className="bg-card px-2 py-1 rounded border border-border block mb-1">
                //span[starts-with(@id, &apos;price-&apos;)]
              </code>
              <span className="text-muted-foreground">ID starts with &quot;price-&quot;</span>
            </div>
            <div>
              <code className="bg-card px-2 py-1 rounded border border-border block mb-1">
                //ul[@class=&apos;items&apos;]/li[position() &lt;= 5]
              </code>
              <span className="text-muted-foreground">First 5 list items</span>
            </div>
            <div>
              <code className="bg-card px-2 py-1 rounded border border-border block mb-1">
                //div[@class=&apos;review&apos;]//span[@class=&apos;rating&apos;]/text()
              </code>
              <span className="text-muted-foreground">Rating text inside review divs</span>
            </div>
          </div>
        </div>

        <h2 className="text-2xl font-bold mt-8">CSS Selectors</h2>
        <p className="text-muted-foreground">
          CSS selectors are familiar to web developers and great for simple selections. They&apos;re more concise
          but less powerful than XPath for complex queries.
        </p>

        <h3 className="text-xl font-semibold mt-6">Basic Syntax</h3>
        <div className="overflow-x-auto mt-4">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left p-3 font-semibold">Selector</th>
                <th className="text-left p-3 font-semibold">Description</th>
                <th className="text-left p-3 font-semibold">Example</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">tag</td>
                <td className="p-3 text-muted-foreground">Element type</td>
                <td className="p-3"><code className="bg-muted px-1 rounded">div</code></td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">.class</td>
                <td className="p-3 text-muted-foreground">Class selector</td>
                <td className="p-3"><code className="bg-muted px-1 rounded">.product-title</code></td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">#id</td>
                <td className="p-3 text-muted-foreground">ID selector</td>
                <td className="p-3"><code className="bg-muted px-1 rounded">#main-content</code></td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">[attr]</td>
                <td className="p-3 text-muted-foreground">Has attribute</td>
                <td className="p-3"><code className="bg-muted px-1 rounded">[data-price]</code></td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">[attr=value]</td>
                <td className="p-3 text-muted-foreground">Attribute equals</td>
                <td className="p-3"><code className="bg-muted px-1 rounded">[type=&quot;submit&quot;]</code></td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">parent &gt; child</td>
                <td className="p-3 text-muted-foreground">Direct child</td>
                <td className="p-3"><code className="bg-muted px-1 rounded">ul &gt; li</code></td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">ancestor descendant</td>
                <td className="p-3 text-muted-foreground">Any descendant</td>
                <td className="p-3"><code className="bg-muted px-1 rounded">.card .price</code></td>
              </tr>
            </tbody>
          </table>
        </div>

        <h3 className="text-xl font-semibold mt-6">CSS Pseudo-selectors</h3>
        <div className="rounded-lg border border-border bg-muted/30 p-4 mt-4">
          <div className="space-y-3 text-sm">
            <div>
              <code className="bg-card px-2 py-1 rounded border border-border">li:first-child</code>
              <span className="text-muted-foreground ml-2">First list item</span>
            </div>
            <div>
              <code className="bg-card px-2 py-1 rounded border border-border">li:nth-child(2)</code>
              <span className="text-muted-foreground ml-2">Second list item</span>
            </div>
            <div>
              <code className="bg-card px-2 py-1 rounded border border-border">p:not(.intro)</code>
              <span className="text-muted-foreground ml-2">Paragraphs without .intro class</span>
            </div>
            <div>
              <code className="bg-card px-2 py-1 rounded border border-border">::text</code>
              <span className="text-muted-foreground ml-2">Extract text content</span>
            </div>
          </div>
        </div>

        <h2 className="text-2xl font-bold mt-8">Regular Expressions (Regex)</h2>
        <p className="text-muted-foreground">
          Regex patterns work on the raw HTML or extracted text. Use them when you need to extract specific
          patterns that CSS/XPath can&apos;t easily select.
        </p>

        <h3 className="text-xl font-semibold mt-6">Common Patterns</h3>
        <div className="overflow-x-auto mt-4">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left p-3 font-semibold">Pattern</th>
                <th className="text-left p-3 font-semibold">Matches</th>
                <th className="text-left p-3 font-semibold">Example Match</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">\$[\d,]+\.?\d*</td>
                <td className="p-3 text-muted-foreground">US Dollar prices</td>
                <td className="p-3"><code className="bg-muted px-1 rounded">$1,299.99</code></td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">\d+\.\d+ stars?</td>
                <td className="p-3 text-muted-foreground">Star ratings</td>
                <td className="p-3"><code className="bg-muted px-1 rounded">4.5 stars</code></td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">[A-Z]\d&#123;9&#125;</td>
                <td className="p-3 text-muted-foreground">Product codes</td>
                <td className="p-3"><code className="bg-muted px-1 rounded">B0123456789</code></td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">\d&#123;1,3&#125;(,\d&#123;3&#125;)*</td>
                <td className="p-3 text-muted-foreground">Numbers with commas</td>
                <td className="p-3"><code className="bg-muted px-1 rounded">1,234,567</code></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="rounded-lg border border-accent/30 bg-accent/5 p-6 mt-6">
          <h3 className="text-lg font-semibold text-accent-foreground mb-2">Pro Tip: Use Capture Groups</h3>
          <p className="text-muted-foreground">
            Use parentheses to capture specific parts of a match. For example, <code className="bg-muted px-1 rounded">Price: \$(\d+\.\d+)</code>
            captures just the number, not &quot;Price: $&quot;.
          </p>
        </div>

        <h2 className="text-2xl font-bold mt-8">Choosing the Right Query Type</h2>
        <div className="overflow-x-auto mt-4">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left p-3 font-semibold">Use Case</th>
                <th className="text-left p-3 font-semibold">Recommended</th>
                <th className="text-left p-3 font-semibold">Why</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border">
                <td className="p-3">Simple class/ID selection</td>
                <td className="p-3 font-semibold text-accent-foreground">CSS</td>
                <td className="p-3 text-muted-foreground">Concise and readable</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3">Text content extraction</td>
                <td className="p-3 font-semibold text-accent-foreground">XPath</td>
                <td className="p-3 text-muted-foreground">text() function is explicit</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3">Parent/sibling navigation</td>
                <td className="p-3 font-semibold text-accent-foreground">XPath</td>
                <td className="p-3 text-muted-foreground">CSS can&apos;t go upward</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3">Pattern in text</td>
                <td className="p-3 font-semibold text-accent-foreground">Regex</td>
                <td className="p-3 text-muted-foreground">Best for pattern matching</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3">Attribute contains value</td>
                <td className="p-3 font-semibold text-accent-foreground">XPath</td>
                <td className="p-3 text-muted-foreground">contains() function</td>
              </tr>
            </tbody>
          </table>
        </div>

        <h2 className="text-2xl font-bold mt-8">Testing Your Queries</h2>
        <p className="text-muted-foreground">
          Before running a full scrape, test your queries using browser developer tools:
        </p>
        <ol className="list-decimal list-inside space-y-2 text-muted-foreground ml-4 mt-4">
          <li>Open DevTools (F12 or right-click → Inspect)</li>
          <li>Go to the Console tab</li>
          <li>For XPath: <code className="bg-muted px-1 rounded">$x(&apos;//your/xpath/here&apos;)</code></li>
          <li>For CSS: <code className="bg-muted px-1 rounded">$$(&apos;your.css.selector&apos;)</code></li>
          <li>For Regex: Use the Elements panel search (Ctrl+F)</li>
        </ol>

        <h2 className="text-2xl font-bold mt-8">Next Steps</h2>
        <div className="grid gap-4 md:grid-cols-2 mt-4">
          <Link
            href="/docs/creating-jobs"
            className="rounded-lg border border-border p-4 hover:border-accent/50 transition-colors group"
          >
            <h4 className="font-semibold group-hover:text-accent-foreground">Creating Jobs</h4>
            <p className="text-sm text-muted-foreground mt-1">Apply queries in a job configuration</p>
          </Link>
          <Link
            href="/docs/javascript-rendering"
            className="rounded-lg border border-border p-4 hover:border-accent/50 transition-colors group"
          >
            <h4 className="font-semibold group-hover:text-accent-foreground">JavaScript Rendering</h4>
            <p className="text-sm text-muted-foreground mt-1">Handle dynamic content with JS</p>
          </Link>
        </div>
      </section>
    </DocLayout>
  );
}
