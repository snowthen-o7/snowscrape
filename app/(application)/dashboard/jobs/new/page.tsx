'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { AppLayout } from '@/components/layout';
import { PageHeader } from '@snowforge/ui';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@snowforge/ui';
import {
  FileText,
  MousePointer2,
  Code,
  ArrowRight,
  Sparkles,
  Zap,
  Target,
  Settings,
} from 'lucide-react';

const creationMethods = [
  {
    id: 'template',
    title: 'Start from Template',
    description: 'Choose from pre-built templates for popular websites',
    icon: FileText,
    href: '/dashboard/templates',
    features: ['50+ templates available', 'Pre-configured queries', 'One-click setup'],
    recommended: true,
  },
  {
    id: 'visual',
    title: 'Visual Builder',
    description: 'Point and click to select elements on any webpage',
    icon: MousePointer2,
    href: '/dashboard/jobs/new/visual',
    features: ['No coding required', 'Auto-generate selectors', 'Live preview'],
    recommended: false,
  },
  {
    id: 'manual',
    title: 'Manual Configuration',
    description: 'Full control with custom XPath or CSS selectors',
    icon: Code,
    href: '/dashboard/jobs/new/manual',
    features: ['Advanced options', 'Custom queries', 'Full flexibility'],
    recommended: false,
  },
];

export default function NewJobPage() {
  const router = useRouter();

  const handleMethodSelect = (method: typeof creationMethods[0]) => {
    if (method.href) {
      router.push(method.href);
    }
  };

  return (
    <AppLayout>
      <div className="space-y-8 max-w-4xl mx-auto">
        <PageHeader
          title="Create New Job"
          description="Choose how you want to set up your scraping job"
          breadcrumbs={[
            { label: 'Jobs', href: '/dashboard/jobs' },
            { label: 'New Job' },
          ]}
        />

        {/* Quick Tips */}
        <div className="bg-muted/50 rounded-lg p-4 border">
          <div className="flex items-start gap-3">
            <Sparkles className="h-5 w-5 text-accent-foreground mt-0.5" />
            <div>
              <p className="font-medium text-sm">Not sure where to start?</p>
              <p className="text-sm text-muted-foreground">
                If you&apos;re scraping a popular website like Amazon, LinkedIn, or Google,
                start with a template. For custom websites, try the Visual Builder.
              </p>
            </div>
          </div>
        </div>

        {/* Creation Methods */}
        <div className="grid gap-6 md:grid-cols-3">
          {creationMethods.map((method) => {
            const Icon = method.icon;
            return (
              <Card
                key={method.id}
                className={`relative cursor-pointer transition-all hover:border-primary hover:shadow-md ${
                  method.recommended ? 'border-accent' : ''
                }`}
                onClick={() => handleMethodSelect(method)}
              >
                {method.recommended && (
                  <div className="absolute -top-3 left-4">
                    <span className="bg-accent text-primary text-xs font-medium px-2 py-1 rounded-full">
                      Recommended
                    </span>
                  </div>
                )}
                <CardHeader>
                  <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center mb-2">
                    <Icon className="h-6 w-6 text-primary" />
                  </div>
                  <CardTitle className="text-lg">{method.title}</CardTitle>
                  <CardDescription>{method.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2 text-sm text-muted-foreground mb-4">
                    {method.features.map((feature, i) => (
                      <li key={i} className="flex items-center gap-2">
                        <div className="h-1.5 w-1.5 rounded-full bg-primary" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                  <Button variant="ghost" className="w-full group">
                    Get Started
                    <ArrowRight className="h-4 w-4 ml-2 group-hover:translate-x-1 transition-transform" />
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Additional Options */}
        <div className="border-t pt-8">
          <h3 className="font-semibold mb-4">Other Options</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <Card className="p-4">
              <div className="flex items-start gap-3">
                <div className="h-10 w-10 rounded-lg bg-muted flex items-center justify-center">
                  <Zap className="h-5 w-5" />
                </div>
                <div className="flex-1">
                  <p className="font-medium text-sm">Import from URL</p>
                  <p className="text-xs text-muted-foreground mb-2">
                    Paste a URL and we&apos;ll auto-detect scrapeable content
                  </p>
                  <Button variant="outline" size="sm" asChild>
                    <Link href="/dashboard/jobs/new/manual">Try It</Link>
                  </Button>
                </div>
              </div>
            </Card>

            <Card className="p-4">
              <div className="flex items-start gap-3">
                <div className="h-10 w-10 rounded-lg bg-muted flex items-center justify-center">
                  <Settings className="h-5 w-5" />
                </div>
                <div className="flex-1">
                  <p className="font-medium text-sm">Duplicate Existing Job</p>
                  <p className="text-xs text-muted-foreground mb-2">
                    Clone configuration from an existing job
                  </p>
                  <Button variant="outline" size="sm" asChild>
                    <Link href="/dashboard/jobs">View Jobs</Link>
                  </Button>
                </div>
              </div>
            </Card>
          </div>
        </div>

        {/* Help Section */}
        <div className="bg-muted/30 rounded-lg p-6 text-center">
          <Target className="h-8 w-8 mx-auto mb-3 text-muted-foreground" />
          <h3 className="font-semibold mb-2">Need Help Getting Started?</h3>
          <p className="text-sm text-muted-foreground mb-4 max-w-md mx-auto">
            Check out our documentation for step-by-step guides on creating effective scraping jobs.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Button variant="outline" size="sm" asChild>
              <Link href="/docs">View Documentation</Link>
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link href="/dashboard/templates">Browse Templates</Link>
            </Button>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
