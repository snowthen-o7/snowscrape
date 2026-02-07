'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from '@clerk/nextjs';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { AppLayout } from '@/components/layout';
import { PageHeader } from '@snowforge/ui';
import { Button } from '@snowforge/ui';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@snowforge/ui';
import {
  Loader2,
  Save,
  FolderOpen,
  Settings,
  Calendar,
  Code,
  Globe,
  FileOutput,
  Shield,
} from 'lucide-react';
import { jobFormSchema, type JobFormValues } from '@/lib/schemas/jobFormSchema';
import type { Template, URLPreviewResponse, SourceType } from '@/lib/types';
import { validateQueries, validateHTTP, validateSFTP } from '@/lib/utils';
import { toast } from '@/lib/toast';
import { TemplateModal } from '@/components/TemplateModal';
import {
  BasicsTab,
  QueriesTab,
  SchedulingTab,
  ProxyTab,
  RenderingTab,
  ExportTab,
} from '@/components/job-form';

export default function ManualConfigurationPage() {
  const router = useRouter();
  const { session } = useSession();

  const form = useForm<JobFormValues>({
    resolver: zodResolver(jobFormSchema),
    defaultValues: {
      name: '',
      rate_limit: 1,
      source_type: 'csv' as SourceType,
      source: '',
      url_template: '',
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
      file_mapping: { delimiter: ',', enclosure: '', escape: '', url_column: '' },
      scheduling: { days: [], hours: [], minutes: [] },
      queries: [{ name: '', type: 'xpath', query: '', join: false }],
      proxy_config: {
        enabled: false,
        geo_targeting: 'any',
        rotation_strategy: 'random',
        max_retries: 3,
        fallback_to_direct: true,
      },
      render_config: {
        enabled: false,
        wait_strategy: 'networkidle',
        wait_timeout_ms: 30000,
        wait_for_selector: null,
        capture_screenshot: false,
        screenshot_full_page: false,
        block_resources: [],
        fallback_to_standard: true,
      },
      export_config: {
        enabled: false,
        formats: ['json'],
        destination: 's3',
        s3_bucket: null,
        webhook_url: null,
        include_screenshots: false,
        compress: false,
      },
      notification_config: {
        enabled: false,
        email_on_success: false,
        email_on_failure: true,
        email_addresses: [],
        webhook_on_success: false,
        webhook_on_failure: true,
        webhook_url: null,
      },
    },
  });

  const [sourceError, setSourceError] = useState<string | null>(null);
  const [queryErrors, setQueryErrors] = useState<(string | null)[]>([]);
  const [sourceLoading, setSourceLoading] = useState(false);
  const [headers, setHeaders] = useState<string[]>([]);
  const [templateModalOpen, setTemplateModalOpen] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [urlPreview, setUrlPreview] = useState<URLPreviewResponse | null>(null);
  const [urlPreviewLoading, setUrlPreviewLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('basics');

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
    const source = form.getValues('source');
    if (!source) return;
    setSourceLoading(true);
    try {
      if (source.startsWith('sftp://')) {
        const { delimiter, enclosure, escape, headers: detectedHeaders } = await validateSFTP(source);
        form.setValue('file_mapping', {
          delimiter, enclosure, escape,
          url_column: form.getValues('file_mapping.url_column'),
        });
        setHeaders(detectedHeaders);
        toast.success('SFTP URL validated successfully!');
      } else {
        const { delimiter, enclosure, escape, headers: detectedHeaders } = await validateHTTP(source);
        form.setValue('file_mapping', {
          delimiter, enclosure, escape,
          url_column: form.getValues('file_mapping.url_column'),
        });
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
    const urlTemplate = form.getValues('url_template');
    if (!urlTemplate) {
      setUrlPreview(null);
      return;
    }
    setUrlPreviewLoading(true);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/preview-url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url_template: urlTemplate,
          timezone: form.getValues('timezone'),
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

  const onSubmit = async (data: JobFormValues) => {
    // Run async query validation (Zod handles sync validation)
    const queryValidationErrors = await validateQueries(data.queries);
    setQueryErrors(queryValidationErrors);

    if (queryValidationErrors.some(e => e !== null)) {
      toast.error('Please fix the query errors before submitting.');
      setActiveTab('queries');
      return;
    }

    if (sourceError) {
      setActiveTab('basics');
      return;
    }

    const sortedScheduling = {
      ...data.scheduling,
      days: [...data.scheduling.days].sort(),
      hours: [...data.scheduling.hours].sort((a, b) => a - b),
      minutes: [...data.scheduling.minutes].sort((a, b) => a - b),
    };

    setIsSubmitting(true);
    try {
      const token = await session?.getToken();
      if (!token) {
        throw new Error('Session is null or token is unavailable');
      }

      const submitData = {
        name: data.name,
        rate_limit: data.rate_limit,
        source_type: data.source_type,
        queries: data.queries,
        scheduling: sortedScheduling,
        proxy_config: data.proxy_config,
        render_config: data.render_config,
        export_config: data.export_config,
        notification_config: data.notification_config,
        ...(data.source_type === 'csv' ? {
          source: data.source,
          file_mapping: data.file_mapping,
        } : {
          url_template: data.url_template,
          timezone: data.timezone,
        }),
      };

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(submitData),
      });

      if (!response.ok) {
        throw new Error('Failed to create job');
      }

      toast.success('Job created successfully!');
      router.push('/dashboard/jobs');
    } catch (error) {
      toast.error('Error creating job');
    } finally {
      setIsSubmitting(false);
    }
  };

  const onFormError = () => {
    // Navigate to the tab with the first error
    const errors = form.formState.errors;
    if (errors.name || errors.rate_limit || errors.source || errors.url_template || errors.file_mapping) {
      setActiveTab('basics');
    } else if (errors.queries) {
      setActiveTab('queries');
    }
    toast.error('Please fix the form errors before submitting.');
  };

  const handleSaveAsTemplate = async () => {
    const templateName = prompt('Enter a name for this template:');
    if (!templateName) return;
    const description = prompt('Enter a description (optional):');

    try {
      const token = await session?.getToken();
      if (!token) throw new Error('Session is null or token is unavailable');

      const formData = form.getValues();
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/templates`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: templateName,
          description: description || undefined,
          config: {
            file_mapping: formData.file_mapping,
            queries: formData.queries,
            scheduling: formData.scheduling,
          },
        }),
      });

      if (!response.ok) throw new Error('Failed to save template');
      toast.success('Template saved successfully!');
    } catch (error) {
      toast.error('Failed to save template');
    }
  };

  const handleLoadTemplate = (template: Template) => {
    form.setValue('file_mapping', template.config.file_mapping);
    form.setValue('queries', template.config.queries);
    form.setValue('scheduling', template.config.scheduling);
    setTemplateModalOpen(false);
    toast.success(`Loaded template: ${template.name}`);
  };

  return (
    <AppLayout>
      <FormProvider {...form}>
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
              <Button onClick={form.handleSubmit(onSubmit, onFormError)} disabled={isSubmitting}>
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

            <TabsContent value="basics" className="space-y-6">
              <BasicsTab
                sourceError={sourceError}
                sourceLoading={sourceLoading}
                headers={headers}
                urlPreview={urlPreview}
                urlPreviewLoading={urlPreviewLoading}
                onValidateSource={validateSource}
                onPreviewUrlTemplate={previewUrlTemplate}
                onSourceErrorClear={() => { setSourceError(null); setUrlPreview(null); }}
                onUrlPreviewClear={() => setUrlPreview(null)}
              />
            </TabsContent>

            <TabsContent value="queries" className="space-y-6">
              <QueriesTab queryErrors={queryErrors} />
            </TabsContent>

            <TabsContent value="scheduling" className="space-y-6">
              <SchedulingTab />
            </TabsContent>

            <TabsContent value="proxy" className="space-y-6">
              <ProxyTab />
            </TabsContent>

            <TabsContent value="rendering" className="space-y-6">
              <RenderingTab />
            </TabsContent>

            <TabsContent value="export" className="space-y-6">
              <ExportTab />
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
              <Button onClick={form.handleSubmit(onSubmit, onFormError)} disabled={isSubmitting}>
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
      </FormProvider>
    </AppLayout>
  );
}
