import { JobCardProps } from "@/lib/types";

export function JobCard({ job, onClick, onPause, onDelete }: JobCardProps) {
	return (
		<div onClick={onClick} className="p-6 bg-gray-800 rounded-lg cursor-pointer">
			<h2 className="text-2xl">{job.name}</h2>
			<p>Status: {job.status}</p>
			<p>Crawl Count: {job.crawl_count}</p>
			<div className="flex mt-4">
				<button onClick={onPause} className="mr-2 bg-yellow-600 px-4 py-2 rounded-lg">
					Pause
				</button>
				<button onClick={onDelete} className="bg-red-600 px-4 py-2 rounded-lg">
					Delete
				</button>
			</div>
		</div>
	);
}
