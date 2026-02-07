interface UrlModalProps {
	closeModal: () => void;
}

export function UrlModal({ closeModal }: UrlModalProps) {
	return (
		<div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center">
			<div className="bg-gray-800 p-6 rounded-lg">
				<h2 className="text-xl mb-4">URL Crawl Details</h2>
				<p>Details about the URL crawl will go here.</p>
				<button
					onClick={closeModal}
					className="mt-4 bg-red-600 px-4 py-2 rounded-lg"
				>
					Close
				</button>
			</div>
		</div>
	);
}
