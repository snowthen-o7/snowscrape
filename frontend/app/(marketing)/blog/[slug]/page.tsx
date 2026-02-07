/**
 * Blog Post Detail Page
 * Individual blog post with content and related articles
 */

import { MarketingLayout } from '@/components/layout';
import { Badge } from '@snowforge/ui';
import { Calendar, Clock, ArrowLeft, Share2 } from 'lucide-react';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import React from 'react';

/**
 * Parse inline markdown formatting (bold and inline code) into React elements.
 * This avoids dangerouslySetInnerHTML entirely, preventing XSS.
 */
function renderInlineContent(text: string): React.ReactNode[] {
  // Match **bold** and `inline code` patterns
  const inlinePattern = /(\*\*(.*?)\*\*|`([^`]+)`)/g;
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = inlinePattern.exec(text)) !== null) {
    // Add text before the match
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    if (match[2] !== undefined) {
      // **bold** match
      parts.push(
        <strong key={`bold-${match.index}`}>{match[2]}</strong>
      );
    } else if (match[3] !== undefined) {
      // `inline code` match
      parts.push(
        <code
          key={`code-${match.index}`}
          className="rounded bg-muted px-1.5 py-0.5 text-sm"
        >
          {match[3]}
        </code>
      );
    }

    lastIndex = match.index + match[0].length;
  }

  // Add remaining text after last match
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length > 0 ? parts : [text];
}

/**
 * Safely render markdown-like blog content as React elements.
 * Handles: paragraphs, ## headings, **bold**, `inline code`, ```code blocks```,
 * and - / numbered list items.
 *
 * No dangerouslySetInnerHTML is used anywhere -- all content is text nodes
 * or React elements, so injected HTML/scripts are rendered as plain text.
 */
function renderMarkdownContent(content: string): React.ReactNode[] {
  const trimmed = content.trim();
  const elements: React.ReactNode[] = [];

  // First, split on fenced code blocks (```...```)
  const codeBlockPattern = /```(\w*)\n([\s\S]*?)```/g;
  const segments: { type: 'text' | 'codeblock'; value: string; lang?: string }[] = [];
  let lastIdx = 0;
  let codeMatch: RegExpExecArray | null;

  while ((codeMatch = codeBlockPattern.exec(trimmed)) !== null) {
    if (codeMatch.index > lastIdx) {
      segments.push({ type: 'text', value: trimmed.slice(lastIdx, codeMatch.index) });
    }
    segments.push({ type: 'codeblock', value: codeMatch[2], lang: codeMatch[1] || undefined });
    lastIdx = codeMatch.index + codeMatch[0].length;
  }
  if (lastIdx < trimmed.length) {
    segments.push({ type: 'text', value: trimmed.slice(lastIdx) });
  }

  let blockIndex = 0;

  for (const segment of segments) {
    if (segment.type === 'codeblock') {
      elements.push(
        <pre
          key={`codeblock-${blockIndex++}`}
          className="mt-6 overflow-x-auto rounded-lg bg-muted p-4"
        >
          <code className="text-sm text-foreground">{segment.value.trimEnd()}</code>
        </pre>
      );
      continue;
    }

    // Split text segments into blocks by double newlines
    const blocks = segment.value.split(/\n\n+/);

    for (const block of blocks) {
      const trimmedBlock = block.trim();
      if (!trimmedBlock) continue;

      // Heading: ## ...
      if (trimmedBlock.startsWith('## ')) {
        const headingText = trimmedBlock.slice(3).trim();
        elements.push(
          <h2
            key={`heading-${blockIndex++}`}
            className="mt-12 mb-4 text-2xl font-bold text-foreground"
          >
            {renderInlineContent(headingText)}
          </h2>
        );
      }
      // Unordered list block: lines starting with "- "
      else if (/^- /.test(trimmedBlock)) {
        const items = trimmedBlock.split('\n').filter((line) => line.trim().startsWith('- '));
        elements.push(
          <ul key={`ul-${blockIndex++}`} className="mt-4 list-disc space-y-2 pl-6 text-muted-foreground">
            {items.map((item, i) => (
              <li key={i}>{renderInlineContent(item.replace(/^-\s+/, ''))}</li>
            ))}
          </ul>
        );
      }
      // Ordered list block: lines starting with "1. ", "2. ", etc.
      else if (/^\d+\.\s/.test(trimmedBlock)) {
        const items = trimmedBlock.split('\n').filter((line) => /^\d+\.\s/.test(line.trim()));
        elements.push(
          <ol key={`ol-${blockIndex++}`} className="mt-4 list-decimal space-y-2 pl-6 text-muted-foreground">
            {items.map((item, i) => (
              <li key={i}>{renderInlineContent(item.replace(/^\d+\.\s+/, ''))}</li>
            ))}
          </ol>
        );
      }
      // Regular paragraph
      else {
        elements.push(
          <p key={`p-${blockIndex++}`} className="mt-6 text-muted-foreground leading-relaxed">
            {renderInlineContent(trimmedBlock)}
          </p>
        );
      }
    }
  }

  return elements;
}

// Sample blog posts data (matches blog list page)
const blogPosts = [
  {
    slug: 'getting-started-with-web-scraping',
    title: 'Getting Started with Web Scraping: A Beginner\'s Guide',
    excerpt: 'Learn the fundamentals of web scraping, including when to use it, legal considerations, and best practices for extracting data from websites.',
    category: 'Tutorial',
    author: 'Sarah Chen',
    date: '2026-01-15',
    readTime: '8 min read',
    content: `
Web scraping is the automated process of extracting data from websites. It's a powerful technique used by businesses and researchers to gather information at scale.

## What is Web Scraping?

Web scraping involves writing code (or using tools like SnowScrape) to automatically visit web pages, extract specific data, and save it in a structured format. This can include product prices, contact information, news articles, job postings, and much more.

## When Should You Use Web Scraping?

Web scraping is ideal when you need to:

- **Monitor competitor prices** across multiple e-commerce sites
- **Aggregate data** from various sources for analysis
- **Track changes** on websites over time
- **Build datasets** for machine learning or research
- **Automate repetitive tasks** that involve copying data from websites

## Legal Considerations

Before you start scraping, it's crucial to understand the legal landscape:

1. **Check robots.txt**: Respect the website's robots.txt file
2. **Review Terms of Service**: Some websites explicitly prohibit scraping
3. **Respect copyright**: Be mindful of copyrighted content
4. **Rate limiting**: Don't overload servers with requests

## Getting Started with SnowScrape

SnowScrape makes web scraping accessible to everyone, no coding required:

1. Sign up for a free account
2. Create a new scraping job
3. Define what data you want to extract using our visual builder
4. Schedule your job to run automatically
5. Export your data in your preferred format

## Best Practices

- **Start small**: Test your scraper on a few pages before scaling up
- **Use appropriate delays**: Don't overwhelm target servers
- **Handle errors gracefully**: Websites change, so build in error handling
- **Monitor your jobs**: Keep an eye on success rates and performance

## Conclusion

Web scraping opens up a world of possibilities for data-driven decision making. With the right tools and ethical practices, you can extract valuable insights from the web efficiently and responsibly.
    `,
  },
  {
    slug: 'xpath-vs-css-selectors',
    title: 'XPath vs CSS Selectors: Which Should You Use?',
    excerpt: 'A comprehensive comparison of XPath and CSS selectors for web scraping, with practical examples and performance considerations.',
    category: 'Technical',
    author: 'Marcus Johnson',
    date: '2026-01-12',
    readTime: '10 min read',
    content: `
When extracting data from web pages, you'll need to specify which elements to target. The two most common methods are XPath and CSS selectors. Let's compare them.

## CSS Selectors: Simple and Familiar

CSS selectors are the same syntax used in CSS stylesheets. If you've done any web development, you already know them.

**Pros:**
- Faster to write for simple queries
- More readable for basic selections
- Slightly better performance
- Familiar to web developers

**Cons:**
- Limited traversal capabilities
- Can't select by text content
- No parent selection (without :has())

**Examples:**
\`\`\`css
.product-title          /* Select by class */
#product-123           /* Select by ID */
div.price > span       /* Direct child */
a[href*="product"]     /* Attribute contains */
\`\`\`

## XPath: Powerful and Flexible

XPath is a query language designed for XML/HTML navigation. It's more verbose but significantly more powerful.

**Pros:**
- Can select parent elements
- Can filter by text content
- More complex traversal options
- Better for dynamic content

**Cons:**
- Steeper learning curve
- More verbose syntax
- Slightly slower performance

**Examples:**
\`\`\`xpath
//div[@class='product-title']           /* Select by class */
//span[contains(text(), 'Price:')]      /* Select by text */
//a[contains(@href, 'product')]         /* Attribute contains */
//div[@class='price']/..                /* Select parent */
\`\`\`

## Performance Comparison

In most cases, the performance difference is negligible. CSS selectors are slightly faster, but the difference is usually less than a few milliseconds per query.

## When to Use Each

**Use CSS Selectors when:**
- Selecting simple, direct elements
- You already know CSS syntax
- Performance is critical (though the difference is small)

**Use XPath when:**
- You need to select parent elements
- Filtering by text content
- Complex element relationships
- Working with XML data

## Recommendation

For beginners, start with CSS selectors for their simplicity. As your scraping needs become more complex, learn XPath to unlock more powerful selection capabilities.

SnowScrape supports both, so you can use whichever makes sense for your use case!
    `,
  },
  // Add more blog post content as needed...
];

interface BlogPostPageProps {
  params: Promise<{
    slug: string;
  }>;
}

export default async function BlogPost({ params }: BlogPostPageProps) {
  const { slug } = await params;
  const post = blogPosts.find((p) => p.slug === slug);

  if (!post) {
    notFound();
  }

  // Get related posts (same category, excluding current)
  const relatedPosts = blogPosts
    .filter((p) => p.category === post.category && p.slug !== post.slug)
    .slice(0, 3);

  return (
    <MarketingLayout>
      {/* Back Button */}
      <section className="bg-background pt-8">
        <div className="mx-auto max-w-4xl px-6 lg:px-8">
          <Link
            href="/blog"
            className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-accent-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Blog
          </Link>
        </div>
      </section>

      {/* Article Header */}
      <section className="bg-background py-12">
        <div className="mx-auto max-w-4xl px-6 lg:px-8">
          <Badge variant="outline">{post.category}</Badge>

          <h1 className="mt-6 text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
            {post.title}
          </h1>

          <div className="mt-6 flex items-center gap-6 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent/10 text-sm font-semibold text-accent-foreground">
                {post.author.split(' ').map((n) => n[0]).join('')}
              </div>
              <div>
                <p className="font-medium text-foreground">{post.author}</p>
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    <span>{new Date(post.date).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    <span>{post.readTime}</span>
                  </div>
                </div>
              </div>
            </div>

            <button className="ml-auto rounded-lg border border-border px-4 py-2 hover:border-accent/50 hover:bg-card">
              <Share2 className="h-4 w-4" />
            </button>
          </div>
        </div>
      </section>

      {/* Article Content */}
      <article className="bg-background pb-24">
        <div className="mx-auto max-w-4xl px-6 lg:px-8">
          <div className="prose prose-lg max-w-none">
            {renderMarkdownContent(post.content)}
          </div>
        </div>
      </article>

      {/* Related Posts */}
      {relatedPosts.length > 0 && (
        <section className="bg-muted/30 py-24">
          <div className="mx-auto max-w-7xl px-6 lg:px-8">
            <h2 className="text-3xl font-bold tracking-tight text-foreground">
              Related Articles
            </h2>

            <div className="mt-12 grid grid-cols-1 gap-8 md:grid-cols-3">
              {relatedPosts.map((relatedPost) => (
                <Link
                  key={relatedPost.slug}
                  href={`/blog/${relatedPost.slug}`}
                  className="group rounded-2xl border border-border bg-card p-6 transition-all hover:border-accent/50 hover:shadow-lg"
                >
                  <Badge variant="outline" className="text-xs">
                    {relatedPost.category}
                  </Badge>

                  <h3 className="mt-4 text-lg font-semibold text-foreground group-hover:text-accent-foreground">
                    {relatedPost.title}
                  </h3>

                  <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">
                    {relatedPost.excerpt}
                  </p>

                  <p className="mt-4 text-xs text-muted-foreground">
                    {new Date(relatedPost.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })} · {relatedPost.readTime}
                  </p>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Newsletter CTA */}
      <section className="bg-background py-24">
        <div className="mx-auto max-w-3xl px-6 lg:px-8">
          <div className="rounded-2xl border border-border bg-card p-8 text-center">
            <h2 className="text-2xl font-bold tracking-tight text-foreground">
              Get more web scraping insights
            </h2>
            <p className="mt-4 text-muted-foreground">
              Subscribe to our newsletter for weekly tips, tutorials, and industry news.
            </p>

            <form className="mt-6 flex flex-col gap-3 sm:flex-row sm:gap-2">
              <input
                type="email"
                placeholder="Enter your email"
                className="flex-1 rounded-lg border border-input bg-background px-4 py-2 text-sm focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20"
                required
              />
              <button
                type="submit"
                className="rounded-lg bg-accent px-6 py-2 font-semibold text-primary hover:bg-accent/90"
              >
                Subscribe
              </button>
            </form>
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}
