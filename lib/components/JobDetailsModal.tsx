import { useEffect, useState } from 'react';
import { JobDetails, JobDetailsModalProps } from '@/lib/types';

export function JobDetailsModal({ jobId, closeModal }: JobDetailsModalProps) {
	const [jobDetails, setJobDetails] = useState<JobDetails | null>(null);
  const [loading, setLoading] = useState(true);

	useEffect(() => {
		const fetchJobDetails = async () => {
			try {
				const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/jobs/${jobId}`);
				const data = await response.json();
				setJobDetails(data);
			} catch (error) {
				console.error("Error fetching job details", error);
			} finally {
				setLoading(false);
			}
		};

		fetchJobDetails();
	}, [jobId]);

	if (loading) {
    return <p>Loading job details...</p>;
  }

  if (!jobDetails) {
    return <p>Job details not found.</p>;
  }

	return (
		<div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center">
			<div className="bg-gray-800 p-6 rounded-lg">
				<h2 className="text-xl mb-4">{jobDetails.name}</h2>
				<p>Status: {jobDetails.status}</p>
				<p>Links to be crawled: {jobDetails.links.length}</p>

				{/* Add any other details about the job */}
				<button onClick={closeModal} className="mt-4 bg-red-600 px-4 py-2 rounded-lg">
					Close
				</button>
			</div>
		</div>
	);
}
