'use client';

import { useState, useEffect } from 'react';
import { useUser, useSession } from '@clerk/nextjs';
import { Webhook } from "@/lib/types";
import { Input } from "@/components/ui/input";
import { Plus, Trash2, TestTube, Copy, CheckCircle, XCircle, RefreshCw } from "lucide-react";
import { toast } from 'react-toastify';

export default function WebhooksPage() {
	const { isLoaded: isUserLoaded } = useUser();
	const { session, isLoaded: isSessionLoaded } = useSession();
	const [webhooks, setWebhooks] = useState<Webhook[]>([]);
	const [loading, setLoading] = useState(true);
	const [refreshing, setRefreshing] = useState(false);
	const [token, setToken] = useState<string | null>(null);
	const [showCreateModal, setShowCreateModal] = useState(false);
	const [copiedSecret, setCopiedSecret] = useState<string | null>(null);

	// Fetch webhooks from the backend
	const fetchWebhooks = async (showRefreshIndicator = false) => {
		if (!isSessionLoaded || !session) {
			return;
		}

		if (showRefreshIndicator) {
			setRefreshing(true);
		}

		try {
			const tkn = await session.getToken();
			setToken(tkn);

			const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/webhooks`, {
				method: "GET",
				headers: {
					"Authorization": `Bearer ${tkn}`,
					...(process.env.NEXT_PUBLIC_API_KEY && { "x-api-key": process.env.NEXT_PUBLIC_API_KEY }),
				},
			});

			if (!response.ok) {
				throw new Error("Failed to fetch webhooks");
			}

			const data: Webhook[] = await response.json();
			setWebhooks(data);
		} catch (error) {
			console.error("Error fetching webhooks", error);
			if (showRefreshIndicator) {
				toast.error("Failed to refresh webhooks");
			}
		} finally {
			setLoading(false);
			setRefreshing(false);
		}
	};

	// Initial fetch on mount
	useEffect(() => {
		fetchWebhooks();
	}, [isSessionLoaded, session]);

	// Handle deleting a webhook
	const handleDeleteWebhook = async (webhookId: string) => {
		if (!confirm("Are you sure you want to delete this webhook?")) {
			return;
		}

		try {
			const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/webhooks/${webhookId}`, {
				method: "DELETE",
				headers: {
					"Authorization": `Bearer ${token}`,
					...(process.env.NEXT_PUBLIC_API_KEY && { "x-api-key": process.env.NEXT_PUBLIC_API_KEY }),
				},
			});

			if (!response.ok) {
				throw new Error("Failed to delete webhook");
			}

			toast.success("Webhook deleted successfully");
			fetchWebhooks(false);
		} catch (error) {
			console.error("Error deleting webhook", error);
			toast.error("Failed to delete webhook");
		}
	};

	// Handle testing a webhook
	const handleTestWebhook = async (webhookId: string) => {
		try {
			const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/webhooks/${webhookId}/test`, {
				method: "POST",
				headers: {
					"Authorization": `Bearer ${token}`,
					...(process.env.NEXT_PUBLIC_API_KEY && { "x-api-key": process.env.NEXT_PUBLIC_API_KEY }),
				},
			});

			if (!response.ok) {
				throw new Error("Failed to test webhook");
			}

			toast.success("Test webhook sent successfully");
		} catch (error) {
			console.error("Error testing webhook", error);
			toast.error("Failed to test webhook");
		}
	};

	// Copy secret to clipboard
	const copySecret = (secret: string, webhookId: string) => {
		navigator.clipboard.writeText(secret);
		setCopiedSecret(webhookId);
		toast.success("Secret copied to clipboard");
		setTimeout(() => setCopiedSecret(null), 2000);
	};

	if (!isUserLoaded || !isSessionLoaded) {
		return <p>Loading...</p>;
	}

	return (
		<div className="p-8 text-white">
			<div className="flex justify-between items-center mb-6">
				<div>
					<h1 className="text-4xl mb-2">Webhooks</h1>
					<p className="text-gray-400">Receive real-time notifications when jobs complete</p>
				</div>
				<div className="flex gap-2">
					<button
						onClick={() => fetchWebhooks(true)}
						disabled={refreshing}
						className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded flex items-center gap-2 disabled:opacity-50"
					>
						<RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
						Refresh
					</button>
					<button
						onClick={() => setShowCreateModal(true)}
						className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded flex items-center gap-2"
					>
						<Plus className="h-4 w-4" />
						Create Webhook
					</button>
				</div>
			</div>

			{/* Webhooks list */}
			{loading ? (
				<div className="text-center py-12 text-gray-400">Loading webhooks...</div>
			) : webhooks.length === 0 ? (
				<div className="text-center py-12 text-gray-400">
					<p className="text-lg">No webhooks configured yet</p>
					<p className="text-sm mt-2">Create your first webhook to receive real-time job notifications</p>
				</div>
			) : (
				<div className="space-y-4">
					{webhooks.map(webhook => (
						<div key={webhook.webhook_id} className="p-6 bg-gray-800 rounded-lg">
							<div className="flex justify-between items-start mb-4">
								<div className="flex-1">
									<div className="flex items-center gap-2 mb-2">
										<h3 className="text-xl font-semibold">{webhook.url}</h3>
										{webhook.active ? (
											<CheckCircle className="h-5 w-5 text-green-500" />
										) : (
											<XCircle className="h-5 w-5 text-red-500" />
										)}
									</div>
									<div className="flex flex-wrap gap-2 mb-2">
										{webhook.events.map(event => (
											<span key={event} className="px-2 py-1 bg-blue-600 text-xs rounded">
												{event}
											</span>
										))}
									</div>
									<p className="text-sm text-gray-400">
										Created: {new Date(webhook.created_at).toLocaleString()}
									</p>
									<p className="text-sm text-gray-400">
										Deliveries: {webhook.total_deliveries} total, {webhook.failed_deliveries} failed
										{webhook.total_deliveries > 0 && (
											<span className="ml-2">
												({((1 - webhook.failed_deliveries / webhook.total_deliveries) * 100).toFixed(1)}% success rate)
											</span>
										)}
									</p>
									{webhook.secret && (
										<div className="mt-2 flex items-center gap-2">
											<code className="text-xs bg-gray-900 px-2 py-1 rounded">
												{webhook.secret.substring(0, 20)}...
											</code>
											<button
												onClick={() => copySecret(webhook.secret!, webhook.webhook_id)}
												className="p-1 hover:bg-gray-700 rounded"
												title="Copy secret"
											>
												{copiedSecret === webhook.webhook_id ? (
													<CheckCircle className="h-4 w-4 text-green-500" />
												) : (
													<Copy className="h-4 w-4" />
												)}
											</button>
										</div>
									)}
								</div>

								<div className="flex gap-2">
									<button
										onClick={() => handleTestWebhook(webhook.webhook_id)}
										className="p-2 bg-purple-600 rounded-lg hover:bg-purple-700"
										title="Test webhook"
									>
										<TestTube className="h-5 w-5" />
									</button>
									<button
										onClick={() => handleDeleteWebhook(webhook.webhook_id)}
										className="p-2 bg-red-600 rounded-lg hover:bg-red-700"
										title="Delete webhook"
									>
										<Trash2 className="h-5 w-5" />
									</button>
								</div>
							</div>
						</div>
					))}
				</div>
			)}

			{/* Create webhook modal */}
			{showCreateModal && (
				<CreateWebhookModal
					closeModal={() => {
						setShowCreateModal(false);
						fetchWebhooks(false);
					}}
					token={token}
				/>
			)}
		</div>
	);
}

// Create webhook modal component
function CreateWebhookModal({ closeModal, token }: { closeModal: () => void; token: string | null }) {
	const [url, setUrl] = useState('');
	const [events, setEvents] = useState<string[]>(['job.completed']);
	const [creating, setCreating] = useState(false);

	const availableEvents = [
		{ value: 'job.created', label: 'Job Created', description: 'When a new job is created' },
		{ value: 'job.started', label: 'Job Started', description: 'When job processing begins' },
		{ value: 'job.completed', label: 'Job Completed', description: 'When a job finishes successfully' },
		{ value: 'job.failed', label: 'Job Failed', description: 'When a job fails with an error' },
		{ value: 'job.cancelled', label: 'Job Cancelled', description: 'When a job is cancelled' },
	];

	const toggleEvent = (eventValue: string) => {
		setEvents(prev =>
			prev.includes(eventValue)
				? prev.filter(e => e !== eventValue)
				: [...prev, eventValue]
		);
	};

	const handleCreate = async () => {
		if (!url) {
			toast.error("Webhook URL is required");
			return;
		}

		if (events.length === 0) {
			toast.error("Select at least one event");
			return;
		}

		setCreating(true);

		try {
			const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/webhooks`, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					"Authorization": `Bearer ${token}`,
					...(process.env.NEXT_PUBLIC_API_KEY && { "x-api-key": process.env.NEXT_PUBLIC_API_KEY }),
				},
				body: JSON.stringify({ url, events }),
			});

			if (!response.ok) {
				const error = await response.json();
				throw new Error(error.message || "Failed to create webhook");
			}

			const data = await response.json();
			toast.success("Webhook created successfully");

			// Show the secret to the user
			if (data.webhook && data.webhook.secret) {
				toast.info(`Save your webhook secret: ${data.webhook.secret}`, {
					autoClose: false
				});
			}

			closeModal();
		} catch (error) {
			console.error("Error creating webhook", error);
			toast.error(error instanceof Error ? error.message : "Failed to create webhook");
		} finally {
			setCreating(false);
		}
	};

	return (
		<div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
			<div className="bg-gray-800 rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
				<h2 className="text-2xl mb-4">Create Webhook</h2>

				<div className="space-y-4">
					{/* URL input */}
					<div>
						<label className="block text-sm font-medium mb-2">Webhook URL</label>
						<Input
							type="url"
							placeholder="https://your-domain.com/webhook"
							value={url}
							onChange={(e) => setUrl(e.target.value)}
							className="w-full"
						/>
						<p className="text-xs text-gray-400 mt-1">
							The URL where webhook events will be sent via HTTP POST
						</p>
					</div>

					{/* Events selection */}
					<div>
						<label className="block text-sm font-medium mb-2">Events to Subscribe</label>
						<div className="space-y-2">
							{availableEvents.map(event => (
								<div
									key={event.value}
									className={`p-3 rounded border cursor-pointer transition-colors ${
										events.includes(event.value)
											? 'border-blue-500 bg-blue-900 bg-opacity-20'
											: 'border-gray-700 hover:border-gray-600'
									}`}
									onClick={() => toggleEvent(event.value)}
								>
									<div className="flex items-start gap-2">
										<input
											type="checkbox"
											checked={events.includes(event.value)}
											onChange={() => toggleEvent(event.value)}
											className="mt-1"
										/>
										<div>
											<div className="font-medium">{event.label}</div>
											<div className="text-sm text-gray-400">{event.description}</div>
										</div>
									</div>
								</div>
							))}
						</div>
					</div>

					{/* Webhook signature info */}
					<div className="bg-gray-900 p-4 rounded text-sm">
						<p className="font-medium mb-2">Webhook Signatures</p>
						<p className="text-gray-400 mb-2">
							All webhook requests include an <code className="bg-gray-800 px-1 rounded">X-Snowscrape-Signature</code> header
							containing an HMAC SHA256 signature of the payload.
						</p>
						<p className="text-gray-400">
							Use the webhook secret (shown after creation) to verify the signature and ensure requests are authentic.
						</p>
					</div>
				</div>

				{/* Modal actions */}
				<div className="flex gap-2 mt-6">
					<button
						onClick={handleCreate}
						disabled={creating}
						className="flex-1 bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded disabled:opacity-50"
					>
						{creating ? "Creating..." : "Create Webhook"}
					</button>
					<button
						onClick={closeModal}
						disabled={creating}
						className="flex-1 bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded disabled:opacity-50"
					>
						Cancel
					</button>
				</div>
			</div>
		</div>
	);
}
