import { JobCardProps } from "@/lib/types";
import { Trash2, PauseCircle, Eye, Download, FileSearch } from "lucide-react";
import { capitalize, getNextRunTime } from "@/lib/utils";

export function JobCard({ job, onClick, onPause, onDelete, onDownload, onPreview }: JobCardProps) {
  const statusTitleCase = capitalize(job.status);  // Transform status to title case
  const nextRunTime = getNextRunTime(job.scheduling, job.status);  // Calculate next run time
  const hasResults = job.results_s3_key || job.last_run;  // Show download if results exist

	return (
    <div className="p-6 bg-gray-800 rounded-lg flex items-center justify-between">
      {/* Job Information */}
      <div>
        <h2 className="text-2xl">{job.name}</h2>
        <p>Status: {statusTitleCase}</p>
        <p>Link Count: {job.link_count}</p>
        <p>Next Run: {nextRunTime}</p>
      </div>

      {/* Actions */}
      <div className="flex space-x-2">
        {/* View Details Icon */}
        <button
          onClick={onClick}
          className="p-2 bg-blue-600 rounded-lg hover:bg-blue-700"
          aria-label="View Details"
        >
          <Eye className="h-5 w-5" />
        </button>

        {/* Preview Results Icon - only show if results exist */}
        {hasResults && onPreview && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onPreview();
            }}
            className="p-2 bg-purple-600 rounded-lg hover:bg-purple-700"
            aria-label="Preview Results"
          >
            <FileSearch className="h-5 w-5" />
          </button>
        )}

        {/* Download Results Icon - only show if results exist */}
        {hasResults && onDownload && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDownload();
            }}
            className="p-2 bg-green-600 rounded-lg hover:bg-green-700"
            aria-label="Download Results"
          >
            <Download className="h-5 w-5" />
          </button>
        )}

        {/* Pause Icon */}
        <button
          onClick={(e) => {
            e.stopPropagation(); // Prevent the card's onClick from triggering
            onPause();
          }}
          className="p-2 bg-yellow-600 rounded-lg hover:bg-yellow-700"
          aria-label="Pause"
        >
          <PauseCircle className="h-5 w-5" />
        </button>

        {/* Delete Icon */}
        <button
          onClick={(e) => {
            e.stopPropagation(); // Prevent the card's onClick from triggering
            onDelete();
          }}
          className="p-2 bg-red-600 rounded-lg hover:bg-red-700"
          aria-label="Delete"
        >
          <Trash2 className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
}