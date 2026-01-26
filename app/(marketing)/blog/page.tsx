/**
 * Blog List Page
 * Browse all blog posts with search and filtering
 */

'use client';

import { MarketingLayout } from '@/components/layout';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Search, Calendar, Clock, ArrowRight } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';

// Sample blog posts data (in production, this would come from MDX files or CMS)
const blogPosts = [
  {
    slug: 'getting-started-with-web-scraping',
    title: 'Getting Started with Web Scraping: A Beginner\'s Guide',
    excerpt: 'Learn the fundamentals of web scraping, including when to use it, legal considerations, and best practices for extracting data from websites.',
    category: 'Tutorial',
    author: 'Sarah Chen',
    date: '2026-01-15',
    readTime: '8 min read',
    image: '/blog/web-scraping-guide.jpg',
  },
  {
    slug: 'xpath-vs-css-selectors',
    title: 'XPath vs CSS Selectors: Which Should You Use?',
    excerpt: 'A comprehensive comparison of XPath and CSS selectors for web scraping, with practical examples and performance considerations.',
    category: 'Technical',
    author: 'Marcus Johnson',
    date: '2026-01-12',
    readTime: '10 min read',
    image: '/blog/xpath-css.jpg',
  },
  {
    slug: 'ecommerce-price-monitoring',
    title: 'How to Build an E-commerce Price Monitoring System',
    excerpt: 'Step-by-step guide to setting up automated price tracking for your online store using SnowScrape\'s scheduling and webhook features.',
    category: 'Use Case',
    author: 'Alex Rivera',
    date: '2026-01-10',
    readTime: '12 min read',
    image: '/blog/price-monitoring.jpg',
  },
  {
    slug: 'handling-javascript-rendered-content',
    title: 'Scraping JavaScript-Rendered Websites in 2026',
    excerpt: 'Modern websites use JavaScript frameworks like React and Vue. Learn how to extract data from dynamically rendered content.',
    category: 'Technical',
    author: 'Emily Taylor',
    date: '2026-01-08',
    readTime: '9 min read',
    image: '/blog/js-rendering.jpg',
  },
  {
    slug: 'proxy-rotation-best-practices',
    title: 'Proxy Rotation: Best Practices and Common Pitfalls',
    excerpt: 'Avoid IP bans and rate limits with effective proxy rotation strategies. Learn about residential vs datacenter proxies and when to use each.',
    category: 'Best Practices',
    author: 'Marcus Johnson',
    date: '2026-01-05',
    readTime: '7 min read',
    image: '/blog/proxy-rotation.jpg',
  },
  {
    slug: 'web-scraping-legal-ethics',
    title: 'The Legal and Ethical Guide to Web Scraping',
    excerpt: 'Understand the legal landscape of web scraping, including robots.txt, terms of service, copyright, and how to scrape responsibly.',
    category: 'Legal',
    author: 'Sarah Chen',
    date: '2026-01-03',
    readTime: '11 min read',
    image: '/blog/legal-ethics.jpg',
  },
  {
    slug: 'real-estate-data-aggregation',
    title: 'Building a Real Estate Data Aggregator with SnowScrape',
    excerpt: 'Case study: How a real estate investment firm uses SnowScrape to aggregate 50,000+ property listings daily from multiple sources.',
    category: 'Case Study',
    author: 'Alex Rivera',
    date: '2025-12-28',
    readTime: '10 min read',
    image: '/blog/real-estate.jpg',
  },
  {
    slug: 'webhooks-integration-guide',
    title: 'Integrating SnowScrape with Webhooks: Complete Guide',
    excerpt: 'Learn how to set up webhooks to automatically send scraped data to your applications, databases, and third-party services.',
    category: 'Tutorial',
    author: 'Emily Taylor',
    date: '2025-12-25',
    readTime: '8 min read',
    image: '/blog/webhooks.jpg',
  },
  {
    slug: 'api-scraping-strategies',
    title: '5 Advanced API Scraping Strategies',
    excerpt: 'Go beyond basic HTML scraping. Learn how to extract data from APIs, handle authentication, pagination, and rate limiting.',
    category: 'Advanced',
    author: 'Marcus Johnson',
    date: '2025-12-22',
    readTime: '13 min read',
    image: '/blog/api-scraping.jpg',
  },
  {
    slug: 'job-market-analysis-linkedin',
    title: 'Analyzing Job Market Trends with LinkedIn Data',
    excerpt: 'How recruiters and job seekers use web scraping to track salary trends, skills demand, and hiring patterns in the tech industry.',
    category: 'Use Case',
    author: 'Sarah Chen',
    date: '2025-12-20',
    readTime: '9 min read',
    image: '/blog/job-market.jpg',
  },
];

const categories = ['All', 'Tutorial', 'Technical', 'Use Case', 'Case Study', 'Best Practices', 'Legal', 'Advanced'];

export default function Blog() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');

  // Filter posts based on search and category
  const filteredPosts = blogPosts.filter((post) => {
    const matchesSearch =
      post.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      post.excerpt.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === 'All' || post.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <MarketingLayout>
      {/* Hero */}
      <section className="bg-gradient-to-br from-brand-primary to-brand-primary/90 py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-3xl text-center">
            <h1 className="text-4xl font-bold tracking-tight text-white sm:text-6xl">
              SnowScrape Blog
            </h1>
            <p className="mt-6 text-lg leading-8 text-gray-300">
              Learn web scraping techniques, best practices, and industry insights from our
              team of experts.
            </p>
          </div>
        </div>
      </section>

      {/* Search & Filters */}
      <section className="bg-background py-12">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-3xl">
            {/* Search Bar */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Search articles..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>

            {/* Category Filter */}
            <div className="mt-6 flex flex-wrap gap-2">
              {categories.map((category) => (
                <Badge
                  key={category}
                  variant={selectedCategory === category ? 'default' : 'outline'}
                  className={`cursor-pointer ${
                    selectedCategory === category
                      ? 'bg-accent text-primary hover:bg-accent/90'
                      : 'hover:border-accent/50'
                  }`}
                  onClick={() => setSelectedCategory(category)}
                >
                  {category}
                </Badge>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Blog Posts Grid */}
      <section className="bg-background pb-24 sm:pb-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          {filteredPosts.length > 0 ? (
            <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
              {filteredPosts.map((post) => (
                <Link
                  key={post.slug}
                  href={`/blog/${post.slug}`}
                  className="group rounded-2xl border border-border bg-card transition-all hover:border-accent/50 hover:shadow-lg"
                >
                  {/* Image Placeholder */}
                  <div className="aspect-video w-full rounded-t-2xl bg-muted flex items-center justify-center">
                    <span className="text-sm text-muted-foreground">Blog Image</span>
                  </div>

                  <div className="p-6">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">
                        {post.category}
                      </Badge>
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        <span>{post.readTime}</span>
                      </div>
                    </div>

                    <h3 className="mt-4 text-xl font-semibold text-foreground group-hover:text-accent-foreground">
                      {post.title}
                    </h3>

                    <p className="mt-2 line-clamp-3 text-sm text-muted-foreground">
                      {post.excerpt}
                    </p>

                    <div className="mt-6 flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-foreground">{post.author}</p>
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Calendar className="h-3 w-3" />
                          <span>{new Date(post.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                        </div>
                      </div>

                      <ArrowRight className="h-5 w-5 text-accent-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="mx-auto max-w-md text-center py-12">
              <p className="text-lg text-muted-foreground">
                No articles found matching your search.
              </p>
              <button
                onClick={() => {
                  setSearchQuery('');
                  setSelectedCategory('All');
                }}
                className="mt-4 text-sm font-medium text-accent-foreground hover:underline"
              >
                Clear filters
              </button>
            </div>
          )}
        </div>
      </section>

      {/* Newsletter Signup */}
      <section className="bg-muted/30 py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl rounded-2xl border border-border bg-card p-8 text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground">
              Never miss an update
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Subscribe to our newsletter for the latest web scraping tips, tutorials, and
              product updates.
            </p>

            <form className="mt-8 flex flex-col gap-4 sm:flex-row sm:gap-2">
              <Input
                type="email"
                placeholder="Enter your email"
                className="flex-1"
                required
              />
              <button
                type="submit"
                className="rounded-lg bg-accent px-6 py-2 font-semibold text-primary hover:bg-accent/90"
              >
                Subscribe
              </button>
            </form>

            <p className="mt-4 text-xs text-muted-foreground">
              We respect your privacy. Unsubscribe at any time.
            </p>
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}
