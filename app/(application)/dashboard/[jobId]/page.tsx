"use client";

import { useParams } from 'next/navigation';
import { useState } from 'react';
import { UrlModal } from "@/components/UrlModal";

export default function JobPage() {
	const [modalOpen, setModalOpen] = useState(false);

	const params = useParams(); // Retrieve dynamic route parameters
	const jobId = params.jobId; // This accesses the [jobId] from the route

	const urls = [
		{ id: 1, url: 'https://example.com/page1' },
		{ id: 2, url: 'https://example.com/page2' },
	];

	return (
		<div className="p-8 text-white">
			<h1 className="text-3xl mb-6">Job {jobId}</h1>
			<div className="grid grid-cols-1 gap-4">
				{urls.map(url => (
					<button
						key={url.id}
						onClick={() => setModalOpen(true)}
						className="p-4 bg-gray-700 rounded-lg"
					>
						{url.url}
					</button>
				))}
			</div>

			{modalOpen && (
				<UrlModal closeModal={() => setModalOpen(false)} />
			)}
		</div>
	);
}
