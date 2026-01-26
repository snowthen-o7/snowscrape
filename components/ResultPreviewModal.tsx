'use client';

import { useState, useEffect } from 'react';
import { X, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'react-toastify';

interface ResultPreviewModalProps {
  closeModal: () => void;
  jobId: string;
  jobName: string;
  token: string | null;
}

interface PaginationInfo {
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

interface PreviewData {
  results: Record<string, any>[];
  pagination: PaginationInfo;
  columns: string[];
}

export function ResultPreviewModal({ closeModal, jobId, jobName, token }: ResultPreviewModalProps) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<PreviewData | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(50);

  // Fetch preview data
  const fetchPreview = async (page: number) => {
    if (!token) {
      toast.error("Authentication token not available");
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/${jobId}/preview?page=${page}&page_size=${pageSize}`,
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
        throw new Error(error.message || "Failed to fetch results preview");
      }

      const previewData: PreviewData = await response.json();
      setData(previewData);
    } catch (error) {
      console.error("Error fetching preview", error);
      toast.error(error instanceof Error ? error.message : "Failed to load results preview");
    } finally {
      setLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    fetchPreview(currentPage);
  }, [currentPage]);

  // Handle page navigation
  const handlePreviousPage = () => {
    if (data?.pagination.has_previous) {
      setCurrentPage(prev => prev - 1);
    }
  };

  const handleNextPage = () => {
    if (data?.pagination.has_next) {
      setCurrentPage(prev => prev + 1);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-gray-800 text-white rounded-lg shadow-lg max-w-6xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-700 flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold">Results Preview</h2>
            <p className="text-gray-400 text-sm mt-1">{jobName}</p>
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
              <span className="ml-3 text-gray-400">Loading results...</span>
            </div>
          ) : data && data.results.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="px-4 py-3 text-left text-sm font-semibold text-gray-300 bg-gray-750">
                      #
                    </th>
                    {data.columns.map((column, idx) => (
                      <th
                        key={idx}
                        className="px-4 py-3 text-left text-sm font-semibold text-gray-300 bg-gray-750"
                      >
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((row, rowIdx) => (
                    <tr
                      key={rowIdx}
                      className="border-b border-gray-700 hover:bg-gray-750 transition-colors"
                    >
                      <td className="px-4 py-3 text-sm text-gray-400">
                        {(currentPage - 1) * pageSize + rowIdx + 1}
                      </td>
                      {data.columns.map((column, colIdx) => (
                        <td
                          key={colIdx}
                          className="px-4 py-3 text-sm text-gray-200 max-w-xs truncate"
                          title={String(row[column] || '')}
                        >
                          {row[column] !== null && row[column] !== undefined
                            ? String(row[column])
                            : '-'}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12 text-gray-400">
              <p>No results available for this job.</p>
            </div>
          )}
        </div>

        {/* Footer with Pagination */}
        {data && data.results.length > 0 && (
          <div className="p-6 border-t border-gray-700 flex justify-between items-center">
            <div className="text-sm text-gray-400">
              Showing {(currentPage - 1) * pageSize + 1} -{' '}
              {Math.min(currentPage * pageSize, data.pagination.total_count)} of{' '}
              {data.pagination.total_count} results
            </div>

            <div className="flex items-center gap-2">
              <Button
                onClick={handlePreviousPage}
                disabled={!data.pagination.has_previous || loading}
                variant="outline"
                size="sm"
                className="flex items-center gap-1"
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </Button>

              <span className="px-4 py-2 text-sm text-gray-300">
                Page {currentPage} of {data.pagination.total_pages}
              </span>

              <Button
                onClick={handleNextPage}
                disabled={!data.pagination.has_next || loading}
                variant="outline"
                size="sm"
                className="flex items-center gap-1"
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
