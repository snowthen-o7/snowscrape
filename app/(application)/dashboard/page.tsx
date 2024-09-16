'use client';

import { useState, useEffect } from 'react';
import { JobDetailsModal } from "@/lib/components/JobDetailsModal";
import { NewJobModal } from "@/lib/components/NewJobModal";
import { JobCard } from "@/lib/components/JobCard";
import { Job } from "@/lib/types";

export default function Dashboard() {
	const [jobs, setJobs] = useState<Job[]>([]);
	const [loading, setLoading] = useState(true);
	const [newJobModalOpen, setNewJobModalOpen] = useState(false);
	const [jobDetailsModalOpen, setJobDetailsModalOpen] = useState<string | null>(null); // Track job we're showing details for
	const [sortOrder, setSortOrder] = useState("asc"); // For sorting

	// Fetch jobs from the backend
	useEffect(() => {
		const fetchJobs = async () => {
			try {
				const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/status`, {
					method: "GET",
					headers: {
						...(process.env.NEXT_PUBLIC_API_KEY && { "x-api-key": process.env.NEXT_PUBLIC_API_KEY }),
					},
				});
				
				const data: Job[] = await response.json();
				setJobs(data);
			} catch (error) {
				console.error("Error fetching jobs", error);
			} finally {
				setLoading(false);
			}
		};

		fetchJobs();
	}, []);

	// Sort jobs
	const sortJobs = (key: keyof Job) => {
		const sortedJobs = [...jobs].sort((a, b) => {
			if (sortOrder === "asc") {
				return a[key] > b[key] ? 1 : -1;
			} else {
				return a[key] < b[key] ? 1 : -1;
			}
		});
		setJobs(sortedJobs);
		setSortOrder(sortOrder === "asc" ? "desc" : "asc");
	};

	// Handle pausing a job
	const handlePauseJob = (jobId: string) => {
		console.log(`Pausing job: ${jobId}`);
		// Add API call to pause the job if necessary
	};

	// Handle deleting a job
	const handleDeleteJob = (jobId: string) => {
		console.log(`Deleting job: ${jobId}`);
		// Add API call to delete the job if necessary
		setJobs(jobs.filter(job => job.id !== jobId)); // Update the state to remove the deleted job
	};

	return (
		<div className="p-8 text-white">
			<h1 className="text-4xl mb-6">Dashboard</h1>

			{/* Button to open new job modal */}
			<button onClick={() => setNewJobModalOpen(true)} className="bg-blue-600 px-4 py-2 rounded">
				Submit New Job
			</button>

			{/* Sorting options */}
			<div className="mt-4 mb-6">
				<button onClick={() => sortJobs("name")} className="px-4 py-2 mr-2 bg-gray-800 rounded">
					Sort by Name
				</button>
				<button onClick={() => sortJobs("status")} className="px-4 py-2 bg-gray-800 rounded">
					Sort by Status
				</button>
			</div>

			{/* Show loading spinner if jobs are loading */}
			{loading ? (
				<p>Loading jobs...</p>
			) : (
				<div className="grid grid-cols-1 md:grid-cols-2 gap-6">
					{jobs.map(job => (
						<JobCard
							key={job.id}
							job={job}
							onClick={() => setJobDetailsModalOpen(job.id)} // Open job details modal
							onPause={() => handlePauseJob(job.id)} // Pause job
							onDelete={() => handleDeleteJob(job.id)} // Delete job
					/>
					))}
				</div>
			)}

			{/* New Job Modal */}
			{newJobModalOpen && <NewJobModal closeModal={() => setNewJobModalOpen(false)} />}

			{/* Job Details Modal */}
			{jobDetailsModalOpen && (
				<JobDetailsModal
					jobId={jobDetailsModalOpen}
					closeModal={() => setJobDetailsModalOpen(null)}
				/>
			)}
		</div>
	);
}
