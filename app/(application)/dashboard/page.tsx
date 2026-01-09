'use client';

import { useState, useEffect, useCallback } from 'react';
import { useUser, useSession } from '@clerk/nextjs';
import { JobModal } from "@/components/JobModal";
import { JobCard } from "@/components/JobCard";
import { JobCardSkeleton } from "@/components/JobCardSkeleton";
import { ResultPreviewModal } from "@/components/ResultPreviewModal";
import { Input } from "@/components/ui/input";
import { Job } from "@/lib/types";
import { Search, RefreshCw } from "lucide-react";
import { toast } from 'react-toastify';

export default function Dashboard() {
	const { isLoaded: isUserLoaded } = useUser();
	const { session, isLoaded: isSessionLoaded } = useSession();
	const [jobs, setJobs] = useState<Job[]>([]);
	const [loading, setLoading] = useState(true);
	const [refreshing, setRefreshing] = useState(false);
	const [jobModalOpen, setJobModalOpen] = useState<{ isOpen: boolean, jobDetails?: Job | null }>({ isOpen: false, jobDetails: null });
	const [previewModalOpen, setPreviewModalOpen] = useState<{ isOpen: boolean, job?: Job | null }>({ isOpen: false, job: null });
	const [sortOrder, setSortOrder] = useState("asc");
	const [sortKey, setSortKey] = useState<keyof Job>("name");
	const [token, setToken] = useState<string | null>(null);
	const [searchQuery, setSearchQuery] = useState("");
	const [statusFilter, setStatusFilter] = useState<string>("all");

	// Fetch jobs from the backend
	const fetchJobs = useCallback(async (showRefreshIndicator = false) => {
		if (!isSessionLoaded || !session) {
			return;
		}

		if (showRefreshIndicator) {
			setRefreshing(true);
		}

		try {
			const tkn = await session.getToken();
			setToken(tkn);

			const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/status`, {
				method: "GET",
				headers: {
					"Authorization": `Bearer ${tkn}`,
					...(process.env.NEXT_PUBLIC_API_KEY && { "x-api-key": process.env.NEXT_PUBLIC_API_KEY }),
				},
			});

			if (!response.ok) {
				throw new Error("Failed to fetch jobs");
			}

			const data: Job[] = await response.json();
			setJobs(data);
		} catch (error) {
			console.error("Error fetching jobs", error);
			if (showRefreshIndicator) {
				toast.error("Failed to refresh jobs");
			}
		} finally {
			setLoading(false);
			setRefreshing(false);
		}
	}, [isSessionLoaded, session]);

	// Initial fetch on mount
	useEffect(() => {
		fetchJobs();
	}, [fetchJobs]);

	// Auto-refresh every 30 seconds
	useEffect(() => {
		if (!isSessionLoaded || !session) return;

		const interval = setInterval(() => {
			fetchJobs(false); // Silent refresh in background
		}, 30000); // 30 seconds

		return () => clearInterval(interval);
	}, [isSessionLoaded, session, fetchJobs]);

	// Sort jobs
	const sortJobs = (key: keyof Job) => {
		const newOrder = sortKey === key && sortOrder === "asc" ? "desc" : "asc";
		const sortedJobs = [...jobs].sort((a, b) => {
			if (newOrder === "asc") {
				return a[key] > b[key] ? 1 : -1;
			} else {
				return a[key] < b[key] ? 1 : -1;
			}
		});
		setJobs(sortedJobs);
		setSortKey(key);
		setSortOrder(newOrder);
	};

	// Filter and search jobs
	const filteredJobs = jobs.filter(job => {
		const matchesSearch = job.name.toLowerCase().includes(searchQuery.toLowerCase());
		const matchesStatus = statusFilter === "all" || job.status === statusFilter;
		return matchesSearch && matchesStatus;
	});

	// Handle pausing a job
	const handlePauseJob = async (jobId: string) => {
		if (!isSessionLoaded || !session) {
			return;
		}

		try {
			// Optimistic update
			const updatedJobs = jobs.map(job =>
				job.job_id === jobId ? { ...job, status: 'paused' } : job
			);
			setJobs(updatedJobs);

			const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/${jobId}/pause`, {
				method: "PATCH",
				headers: {
					"Authorization": `Bearer ${token}`,
					...(process.env.NEXT_PUBLIC_API_KEY && { "x-api-key": process.env.NEXT_PUBLIC_API_KEY }),
				},
			});

			if (!response.ok) {
				throw new Error("Failed to pause job");
			}

			toast.success("Job paused successfully");
			// Refresh to get latest state from server
			fetchJobs(false);
		} catch (error) {
			console.error("Error pausing job", error);
			toast.error("Failed to pause job");
			// Refresh to revert optimistic update
			fetchJobs(false);
		}
	};

	// Handle deleting a job
	const handleDeleteJob = async (jobId: string) => {
		if (!isSessionLoaded || !session) {
			return;
		}

		// Confirmation dialog
		if (!confirm("Are you sure you want to delete this job? This action cannot be undone.")) {
			return;
		}

		try {
			// Optimistic update
			setJobs(jobs.filter(job => job.job_id !== jobId));

			const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/${jobId}`, {
				method: "DELETE",
				headers: {
					"Authorization": `Bearer ${token}`,
					...(process.env.NEXT_PUBLIC_API_KEY && { "x-api-key": process.env.NEXT_PUBLIC_API_KEY }),
				},
			});

			if (!response.ok) {
				throw new Error("Failed to delete job");
			}

			toast.success("Job deleted successfully");
		} catch (error) {
			console.error("Error deleting job", error);
			toast.error("Failed to delete job");
			// Refresh to revert optimistic update
			fetchJobs(false);
		}
	};

	// Handle downloading job results
	const handleDownload = async (jobId: string) => {
		if (!isSessionLoaded || !session) {
			return;
		}

		try {
			const response = await fetch(
				`${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/${jobId}/download?format=json`,
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
				throw new Error(error.message || "Failed to get download URL");
			}

			const data = await response.json();

			// Open download URL in new tab
			window.open(data.download_url, '_blank');
			toast.success("Download started");
		} catch (error) {
			console.error("Error downloading results", error);
			toast.error(error instanceof Error ? error.message : "Failed to download results");
		}
	};

	// Handle opening preview modal
	const handlePreview = (job: Job) => {
		setPreviewModalOpen({ isOpen: true, job });
	};

	if (!isUserLoaded || !isSessionLoaded) {
		return <p>Loading...</p>; // Show loading state until Clerk is fully loaded
	}

	return (
		<div className="p-8 text-white">
			<div className="flex justify-between items-center mb-6">
				<h1 className="text-4xl">Dashboard</h1>
				<div className="flex gap-2">
					<button
						onClick={() => fetchJobs(true)}
						disabled={refreshing}
						className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded flex items-center gap-2 disabled:opacity-50"
					>
						<RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
						Refresh
					</button>
					<button
						onClick={() => setJobModalOpen({ isOpen: true, jobDetails: null })}
						className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded"
					>
						Submit New Job
					</button>
				</div>
			</div>

			{/* Search and Filter */}
			<div className="mb-6 flex flex-col md:flex-row gap-4">
				<div className="flex-1 relative">
					<Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
					<Input
						type="text"
						placeholder="Search jobs by name..."
						value={searchQuery}
						onChange={(e) => setSearchQuery(e.target.value)}
						className="pl-10"
					/>
				</div>
				<div className="flex gap-2">
					<select
						value={statusFilter}
						onChange={(e) => setStatusFilter(e.target.value)}
						className="px-4 py-2 bg-gray-800 rounded border border-gray-700"
					>
						<option value="all">All Status</option>
						<option value="ready">Ready</option>
						<option value="queued">Queued</option>
						<option value="processing">Processing</option>
						<option value="paused">Paused</option>
						<option value="completed">Completed</option>
						<option value="error">Error</option>
					</select>
					<button
						onClick={() => sortJobs("name")}
						className={`px-4 py-2 rounded ${sortKey === 'name' ? 'bg-blue-600' : 'bg-gray-800'}`}
					>
						Name {sortKey === 'name' && (sortOrder === 'asc' ? '↑' : '↓')}
					</button>
					<button
						onClick={() => sortJobs("status")}
						className={`px-4 py-2 rounded ${sortKey === 'status' ? 'bg-blue-600' : 'bg-gray-800'}`}
					>
						Status {sortKey === 'status' && (sortOrder === 'asc' ? '↑' : '↓')}
					</button>
				</div>
			</div>

			{/* Jobs grid with loading skeletons */}
			{loading ? (
				<div className="grid grid-cols-1 md:grid-cols-2 gap-6">
					{[...Array(4)].map((_, i) => (
						<JobCardSkeleton key={i} />
					))}
				</div>
			) : filteredJobs.length === 0 ? (
				<div className="text-center py-12 text-gray-400">
					<p className="text-lg">
						{searchQuery || statusFilter !== "all"
							? "No jobs match your search criteria"
							: "No jobs yet. Create your first job to get started!"}
					</p>
				</div>
			) : (
				<div className="grid grid-cols-1 md:grid-cols-2 gap-6">
					{filteredJobs.map(job => (
						<JobCard
							key={job.job_id}
							job={job}
							onClick={() => setJobModalOpen({ isOpen: true, jobDetails: job })}
							onPause={() => handlePauseJob(job.job_id)}
							onDelete={() => handleDeleteJob(job.job_id)}
							onDownload={() => handleDownload(job.job_id)}
							onPreview={() => handlePreview(job)}
						/>
					))}
				</div>
			)}

			{/* Unified Job Modal */}
			{jobModalOpen.isOpen && session && (
				<JobModal
					closeModal={() => {
						setJobModalOpen({ isOpen: false, jobDetails: null });
						fetchJobs(false); // Refresh after modal closes
					}}
					jobDetails={jobModalOpen.jobDetails}
					session={session}
				/>
			)}

			{/* Result Preview Modal */}
			{previewModalOpen.isOpen && previewModalOpen.job && (
				<ResultPreviewModal
					closeModal={() => setPreviewModalOpen({ isOpen: false, job: null })}
					jobId={previewModalOpen.job.job_id}
					jobName={previewModalOpen.job.name}
					token={token}
				/>
			)}
		</div>
	);
}
