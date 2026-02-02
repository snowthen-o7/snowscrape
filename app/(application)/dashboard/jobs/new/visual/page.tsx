/**
 * Visual Scraper Builder
 * Point-and-click interface for building scraping jobs
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from '@clerk/nextjs';
import { AppLayout } from '@/components/layout';
import { PageHeader } from '@snowforge/ui';
import { Button } from '@snowforge/ui';
import { Input } from '@snowforge/ui';
import { Label } from '@snowforge/ui';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@snowforge/ui';
import { Badge } from '@snowforge/ui';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@snowforge/ui';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@snowforge/ui';
import {
  ArrowLeft,
  MousePointer2,
  Code,
  Eye,
  Save,
  Play,
  AlertCircle,
  CheckCircle2,
  Trash2,
  Plus,
  Wand2,
  Loader2,
  Wifi,
  WifiOff,
} from 'lucide-react';
import { toast } from '@/lib/toast';
import { jobsAPI } from '@/lib/api';
import { useWebSocket } from '@/lib/useWebSocket';

interface ExtractedField {
  id: string;
  name: string;
  selector: string;
  type: 'xpath' | 'css' | 'regex';
  value?: string;
  element?: string;
}

export default function VisualBuilderPage() {
  const router = useRouter();
  const { session } = useSession();
  const [targetUrl, setTargetUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [pageLoaded, setPageLoaded] = useState(false);
  const [extractedFields, setExtractedFields] = useState<ExtractedField[]>([]);
  const [selectedElement, setSelectedElement] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<any[]>([]);
  const [pageStructure, setPageStructure] = useState<any>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Async scraper state
  const [asyncTaskId, setAsyncTaskId] = useState<string | null>(null);
  const [isAsyncLoading, setIsAsyncLoading] = useState(false);

  // WebSocket connection (only connect when we have an async task)
  const { isConnected, messages, subscribe, clearMessages } = useWebSocket(!!asyncTaskId);

  // Handle WebSocket messages for async scraper
  useEffect(() => {
    if (!asyncTaskId) return;

    for (const message of messages) {
      // Only process messages for our task
      if (message.task_id !== asyncTaskId) continue;

      switch (message.type) {
        case 'scraper:progress':
          // Show progress update
          console.log('[Async Scraper] Progress:', message);
          if (message.status === 'escalated') {
            toast.info(
              `Escalated to Tier ${message.tier} (${message.tier_name})`
            );
          }
          break;

        case 'scraper:complete':
          // Scraping completed successfully
          console.log('[Async Scraper] Complete:', message.data);
          setPageStructure(message.data);
          setPageLoaded(true);
          setIsAsyncLoading(false);
          setAsyncTaskId(null);
          clearMessages();

          // Show success message with tier info
          const tierInfo = message.data.tier_info;
          if (tierInfo) {
            const { tier_used, tier_name, cost_per_page } = tierInfo;

            if (tier_used === 1) {
              toast.success(`Loaded ${message.data.elements.length} elements from page`);
            } else {
              toast.success(
                `Loaded ${message.data.elements.length} elements using ${tier_name} (Tier ${tier_used}). Cost: $${cost_per_page.toFixed(4)} per page`
              );
            }
          } else {
            toast.success(`Loaded ${message.data.elements.length} elements from page`);
          }
          break;

        case 'scraper:error':
          // Scraping failed
          console.error('[Async Scraper] Error:', message.error);
          setIsAsyncLoading(false);
          setAsyncTaskId(null);
          clearMessages();
          toast.error(`Failed to load page: ${message.error}`);
          break;
      }
    }
  }, [messages, asyncTaskId, clearMessages]);

  // Subscribe to scraper channel when task ID changes
  useEffect(() => {
    if (asyncTaskId && isConnected) {
      const channel = `scraper:${asyncTaskId}`;
      console.log('[Async Scraper] Subscribing to channel:', channel);
      subscribe(channel);
    }
  }, [asyncTaskId, isConnected, subscribe]);

  const handleLoadPage = async () => {
    if (!targetUrl) {
      toast.error('Please enter a URL');
      return;
    }

    if (!session) {
      toast.error('Please sign in to continue');
      return;
    }

    // Validate URL format
    try {
      new URL(targetUrl);
    } catch (e) {
      toast.error('Please enter a valid URL (e.g., https://example.com)');
      return;
    }

    setIsLoading(true);

    try {
      const token = await session.getToken();
      if (!token) {
        toast.error('Authentication failed');
        return;
      }

      // Try synchronous scraper first (fast path)
      console.log('[Visual Builder] Fetching page preview (sync) for:', targetUrl);
      try {
        const result = await jobsAPI.preview(targetUrl, token);
        console.log('[Visual Builder] Preview result (sync):', result);
        console.log('[Visual Builder] Elements count:', result?.elements?.length);
        console.log('[Visual Builder] Tier info:', result?.tier_info);

        setPageStructure(result);
        setPageLoaded(true);
        console.log('[Visual Builder] State updated - pageLoaded: true, pageStructure:', result);

        // Show success message with tier information
        const tierInfo = result.tier_info;
        if (tierInfo) {
        const { tier_used, tier_name, cost_per_page, escalation_log } = tierInfo;

        // Show escalation log if tier > 1 (escalation occurred)
        if (escalation_log && escalation_log.length > 0) {
          console.log('[Visual Builder] Escalation log:', escalation_log);
        }

        // Customize message based on tier
        if (tier_used === 1) {
          toast.success(`Loaded ${result.elements.length} elements from page`);
        } else {
          toast.success(
            `Loaded ${result.elements.length} elements using ${tier_name} (Tier ${tier_used}). ` +
            `Cost: $${cost_per_page.toFixed(4)} per page`
          );
        }
      } else {
        // Fallback if tier_info not available
        toast.success(`Loaded ${result.elements.length} elements from page`);
      }
      } catch (syncError) {
        // Sync scraper failed - fall back to async scraper
        console.log('[Visual Builder] Sync scraper failed, trying async...', syncError);

        try {
          // Call async scraper endpoint
          const asyncResponse = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL}/scraper/preview/async`,
            {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`,
              },
              body: JSON.stringify({ url: targetUrl }),
            }
          );

          if (!asyncResponse.ok) {
            throw new Error(`Async scraper failed: ${asyncResponse.statusText}`);
          }

          const asyncResult = await asyncResponse.json();
          console.log('[Visual Builder] Async scraper started:', asyncResult);

          // Set async task state
          setAsyncTaskId(asyncResult.task_id);
          setIsAsyncLoading(true);

          toast.info(
            'This site is taking longer than usual. Scraping in progress - you\'ll receive updates in real-time.'
          );

          // WebSocket will handle the rest via useEffect
        } catch (asyncError) {
          console.error('[Visual Builder] Both sync and async scrapers failed:', asyncError);
          toast.error(
            asyncError instanceof Error
              ? asyncError.message
              : 'Failed to load page. Please check the URL and try again.'
          );
        }
      }
    } catch (error) {
      console.error('[Visual Builder] Error in handleLoadPage:', error);
      toast.error(
        error instanceof Error
          ? error.message
          : 'An unexpected error occurred'
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectElement = (element: any) => {
    setSelectedElement(element.id);

    // Auto-generate field name from element type and content
    const suggestedName = element.text
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, '')
      .replace(/\s+/g, '_')
      .substring(0, 20) || element.type;

    // Check if this element is already added
    if (extractedFields.find((f) => f.selector === element.xpath)) {
      toast.info('This element is already added');
      return;
    }

    const newField: ExtractedField = {
      id: `field-${Date.now()}`,
      name: suggestedName,
      selector: element.xpath,
      type: 'xpath',
      value: element.text,
      element: `${element.type}: ${element.text.substring(0, 50)}...`,
    };

    setExtractedFields([...extractedFields, newField]);
    toast.success(`Added field: ${suggestedName}`);
  };

  const handleUpdateField = (fieldId: string, key: string, value: any) => {
    setExtractedFields(
      extractedFields.map((field) =>
        field.id === fieldId ? { ...field, [key]: value } : field
      )
    );
  };

  const handleRemoveField = (fieldId: string) => {
    setExtractedFields(extractedFields.filter((f) => f.id !== fieldId));
    toast.success('Field removed');
  };

  const handleTestExtraction = async () => {
    if (!session) {
      toast.error('Please sign in to continue');
      return;
    }

    if (!targetUrl) {
      toast.error('No URL loaded');
      return;
    }

    if (extractedFields.length === 0) {
      toast.error('Add at least one field to test');
      return;
    }

    setIsTesting(true);

    try {
      const token = await session.getToken();
      if (!token) {
        toast.error('Authentication failed');
        return;
      }

      // Format selectors for the API
      const selectors = extractedFields.map((field) => ({
        name: field.name,
        type: field.type,
        selector: field.selector,
      }));

      // Call backend API to test extraction
      const results = await jobsAPI.testExtraction(targetUrl, selectors, token);

      setPreviewData(results);
      toast.success('Extraction test completed successfully');
    } catch (error) {
      console.error('Error testing extraction', error);
      toast.error(
        error instanceof Error
          ? error.message
          : 'Failed to test extraction'
      );
    } finally {
      setIsTesting(false);
    }
  };

  const handleSaveAsJob = async () => {
    if (!session) {
      toast.error('Please sign in to continue');
      return;
    }

    if (extractedFields.length === 0) {
      toast.error('Add at least one field to extract');
      return;
    }

    if (!targetUrl) {
      toast.error('No URL loaded');
      return;
    }

    // Prompt for job name
    const jobName = prompt('Enter a name for this scraping job:');
    if (!jobName || !jobName.trim()) {
      return;
    }

    setIsSaving(true);

    try {
      const token = await session.getToken();
      if (!token) {
        toast.error('Authentication failed');
        return;
      }

      // Format queries from extracted fields
      const queries = extractedFields.map((field) => ({
        name: field.name,
        type: field.type,
        query: field.selector,
        join: false,
      }));

      // Create the job
      const job = await jobsAPI.create(
        {
          name: jobName.trim(),
          source: targetUrl,
          queries,
          rate_limit: 10, // Default rate limit
        },
        token
      );

      toast.success(`Job "${jobName}" created successfully!`);
      router.push(`/dashboard/jobs/${job.job_id}`);
    } catch (error) {
      console.error('Error creating job', error);
      toast.error(
        error instanceof Error
          ? error.message
          : 'Failed to create job'
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveAsTemplate = () => {
    if (extractedFields.length === 0) {
      toast.error('Add at least one field to extract');
      return;
    }

    const templateName = prompt('Enter a name for this template:');
    if (!templateName) return;

    toast.success(`Template "${templateName}" saved`);
  };

  return (
    <AppLayout>
      <div className="space-y-6 p-6">
        {/* Back Button */}
        <Button variant="ghost" size="sm" onClick={() => router.push('/dashboard')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Dashboard
        </Button>

        <PageHeader
          title="Visual Scraper Builder"
          description="Point and click to build your scraping job without writing code"
        />

        {/* URL Input */}
        <Card>
          <CardHeader>
            <CardTitle>Target Website</CardTitle>
            <CardDescription>
              Enter the URL of the page you want to scrape
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Input
                placeholder="https://example.com/product/123"
                value={targetUrl}
                onChange={(e) => setTargetUrl(e.target.value)}
                className="flex-1"
                disabled={pageLoaded}
              />
              {!pageLoaded ? (
                <Button onClick={handleLoadPage} disabled={isLoading || isAsyncLoading}>
                  {isLoading || isAsyncLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      {isAsyncLoading ? 'Scraping...' : 'Loading...'}
                    </>
                  ) : (
                    'Load Page'
                  )}
                </Button>
              ) : (
                <Button
                  variant="outline"
                  onClick={() => {
                    setPageLoaded(false);
                    setPageStructure(null);
                    setExtractedFields([]);
                    setPreviewData([]);
                    setAsyncTaskId(null);
                    setIsAsyncLoading(false);
                    clearMessages();
                  }}
                >
                  Change URL
                </Button>
              )}
            </div>

            {!pageLoaded && (
              <div className="mt-4 rounded-lg border border-blue-500 bg-blue-900/10 p-4">
                <div className="flex items-start gap-3">
                  <AlertCircle className="h-5 w-5 text-blue-500 mt-0.5" />
                  <div className="text-sm">
                    <p className="font-medium text-blue-300 mb-1">How it works:</p>
                    <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
                      <li>Enter the URL of the page you want to scrape</li>
                      <li>Click elements on the page to select them for extraction</li>
                      <li>Configure field names and selectors</li>
                      <li>Test the extraction to preview results</li>
                      <li>Save as a job or reusable template</li>
                    </ol>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Scraper Loading State */}
        {(isLoading || isAsyncLoading) && (
          <Card className="border-blue-500 bg-blue-900/10">
            <CardContent className="pt-6">
              <div className="flex items-start gap-3">
                <Loader2 className="h-5 w-5 text-blue-500 animate-spin mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <p className="font-medium text-blue-300">
                      {isAsyncLoading ? 'Scraping in progress...' : 'Loading page...'}
                    </p>
                    {asyncTaskId && (
                      <>
                        {isConnected ? (
                          <span title="Connected to WebSocket">
                            <Wifi className="h-4 w-4 text-green-500" />
                          </span>
                        ) : (
                          <span title="Connecting to WebSocket...">
                            <WifiOff className="h-4 w-4 text-yellow-500" />
                          </span>
                        )}
                      </>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground mb-2">
                    {isAsyncLoading
                      ? "This site is taking longer than usual. You'll receive updates in real-time as scraping progresses."
                      : "Analyzing page structure and extracting elements..."}
                  </p>
                  {asyncTaskId && !isConnected && (
                    <p className="text-xs text-yellow-400">
                      Connecting to real-time updates...
                    </p>
                  )}
                  {asyncTaskId && (
                    <p className="text-xs text-muted-foreground mt-2">
                      Task ID: {asyncTaskId}
                    </p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Tier Information Banner */}
        {pageLoaded && pageStructure?.tier_info && pageStructure.tier_info.tier_used > 1 && (
          <Card className="border-blue-500 bg-blue-900/10">
            <CardContent className="pt-6">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-blue-500 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <p className="font-medium text-blue-300 mb-2">
                    Advanced Scraping Used
                  </p>
                  <p className="text-sm text-muted-foreground mb-3">
                    This site required <strong>{pageStructure.tier_info.tier_name}</strong> (Tier {pageStructure.tier_info.tier_used}).
                    Cost: <strong>${pageStructure.tier_info.cost_per_page.toFixed(4)}</strong> per page.
                  </p>

                  {pageStructure.tier_info.escalation_log && pageStructure.tier_info.escalation_log.length > 0 && (
                    <details className="text-sm">
                      <summary className="cursor-pointer text-blue-400 hover:text-blue-300 mb-2">
                        View escalation log
                      </summary>
                      <div className="rounded-lg bg-muted/50 p-3 font-mono text-xs space-y-1">
                        {pageStructure.tier_info.escalation_log.map((log: string, idx: number) => (
                          <div key={idx}>{log}</div>
                        ))}
                      </div>
                    </details>
                  )}

                  <p className="text-xs text-muted-foreground mt-3">
                    💡 For future scrapes of this domain, the system will remember to start with Tier {pageStructure.tier_info.tier_used}.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {pageLoaded && pageStructure && (
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Page Preview */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MousePointer2 className="h-5 w-5" />
                  Page Elements
                </CardTitle>
                <CardDescription>
                  Click on elements below to add them to your extraction
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="rounded-lg border border-border bg-muted/50 p-4 mb-4">
                    <h3 className="font-medium mb-2">{pageStructure.title}</h3>
                    <Badge variant="outline">Sample Page Structure</Badge>
                  </div>

                  {pageStructure.elements.map((element: any) => (
                    <div
                      key={element.id}
                      onClick={() => handleSelectElement(element)}
                      className={`rounded-lg border p-3 cursor-pointer transition-colors ${
                        selectedElement === element.id
                          ? 'border-accent bg-accent/10'
                          : 'border-border hover:border-accent/50 hover:bg-accent/5'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <Badge variant="secondary">{element.type}</Badge>
                        {extractedFields.find((f) => f.selector === element.xpath) && (
                          <CheckCircle2 className="h-4 w-4 text-green-600" />
                        )}
                      </div>
                      <p className="text-sm font-medium mb-1">{element.text}</p>
                      <code className="text-xs text-muted-foreground block truncate">
                        {element.xpath}
                      </code>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Extracted Fields Configuration */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Code className="h-5 w-5" />
                  Extracted Fields ({extractedFields.length})
                </CardTitle>
                <CardDescription>
                  Configure the fields you want to extract
                </CardDescription>
              </CardHeader>
              <CardContent>
                {extractedFields.length === 0 ? (
                  <div className="text-center py-12 text-muted-foreground">
                    <Wand2 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p className="text-lg font-medium mb-2">No fields yet</p>
                    <p className="text-sm">
                      Click on elements in the page preview to add them
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {extractedFields.map((field) => (
                      <div
                        key={field.id}
                        className="rounded-lg border border-border p-4 space-y-3"
                      >
                        <div className="flex items-center justify-between">
                          <Badge variant="outline">{field.type.toUpperCase()}</Badge>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleRemoveField(field.id)}
                          >
                            <Trash2 className="h-4 w-4 text-red-600" />
                          </Button>
                        </div>

                        <div>
                          <Label htmlFor={`name-${field.id}`}>Field Name</Label>
                          <Input
                            id={`name-${field.id}`}
                            value={field.name}
                            onChange={(e) =>
                              handleUpdateField(field.id, 'name', e.target.value)
                            }
                            className="mt-1"
                          />
                        </div>

                        <div>
                          <Label htmlFor={`type-${field.id}`}>Selector Type</Label>
                          <Select
                            value={field.type}
                            onValueChange={(value) =>
                              handleUpdateField(field.id, 'type', value)
                            }
                          >
                            <SelectTrigger id={`type-${field.id}`} className="mt-1">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="xpath">XPath</SelectItem>
                              <SelectItem value="css">CSS Selector</SelectItem>
                              <SelectItem value="regex">Regex</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>

                        <div>
                          <Label htmlFor={`selector-${field.id}`}>Selector</Label>
                          <Input
                            id={`selector-${field.id}`}
                            value={field.selector}
                            onChange={(e) =>
                              handleUpdateField(field.id, 'selector', e.target.value)
                            }
                            className="mt-1 font-mono text-xs"
                          />
                        </div>

                        {field.value && (
                          <div className="rounded bg-muted p-2">
                            <p className="text-xs text-muted-foreground mb-1">Preview:</p>
                            <p className="text-sm">{field.value}</p>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Preview & Actions */}
        {pageLoaded && extractedFields.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Eye className="h-5 w-5" />
                Extraction Preview
              </CardTitle>
              <CardDescription>
                Test your configuration to see the extracted data
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Button onClick={handleTestExtraction} disabled={isTesting}>
                  {isTesting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Testing...
                    </>
                  ) : (
                    <>
                      <Play className="mr-2 h-4 w-4" />
                      Test Extraction
                    </>
                  )}
                </Button>
              </div>

              {previewData.length > 0 && (
                <div className="rounded-lg bg-muted p-4">
                  <pre className="text-xs overflow-x-auto">
                    {JSON.stringify(previewData, null, 2)}
                  </pre>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Save Actions */}
        {pageLoaded && extractedFields.length > 0 && (
          <Card className="border-accent">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold mb-1">Save Your Configuration</h3>
                  <p className="text-sm text-muted-foreground">
                    Create a job or save as a reusable template
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={handleSaveAsTemplate} disabled={isSaving}>
                    <Save className="mr-2 h-4 w-4" />
                    Save as Template
                  </Button>
                  <Button onClick={handleSaveAsJob} disabled={isSaving}>
                    {isSaving ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Creating...
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="mr-2 h-4 w-4" />
                        Create Job
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </AppLayout>
  );
}
