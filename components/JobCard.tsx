import { JobCardProps } from "@/lib/types";
import { Trash2, PauseCircle, Eye } from "lucide-react";

export function JobCard({ job, onClick, onPause, onDelete }: JobCardProps) {
	return (
    <div className="p-6 bg-gray-800 rounded-lg flex items-center justify-between">
      {/* Job Information */}
      <div>
        <h2 className="text-2xl">{job.name}</h2>
        <p>Status: {job.status}</p>
        <p>Crawl Count: {job.crawl_count}</p>
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