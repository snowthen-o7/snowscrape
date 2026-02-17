'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';
import { AppLayout } from '@/components/layout';
import { PageHeader } from '@snowforge/ui';
import { Button } from '@snowforge/ui';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@snowforge/ui';
import { Input } from '@snowforge/ui';
import { Label } from '@snowforge/ui';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Loader2,
  Sparkles,
  Trash2,
  Pencil,
} from 'lucide-react';
import { jobsAPI, type AISuggestResponse } from '@/lib/api/jobs';
import { toast } from '@/lib/toast';

type Step = 'describe' | 'review' | 'configure';

interface SuggestionField {
  name: string;
  type: 'xpath' | 'css' | 'regex' | 'ai';
  query: string;
  description: string;
  sample_value: string;
  accepted: boolean;
  useAi: boolean;
}

export default function AIJobCreationPage() {
  const router = useRouter();
  const { getToken } = useAuth();

  const [step, setStep] = useState<Step>('describe');
  const [url, setUrl] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<SuggestionField[]>([]);

  // Configure step
  const [jobName, setJobName] = useState('');
  const [rateLimit, setRateLimit] = useState(2);

  const handleAnalyze = async () => {
    if (!url || !description) {
      toast.error('Please enter both a URL and description');
      return;
    }

    setLoading(true);
    try {
      const token = await getToken();
      if (!token) throw new Error('Not authenticated');

      const result: AISuggestResponse = await jobsAPI.aiSuggestQueries(url, description, token);

      setSuggestions(
        result.suggestions.map((s) => ({
          ...s,
          accepted: true,
          useAi: s.type === 'ai',
        }))
      );

      setStep('review');
    } catch (error: any) {
      toast.error(error.message || 'Failed to analyze page');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateJob = async () => {
    const acceptedFields = suggestions.filter((s) => s.accepted);
    if (acceptedFields.length === 0) {
      toast.error('Please accept at least one field');
      return;
    }

    if (!jobName.trim()) {
      toast.error('Please enter a job name');
      return;
    }

    setLoading(true);
    try {
      const token = await getToken();
      if (!token) throw new Error('Not authenticated');

      const queries = acceptedFields.map((field) => ({
        name: field.name,
        type: field.useAi ? ('ai' as const) : (field.type === 'css' ? 'xpath' as const : field.type as 'xpath' | 'regex' | 'ai'),
        query: field.useAi ? field.description : field.query,
        join: false,
      }));

      await jobsAPI.create(
        {
          name: jobName,
          source: url,
          source_type: 'direct_url',
          url_template: url,
          rate_limit: rateLimit,
          queries,
        } as any,
        token
      );

      toast.success('Job created successfully');
      router.push('/dashboard/jobs');
    } catch (error: any) {
      toast.error(error.message || 'Failed to create job');
    } finally {
      setLoading(false);
    }
  };

  const toggleField = (index: number) => {
    setSuggestions((prev) =>
      prev.map((s, i) => (i === index ? { ...s, accepted: !s.accepted } : s))
    );
  };

  const toggleUseAi = (index: number) => {
    setSuggestions((prev) =>
      prev.map((s, i) => (i === index ? { ...s, useAi: !s.useAi } : s))
    );
  };

  return (
    <AppLayout>
      <div className="space-y-8 max-w-3xl mx-auto">
        <PageHeader
          title="AI-Assisted Job Creation"
          description="Describe what you want to extract and let AI set up the job for you"
          breadcrumbs={[
            { label: 'Jobs', href: '/dashboard/jobs' },
            { label: 'New Job', href: '/dashboard/jobs/new' },
            { label: 'AI-Assisted' },
          ]}
        />

        {/* Step indicator */}
        <div className="flex items-center gap-2 text-sm">
          {(['describe', 'review', 'configure'] as Step[]).map((s, i) => (
            <div key={s} className="flex items-center gap-2">
              {i > 0 && <div className="w-8 h-px bg-border" />}
              <div
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium ${
                  step === s
                    ? 'bg-primary text-primary-foreground'
                    : suggestions.length > 0 && i < ['describe', 'review', 'configure'].indexOf(step)
                      ? 'bg-primary/20 text-primary'
                      : 'bg-muted text-muted-foreground'
                }`}
              >
                <span>{i + 1}</span>
                <span className="capitalize">{s}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Step 1: Describe */}
        {step === 'describe' && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5" />
                Describe Your Data
              </CardTitle>
              <CardDescription>
                Enter the URL you want to scrape and describe what data you need
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="url">Target URL</Label>
                <Input
                  id="url"
                  placeholder="https://example.com/products"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">What data do you want to extract?</Label>
                <textarea
                  id="description"
                  className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  placeholder="e.g., I want to extract each product's name, price, rating, number of reviews, and whether it's in stock"
                  rows={4}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Be specific about the fields you need. AI will suggest the best selectors for each.
                </p>
              </div>
              <div className="flex justify-end">
                <Button onClick={handleAnalyze} disabled={loading || !url || !description}>
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      Analyze Page
                      <ArrowRight className="h-4 w-4 ml-2" />
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 2: Review suggestions */}
        {step === 'review' && (
          <Card>
            <CardHeader>
              <CardTitle>Review Suggested Fields</CardTitle>
              <CardDescription>
                AI found {suggestions.length} extractable fields. Accept, reject, or edit each one.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {suggestions.map((field, index) => (
                <div
                  key={index}
                  className={`p-4 border rounded-lg transition-colors ${
                    field.accepted ? 'border-primary/30 bg-primary/5' : 'border-border opacity-60'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium text-sm">{field.name}</span>
                        <span className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                          {field.useAi ? 'AI' : field.type}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground mb-1">{field.description}</p>
                      {field.sample_value && (
                        <p className="text-xs font-mono bg-muted px-2 py-1 rounded truncate">
                          {field.sample_value}
                        </p>
                      )}
                      {!field.useAi && (
                        <p className="text-xs font-mono text-muted-foreground mt-1 truncate">
                          {field.query}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => toggleUseAi(index)}
                        title={field.useAi ? 'Switch to selector' : 'Switch to AI'}
                      >
                        {field.useAi ? <Pencil className="h-3.5 w-3.5" /> : <Sparkles className="h-3.5 w-3.5" />}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => toggleField(index)}
                      >
                        {field.accepted ? (
                          <Check className="h-4 w-4 text-primary" />
                        ) : (
                          <Trash2 className="h-4 w-4 text-muted-foreground" />
                        )}
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
              <div className="flex justify-between pt-4">
                <Button variant="outline" onClick={() => setStep('describe')}>
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Back
                </Button>
                <Button
                  onClick={() => {
                    if (!jobName) setJobName(`AI Job - ${new URL(url).hostname}`);
                    setStep('configure');
                  }}
                  disabled={suggestions.filter((s) => s.accepted).length === 0}
                >
                  Continue
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 3: Configure */}
        {step === 'configure' && (
          <Card>
            <CardHeader>
              <CardTitle>Configure Job</CardTitle>
              <CardDescription>
                Set the job name and rate limit, then create your job.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="jobName">Job Name</Label>
                <Input
                  id="jobName"
                  value={jobName}
                  onChange={(e) => setJobName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="rateLimit">Rate Limit (requests/second)</Label>
                <Input
                  id="rateLimit"
                  type="number"
                  min={1}
                  max={8}
                  value={rateLimit}
                  onChange={(e) => setRateLimit(Number(e.target.value))}
                />
              </div>

              <div className="bg-muted/50 rounded-lg p-4 space-y-2">
                <p className="text-sm font-medium">
                  {suggestions.filter((s) => s.accepted).length} fields selected
                </p>
                <div className="flex flex-wrap gap-2">
                  {suggestions
                    .filter((s) => s.accepted)
                    .map((s, i) => (
                      <span
                        key={i}
                        className="text-xs px-2 py-1 rounded-full bg-primary/10 text-primary"
                      >
                        {s.name} ({s.useAi ? 'AI' : s.type})
                      </span>
                    ))}
                </div>
              </div>

              <div className="flex justify-between pt-4">
                <Button variant="outline" onClick={() => setStep('review')}>
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Back
                </Button>
                <Button onClick={handleCreateJob} disabled={loading}>
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    'Create Job'
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </AppLayout>
  );
}
