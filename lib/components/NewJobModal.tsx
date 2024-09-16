'use client';

import { useState } from 'react';
import { FormData, FileMapping, Query, Scheduling } from '@/lib/types';
import { detectCSVSettings, validateQueries } from '@/lib/utils';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

export function NewJobModal({ closeModal }: { closeModal: () => void }) {
  const [formData, setFormData] = useState<FormData>({
    name: '',
    rate_limit: 1,
    source: '',
    file_mapping: { delimiter: ',', enclosure: '', escape: '', url_column: '' },
    scheduling: { days: [], hours: [] }, // Array for selected days and hours
    queries: [{ name: '', type: 'xpath', query: '', join: '' }]
  });

  const [sourceError, setSourceError] = useState<string | null>(null);
  const [queryErrors, setQueryErrors] = useState<(string | null)[]>([]); // Track errors for each query
  const [headers, setHeaders] = useState<string[]>([]); // Track headers from the source file
  const maxQueries = 10;

  // Helper function to set error and show toast
  const setErrorAndToast = (setError: React.Dispatch<React.SetStateAction<string | null>>, errorMessage: string) => {
    setError(errorMessage);
    toast.error(errorMessage, { position: 'top-right' });
  };

  // Handle validation when clicking away from the source input
  const validateSource = async () => {
    try {
      const response = await fetch(formData.source);
      if (!response.ok) {
        setErrorAndToast(setSourceError, 'Invalid URL or cannot reach the source.');
        return;
      }
      const fileText = await response.text();
      const detected = detectCSVSettings(fileText); // Detect CSV settings and headers

      // Set detected settings directly into the formData state
      setFormData((prevState) => ({
        ...prevState,
        file_mapping: {
          delimiter: detected.delimiter || ',',
          enclosure: detected.enclosure || '',
          escape: detected.escape || '',
          url_column: prevState.file_mapping.url_column // Preserve URL column as default
        }
      }));

      setHeaders(detected.headers); // Update the dropdown options for URL Column
      setSourceError(null); // Clear error if valid

      // Success toast notification
      toast.success('File settings detected successfully!', { position: 'top-right' });
    } catch (error) {
      setErrorAndToast(setSourceError, 'Failed to fetch the source URL.');
    }
  };

  const handleInputChange = (field: keyof FormData, value: string | number) => {
    setFormData({ ...formData, [field]: value });
  };

  const handleFileMappingChange = (field: keyof FileMapping, value: string | number) => {
    setFormData({
      ...formData,
      file_mapping: { ...formData.file_mapping, [field]: value }
    });
  };

  const handleQueryChange = (index: number, field: keyof Query, value: string) => {
    const updatedQueries = [...formData.queries];
  
    if (field === 'type') {
      // Ensure that the value is one of the allowed types
      if (value === 'xpath' || value === 'regex' || value === 'jsonpath') {
        updatedQueries[index][field] = value;
      } else {
        console.error("Invalid type value");
        return; // Invalid type, so don't proceed
      }
    } else {
      updatedQueries[index][field] = value;
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
      queries: [...formData.queries, { name: '', type: 'xpath', query: '', join: '' }]
    });
    setQueryErrors([...queryErrors, null]); // Add a new error state for the added query
  };

  const handleSubmit = async () => {
    await validateSource();
    const queryValidationErrors = await validateQueries(formData.queries); // Get query-specific errors
    setQueryErrors(queryValidationErrors); // Update queryErrors state with the result

    const queriesAreValid = queryValidationErrors.every(error => error === null); // Check if all queries are valid
    
    if (!queriesAreValid || sourceError) {
      return; // Don't submit if there are errors
    }

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs`, {
        method: "POST",
        headers: {
          ...(process.env.NEXT_PUBLIC_API_KEY && { "x-api-key": process.env.NEXT_PUBLIC_API_KEY }),
        },
        body: JSON.stringify(formData),
      });
      if (!response.ok) {
        throw new Error("Failed to submit job");
      }
      closeModal(); // Close the modal on success
    } catch (error) {
      setErrorAndToast(setSourceError, "Error submitting job");
    }
  };

  // Helper for scheduling
  const handleSchedulingChange = (field: keyof Scheduling, value: string[] | number[]) => {
    // Ensure that we update the selected options without resetting the previous selection
    setFormData((prevState) => ({
      ...prevState,
      scheduling: {
        ...prevState.scheduling,
        [field]: value, // Update the days or hours field with the new selection
      }
    }));
  };

  // Schedule options
  const daysOfWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  const hoursOfDay = Array.from({ length: 24 }, (_, i) => i); // 0 - 23 hours

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center">
      <div className="bg-gray-800 p-6 rounded-lg w-3/4 max-w-6xl max-h-screen overflow-y-auto"> {/* Adjust modal width */}
        <ToastContainer />
        
        <h2 className="text-xl mb-4">Submit a New Job</h2>

        {/* Section for job basics */}
        <div className="grid grid-cols-2 gap-6">
          <div className="mb-4">
            <label className="block mb-1">
              Job Name <span className="text-gray-400">(required)</span>
              <span className="tooltip" title="Enter a unique name for the job."> ⓘ</span>
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={e => handleInputChange('name', e.target.value)}
              className="w-full p-2 bg-gray-700"
            />
          </div>

          <div className="mb-4">
            <label className="block mb-1">
              Rate Limit (1-8) <span className="tooltip" title="Set the maximum number of parallel crawls."> ⓘ</span>
            </label>
            <input
              type="number"
              value={formData.rate_limit}
              min={1}
              max={8}
              onChange={e => handleInputChange('rate_limit', parseInt(e.target.value))}
              className="w-full p-2 bg-gray-700"
            />
          </div>

          <div className="mb-4">
            <label className="block mb-1">
              Source URL <span className="text-gray-400">(required)</span>
              <span className="tooltip" title="The URL where the list of links is located."> ⓘ</span>
            </label>
            <input
              type="text"
              value={formData.source}
              onBlur={validateSource} // Fetch and validate the source URL on blur
              onChange={e => setFormData({ ...formData, source: e.target.value })}
              className="w-full p-2 bg-gray-700"
            />
            {sourceError && <p className="text-red-500 mt-1">{sourceError}</p>}
          </div>
        </div>

        {/* Section for file mapping (Advanced Settings toggle) */}
        <div className="mb-6">
          <h3 className="text-lg mb-2">File Mapping</h3>
          {(
            <div className="grid grid-cols-2 gap-6 mt-4">
              <div>
                <label className="block mb-1">
                  Delimiter <span className="tooltip" title="The character used to separate fields."> ⓘ</span>
                </label>
                <select
                  value={formData.file_mapping.delimiter}
                  onChange={e => handleFileMappingChange('delimiter', e.target.value)}
                  className="w-full p-2 bg-gray-700"
                >
                  <option value=",">,</option>
                  <option value=";">;</option>
                  <option value="|">|</option>
                  <option value="\t">Tab</option>
                </select>
              </div>

              <div>
                <label className="block mb-1">
                  Enclosure <span className="tooltip" title="The character that encloses fields."> ⓘ</span>
                </label>
                <select
                  value={formData.file_mapping.enclosure}
                  onChange={e => handleFileMappingChange('enclosure', e.target.value)}
                  className="w-full p-2 bg-gray-700"
                >
                  <option value='"'>"</option>
                  <option value="'">'</option>
                  <option value=''>(None)</option>
                </select>
              </div>

              <div>
                <label className="block mb-1">
                  Escape <span className="tooltip" title="The escape character."> ⓘ</span>
                </label>
                <select
                  value={formData.file_mapping.escape}
                  onChange={e => handleFileMappingChange('escape', e.target.value)}
                  className="w-full p-2 bg-gray-700"
                >
                  <option value="\\">\\</option>
                  <option value="/">/</option>
                  <option value='"'>"</option>
                  <option value="'">'</option>
                  <option value=''>(None)</option>
                </select>
              </div>

              <div>
                <label className="block mb-1">
                  URL Column <span className="tooltip" title="The column where the URLs are stored."> ⓘ</span>
                </label>
                <select
                  value={formData.file_mapping.url_column}
                  onChange={e => handleFileMappingChange('url_column', parseInt(e.target.value))}
                  className="w-full p-2 bg-gray-700"
                >
                  {headers.length > 0 ? (
                    headers.map((header, index) => (
                      <option key={index} value={index}>{header}</option>
                    ))
                  ) : (
                    <option value={0}>No headers detected</option>
                  )}
                </select>
              </div>
            </div>
          )}
        </div>

        {/* Section for scheduling */}
        <div className="mb-6">
          <h3 className="text-lg mb-2">Scheduling</h3>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block mb-1">
                Select Days <span className="tooltip" title="Choose the days you want the job to run."> ⓘ</span>
              </label>
              <select
                multiple
                value={formData.scheduling.days}
                onChange={e => handleSchedulingChange('days', Array.from(e.target.selectedOptions).map(o => o.value))}
                className="w-full p-2 bg-gray-700"
              >
                <option value="Every Day">Every Day</option>
                {daysOfWeek.map(day => (
                  <option key={day} value={day}>{day}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block mb-1">
                Select Hours <span className="tooltip" title="Choose the hours of the day the job should run."> ⓘ</span>
              </label>
              <select
                multiple
                value={formData.scheduling.hours}
                onChange={e => handleSchedulingChange('hours', Array.from(e.target.selectedOptions).map(o => parseInt(o.value)))}
                className="w-full p-2 bg-gray-700"
              >
                <option value="Every Hour">Every Hour</option>
                {hoursOfDay.map(hour => (
                  <option key={hour} value={hour}>{hour}:00</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Queries section */}
        <h3 className="text-lg mb-2">Queries</h3>
        {formData.queries.map((query, index) => (
          <div key={index} className="mb-4 flex items-center">
            <div className="flex-grow">
              <input
                type="text"
                placeholder="Query Name"
                value={query.name}
                onChange={e => handleQueryChange(index, 'name', e.target.value)}
                className="w-full mb-2 p-2 bg-gray-700"
              />
              <select
                value={query.type}
                onChange={e => handleQueryChange(index, 'type', e.target.value)}
                className="w-full mb-2 p-2 bg-gray-700"
              >
                <option value="xpath">XPath</option>
                <option value="regex">Regex</option>
                <option value="jsonpath">JSONPath</option>
              </select>
              <input
                type="text"
                placeholder="Query Expression"
                value={query.query}
                onChange={e => handleQueryChange(index, 'query', e.target.value)}
                className="w-full mb-2 p-2 bg-gray-700"
              />
              <input
                type="text"
                placeholder="Join (optional)"
                value={query.join}
                onChange={e => handleQueryChange(index, 'join', e.target.value)}
                className="w-full p-2 bg-gray-700"
              />
            </div>

            {/* Delete button */}
            <button
              onClick={() => {
                const updatedQueries = formData.queries.filter((_, i) => i !== index);
                setFormData({ ...formData, queries: updatedQueries });
              }}
              className="ml-4 bg-red-600 px-4 py-2 rounded-lg"
            >
              Delete
            </button>
          </div>
        ))}

        {/* Add Query button */}
        <button onClick={handleAddQuery} className="mb-6 bg-blue-600 px-4 py-2 rounded">
          Add Query
        </button>

        {/* Buttons container */}
        <div className="flex justify-between items-center">
          {/* Submit button */}
          <div className="flex space-x-4">
            <button onClick={handleSubmit} className="bg-blue-600 px-4 py-2 rounded-lg">
              Submit
            </button>
          </div>

          {/* Cancel button - right-aligned */}
          <div className="flex justify-end flex-grow">
            <button onClick={closeModal} className="bg-red-600 px-4 py-2 rounded-lg">
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
