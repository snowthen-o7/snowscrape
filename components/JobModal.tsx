'use client';

import { useEffect, useState } from 'react';

import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"

import { X, Loader2, Plus, Trash2 } from 'lucide-react'
import { SessionResource } from '@clerk/types';
import { FormData, FileMapping, Job, Query, Scheduling } from '@/lib/types';
import { validateQueries, validateHTTP, validateSFTP } from '@/lib/utils';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

export function JobModal({ closeModal, jobDetails, session }: {
  closeModal: () => void,
  jobDetails?: Job | null,
  session: SessionResource | null,
 }) {
  const [formData, setFormData] = useState<FormData>({
    name: '',
    rate_limit: 1,
    source: '',
    file_mapping: { delimiter: ',', enclosure: '', escape: '', url_column: '' } as FileMapping,
    scheduling: { days: [], hours: [] } as Scheduling, // Array for selected days and hours
    queries: [{ name: '', type: 'xpath', query: '', join: false }] as Query[] // Explicitly type the queries as an array of Query
  });

  const [sourceError, setSourceError] = useState<string | null>(null);
  const [queryErrors, setQueryErrors] = useState<(string | null)[]>([]); // Track errors for each query
  const [sourceLoading, setSourceLoading] = useState<boolean>(false);
  const [headers, setHeaders] = useState<string[]>([]); // Track headers from the source file
  const maxQueries = 10;

  // Helper function to set error and show toast
  const setErrorAndToast = (setError: React.Dispatch<React.SetStateAction<string | null>>, errorMessage: string) => {
    setError(errorMessage);
    toast.error(errorMessage, { position: 'top-right' });
  };

  useEffect(() => {
    console.log("JobDetails", jobDetails);
    // If jobDetails are passed in, populate formData with jobDetails values
    if (jobDetails) {
      setFormData({
        name: jobDetails.name,
        rate_limit: jobDetails.rate_limit,
        source: jobDetails.source,
        file_mapping: jobDetails.file_mapping,
        scheduling: jobDetails.scheduling,
        queries: jobDetails.queries.map(query => ({
          ...query,
          join: !!query.join, // Convert join to a boolean value
        }))
      });

      // Set headers if available
      if (jobDetails.file_mapping?.url_column && jobDetails.file_mapping.url_column !== 'default') {
        setHeaders([jobDetails.file_mapping.url_column]);
      }
    }
  }, [jobDetails]);

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
      if (value === 'xpath' || value === 'regex' || value === 'jsonpath') {
        updatedQueries[index][field] = value; // 'value' already has the correct type
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
    if (!formData.file_mapping.url_column) {
      setErrorAndToast(setSourceError, "Please select a URL column.");
      return; // Stop submission if no column is selected
    }

    const queryValidationErrors = await validateQueries(formData.queries); // Get query-specific errors
    setQueryErrors(queryValidationErrors); // Update queryErrors state with the result

    const queriesAreValid = queryValidationErrors.every(error => error === null); // Check if all queries are valid
    
    if (!queriesAreValid || sourceError) {
      return; // Don't submit if there are errors
    }

    try {
      const token = session?.getToken(); // Use optional chaining to ensure session is not null
      if (!token) {
        throw new Error("Session is null or token is unavailable");
      }
      const url = jobDetails ? `${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/${jobDetails.job_id}` : `${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs`;
      const method = jobDetails ? "PUT" : "POST";

      const response = await fetch(url, {
        method,
        headers: {
          "Authorization": `Bearer ${token}`,
          ...(process.env.NEXT_PUBLIC_API_KEY && { "x-api-key": process.env.NEXT_PUBLIC_API_KEY }),
        },
        body: JSON.stringify(formData),
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
  
      return { ...prevState, scheduling: updatedScheduling };
    });
  };

  // Schedule options
  const daysOfWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  const hours = Array.from({ length: 24 }, (_, i) => i); // 0 - 23 hours

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4">
      <div className="bg-gray-800 text-white rounded-lg shadow-lg max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 space-y-6">
          <div className="flex justify-between items-center">
            <ToastContainer />
            <h2 className="text-2xl font-bold">{jobDetails ? `Edit Job - ${jobDetails.name}` : "Submit a New Job"}</h2>
            <Button variant="ghost" size="icon" onClick={closeModal}><X className="h-6 w-6" /></Button>
          </div>

          {/* General Job Info */}
          <div className="space-y-4">
            <h3 className="text-xl font-semibold">General Job Info</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="name">Name</Label>
                <Input id="name" placeholder="Job Name" value={formData.name} onChange={e => handleInputChange('name', e.target.value)} />
              </div>
              <div>
                <Label htmlFor="rateLimit">Rate Limit</Label>
                <Input id="rateLimit" type="number" min={1} max={8} placeholder="1-8" value={formData.rate_limit} onChange={e => handleInputChange('rate_limit', parseInt(e.target.value))}/>
              </div>
              <div>
                <Label htmlFor="sourceUrl">Source URL</Label>
                <Input id="sourceUrl" placeholder="https://example.com" value={formData.source} onChange={e => handleInputChange('source', e.target.value)} onBlur={validateSource} />
                {sourceLoading && (
                  <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                    <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
                  </div>
                )}
              </div>
              {sourceLoading && (
                <div className="md:col-span-2 text-sm text-blue-400">
                  Validating source URL... Please wait.
                </div>
              )}
            </div>
          </div>

          {/* File Mapping */}
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
                <Select value={formData.file_mapping.url_column} onValueChange={value => handleFileMappingChange('url_column', value)}>
                  <SelectTrigger id="urlColumn">
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
              </div>
            </div>
          </div>

          {/* Scheduling */}
          <div className="space-y-4">
            <h3 className="text-xl font-semibold">Scheduling</h3>
            <div className="space-y-2"></div>
              <Label>Days of Week</Label>
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

          {/* Queries */}
            <div className="space-y-4">
              <h3 className="text-xl font-semibold">Queries</h3>
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
                          <SelectItem value="xpath">XPath</SelectItem>
                          <SelectItem value="regex">Regex</SelectItem>
                          <SelectItem value="jsonpath">JSONPath</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="md:col-span-2">
                      <Label htmlFor={`queryExpression-${index}`}>Expression</Label>
                      <Input id={`queryExpression-${index}`} placeholder="Expression (e.g. //html)" value={query.query} onChange={e => handleQueryChange(index, 'query', e.target.value)} />
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

            {/* Form Actions */}
            <div className="flex justify-end space-x-4">
              <Button onClick={closeModal} variant="outline">Cancel</Button>
              <Button onClick={handleSubmit}>Submit</Button>
            </div>
          </div>
        </div>
      </div>
  );
}