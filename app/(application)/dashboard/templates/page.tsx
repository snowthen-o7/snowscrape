/**
 * Template Marketplace Page
 * Browse, search, and use pre-configured scraping templates
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from '@clerk/nextjs';
import { AppLayout } from '@/components/layout/AppLayout';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Template } from '@/lib/types';
import {
  Search,
  Star,
  TrendingUp,
  Package,
  ShoppingCart,
  Briefcase,
  Home,
  Users,
  FileText,
  Calendar,
  ExternalLink,
  Download,
  Eye,
} from 'lucide-react';
import { toast } from '@/lib/toast';
import { EmptyState } from '@/components/EmptyState';

// Official templates with categories and metadata
const OFFICIAL_TEMPLATES = [
  {
    id: 'amazon-product',
    name: 'Amazon Product Scraper',
    description: 'Extract product details, prices, reviews, and ratings from Amazon product pages',
    category: 'E-commerce',
    icon: ShoppingCart,
    difficulty: 'Easy',
    rating: 4.8,
    usageCount: 1250,
    official: true,
    tags: ['e-commerce', 'products', 'reviews', 'pricing'],
    sampleUrl: 'https://www.amazon.com/dp/B08N5WRWNW',
  },
  {
    id: 'linkedin-profile',
    name: 'LinkedIn Profile Extractor',
    description: 'Scrape professional profiles including name, title, company, education, and skills',
    category: 'Social Media',
    icon: Users,
    difficulty: 'Medium',
    rating: 4.6,
    usageCount: 890,
    official: true,
    tags: ['linkedin', 'profiles', 'recruitment', 'networking'],
    sampleUrl: 'https://www.linkedin.com/in/example',
  },
  {
    id: 'real-estate-zillow',
    name: 'Zillow Real Estate Listings',
    description: 'Extract property details, prices, features, and location data from Zillow',
    category: 'Real Estate',
    icon: Home,
    difficulty: 'Medium',
    rating: 4.7,
    usageCount: 720,
    official: true,
    tags: ['real estate', 'housing', 'zillow', 'properties'],
    sampleUrl: 'https://www.zillow.com/homedetails/',
  },
  {
    id: 'google-serp',
    name: 'Google Search Results',
    description: 'Scrape Google search results including titles, descriptions, URLs, and rankings',
    category: 'SEO',
    icon: Search,
    difficulty: 'Easy',
    rating: 4.9,
    usageCount: 2100,
    official: true,
    tags: ['seo', 'google', 'search', 'rankings'],
    sampleUrl: 'https://www.google.com/search?q=example',
  },
  {
    id: 'news-articles',
    name: 'News Article Scraper',
    description: 'Extract article content, author, publish date, and metadata from news sites',
    category: 'Content',
    icon: FileText,
    difficulty: 'Easy',
    rating: 4.5,
    usageCount: 650,
    official: true,
    tags: ['news', 'articles', 'content', 'journalism'],
    sampleUrl: 'https://www.example.com/article',
  },
  {
    id: 'job-listings-indeed',
    name: 'Indeed Job Listings',
    description: 'Scrape job postings with title, company, location, salary, and description',
    category: 'Jobs',
    icon: Briefcase,
    difficulty: 'Medium',
    rating: 4.6,
    usageCount: 980,
    official: true,
    tags: ['jobs', 'recruitment', 'indeed', 'careers'],
    sampleUrl: 'https://www.indeed.com/viewjob?jk=example',
  },
  {
    id: 'event-listings',
    name: 'Event Listings Scraper',
    description: 'Extract event details including name, date, location, and ticket information',
    category: 'Events',
    icon: Calendar,
    difficulty: 'Easy',
    rating: 4.4,
    usageCount: 430,
    official: true,
    tags: ['events', 'calendar', 'tickets', 'venues'],
    sampleUrl: 'https://www.eventbrite.com/e/example',
  },
  {
    id: 'stock-market-data',
    name: 'Stock Market Data',
    description: 'Scrape stock prices, market cap, volume, and financial metrics',
    category: 'Finance',
    icon: TrendingUp,
    difficulty: 'Medium',
    rating: 4.7,
    usageCount: 1120,
    official: true,
    tags: ['finance', 'stocks', 'market', 'trading'],
    sampleUrl: 'https://finance.yahoo.com/quote/AAPL',
  },
];

export default function TemplatesPage() {
  const router = useRouter();
  const { session } = useSession();
  const [userTemplates, setUserTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [difficultyFilter, setDifficultyFilter] = useState('all');
  const [sortBy, setSortBy] = useState('popular');

  // Fetch user templates
  useEffect(() => {
    const fetchTemplates = async () => {
      if (!session) return;

      try {
        const token = await session.getToken();
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_BASE_URL}/templates`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
              ...(process.env.NEXT_PUBLIC_API_KEY && {
                'x-api-key': process.env.NEXT_PUBLIC_API_KEY,
              }),
            },
          }
        );

        if (response.ok) {
          const data = await response.json();
          setUserTemplates(data);
        }
      } catch (error) {
        console.error('Error fetching templates', error);
      } finally {
        setLoading(false);
      }
    };

    fetchTemplates();
  }, [session]);

  // Get unique categories
  const categories = ['all', ...new Set(OFFICIAL_TEMPLATES.map((t) => t.category))];

  // Filter and sort templates
  const filteredOfficialTemplates = OFFICIAL_TEMPLATES.filter((template) => {
    const matchesSearch =
      template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      template.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      template.tags.some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesCategory =
      categoryFilter === 'all' || template.category === categoryFilter;

    const matchesDifficulty =
      difficultyFilter === 'all' || template.difficulty === difficultyFilter;

    return matchesSearch && matchesCategory && matchesDifficulty;
  }).sort((a, b) => {
    switch (sortBy) {
      case 'popular':
        return b.usageCount - a.usageCount;
      case 'rating':
        return b.rating - a.rating;
      case 'name':
        return a.name.localeCompare(b.name);
      default:
        return 0;
    }
  });

  const handleUseTemplate = (templateId: string) => {
    router.push(`/dashboard/templates/${templateId}`);
  };

  return (
    <AppLayout>
      <div className="space-y-6 p-6">
        <PageHeader
          title="Template Marketplace"
          description="Browse and use pre-configured scraping templates for common websites"
        />

        {/* Search and Filters */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search templates..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>

          <div className="flex gap-2">
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                {categories.map((category) => (
                  <SelectItem key={category} value={category}>
                    {category === 'all' ? 'All Categories' : category}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={difficultyFilter} onValueChange={setDifficultyFilter}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="Difficulty" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Levels</SelectItem>
                <SelectItem value="Easy">Easy</SelectItem>
                <SelectItem value="Medium">Medium</SelectItem>
                <SelectItem value="Hard">Hard</SelectItem>
              </SelectContent>
            </Select>

            <Select value={sortBy} onValueChange={setSortBy}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="popular">Most Popular</SelectItem>
                <SelectItem value="rating">Highest Rated</SelectItem>
                <SelectItem value="name">Name (A-Z)</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="official" className="space-y-6">
          <TabsList>
            <TabsTrigger value="official">
              <Star className="mr-2 h-4 w-4" />
              Official Templates ({OFFICIAL_TEMPLATES.length})
            </TabsTrigger>
            <TabsTrigger value="my-templates">
              <Package className="mr-2 h-4 w-4" />
              My Templates ({userTemplates.length})
            </TabsTrigger>
          </TabsList>

          {/* Official Templates */}
          <TabsContent value="official">
            {filteredOfficialTemplates.length === 0 ? (
              <EmptyState
                icon={<Search className="h-12 w-12" />}
                title="No templates found"
                description="Try adjusting your search or filter criteria"
                action={{
                  label: 'Clear Filters',
                  onClick: () => {
                    setSearchQuery('');
                    setCategoryFilter('all');
                    setDifficultyFilter('all');
                  },
                }}
              />
            ) : (
              <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {filteredOfficialTemplates.map((template) => {
                  const Icon = template.icon;
                  return (
                    <Card
                      key={template.id}
                      className="group hover:border-brand-accent transition-colors cursor-pointer"
                      onClick={() => handleUseTemplate(template.id)}
                    >
                      <CardHeader>
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-brand-accent/10">
                            <Icon className="h-6 w-6 text-brand-accent" />
                          </div>
                          <div className="flex items-center gap-2">
                            {template.official && (
                              <Badge variant="outline" className="text-brand-accent border-brand-accent">
                                Official
                              </Badge>
                            )}
                          </div>
                        </div>
                        <CardTitle className="text-lg group-hover:text-brand-accent transition-colors">
                          {template.name}
                        </CardTitle>
                        <CardDescription className="line-clamp-2">
                          {template.description}
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="flex items-center justify-between text-sm">
                          <div className="flex items-center gap-1">
                            <Star className="h-4 w-4 fill-yellow-500 text-yellow-500" />
                            <span className="font-medium">{template.rating}</span>
                          </div>
                          <div className="flex items-center gap-1 text-muted-foreground">
                            <Download className="h-4 w-4" />
                            <span>{template.usageCount.toLocaleString()} uses</span>
                          </div>
                        </div>

                        <div className="flex flex-wrap gap-2">
                          <Badge variant="secondary">{template.category}</Badge>
                          <Badge
                            variant="outline"
                            className={
                              template.difficulty === 'Easy'
                                ? 'border-green-600 text-green-600'
                                : template.difficulty === 'Medium'
                                ? 'border-yellow-600 text-yellow-600'
                                : 'border-red-600 text-red-600'
                            }
                          >
                            {template.difficulty}
                          </Badge>
                        </div>

                        <div className="flex gap-2">
                          <Button
                            className="flex-1"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleUseTemplate(template.id);
                            }}
                          >
                            <ExternalLink className="mr-2 h-4 w-4" />
                            Use Template
                          </Button>
                          <Button
                            variant="outline"
                            size="icon"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleUseTemplate(template.id);
                            }}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </TabsContent>

          {/* My Templates */}
          <TabsContent value="my-templates">
            {loading ? (
              <div className="text-center py-12 text-muted-foreground">
                Loading your templates...
              </div>
            ) : userTemplates.length === 0 ? (
              <EmptyState
                icon={<Package className="h-12 w-12" />}
                title="No templates yet"
                description="Create a job and save it as a template for quick reuse"
                action={{
                  label: 'Create Job',
                  onClick: () => router.push('/dashboard'),
                }}
              />
            ) : (
              <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {userTemplates.map((template) => (
                  <Card
                    key={template.template_id}
                    className="group hover:border-brand-accent transition-colors cursor-pointer"
                    onClick={() => handleUseTemplate(template.template_id)}
                  >
                    <CardHeader>
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-brand-accent/10">
                          <Package className="h-6 w-6 text-brand-accent" />
                        </div>
                      </div>
                      <CardTitle className="text-lg group-hover:text-brand-accent transition-colors">
                        {template.name}
                      </CardTitle>
                      {template.description && (
                        <CardDescription className="line-clamp-2">
                          {template.description}
                        </CardDescription>
                      )}
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="flex items-center justify-between text-sm text-muted-foreground">
                        <span>
                          Created {new Date(template.created_at).toLocaleDateString()}
                        </span>
                        {template.last_used && (
                          <span>
                            Used {new Date(template.last_used).toLocaleDateString()}
                          </span>
                        )}
                      </div>

                      <div className="flex flex-wrap gap-2">
                        <Badge variant="secondary">
                          {template.config.queries.length} queries
                        </Badge>
                        <Badge variant="outline">
                          {template.config.scheduling.days.length} days
                        </Badge>
                      </div>

                      <Button
                        className="w-full"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleUseTemplate(template.template_id);
                        }}
                      >
                        Use Template
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </AppLayout>
  );
}
