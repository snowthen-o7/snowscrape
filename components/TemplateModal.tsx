'use client';

import { useState, useEffect } from 'react';
import { X, Loader2, Trash2, Calendar, Clock } from 'lucide-react';
import { Button } from '@snowforge/ui';
import { Template } from "@/lib/types";
import { toast } from 'react-toastify';

interface TemplateModalProps {
  closeModal: () => void;
  onSelectTemplate: (template: Template) => void;
  token: string | null;
}

export function TemplateModal({ closeModal, onSelectTemplate, token }: TemplateModalProps) {
  const [loading, setLoading] = useState(true);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Fetch templates
  const fetchTemplates = async () => {
    if (!token) {
      toast.error("Authentication token not available");
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/templates`,
        {
          method: "GET",
          headers: {
            "Authorization": `Bearer ${token}`,
            ...(process.env.NEXT_PUBLIC_API_KEY && { "x-api-key": process.env.NEXT_PUBLIC_API_KEY }),
          },
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "Failed to fetch templates");
      }

      const data: Template[] = await response.json();
      setTemplates(data);
    } catch (error) {
      console.error("Error fetching templates", error);
      toast.error(error instanceof Error ? error.message : "Failed to load templates");
    } finally {
      setLoading(false);
    }
  };

  // Delete template
  const handleDelete = async (templateId: string) => {
    if (!token) return;

    if (!confirm("Are you sure you want to delete this template?")) {
      return;
    }

    setDeletingId(templateId);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/templates/${templateId}`,
        {
          method: "DELETE",
          headers: {
            "Authorization": `Bearer ${token}`,
            ...(process.env.NEXT_PUBLIC_API_KEY && { "x-api-key": process.env.NEXT_PUBLIC_API_KEY }),
          },
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "Failed to delete template");
      }

      toast.success("Template deleted successfully");
      // Remove from local state
      setTemplates(templates.filter(t => t.template_id !== templateId));
    } catch (error) {
      console.error("Error deleting template", error);
      toast.error(error instanceof Error ? error.message : "Failed to delete template");
    } finally {
      setDeletingId(null);
    }
  };

  // Format date
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  // Initial load
  useEffect(() => {
    fetchTemplates();
  }, []);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-gray-800 text-white rounded-lg shadow-lg max-w-4xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-700 flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold">Job Templates</h2>
            <p className="text-gray-400 text-sm mt-1">
              Select a template to load its configuration
            </p>
          </div>
          <Button variant="ghost" size="icon" onClick={closeModal}>
            <X className="h-6 w-6" />
          </Button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
              <span className="ml-3 text-gray-400">Loading templates...</span>
            </div>
          ) : templates.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <p className="text-lg">No templates yet.</p>
              <p className="text-sm mt-2">
                Create a job and save it as a template for quick reuse.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {templates.map((template) => (
                <div
                  key={template.template_id}
                  className="p-4 bg-gray-750 rounded-lg border border-gray-700 hover:border-gray-600 transition-colors"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1 cursor-pointer" onClick={() => onSelectTemplate(template)}>
                      <h3 className="text-lg font-semibold text-white mb-1">
                        {template.name}
                      </h3>
                      {template.description && (
                        <p className="text-sm text-gray-400 mb-3">
                          {template.description}
                        </p>
                      )}
                      <div className="flex items-center gap-4 text-xs text-gray-500">
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          Created {formatDate(template.created_at)}
                        </span>
                        {template.last_used && (
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            Last used {formatDate(template.last_used)}
                          </span>
                        )}
                      </div>
                      <div className="mt-3 flex gap-2 text-xs">
                        <span className="px-2 py-1 bg-blue-900 text-blue-200 rounded">
                          {template.config.queries.length} {template.config.queries.length === 1 ? 'query' : 'queries'}
                        </span>
                        <span className="px-2 py-1 bg-green-900 text-green-200 rounded">
                          {template.config.scheduling.days.length} {template.config.scheduling.days.length === 1 ? 'day' : 'days'}
                        </span>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(template.template_id);
                      }}
                      disabled={deletingId === template.template_id}
                      className="text-red-400 hover:text-red-300 hover:bg-red-900/20"
                    >
                      {deletingId === template.template_id ? (
                        <Loader2 className="h-5 w-5 animate-spin" />
                      ) : (
                        <Trash2 className="h-5 w-5" />
                      )}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
