'use client';

import { useEffect, useState } from 'react';

import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"

import { X, Loader2, Plus, Trash2, Save, FolderOpen, Link, FileText, AlertCircle, CheckCircle2 } from 'lucide-react'
import { SessionResource } from '@clerk/types';
import { FormData, FileMapping, Job, Query, Scheduling, Template, ProxyConfig, RenderConfig, ExportConfig, NotificationConfig, SourceType, URLPreviewResponse, COMMON_TIMEZONES } from '@/lib/types';
import { validateQueries, validateHTTP, validateSFTP } from '@/lib/utils';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { TemplateModal } from './TemplateModal';
import { QueryTypeHelpButton } from './QueryTypeHelp';

export function JobModal({ closeModal, jobDetails, session }: {
  closeModal: () => void,
  jobDetails?: Job | null,
  session: SessionResource | null,
 }) {
  const [formData, setFormData] = useState<FormData>({
    name: '',
    rate_limit: 1,
    source_type: 'csv' as SourceType,
    source: '',
    url_template: '',
    timezone: typeof window !== 'undefined' ? (Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC') : 'UTC',
    file_mapping: { delimiter: ',', enclosure: '', escape: '', url_column: '' } as FileMapping,
    scheduling: { days: [], hours: [], minutes: [] } as Scheduling, // Array for selected days and hours
    queries: [{ name: '', type: 'xpath', query: '', join: false }] as Query[], // Explicitly type the queries as an array of Query
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
  const [queryErrors, setQueryErrors] = useState<(string | null)[]>([]); // Track errors for each query
  const [sourceLoading, setSourceLoading] = useState<boolean>(false);
  const [headers, setHeaders] = useState<string[]>([]); // Track headers from the source file
  const [templateModalOpen, setTemplateModalOpen] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [urlPreview, setUrlPreview] = useState<URLPreviewResponse | null>(null);
  const [urlPreviewLoading, setUrlPreviewLoading] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string | null>>({});
  const maxQueries = 10;

  // Helper to clear a field error when user starts typing
  const clearFieldError = (field: string) => {
    if (fieldErrors[field]) {
      setFieldErrors(prev => ({ ...prev, [field]: null }));
    }
  };

  // Helper function to set error and show toast
  const setErrorAndToast = (setError: React.Dispatch<React.SetStateAction<string | null>>, errorMessage: string) => {
    setError(errorMessage);
    toast.error(errorMessage, { position: 'top-right' });
  };

  useEffect(() => {
    console.log("JobDetails", jobDetails);
    // Fetch token
    const fetchToken = async () => {
      if (session) {
        const tkn = await session.getToken();
        setToken(tkn);
      }
    };
    fetchToken();

    // If jobDetails are passed in, populate formData with jobDetails values
    if (jobDetails) {
      const sourceType = jobDetails.source_type || 'csv';
      setFormData({
        name: jobDetails.name,
        rate_limit: jobDetails.rate_limit,
        source_type: sourceType as SourceType,
        source: jobDetails.source || '',
        url_template: jobDetails.url_template || '',
        timezone: jobDetails.timezone || 'UTC',
        file_mapping: jobDetails.file_mapping || { delimiter: ',', enclosure: '', escape: '', url_column: '' },
        scheduling: jobDetails.scheduling,
        queries: jobDetails.queries.map(query => ({
          ...query,
          join: !!query.join, // Convert join to a boolean value
        })),
        proxy_config: jobDetails.proxy_config || {
          enabled: false,
          geo_targeting: 'any',
          rotation_strategy: 'random',
          max_retries: 3,
          fallback_to_direct: true
        },
        render_config: jobDetails.render_config || {
          enabled: false,
          wait_strategy: 'networkidle',
          wait_timeout_ms: 30000,
          wait_for_selector: null,
          capture_screenshot: false,
          screenshot_full_page: false,
          block_resources: [],
          fallback_to_standard: true
        },
        export_config: jobDetails.export_config || {
          enabled: false,
          formats: ['json'],
          destination: 's3',
          s3_bucket: null,
          webhook_url: null,
          include_screenshots: false,
          compress: false
        },
        notification_config: jobDetails.notification_config || {
          enabled: false,
          email_on_success: false,
          email_on_failure: true,
          email_addresses: [],
          webhook_on_success: false,
          webhook_on_failure: true,
          webhook_url: null
        }
      });

      // Set headers if available (only for CSV mode)
      if (sourceType === 'csv' && jobDetails.file_mapping?.url_column && jobDetails.file_mapping.url_column !== 'default') {
        setHeaders([jobDetails.file_mapping.url_column]);
      }

      // Preview URL template if in direct_url mode
      if (sourceType === 'direct_url' && jobDetails.url_template) {
        previewUrlTemplateAsync(jobDetails.url_template);
      }
    }
  }, [jobDetails, session]);

  // Preview URL template function (async version for useEffect)
  const previewUrlTemplateAsync = async (template: string, timezone?: string) => {
    if (!template) {
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
          url_template: template,
          timezone: timezone || formData.timezone,
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

  // Preview URL template for current formData
  const previewUrlTemplate = async () => {
    await previewUrlTemplateAsync(formData.url_template, formData.timezone);
  };

  // Handle validation when clicking away from the source input
  const validateSource = async () => {
    if (!formData.source) return; // Only validate if the source is not empty
    setSourceLoading(true); // Show loading spinner
    try {
      if (formData.source.startsWith('sftp://')) {
        // SFTP validation
        const { delimiter, enclosure, escape, headers: detectedHeaders } = await validateSFTP(formData.source);
        console.log(delimiter, enclosure, escape, detectedHeaders);
  
        // Set detected settings directly into the formData state
        setFormData((prevState) => ({
          ...prevState,
          file_mapping: {
            delimiter,
            enclosure,
            escape,
            url_column: prevState.file_mapping.url_column // Preserve URL column as default
          }
        }));
  
        setHeaders(detectedHeaders); // Update the dropdown options for URL Column
        toast.success('SFTP URL validated successfully!', { position: 'top-right' });
      } else {
        // HTTP/HTTPS validation
        const { delimiter, enclosure, escape, headers: detectedHeaders } = await validateHTTP(formData.source);
  
        // Set detected settings directly into the formData state
        setFormData((prevState) => ({
          ...prevState,
          file_mapping: {
            delimiter,
            enclosure,
            escape,
            url_column: prevState.file_mapping.url_column // Preserve URL column as default
          }
        }));
  
        setHeaders(detectedHeaders); // Update the dropdown options for URL Column
        toast.success('File settings detected successfully!', { position: 'top-right' });
      }
      setSourceError(null); // Clear error if valid
    } catch (error) {
      setErrorAndToast(setSourceError, (error as Error).message);
    } finally {
      setSourceLoading(false);  // Stop loading spinner
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
    const updatedQueries = [...formData.queries]; // Copy the existing queries

    // Cast 'value' based on the 'field' being updated
    if (field === 'name' || field === 'query') {
      updatedQueries[index][field] = value as string; // Cast 'value' to string
    } else if (field === 'join') {
      updatedQueries[index][field] = value as boolean; // Cast 'value' to boolean
    } else if (field === 'type') {
      // Ensure that the value for 'type' is one of the allowed types
      const validTypes = ['xpath', 'regex', 'jsonpath', 'pdf_text', 'pdf_table', 'pdf_metadata'];
      if (validTypes.includes(value as string)) {
        updatedQueries[index][field] = value as Query['type']; // Cast to correct type
      } else {
        console.error("Invalid type value");
        return; // Stop if the type value is invalid
      }
    }
  
    setFormData({ ...formData, queries: updatedQueries });
  };

  const handleAddQuery = () => {
    if (formData.queries.length >= maxQueries) {
      toast.error('Maximum of 10 queries allowed', { position: 'top-right' });
      return;
    }

    const hasBlankQuery = formData.queries.some(query => !query.name || !query.query);
    if (hasBlankQuery) {
      toast.error('Please fill out all query fields before adding a new one.', { position: 'top-right' });
      return;
    }

    setFormData({
      ...formData,
      queries: [...formData.queries, { name: '', type: 'xpath', query: '', join: false }]
    });
    setQueryErrors([...queryErrors, null]); // Add a new error state for the added query
  };

  const handleSubmit = async () => {
    // Clear previous field errors
    setFieldErrors({});

    // Validate job name
    if (!formData.name || formData.name.trim() === '') {
      setFieldErrors(prev => ({ ...prev, name: "Please enter a job name." }));
      toast.error("Please enter a job name.", { position: 'top-right' });
      return;
    }

    // Validation based on source type
    if (formData.source_type === 'csv') {
      if (!formData.source) {
        setFieldErrors(prev => ({ ...prev, source: "Please enter a source URL." }));
        setErrorAndToast(setSourceError, "Please enter a source URL.");
        return;
      }
      if (!formData.file_mapping.url_column) {
        setFieldErrors(prev => ({ ...prev, url_column: "Please select a URL column." }));
        setErrorAndToast(setSourceError, "Please select a URL column.");
        return; // Stop submission if no column is selected
      }
    } else {
      // direct_url mode
      if (!formData.url_template) {
        setFieldErrors(prev => ({ ...prev, url_template: "Please enter a URL template." }));
        setErrorAndToast(setSourceError, "Please enter a URL template.");
        return;
      }
      if (urlPreview && !urlPreview.valid) {
        setFieldErrors(prev => ({ ...prev, url_template: urlPreview.error || "Invalid URL template." }));
        setErrorAndToast(setSourceError, urlPreview.error || "Invalid URL template.");
        return;
      }
    }

    const queryValidationErrors = await validateQueries(formData.queries); // Get query-specific errors
    setQueryErrors(queryValidationErrors); // Update queryErrors state with the result

    const queriesAreValid = queryValidationErrors.every(error => error === null); // Check if all queries are valid

    if (!queriesAreValid || sourceError) {
      return; // Don't submit if there are errors
    }

    // Sort the scheduling arrays before submitting the form
    const sortedScheduling = {
      ...formData.scheduling,
      days: [...formData.scheduling.days].sort(),
      hours: [...formData.scheduling.hours].sort((a, b) => a - b),  // Sort numerically
      minutes: [...formData.scheduling.minutes].sort((a, b) => a - b),  // Sort numerically
    };

    try {
      const token = await session?.getToken(); // Use optional chaining to ensure session is not null
      if (!token) {
        throw new Error("Session is null or token is unavailable");
      }
      const url = jobDetails ? `${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/${jobDetails.job_id}` : `${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs`;
      const method = jobDetails ? "PUT" : "POST";

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

      const response = await fetch(url, {
        method,
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
          ...(process.env.NEXT_PUBLIC_API_KEY && { "x-api-key": process.env.NEXT_PUBLIC_API_KEY }),
        },
        body: JSON.stringify(submitData),
      });

      if (!response.ok) {
        throw new Error(jobDetails ? "Failed to update job" : "Failed to submit job");
      }

      closeModal(); // Close the modal on success
      toast.success(jobDetails ? "Job updated successfully!" : "Job created successfully!", { position: 'top-right' });
    } catch (error) {
      toast.error(jobDetails ? "Error updating job" : "Error submitting job", { position: 'top-right' });
    }
  };

  // Helper for scheduling
  const handleSchedulingChange = (field: keyof Scheduling, value: string[] | number[]) => {
    setFormData((prevState) => {
      const updatedScheduling = { ...prevState.scheduling };
  
      // Handle "Every Day" and disable other days
      if (field === 'days') {
        // Type assertion to treat `value` as a string array for days
        const daysValue = value as string[];

        if (daysValue.includes('Every Day')) {
          updatedScheduling.days = ['Every Day']; // Only "Every Day" should be selected
        } else {
          updatedScheduling.days = daysValue.filter((day) => day !== 'Every Day'); // Remove "Every Day" if others are selected, Ensure only strings are passed here
        }
      }
  
      // Handle "24" (Every Hour) and disable other hours
      if (field === 'hours') {
        // Type assertion to treat `value` as a number array for hours
        const hoursValue = value as number[];

        if (hoursValue.includes(24)) {
          updatedScheduling.hours = [24]; // Only "24" (Every Hour) should be selected
        } else {
          updatedScheduling.hours = hoursValue.filter((hour) => hour !== 24); // Remove "24" if others are selected
        }
      }

      // Handle "minutes" (multiples of 5)
      if (field === 'minutes') {
        const minutesValue = value as number[];

        // Simply update the selected minutes
        updatedScheduling.minutes = minutesValue;
      }
  
      return { ...prevState, scheduling: updatedScheduling };
    });
  };

  // Save current configuration as template
  const handleSaveAsTemplate = async () => {
    const templateName = prompt("Enter a name for this template:");
    if (!templateName) return;

    const description = prompt("Enter a description (optional):");

    try {
      const token = await session?.getToken();
      if (!token) {
        throw new Error("Session is null or token is unavailable");
      }

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/templates`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
          ...(process.env.NEXT_PUBLIC_API_KEY && { "x-api-key": process.env.NEXT_PUBLIC_API_KEY }),
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

      if (!response.ok) {
        throw new Error("Failed to save template");
      }

      toast.success("Template saved successfully!", { position: 'top-right' });
    } catch (error) {
      console.error("Error saving template", error);
      toast.error("Failed to save template", { position: 'top-right' });
    }
  };

  // Load configuration from template
  const handleLoadTemplate = (template: Template) => {
    setFormData({
      ...formData,
      file_mapping: template.config.file_mapping,
      queries: template.config.queries,
      scheduling: template.config.scheduling,
    });
    setTemplateModalOpen(false);
    toast.success(`Loaded template: ${template.name}`, { position: 'top-right' });
  };

  // Schedule options
  const daysOfWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  const hours = Array.from({ length: 24 }, (_, i) => i); // 0 - 23 hours
  const minutes = Array.from({ length: 12 }, (_, i) => i * 5); // Multiples of 5 minutes

  return (
    <>
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4">
      <div className="bg-gray-800 text-white rounded-lg shadow-lg max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 space-y-6">
          <div className="flex justify-between items-center">
            <ToastContainer />
            <div className="flex-1">
              <h2 className="text-2xl font-bold">{jobDetails ? `Edit Job - ${jobDetails.name}` : "Submit a New Job"}</h2>
            </div>
            <div className="flex items-center gap-2">
              {!jobDetails && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setTemplateModalOpen(true)}
                  className="flex items-center gap-2"
                >
                  <FolderOpen className="h-4 w-4" />
                  Load Template
                </Button>
              )}
              <Button variant="ghost" size="icon" onClick={closeModal}><X className="h-6 w-6" /></Button>
            </div>
          </div>

          {/* General Job Info */}
          <div className="space-y-4">
            <h3 className="text-xl font-semibold">General Job Info</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  placeholder="Job Name"
                  value={formData.name}
                  onChange={e => {
                    handleInputChange('name', e.target.value);
                    clearFieldError('name');
                  }}
                  className={fieldErrors.name ? 'border-red-500 focus-visible:ring-red-500' : ''}
                />
                {fieldErrors.name && <p className="text-sm text-red-400">{fieldErrors.name}</p>}
              </div>
              <div>
                <Label htmlFor="rateLimit">Rate Limit</Label>
                <Input id="rateLimit" type="number" min={1} max={8} placeholder="1-8" value={formData.rate_limit} onChange={e => handleInputChange('rate_limit', parseInt(e.target.value))}/>
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
              <p className="text-sm text-gray-400">
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
                    <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                      <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
                    </div>
                  )}
                </div>
                {sourceError && <p className="text-sm text-red-400">{sourceError}</p>}
                {sourceLoading && (
                  <p className="text-sm text-blue-400">
                    Validating source URL... Please wait.
                  </p>
                )}
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
                        <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                          <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
                        </div>
                      )}
                    </div>
                    {sourceError && <p className="text-sm text-red-400">{sourceError}</p>}
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
                    <p className="text-xs text-gray-400">
                      Date/time variables will be resolved in this timezone
                    </p>
                  </div>
                </div>

                {/* URL Preview */}
                {urlPreview && (
                  <div className={`p-3 rounded-lg border ${urlPreview.valid ? 'border-green-500/30 bg-green-500/10' : 'border-red-500/30 bg-red-500/10'}`}>
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
                            <p className="text-sm text-gray-300 break-all">
                              {urlPreview.resolved}
                            </p>
                            {urlPreview.variables && urlPreview.variables.length > 0 && (
                              <p className="text-xs text-gray-400 mt-2">
                                Variables: {urlPreview.variables.map(v =>
                                  `{{${v.type}${v.offset || ''}${v.format ? ':' + v.format : ''}}}`
                                ).join(', ')}
                              </p>
                            )}
                          </>
                        ) : (
                          <p className="text-sm text-red-400">{urlPreview.error}</p>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Variable Syntax Help */}
                <div className="p-3 rounded-lg bg-gray-700/50 border border-gray-600">
                  <p className="text-sm font-medium mb-2 text-gray-200">Supported Variables</p>
                  <div className="text-xs text-gray-400 space-y-1">
                    <p><code className="bg-gray-700 px-1 rounded">{`{{date}}`}</code> - Current date (YYYY-MM-DD)</p>
                    <p><code className="bg-gray-700 px-1 rounded">{`{{date:Y-m-d}}`}</code> - Custom format (2026-01-22)</p>
                    <p><code className="bg-gray-700 px-1 rounded">{`{{date:m/d/Y}}`}</code> - US format (01/22/2026)</p>
                    <p><code className="bg-gray-700 px-1 rounded">{`{{date+1d:Y-m-d}}`}</code> - Tomorrow&apos;s date</p>
                    <p><code className="bg-gray-700 px-1 rounded">{`{{date-1d:Y-m-d}}`}</code> - Yesterday&apos;s date</p>
                    <p><code className="bg-gray-700 px-1 rounded">{`{{time:H_i}}`}</code> - Current time (20_00)</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* File Mapping - Only shown for CSV mode */}
          {formData.source_type === 'csv' && (
            <div className="space-y-4">
              <h3 className="text-xl font-semibold">File Mapping</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
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
                <div>
                  <Label htmlFor="enclosure">Enclosure</Label>
                  <Select value={formData.file_mapping.enclosure} onValueChange={value => handleFileMappingChange('enclosure', value)}>
                    <SelectTrigger id="enclosure">
                      <SelectValue placeholder="Select enclosure" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value='"'>"</SelectItem>
                      <SelectItem value="'">'</SelectItem>
                      <SelectItem value="none">None</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="escape">Escape</Label>
                  <Select value={formData.file_mapping.escape} onValueChange={value => handleFileMappingChange('escape', value)}>
                    <SelectTrigger id="escape">
                      <SelectValue placeholder="Select escape" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="\\">\\</SelectItem>
                      <SelectItem value="/">/</SelectItem>
                      <SelectItem value='"'>"</SelectItem>
                      <SelectItem value="'">'</SelectItem>
                      <SelectItem value="none">None</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
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
                      <SelectItem value="default">Default (Auto-detect)</SelectItem>  {/* Add default option */}
                      {headers.length > 0 && (
                        headers.map((header, index) => (
                          <SelectItem key={index} value={header}>{header}</SelectItem>
                        ))
                      )}
                  </SelectContent>
                  </Select>
                  {fieldErrors.url_column && <p className="text-sm text-red-400">{fieldErrors.url_column}</p>}
                </div>
              </div>
            </div>
          )}

          {/* Scheduling */}
          <div className="space-y-4">
            <h3 className="text-xl font-semibold">Scheduling</h3>

            {/* Days */}
            <div className="space-y-2">
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
                  <Label htmlFor="everyDay">Every Day</Label>
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
                      disabled={formData.scheduling.days.includes('Every Day')} // Disable if "Every Day" is selected
                    />
                    <Label htmlFor={day.toLowerCase()}>{day}</Label>
                  </div>
                ))}
              </div>
            </div>

            {/* Hours */}
            <div className="space-y-2">
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
                  <Label htmlFor="everyHour">Every Hour</Label>
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
                      disabled={formData.scheduling.hours.includes(24)} // Disable if "24" (Every Hour) is selected
                    />
                    <Label htmlFor={`hour-${hour}`}>{`${hour.toString().padStart(2, '0')}:00`}</Label>
                  </div>
                ))}
              </div>
            </div>

            {/* Minutes */}
            <div className="space-y-2">
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
                    <Label htmlFor={`minute-${minute}`}>{`${minute.toString().padStart(2, '0')}m`}</Label>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Queries */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xl font-semibold">Queries</h3>
                <QueryTypeHelpButton />
              </div>
              {formData.queries.map((query, index) => (
                <div key={index} className="p-4 bg-gray-700 rounded-lg space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor={`queryName-${index}`}>Name</Label>
                      <Input id={`queryName-${index}`} placeholder="Name" value={query.name} onChange={e => handleQueryChange(index, 'name', e.target.value)} />
                    </div>
                    <div>
                      <Label htmlFor={`queryType-${index}`}>Type</Label>
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
                    <div className="md:col-span-2">
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
                        <p className="text-xs text-gray-400 mt-1">
                          Leave empty to extract all columns. Enter a column name to extract only that column.
                        </p>
                      )}
                      {query.type === 'pdf_text' && (
                        <p className="text-xs text-gray-400 mt-1">
                          Leave empty to extract all text. Enter a regex pattern to extract specific data.
                        </p>
                      )}
                      {query.type === 'pdf_metadata' && (
                        <p className="text-xs text-gray-400 mt-1">
                          Extracts PDF metadata (title, author, page count, etc.)
                        </p>
                      )}
                    </div>
                    <div className="flex items-center space-x-2">
                      <Switch id={`join-${index}`} checked={!!query.join} onCheckedChange={() => handleQueryChange(index, 'join', query.join ? '' : 'join')} />
                      <Label htmlFor={`join-${index}`}>Join</Label>
                    </div>
                  </div>
                  {formData.queries.length > 1 && (
                    <Button
                      variant="destructive"
                      size="icon"
                      onClick={() => {
                        const updatedQueries = formData.queries.filter((_, i) => i !== index);
                        setFormData({ ...formData, queries: updatedQueries });
                      }}
                      className="mt-2"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              ))}
              {formData.queries.length < 10 && (
                <Button onClick={handleAddQuery} className="w-full">
                  <Plus className="h-4 w-4 mr-2" />
                  Add Query
                </Button>
              )}
            </div>

            {/* Proxy Configuration */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xl font-semibold">Proxy Configuration</h3>
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

              {formData.proxy_config?.enabled && (
                <div className="p-4 bg-gray-700 rounded-lg space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="geoTargeting">Geo-Targeting</Label>
                      <Select
                        value={formData.proxy_config?.geo_targeting || 'any'}
                        onValueChange={(value) =>
                          setFormData({
                            ...formData,
                            proxy_config: {
                              ...formData.proxy_config!,
                              geo_targeting: value as 'us' | 'eu' | 'as' | 'any'
                            }
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
                      <p className="text-xs text-gray-400 mt-1">
                        Target specific geographic regions for your proxies
                      </p>
                    </div>

                    <div>
                      <Label htmlFor="rotationStrategy">Rotation Strategy</Label>
                      <Select
                        value={formData.proxy_config?.rotation_strategy || 'random'}
                        onValueChange={(value) =>
                          setFormData({
                            ...formData,
                            proxy_config: {
                              ...formData.proxy_config!,
                              rotation_strategy: value as 'random' | 'round-robin'
                            }
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
                      <p className="text-xs text-gray-400 mt-1">
                        How proxies are selected for each request
                      </p>
                    </div>

                    <div>
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
                            proxy_config: {
                              ...formData.proxy_config!,
                              max_retries: parseInt(e.target.value)
                            }
                          })
                        }
                      />
                      <p className="text-xs text-gray-400 mt-1">
                        Number of retry attempts on proxy failure
                      </p>
                    </div>

                    <div className="flex items-center space-x-2">
                      <Switch
                        id="fallbackToDirect"
                        checked={formData.proxy_config?.fallback_to_direct !== false}
                        onCheckedChange={(checked) =>
                          setFormData({
                            ...formData,
                            proxy_config: {
                              ...formData.proxy_config!,
                              fallback_to_direct: checked
                            }
                          })
                        }
                      />
                      <Label htmlFor="fallbackToDirect" className="text-sm">
                        Fallback to direct connection if no proxy available
                      </Label>
                    </div>
                  </div>

                  <div className="bg-blue-900 bg-opacity-20 border border-blue-500 rounded p-3 text-sm">
                    <p className="text-blue-300 font-medium mb-1">Proxy Pool Information</p>
                    <p className="text-gray-300">
                      Using AWS-based proxy pool with servers in multiple regions.
                      Proxies are automatically health-checked every 5 minutes.
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* JavaScript Rendering Configuration */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xl font-semibold">JavaScript Rendering</h3>
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

              {formData.render_config?.enabled && (
                <div className="p-4 bg-gray-700 rounded-lg space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="waitStrategy">Wait Strategy</Label>
                      <Select
                        value={formData.render_config?.wait_strategy || 'networkidle'}
                        onValueChange={(value) =>
                          setFormData({
                            ...formData,
                            render_config: {
                              ...formData.render_config!,
                              wait_strategy: value as 'load' | 'domcontentloaded' | 'networkidle'
                            }
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
                      <p className="text-xs text-gray-400 mt-1">
                        When to consider the page loaded
                      </p>
                    </div>

                    <div>
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
                            render_config: {
                              ...formData.render_config!,
                              wait_timeout_ms: parseInt(e.target.value)
                            }
                          })
                        }
                      />
                      <p className="text-xs text-gray-400 mt-1">
                        Maximum time to wait for page load (5-120 seconds)
                      </p>
                    </div>

                    <div className="md:col-span-2">
                      <Label htmlFor="waitForSelector">Wait for Selector (optional)</Label>
                      <Input
                        id="waitForSelector"
                        type="text"
                        placeholder="e.g., .product-list, #content"
                        value={formData.render_config?.wait_for_selector || ''}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            render_config: {
                              ...formData.render_config!,
                              wait_for_selector: e.target.value || null
                            }
                          })
                        }
                      />
                      <p className="text-xs text-gray-400 mt-1">
                        CSS selector to wait for before considering page ready
                      </p>
                    </div>

                    <div className="flex items-center space-x-2">
                      <Switch
                        id="captureScreenshot"
                        checked={formData.render_config?.capture_screenshot || false}
                        onCheckedChange={(checked) =>
                          setFormData({
                            ...formData,
                            render_config: {
                              ...formData.render_config!,
                              capture_screenshot: checked
                            }
                          })
                        }
                      />
                      <Label htmlFor="captureScreenshot" className="text-sm">
                        Capture screenshot of rendered page
                      </Label>
                    </div>

                    {formData.render_config?.capture_screenshot && (
                      <div className="flex items-center space-x-2">
                        <Switch
                          id="screenshotFullPage"
                          checked={formData.render_config?.screenshot_full_page || false}
                          onCheckedChange={(checked) =>
                            setFormData({
                              ...formData,
                              render_config: {
                                ...formData.render_config!,
                                screenshot_full_page: checked
                              }
                            })
                          }
                        />
                        <Label htmlFor="screenshotFullPage" className="text-sm">
                          Full page screenshot (may increase size)
                        </Label>
                      </div>
                    )}

                    <div className="flex items-center space-x-2">
                      <Switch
                        id="fallbackToStandard"
                        checked={formData.render_config?.fallback_to_standard !== false}
                        onCheckedChange={(checked) =>
                          setFormData({
                            ...formData,
                            render_config: {
                              ...formData.render_config!,
                              fallback_to_standard: checked
                            }
                          })
                        }
                      />
                      <Label htmlFor="fallbackToStandard" className="text-sm">
                        Fallback to standard requests if rendering fails
                      </Label>
                    </div>
                  </div>

                  <div className="bg-blue-900 bg-opacity-20 border border-blue-500 rounded p-3 text-sm">
                    <p className="text-blue-300 font-medium mb-1">JavaScript Rendering Information</p>
                    <p className="text-gray-300">
                      Uses Playwright headless browser to render JavaScript-heavy websites (SPAs).
                      Ideal for React, Vue, Angular applications. Note: Increases processing time and cost.
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Export Settings */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xl font-semibold">Export Settings</h3>
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

              {formData.export_config?.enabled && (
                <div className="p-4 bg-gray-700 rounded-lg space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="exportFormats">Export Formats</Label>
                      <div className="space-y-2 mt-2">
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
                                  export_config: {
                                    ...formData.export_config!,
                                    formats: newFormats.length > 0 ? newFormats : ['json']
                                  }
                                });
                              }}
                            />
                            <Label htmlFor={`format-${format}`} className="text-sm uppercase">
                              {format}
                            </Label>
                          </div>
                        ))}
                      </div>
                      <p className="text-xs text-gray-400 mt-2">
                        Select one or more export formats
                      </p>
                    </div>

                    <div>
                      <Label htmlFor="exportDestination">Destination</Label>
                      <Select
                        value={formData.export_config?.destination || 's3'}
                        onValueChange={(value) =>
                          setFormData({
                            ...formData,
                            export_config: {
                              ...formData.export_config!,
                              destination: value as 's3' | 'local' | 'webhook'
                            }
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
                      <p className="text-xs text-gray-400 mt-1">
                        Where to store exported data
                      </p>
                    </div>

                    {formData.export_config?.destination === 's3' && (
                      <div className="md:col-span-2">
                        <Label htmlFor="s3Bucket">S3 Bucket Name</Label>
                        <Input
                          id="s3Bucket"
                          type="text"
                          placeholder="my-bucket-name"
                          value={formData.export_config?.s3_bucket || ''}
                          onChange={(e) =>
                            setFormData({
                              ...formData,
                              export_config: {
                                ...formData.export_config!,
                                s3_bucket: e.target.value || null
                              }
                            })
                          }
                        />
                        <p className="text-xs text-gray-400 mt-1">
                          S3 bucket for storing results
                        </p>
                      </div>
                    )}

                    {formData.export_config?.destination === 'webhook' && (
                      <div className="md:col-span-2">
                        <Label htmlFor="webhookUrl">Webhook URL</Label>
                        <Input
                          id="webhookUrl"
                          type="url"
                          placeholder="https://example.com/webhook"
                          value={formData.export_config?.webhook_url || ''}
                          onChange={(e) =>
                            setFormData({
                              ...formData,
                              export_config: {
                                ...formData.export_config!,
                                webhook_url: e.target.value || null
                              }
                            })
                          }
                        />
                        <p className="text-xs text-gray-400 mt-1">
                          POST results to this URL
                        </p>
                      </div>
                    )}

                    <div className="flex items-center space-x-2">
                      <Switch
                        id="includeScreenshots"
                        checked={formData.export_config?.include_screenshots || false}
                        onCheckedChange={(checked) =>
                          setFormData({
                            ...formData,
                            export_config: {
                              ...formData.export_config!,
                              include_screenshots: checked
                            }
                          })
                        }
                      />
                      <Label htmlFor="includeScreenshots" className="text-sm">
                        Include screenshots in export (if captured)
                      </Label>
                    </div>

                    <div className="flex items-center space-x-2">
                      <Switch
                        id="compressExport"
                        checked={formData.export_config?.compress || false}
                        onCheckedChange={(checked) =>
                          setFormData({
                            ...formData,
                            export_config: {
                              ...formData.export_config!,
                              compress: checked
                            }
                          })
                        }
                      />
                      <Label htmlFor="compressExport" className="text-sm">
                        Compress exported files (ZIP)
                      </Label>
                    </div>
                  </div>

                  <div className="bg-blue-900 bg-opacity-20 border border-blue-500 rounded p-3 text-sm">
                    <p className="text-blue-300 font-medium mb-1">Export Information</p>
                    <p className="text-gray-300">
                      Configure how and where your scraped data is exported.
                      Results are automatically exported after each job run.
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Notification Settings */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xl font-semibold">Notification Settings</h3>
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

              {formData.notification_config?.enabled && (
                <div className="p-4 bg-gray-700 rounded-lg space-y-4">
                  <div className="space-y-3">
                    <h4 className="text-sm font-semibold text-gray-200">Email Notifications</h4>

                    <div className="flex items-center space-x-2">
                      <Switch
                        id="emailOnSuccess"
                        checked={formData.notification_config?.email_on_success || false}
                        onCheckedChange={(checked) =>
                          setFormData({
                            ...formData,
                            notification_config: {
                              ...formData.notification_config!,
                              email_on_success: checked
                            }
                          })
                        }
                      />
                      <Label htmlFor="emailOnSuccess" className="text-sm">
                        Send email on successful job completion
                      </Label>
                    </div>

                    <div className="flex items-center space-x-2">
                      <Switch
                        id="emailOnFailure"
                        checked={formData.notification_config?.email_on_failure !== false}
                        onCheckedChange={(checked) =>
                          setFormData({
                            ...formData,
                            notification_config: {
                              ...formData.notification_config!,
                              email_on_failure: checked
                            }
                          })
                        }
                      />
                      <Label htmlFor="emailOnFailure" className="text-sm">
                        Send email on job failure
                      </Label>
                    </div>

                    <div>
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
                              email_addresses: e.target.value
                                .split(',')
                                .map(email => email.trim())
                                .filter(email => email.length > 0)
                            }
                          })
                        }
                      />
                      <p className="text-xs text-gray-400 mt-1">
                        Comma-separated email addresses for notifications
                      </p>
                    </div>
                  </div>

                  <div className="space-y-3 pt-3 border-t border-gray-600">
                    <h4 className="text-sm font-semibold text-gray-200">Webhook Notifications</h4>

                    <div className="flex items-center space-x-2">
                      <Switch
                        id="webhookOnSuccess"
                        checked={formData.notification_config?.webhook_on_success || false}
                        onCheckedChange={(checked) =>
                          setFormData({
                            ...formData,
                            notification_config: {
                              ...formData.notification_config!,
                              webhook_on_success: checked
                            }
                          })
                        }
                      />
                      <Label htmlFor="webhookOnSuccess" className="text-sm">
                        Trigger webhook on successful job completion
                      </Label>
                    </div>

                    <div className="flex items-center space-x-2">
                      <Switch
                        id="webhookOnFailure"
                        checked={formData.notification_config?.webhook_on_failure !== false}
                        onCheckedChange={(checked) =>
                          setFormData({
                            ...formData,
                            notification_config: {
                              ...formData.notification_config!,
                              webhook_on_failure: checked
                            }
                          })
                        }
                      />
                      <Label htmlFor="webhookOnFailure" className="text-sm">
                        Trigger webhook on job failure
                      </Label>
                    </div>

                    <div>
                      <Label htmlFor="notificationWebhookUrl">Webhook URL</Label>
                      <Input
                        id="notificationWebhookUrl"
                        type="url"
                        placeholder="https://example.com/notify"
                        value={formData.notification_config?.webhook_url || ''}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            notification_config: {
                              ...formData.notification_config!,
                              webhook_url: e.target.value || null
                            }
                          })
                        }
                      />
                      <p className="text-xs text-gray-400 mt-1">
                        POST job status updates to this URL
                      </p>
                    </div>
                  </div>

                  <div className="bg-blue-900 bg-opacity-20 border border-blue-500 rounded p-3 text-sm">
                    <p className="text-blue-300 font-medium mb-1">Notification Information</p>
                    <p className="text-gray-300">
                      Receive real-time updates about your jobs via email or webhook.
                      Email notifications use your Clerk account email by default.
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Form Actions */}
            <div className="flex justify-between items-center">
              <div>
                {!jobDetails && (
                  <Button
                    onClick={handleSaveAsTemplate}
                    variant="outline"
                    className="flex items-center gap-2"
                  >
                    <Save className="h-4 w-4" />
                    Save as Template
                  </Button>
                )}
              </div>
              <div className="flex space-x-4">
                <Button onClick={closeModal} variant="outline">Cancel</Button>
                <Button onClick={handleSubmit}>Submit</Button>
              </div>
            </div>
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
    </>
  );
}