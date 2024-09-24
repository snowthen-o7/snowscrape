'use client';

import { useState, useEffect } from 'react';
import { useUser, useSession } from '@clerk/nextjs';
import { JobModal } from "@/components/JobModal";
import { JobCard } from "@/components/JobCard";
import { Job } from "@/lib/types";

export default function Dashboard() {
	const { isLoaded: isUserLoaded } = useUser();
	const { session, isLoaded: isSessionLoaded } = useSession();
	const [jobs, setJobs] = useState<Job[]>([]);
	const [loading, setLoading] = useState(true);
	const [jobModalOpen, setJobModalOpen] = useState<{ isOpen: boolean, jobDetails?: Job | null }>({ isOpen: false, jobDetails: null }); // Unified modal state
	const [sortOrder, setSortOrder] = useState("asc"); // For sorting
	const [token, setToken] = useState<string | null>(null);

	// Fetch jobs from the backend
	useEffect(() => {
    const fetchJobs = async () => {
      if (!isSessionLoaded || !session) {
        return; // Wait until the session is loaded
      }
      
      try {
        const tkn = await session.getToken(); // Get the session token
				setToken(tkn);

        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/status`, {
          method: "GET",
          headers: {
            "Authorization": `Bearer ${token}`, // Use token in the Authorization header
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
  }, [isSessionLoaded, session]); // Fetch jobs once session is loaded

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
	const handlePauseJob = async (jobId: string) => {
    console.log(`Pausing job: ${jobId}`);

    if (!isSessionLoaded || !session) {
      return;
    }

    try {
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

      const updatedJobs = jobs.map(job => 
        job.job_id === jobId ? { ...job, status: 'paused' } : job
      );
      setJobs(updatedJobs);
    } catch (error) {
      console.error("Error pausing job", error);
    }
  };

	// Handle deleting a job
	const handleDeleteJob = async (jobId: string) => {
    console.log(`Deleting job: ${jobId}`);

    if (!isSessionLoaded || !session) {
      return;
    }

    try {
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

      setJobs(jobs.filter(job => job.job_id !== jobId)); // Remove deleted job from state
    } catch (error) {
      console.error("Error deleting job", error);
    }
  };

	if (!isUserLoaded || !isSessionLoaded) {
		return <p>Loading...</p>; // Show loading state until Clerk is fully loaded
	}

	return (
		<div className="p-8 text-white">
			<h1 className="text-4xl mb-6">Dashboard</h1>

			{/* Button to open new job modal */}
			<button onClick={() => setJobModalOpen({ isOpen: true, jobDetails: null })} className="bg-blue-600 px-4 py-2 rounded">
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
							key={job.job_id}
							job={job}
							onClick={() => setJobModalOpen({ isOpen: true, jobDetails: job })} // Open job details modal
							onPause={() => handlePauseJob(job.job_id)} // Pause job
							onDelete={() => handleDeleteJob(job.job_id)} // Delete job
						/>
					))}
				</div>
			)}

			{/* Unified Job Modal for both creating new jobs and updating existing ones */}
			{jobModalOpen.isOpen && (
				<JobModal
					closeModal={() => setJobModalOpen({ isOpen: false, jobDetails: null })}
					jobDetails={jobModalOpen.jobDetails} // Pass job details if editing, or null if creating a new job
					session={session}
				/>
			)}
		</div>
	);
}
