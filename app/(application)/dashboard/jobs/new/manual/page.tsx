'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from '@clerk/nextjs';
import { AppLayout } from '@/components/layout';
import { PageHeader } from '@/components/PageHeader';
import {
  Button,
  Checkbox,
  Input,
  Label,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Switch,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@snowforge/ui';
import {
  Loader2,
  Plus,
  Trash2,
  Save,
  FolderOpen,
  Settings,
  Calendar,
  Code,
  Globe,
  FileOutput,
  Bell,
  Shield,
  Link,
  FileText,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';
import { FormData, FileMapping, Query, Scheduling, Template, ProxyConfig, RenderConfig, ExportConfig, NotificationConfig, SourceType, URLPreviewResponse, COMMON_TIMEZONES } from '@/lib/types';
import { validateQueries, validateHTTP, validateSFTP } from '@/lib/utils';
import { toast } from '@/lib/toast';
import { TemplateModal } from '@/components/TemplateModal';
import { QueryTypeHelpButton } from '@/components/QueryTypeHelp';

export default function ManualConfigurationPage() {
  const router = useRouter();
  const { session } = useSession();
  const [formData, setFormData] = useState<FormData>({
    name: '',
    rate_limit: 1,
    source_type: 'csv' as SourceType,
    source: '',
    url_template: '',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',  // Default to browser timezone
    file_mapping: { delimiter: ',', enclosure: '', escape: '', url_column: '' } as FileMapping,
    scheduling: { days: [], hours: [], minutes: [] } as Scheduling,
    queries: [{ name: '', type: 'xpath', query: '', join: false }] as Query[],
    proxy_config: {
      enabled: false,
      geo_targeting: 'any',
      rotation_strategy: 'random',
      max_retries: 3,
      fallback_to_direct: true
    } as ProxyConfig,
    render_config: {
      enabled: false,
      wait_strategy: 'networkidle',
      wait_timeout_ms: 30000,
      wait_for_selector: null,
      capture_screenshot: false,
      screenshot_full_page: false,
      block_resources: [],
      fallback_to_standard: true
    } as RenderConfig,
    export_config: {
      enabled: false,
      formats: ['json'],
      destination: 's3',
      s3_bucket: null,
      webhook_url: null,
      include_screenshots: false,
      compress: false
    } as ExportConfig,
    notification_config: {
      enabled: false,
      email_on_success: false,
      email_on_failure: true,
      email_addresses: [],
      webhook_on_success: false,
      webhook_on_failure: true,
      webhook_url: null
    } as NotificationConfig
  });

  const [sourceError, setSourceError] = useState<string | null>(null);
  const [queryErrors, setQueryErrors] = useState<(string | null)[]>([]);
  const [sourceLoading, setSourceLoading] = useState<boolean>(false);
  const [headers, setHeaders] = useState<string[]>([]);
  const [templateModalOpen, setTemplateModalOpen] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [urlPreview, setUrlPreview] = useState<URLPreviewResponse | null>(null);
  const [urlPreviewLoading, setUrlPreviewLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('basics');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string | null>>({});
  const maxQueries = 10;

  // Helper to clear a field error when user starts typing
  const clearFieldError = (field: string) => {
    if (fieldErrors[field]) {
      setFieldErrors(prev => ({ ...prev, [field]: null }));
    }
  };

  useEffect(() => {
    const fetchToken = async () => {
      if (session) {
        const tkn = await session.getToken();
        setToken(tkn);
      }
    };
    fetchToken();
  }, [session]);

  const validateSource = async () => {
    if (!formData.source) return;
    setSourceLoading(true);
    try {
      if (formData.source.startsWith('sftp://')) {
        const { delimiter, enclosure, escape, headers: detectedHeaders } = await validateSFTP(formData.source);
        setFormData((prevState) => ({
          ...prevState,
          file_mapping: { delimiter, enclosure, escape, url_column: prevState.file_mapping.url_column }
        }));
        setHeaders(detectedHeaders);
        toast.success('SFTP URL validated successfully!');
      } else {
        const { delimiter, enclosure, escape, headers: detectedHeaders } = await validateHTTP(formData.source);
        setFormData((prevState) => ({
          ...prevState,
          file_mapping: { delimiter, enclosure, escape, url_column: prevState.file_mapping.url_column }
        }));
        setHeaders(detectedHeaders);
        toast.success('File settings detected successfully!');
      }
      setSourceError(null);
    } catch (error) {
      setSourceError((error as Error).message);
      toast.error((error as Error).message);
    } finally {
      setSourceLoading(false);
    }
  };

  const previewUrlTemplate = async () => {
    if (!formData.url_template) {
      setUrlPreview(null);
      return;
    }
    setUrlPreviewLoading(true);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/preview-url`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url_template: formData.url_template,
          timezone: formData.timezone,
        }),
      });
      const data = await response.json();
      setUrlPreview(data);
      if (data.valid) {
        setSourceError(null);
      } else {
        setSourceError(data.error);
      }
    } catch (error) {
      setUrlPreview(null);
      setSourceError((error as Error).message);
    } finally {
      setUrlPreviewLoading(false);
    }
  };

  const handleInputChange = (field: keyof FormData, value: string | number) => {
    setFormData({ ...formData, [field]: value });
  };

  const handleFileMappingChange = (field: keyof FileMapping, value: string) => {
    setFormData({
      ...formData,
      file_mapping: { ...formData.file_mapping, [field]: value }
    });
  };

  const handleQueryChange = (index: number, field: keyof Query, value: string | boolean) => {
    const updatedQueries = [...formData.queries];
    if (field === 'name' || field === 'query') {
      updatedQueries[index][field] = value as string;
    } else if (field === 'join') {
      updatedQueries[index][field] = value as boolean;
    } else if (field === 'type') {
      const validTypes = ['xpath', 'regex', 'jsonpath', 'pdf_text', 'pdf_table', 'pdf_metadata'];
      if (validTypes.includes(value as string)) {
        updatedQueries[index][field] = value as Query['type'];
      }
    }
    setFormData({ ...formData, queries: updatedQueries });
  };

  const handleAddQuery = () => {
    if (formData.queries.length >= maxQueries) {
      toast.error('Maximum of 10 queries allowed');
      return;
    }
    const hasBlankQuery = formData.queries.some(query => !query.name || !query.query);
    if (hasBlankQuery) {
      toast.error('Please fill out all query fields before adding a new one.');
      return;
    }
    setFormData({
      ...formData,
      queries: [...formData.queries, { name: '', type: 'xpath', query: '', join: false }]
    });
    setQueryErrors([...queryErrors, null]);
  };

  const handleSchedulingChange = (field: keyof Scheduling, value: string[] | number[]) => {
    setFormData((prevState) => {
      const updatedScheduling = { ...prevState.scheduling };
      if (field === 'days') {
        const daysValue = value as string[];
        if (daysValue.includes('Every Day')) {
          updatedScheduling.days = ['Every Day'];
        } else {
          updatedScheduling.days = daysValue.filter((day) => day !== 'Every Day');
        }
      }
      if (field === 'hours') {
        const hoursValue = value as number[];
        if (hoursValue.includes(24)) {
          updatedScheduling.hours = [24];
        } else {
          updatedScheduling.hours = hoursValue.filter((hour) => hour !== 24);
        }
      }
      if (field === 'minutes') {
        updatedScheduling.minutes = value as number[];
      }
      return { ...prevState, scheduling: updatedScheduling };
    });
  };

  const handleSubmit = async () => {
    // Clear previous field errors
    setFieldErrors({});

    // Validate job name
    if (!formData.name || formData.name.trim() === '') {
      setFieldErrors(prev => ({ ...prev, name: "Please enter a job name." }));
      toast.error("Please enter a job name.");
      setActiveTab('basics');
      return;
    }

    // Validation based on source type - switch to basics tab if there are errors
    if (formData.source_type === 'csv') {
      if (!formData.source) {
        setFieldErrors(prev => ({ ...prev, source: "Please enter a source URL." }));
        setSourceError("Please enter a source URL.");
        toast.error("Please enter a source URL.");
        setActiveTab('basics');
        return;
      }
      if (!formData.file_mapping.url_column || formData.file_mapping.url_column === '') {
        setFieldErrors(prev => ({ ...prev, url_column: "Please select a URL column." }));
        setSourceError("Please select a URL column.");
        toast.error("Please select a URL column.");
        setActiveTab('basics');
        return;
      }
    } else {
      // direct_url mode
      if (!formData.url_template) {
        setFieldErrors(prev => ({ ...prev, url_template: "Please enter a URL template." }));
        setSourceError("Please enter a URL template.");
        toast.error("Please enter a URL template.");
        setActiveTab('basics');
        return;
      }
      if (urlPreview && !urlPreview.valid) {
        setFieldErrors(prev => ({ ...prev, url_template: urlPreview.error || "Invalid URL template." }));
        setSourceError(urlPreview.error || "Invalid URL template.");
        toast.error(urlPreview.error || "Invalid URL template.");
        setActiveTab('basics');
        return;
      }
    }

    // Validate queries - switch to queries tab if there are errors
    const queryValidationErrors = await validateQueries(formData.queries);
    setQueryErrors(queryValidationErrors);
    const queriesAreValid = queryValidationErrors.every(error => error === null);

    if (!queriesAreValid) {
      toast.error("Please fix the query errors before submitting.");
      setActiveTab('queries');
      return;
    }

    if (sourceError) {
      setActiveTab('basics');
      return;
    }

    const sortedScheduling = {
      ...formData.scheduling,
      days: [...formData.scheduling.days].sort(),
      hours: [...formData.scheduling.hours].sort((a, b) => a - b),
      minutes: [...formData.scheduling.minutes].sort((a, b) => a - b),
    };

    setIsSubmitting(true);
    try {
      const token = await session?.getToken();
      if (!token) {
        throw new Error("Session is null or token is unavailable");
      }

      // Build submission data based on source type
      const submitData = {
        name: formData.name,
        rate_limit: formData.rate_limit,
        source_type: formData.source_type,
        queries: formData.queries,
        scheduling: sortedScheduling,
        proxy_config: formData.proxy_config,
        render_config: formData.render_config,
        export_config: formData.export_config,
        notification_config: formData.notification_config,
        ...(formData.source_type === 'csv' ? {
          source: formData.source,
          file_mapping: formData.file_mapping,
        } : {
          url_template: formData.url_template,
          timezone: formData.timezone,
        }),
      };

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(submitData),
      });

      if (!response.ok) {
        throw new Error("Failed to create job");
      }

      toast.success("Job created successfully!");
      router.push('/dashboard/jobs');
    } catch (error) {
      toast.error("Error creating job");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveAsTemplate = async () => {
    const templateName = prompt("Enter a name for this template:");
    if (!templateName) return;
    const description = prompt("Enter a description (optional):");

    try {
      const token = await session?.getToken();
      if (!token) throw new Error("Session is null or token is unavailable");

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/templates`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: templateName,
          description: description || undefined,
          config: {
            file_mapping: formData.file_mapping,
            queries: formData.queries,
            scheduling: formData.scheduling,
          }
        }),
      });

      if (!response.ok) throw new Error("Failed to save template");
      toast.success("Template saved successfully!");
    } catch (error) {
      toast.error("Failed to save template");
    }
  };

  const handleLoadTemplate = (template: Template) => {
    setFormData({
      ...formData,
      file_mapping: template.config.file_mapping,
      queries: template.config.queries,
      scheduling: template.config.scheduling,
    });
    setTemplateModalOpen(false);
    toast.success(`Loaded template: ${template.name}`);
  };

  const daysOfWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  const hours = Array.from({ length: 24 }, (_, i) => i);
  const minutes = Array.from({ length: 12 }, (_, i) => i * 5);

  return (
    <AppLayout>
      <div className="space-y-6 max-w-4xl mx-auto">
        <PageHeader
          title="Manual Configuration"
          description="Create a job with full control over XPath, CSS selectors, and advanced options"
          breadcrumbs={[
            { label: 'Jobs', href: '/dashboard/jobs' },
            { label: 'New Job', href: '/dashboard/jobs/new' },
            { label: 'Manual Configuration' },
          ]}
        />

        {/* Action Bar */}
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            onClick={() => setTemplateModalOpen(true)}
            className="flex items-center gap-2"
          >
            <FolderOpen className="h-4 w-4" />
            Load Template
          </Button>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => router.back()}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Create Job
            </Button>
          </div>
        </div>

        {/* Form Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-6">
            <TabsTrigger value="basics" className="flex items-center gap-2">
              <Settings className="h-4 w-4" />
              <span className="hidden sm:inline">Basics</span>
            </TabsTrigger>
            <TabsTrigger value="queries" className="flex items-center gap-2">
              <Code className="h-4 w-4" />
              <span className="hidden sm:inline">Queries</span>
            </TabsTrigger>
            <TabsTrigger value="scheduling" className="flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              <span className="hidden sm:inline">Schedule</span>
            </TabsTrigger>
            <TabsTrigger value="proxy" className="flex items-center gap-2">
              <Shield className="h-4 w-4" />
              <span className="hidden sm:inline">Proxy</span>
            </TabsTrigger>
            <TabsTrigger value="rendering" className="flex items-center gap-2">
              <Globe className="h-4 w-4" />
              <span className="hidden sm:inline">Render</span>
            </TabsTrigger>
            <TabsTrigger value="export" className="flex items-center gap-2">
              <FileOutput className="h-4 w-4" />
              <span className="hidden sm:inline">Export</span>
            </TabsTrigger>
          </TabsList>

          {/* Basics Tab */}
          <TabsContent value="basics" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>General Information</CardTitle>
                <CardDescription>Basic job settings and source configuration</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">Job Name</Label>
                    <Input
                      id="name"
                      placeholder="My Scraping Job"
                      value={formData.name}
                      onChange={e => {
                        handleInputChange('name', e.target.value);
                        clearFieldError('name');
                      }}
                      className={fieldErrors.name ? 'border-red-500 focus-visible:ring-red-500' : ''}
                    />
                    {fieldErrors.name && <p className="text-sm text-destructive">{fieldErrors.name}</p>}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="rateLimit">Rate Limit (requests/second)</Label>
                    <Input
                      id="rateLimit"
                      type="number"
                      min={1}
                      max={8}
                      placeholder="1-8"
                      value={formData.rate_limit}
                      onChange={e => handleInputChange('rate_limit', parseInt(e.target.value))}
                    />
                  </div>
                </div>

                {/* Source Type Toggle */}
                <div className="space-y-3">
                  <Label>Source Type</Label>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant={formData.source_type === 'csv' ? 'default' : 'outline'}
                      className="flex items-center gap-2"
                      onClick={() => {
                        setFormData({ ...formData, source_type: 'csv' });
                        setSourceError(null);
                        setUrlPreview(null);
                      }}
                    >
                      <FileText className="h-4 w-4" />
                      CSV File
                    </Button>
                    <Button
                      type="button"
                      variant={formData.source_type === 'direct_url' ? 'default' : 'outline'}
                      className="flex items-center gap-2"
                      onClick={() => {
                        setFormData({ ...formData, source_type: 'direct_url' });
                        setSourceError(null);
                      }}
                    >
                      <Link className="h-4 w-4" />
                      Direct URL
                    </Button>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {formData.source_type === 'csv'
                      ? 'Parse URLs from a CSV file hosted on HTTP/HTTPS or SFTP'
                      : 'Use a single URL with optional date/time variables (e.g., {{date:Y-m-d}})'}
                  </p>
                </div>

                {/* CSV Source Mode */}
                {formData.source_type === 'csv' && (
                  <div className="space-y-2">
                    <Label htmlFor="sourceUrl">Source URL</Label>
                    <div className="relative">
                      <Input
                        id="sourceUrl"
                        placeholder="https://example.com/data.csv or sftp://..."
                        value={formData.source}
                        onChange={e => {
                          handleInputChange('source', e.target.value);
                          clearFieldError('source');
                        }}
                        onBlur={validateSource}
                        className={fieldErrors.source ? 'border-red-500 focus-visible:ring-red-500' : ''}
                      />
                      {sourceLoading && (
                        <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                          <Loader2 className="h-4 w-4 text-brand-accent animate-spin" />
                        </div>
                      )}
                    </div>
                    {sourceError && <p className="text-sm text-destructive">{sourceError}</p>}
                    {sourceLoading && <p className="text-sm text-muted-foreground">Validating source URL...</p>}
                  </div>
                )}

                {/* Direct URL Mode */}
                {formData.source_type === 'direct_url' && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2 md:col-span-2">
                        <Label htmlFor="urlTemplate">URL Template</Label>
                        <div className="relative">
                          <Input
                            id="urlTemplate"
                            placeholder="https://example.com/report_{{date:Y-m-d}}.pdf"
                            value={formData.url_template}
                            onChange={e => {
                              setFormData({ ...formData, url_template: e.target.value });
                              setUrlPreview(null);
                              clearFieldError('url_template');
                            }}
                            onBlur={previewUrlTemplate}
                            className={fieldErrors.url_template ? 'border-red-500 focus-visible:ring-red-500' : ''}
                          />
                          {urlPreviewLoading && (
                            <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                              <Loader2 className="h-4 w-4 text-brand-accent animate-spin" />
                            </div>
                          )}
                        </div>
                        {sourceError && <p className="text-sm text-destructive">{sourceError}</p>}
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="timezone">Timezone</Label>
                        <Select
                          value={formData.timezone}
                          onValueChange={value => {
                            setFormData({ ...formData, timezone: value });
                            setUrlPreview(null);
                            // Trigger preview with new timezone
                            if (formData.url_template) {
                              setTimeout(previewUrlTemplate, 100);
                            }
                          }}
                        >
                          <SelectTrigger id="timezone">
                            <SelectValue placeholder="Select timezone" />
                          </SelectTrigger>
                          <SelectContent>
                            {COMMON_TIMEZONES.map((tz) => (
                              <SelectItem key={tz} value={tz}>{tz}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <p className="text-xs text-muted-foreground">
                          Date/time variables will be resolved in this timezone
                        </p>
                      </div>
                    </div>

                    {/* URL Preview */}
                    {urlPreview && (
                      <div className={`p-4 rounded-lg border ${urlPreview.valid ? 'border-green-500/30 bg-green-500/5' : 'border-red-500/30 bg-red-500/5'}`}>
                        <div className="flex items-start gap-2">
                          {urlPreview.valid ? (
                            <CheckCircle2 className="h-5 w-5 text-green-500 mt-0.5" />
                          ) : (
                            <AlertCircle className="h-5 w-5 text-red-500 mt-0.5" />
                          )}
                          <div className="space-y-1 flex-1">
                            <p className="text-sm font-medium">
                              {urlPreview.valid ? 'URL Preview' : 'Invalid Template'}
                            </p>
                            {urlPreview.valid ? (
                              <>
                                <p className="text-sm text-muted-foreground break-all">
                                  {urlPreview.resolved}
                                </p>
                                {urlPreview.variables && urlPreview.variables.length > 0 && (
                                  <p className="text-xs text-muted-foreground mt-2">
                                    Variables: {urlPreview.variables.map(v =>
                                      `{{${v.type}${v.offset || ''}${v.format ? ':' + v.format : ''}}}`
                                    ).join(', ')}
                                  </p>
                                )}
                              </>
                            ) : (
                              <p className="text-sm text-red-500">{urlPreview.error}</p>
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Variable Syntax Help */}
                    <div className="p-4 rounded-lg bg-muted/50 border">
                      <p className="text-sm font-medium mb-2">Supported Variables</p>
                      <div className="text-xs text-muted-foreground space-y-1">
                        <p><code className="bg-muted px-1 rounded">{`{{date}}`}</code> - Current date (YYYY-MM-DD)</p>
                        <p><code className="bg-muted px-1 rounded">{`{{date:Y-m-d}}`}</code> - Custom format (2026-01-22)</p>
                        <p><code className="bg-muted px-1 rounded">{`{{date:m/d/Y}}`}</code> - US format (01/22/2026)</p>
                        <p><code className="bg-muted px-1 rounded">{`{{date+1d:Y-m-d}}`}</code> - Tomorrow&apos;s date</p>
                        <p><code className="bg-muted px-1 rounded">{`{{date-1d:Y-m-d}}`}</code> - Yesterday&apos;s date</p>
                        <p><code className="bg-muted px-1 rounded">{`{{time:H_i}}`}</code> - Current time (20_00)</p>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* File Mapping - Only shown for CSV mode */}
            {formData.source_type === 'csv' && (
              <Card>
                <CardHeader>
                  <CardTitle>File Mapping</CardTitle>
                  <CardDescription>Configure how to parse the source file</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="delimiter">Delimiter</Label>
                      <Select value={formData.file_mapping.delimiter} onValueChange={value => handleFileMappingChange('delimiter', value)}>
                        <SelectTrigger id="delimiter">
                          <SelectValue placeholder="Select delimiter" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value=",">,</SelectItem>
                          <SelectItem value=";">;</SelectItem>
                          <SelectItem value="|">|</SelectItem>
                          <SelectItem value="\t">Tab</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="enclosure">Enclosure</Label>
                      <Select value={formData.file_mapping.enclosure} onValueChange={value => handleFileMappingChange('enclosure', value)}>
                        <SelectTrigger id="enclosure">
                          <SelectValue placeholder="Select enclosure" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value='"'>&quot;</SelectItem>
                          <SelectItem value="'">&apos;</SelectItem>
                          <SelectItem value="none">None</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="escape">Escape Character</Label>
                      <Select value={formData.file_mapping.escape} onValueChange={value => handleFileMappingChange('escape', value)}>
                        <SelectTrigger id="escape">
                          <SelectValue placeholder="Select escape" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="\\">\\</SelectItem>
                          <SelectItem value="/">/</SelectItem>
                          <SelectItem value='"'>&quot;</SelectItem>
                          <SelectItem value="none">None</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="urlColumn">URL Column</Label>
                      <Select
                        value={formData.file_mapping.url_column}
                        onValueChange={value => {
                          handleFileMappingChange('url_column', value);
                          clearFieldError('url_column');
                        }}
                      >
                        <SelectTrigger id="urlColumn" className={fieldErrors.url_column ? 'border-red-500 focus:ring-red-500' : ''}>
                          <SelectValue placeholder="Select URL column" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="default">Default (Auto-detect)</SelectItem>
                          {headers.map((header, index) => (
                            <SelectItem key={index} value={header}>{header}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      {fieldErrors.url_column && <p className="text-sm text-destructive">{fieldErrors.url_column}</p>}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Queries Tab */}
          <TabsContent value="queries" className="space-y-6">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Data Queries</CardTitle>
                    <CardDescription>Define queries to extract data from HTML, JSON, or PDF content</CardDescription>
                  </div>
                  <QueryTypeHelpButton />
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {formData.queries.map((query, index) => (
                  <div key={index} className="p-4 border rounded-lg space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Query {index + 1}</span>
                      {formData.queries.length > 1 && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => {
                            const updatedQueries = formData.queries.filter((_, i) => i !== index);
                            setFormData({ ...formData, queries: updatedQueries });
                          }}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      )}
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor={`queryName-${index}`}>Field Name</Label>
                        <Input
                          id={`queryName-${index}`}
                          placeholder="e.g., title, price, description"
                          value={query.name}
                          onChange={e => handleQueryChange(index, 'name', e.target.value)}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor={`queryType-${index}`}>Query Type</Label>
                        <Select value={query.type} onValueChange={value => handleQueryChange(index, 'type', value)}>
                          <SelectTrigger>
                            <SelectValue placeholder="Select type" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="xpath">XPath (HTML)</SelectItem>
                            <SelectItem value="regex">Regex (Text)</SelectItem>
                            <SelectItem value="jsonpath">JSONPath (JSON)</SelectItem>
                            <SelectItem value="pdf_table">PDF Table</SelectItem>
                            <SelectItem value="pdf_text">PDF Text</SelectItem>
                            <SelectItem value="pdf_metadata">PDF Metadata</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="md:col-span-2 space-y-2">
                        <Label htmlFor={`queryExpression-${index}`}>
                          {query.type.startsWith('pdf_') ? 'Expression (Optional)' : 'Expression'}
                        </Label>
                        <Input
                          id={`queryExpression-${index}`}
                          placeholder={
                            query.type === 'xpath' ? '//div[@class="price"]/text()' :
                            query.type === 'regex' ? '\\$([\\d.]+)' :
                            query.type === 'jsonpath' ? '$.data.price' :
                            query.type === 'pdf_table' ? 'Column name to extract (optional)' :
                            query.type === 'pdf_text' ? 'Regex pattern to apply (optional)' :
                            ''
                          }
                          value={query.query}
                          onChange={e => handleQueryChange(index, 'query', e.target.value)}
                        />
                        {query.type === 'pdf_table' && (
                          <p className="text-xs text-muted-foreground">
                            Leave empty to extract all columns. Enter a column name to extract only that column.
                          </p>
                        )}
                        {query.type === 'pdf_text' && (
                          <p className="text-xs text-muted-foreground">
                            Leave empty to extract all text. Enter a regex pattern to extract specific data.
                          </p>
                        )}
                        {query.type === 'pdf_metadata' && (
                          <p className="text-xs text-muted-foreground">
                            Extracts PDF metadata (title, author, page count, etc.)
                          </p>
                        )}
                        {queryErrors[index] && <p className="text-sm text-destructive">{queryErrors[index]}</p>}
                      </div>
                      <div className="flex items-center space-x-2">
                        <Switch
                          id={`join-${index}`}
                          checked={!!query.join}
                          onCheckedChange={(checked) => handleQueryChange(index, 'join', checked)}
                        />
                        <Label htmlFor={`join-${index}`}>Join multiple results</Label>
                      </div>
                    </div>
                  </div>
                ))}
                {formData.queries.length < maxQueries && (
                  <Button onClick={handleAddQuery} variant="outline" className="w-full">
                    <Plus className="h-4 w-4 mr-2" />
                    Add Query
                  </Button>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Scheduling Tab */}
          <TabsContent value="scheduling" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Schedule</CardTitle>
                <CardDescription>Configure when the job should run automatically</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-3">
                  <Label>Days</Label>
                  <div className="flex flex-wrap gap-2">
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="everyDay"
                        checked={formData.scheduling.days.includes('Every Day')}
                        onCheckedChange={(checked) => {
                          handleSchedulingChange('days', checked ? ['Every Day'] : []);
                        }}
                      />
                      <Label htmlFor="everyDay" className="font-medium">Every Day</Label>
                    </div>
                    {daysOfWeek.map(day => (
                      <div key={day} className="flex items-center space-x-2">
                        <Checkbox
                          id={day.toLowerCase()}
                          onCheckedChange={(checked) => {
                            const newDays = checked ? [...formData.scheduling.days, day] : formData.scheduling.days.filter(d => d !== day);
                            handleSchedulingChange('days', newDays);
                          }}
                          checked={formData.scheduling.days.includes(day)}
                          disabled={formData.scheduling.days.includes('Every Day')}
                        />
                        <Label htmlFor={day.toLowerCase()}>{day.slice(0, 3)}</Label>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="space-y-3">
                  <Label>Hours</Label>
                  <div className="flex flex-wrap gap-2">
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="everyHour"
                        checked={formData.scheduling.hours.includes(24)}
                        onCheckedChange={(checked) => {
                          handleSchedulingChange('hours', checked ? [24] : []);
                        }}
                      />
                      <Label htmlFor="everyHour" className="font-medium">Every Hour</Label>
                    </div>
                    {hours.map(hour => (
                      <div key={hour} className="flex items-center space-x-2">
                        <Checkbox
                          id={`hour-${hour}`}
                          onCheckedChange={(checked) => {
                            const newHours = checked ? [...formData.scheduling.hours, hour] : formData.scheduling.hours.filter(h => h !== hour);
                            handleSchedulingChange('hours', newHours);
                          }}
                          checked={formData.scheduling.hours.includes(hour)}
                          disabled={formData.scheduling.hours.includes(24)}
                        />
                        <Label htmlFor={`hour-${hour}`}>{`${hour.toString().padStart(2, '0')}:00`}</Label>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="space-y-3">
                  <Label>Minutes</Label>
                  <div className="flex flex-wrap gap-2">
                    {minutes.map(minute => (
                      <div key={minute} className="flex items-center space-x-2">
                        <Checkbox
                          id={`minute-${minute}`}
                          checked={formData.scheduling.minutes.includes(minute)}
                          onCheckedChange={(checked) => {
                            const newMinutes = checked ? [...formData.scheduling.minutes, minute] : formData.scheduling.minutes.filter(m => m !== minute);
                            handleSchedulingChange('minutes', newMinutes);
                          }}
                        />
                        <Label htmlFor={`minute-${minute}`}>{`:${minute.toString().padStart(2, '0')}`}</Label>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Proxy Tab */}
          <TabsContent value="proxy" className="space-y-6">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Proxy Configuration</CardTitle>
                    <CardDescription>Configure proxy rotation for avoiding rate limits</CardDescription>
                  </div>
                  <Switch
                    checked={formData.proxy_config?.enabled || false}
                    onCheckedChange={(checked) =>
                      setFormData({
                        ...formData,
                        proxy_config: { ...formData.proxy_config!, enabled: checked }
                      })
                    }
                  />
                </div>
              </CardHeader>
              {formData.proxy_config?.enabled && (
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="geoTargeting">Geo-Targeting</Label>
                      <Select
                        value={formData.proxy_config?.geo_targeting || 'any'}
                        onValueChange={(value) =>
                          setFormData({
                            ...formData,
                            proxy_config: { ...formData.proxy_config!, geo_targeting: value as any }
                          })
                        }
                      >
                        <SelectTrigger id="geoTargeting">
                          <SelectValue placeholder="Select region" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="any">Any Region</SelectItem>
                          <SelectItem value="us">United States</SelectItem>
                          <SelectItem value="eu">Europe</SelectItem>
                          <SelectItem value="as">Asia</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="rotationStrategy">Rotation Strategy</Label>
                      <Select
                        value={formData.proxy_config?.rotation_strategy || 'random'}
                        onValueChange={(value) =>
                          setFormData({
                            ...formData,
                            proxy_config: { ...formData.proxy_config!, rotation_strategy: value as any }
                          })
                        }
                      >
                        <SelectTrigger id="rotationStrategy">
                          <SelectValue placeholder="Select strategy" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="random">Random</SelectItem>
                          <SelectItem value="round-robin">Round Robin</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="maxRetries">Max Retries</Label>
                      <Input
                        id="maxRetries"
                        type="number"
                        min={1}
                        max={10}
                        value={formData.proxy_config?.max_retries || 3}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            proxy_config: { ...formData.proxy_config!, max_retries: parseInt(e.target.value) }
                          })
                        }
                      />
                    </div>
                    <div className="flex items-center space-x-2 pt-6">
                      <Switch
                        id="fallbackToDirect"
                        checked={formData.proxy_config?.fallback_to_direct !== false}
                        onCheckedChange={(checked) =>
                          setFormData({
                            ...formData,
                            proxy_config: { ...formData.proxy_config!, fallback_to_direct: checked }
                          })
                        }
                      />
                      <Label htmlFor="fallbackToDirect">Fallback to direct connection</Label>
                    </div>
                  </div>
                </CardContent>
              )}
            </Card>
          </TabsContent>

          {/* Rendering Tab */}
          <TabsContent value="rendering" className="space-y-6">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>JavaScript Rendering</CardTitle>
                    <CardDescription>Enable for JavaScript-heavy websites (SPAs)</CardDescription>
                  </div>
                  <Switch
                    checked={formData.render_config?.enabled || false}
                    onCheckedChange={(checked) =>
                      setFormData({
                        ...formData,
                        render_config: { ...formData.render_config!, enabled: checked }
                      })
                    }
                  />
                </div>
              </CardHeader>
              {formData.render_config?.enabled && (
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="waitStrategy">Wait Strategy</Label>
                      <Select
                        value={formData.render_config?.wait_strategy || 'networkidle'}
                        onValueChange={(value) =>
                          setFormData({
                            ...formData,
                            render_config: { ...formData.render_config!, wait_strategy: value as any }
                          })
                        }
                      >
                        <SelectTrigger id="waitStrategy">
                          <SelectValue placeholder="Select wait strategy" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="load">Load (fastest)</SelectItem>
                          <SelectItem value="domcontentloaded">DOM Content Loaded</SelectItem>
                          <SelectItem value="networkidle">Network Idle (recommended)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="waitTimeout">Wait Timeout (ms)</Label>
                      <Input
                        id="waitTimeout"
                        type="number"
                        min={5000}
                        max={120000}
                        step={1000}
                        value={formData.render_config?.wait_timeout_ms || 30000}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            render_config: { ...formData.render_config!, wait_timeout_ms: parseInt(e.target.value) }
                          })
                        }
                      />
                    </div>
                    <div className="md:col-span-2 space-y-2">
                      <Label htmlFor="waitForSelector">Wait for Selector (optional)</Label>
                      <Input
                        id="waitForSelector"
                        type="text"
                        placeholder="e.g., .product-list, #content"
                        value={formData.render_config?.wait_for_selector || ''}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            render_config: { ...formData.render_config!, wait_for_selector: e.target.value || null }
                          })
                        }
                      />
                    </div>
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="captureScreenshot"
                        checked={formData.render_config?.capture_screenshot || false}
                        onCheckedChange={(checked) =>
                          setFormData({
                            ...formData,
                            render_config: { ...formData.render_config!, capture_screenshot: checked }
                          })
                        }
                      />
                      <Label htmlFor="captureScreenshot">Capture screenshot</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="fallbackToStandard"
                        checked={formData.render_config?.fallback_to_standard !== false}
                        onCheckedChange={(checked) =>
                          setFormData({
                            ...formData,
                            render_config: { ...formData.render_config!, fallback_to_standard: checked }
                          })
                        }
                      />
                      <Label htmlFor="fallbackToStandard">Fallback to standard requests</Label>
                    </div>
                  </div>
                </CardContent>
              )}
            </Card>
          </TabsContent>

          {/* Export Tab */}
          <TabsContent value="export" className="space-y-6">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Export Settings</CardTitle>
                    <CardDescription>Configure how and where to export results</CardDescription>
                  </div>
                  <Switch
                    checked={formData.export_config?.enabled || false}
                    onCheckedChange={(checked) =>
                      setFormData({
                        ...formData,
                        export_config: { ...formData.export_config!, enabled: checked }
                      })
                    }
                  />
                </div>
              </CardHeader>
              {formData.export_config?.enabled && (
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Export Formats</Label>
                      <div className="space-y-2">
                        {(['json', 'csv', 'xlsx'] as const).map((format) => (
                          <div key={format} className="flex items-center space-x-2">
                            <Checkbox
                              id={`format-${format}`}
                              checked={formData.export_config?.formats?.includes(format) || false}
                              onCheckedChange={(checked) => {
                                const currentFormats = formData.export_config?.formats || [];
                                const newFormats = checked
                                  ? [...currentFormats, format]
                                  : currentFormats.filter(f => f !== format);
                                setFormData({
                                  ...formData,
                                  export_config: { ...formData.export_config!, formats: newFormats.length > 0 ? newFormats : ['json'] }
                                });
                              }}
                            />
                            <Label htmlFor={`format-${format}`} className="uppercase">{format}</Label>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="exportDestination">Destination</Label>
                      <Select
                        value={formData.export_config?.destination || 's3'}
                        onValueChange={(value) =>
                          setFormData({
                            ...formData,
                            export_config: { ...formData.export_config!, destination: value as any }
                          })
                        }
                      >
                        <SelectTrigger id="exportDestination">
                          <SelectValue placeholder="Select destination" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="s3">S3 Bucket</SelectItem>
                          <SelectItem value="local">Local Storage</SelectItem>
                          <SelectItem value="webhook">Webhook POST</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="compressExport"
                        checked={formData.export_config?.compress || false}
                        onCheckedChange={(checked) =>
                          setFormData({
                            ...formData,
                            export_config: { ...formData.export_config!, compress: checked }
                          })
                        }
                      />
                      <Label htmlFor="compressExport">Compress files (ZIP)</Label>
                    </div>
                  </div>
                </CardContent>
              )}
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Notifications</CardTitle>
                    <CardDescription>Get notified when jobs complete or fail</CardDescription>
                  </div>
                  <Switch
                    checked={formData.notification_config?.enabled || false}
                    onCheckedChange={(checked) =>
                      setFormData({
                        ...formData,
                        notification_config: { ...formData.notification_config!, enabled: checked }
                      })
                    }
                  />
                </div>
              </CardHeader>
              {formData.notification_config?.enabled && (
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="emailOnSuccess"
                        checked={formData.notification_config?.email_on_success || false}
                        onCheckedChange={(checked) =>
                          setFormData({
                            ...formData,
                            notification_config: { ...formData.notification_config!, email_on_success: checked }
                          })
                        }
                      />
                      <Label htmlFor="emailOnSuccess">Email on success</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="emailOnFailure"
                        checked={formData.notification_config?.email_on_failure !== false}
                        onCheckedChange={(checked) =>
                          setFormData({
                            ...formData,
                            notification_config: { ...formData.notification_config!, email_on_failure: checked }
                          })
                        }
                      />
                      <Label htmlFor="emailOnFailure">Email on failure</Label>
                    </div>
                    <div className="md:col-span-2 space-y-2">
                      <Label htmlFor="emailAddresses">Email Addresses</Label>
                      <Input
                        id="emailAddresses"
                        type="text"
                        placeholder="email1@example.com, email2@example.com"
                        value={formData.notification_config?.email_addresses?.join(', ') || ''}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            notification_config: {
                              ...formData.notification_config!,
                              email_addresses: e.target.value.split(',').map(email => email.trim()).filter(email => email.length > 0)
                            }
                          })
                        }
                      />
                    </div>
                  </div>
                </CardContent>
              )}
            </Card>
          </TabsContent>
        </Tabs>

        {/* Bottom Action Bar */}
        <div className="flex items-center justify-between border-t pt-6">
          <Button variant="outline" onClick={handleSaveAsTemplate} className="flex items-center gap-2">
            <Save className="h-4 w-4" />
            Save as Template
          </Button>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => router.back()}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Create Job
            </Button>
          </div>
        </div>
      </div>

      {/* Template Modal */}
      {templateModalOpen && (
        <TemplateModal
          closeModal={() => setTemplateModalOpen(false)}
          onSelectTemplate={handleLoadTemplate}
          token={token}
        />
      )}
    </AppLayout>
  );
}
