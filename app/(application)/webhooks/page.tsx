'use client';

import { useState, useEffect } from 'react';
import { useUser, useSession } from '@clerk/nextjs';
import { Webhook } from "@/lib/types";
import { Input, Button } from '@snowforge/ui';
import { AppLayout } from '@/components/layout';
import { PageHeader } from '@/components/PageHeader';
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
		return (
			<AppLayout>
				<div className="flex items-center justify-center min-h-[60vh]">
					<p className="text-muted-foreground">Loading...</p>
				</div>
			</AppLayout>
		);
	}

	return (
		<AppLayout>
			<div className="space-y-6 p-6">
				{/* Page Header */}
				<PageHeader
					title="Webhooks"
					description="Receive real-time notifications when jobs complete"
					actions={
						<div className="flex items-center gap-2">
							<Button
								variant="outline"
								size="sm"
								onClick={() => fetchWebhooks(true)}
								disabled={refreshing}
							>
								<RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
								Refresh
							</Button>
							<Button
								size="sm"
								onClick={() => setShowCreateModal(true)}
							>
								<Plus className="mr-2 h-4 w-4" />
								Create Webhook
							</Button>
						</div>
					}
				/>

				{/* Webhooks list */}
				{loading ? (
					<div className="text-center py-12 text-muted-foreground">Loading webhooks...</div>
				) : webhooks.length === 0 ? (
					<div className="text-center py-12 text-muted-foreground">
						<p className="text-lg">No webhooks configured yet</p>
						<p className="text-sm mt-2">Create your first webhook to receive real-time job notifications</p>
					</div>
				) : (
					<div className="space-y-4">
						{webhooks.map(webhook => (
							<div key={webhook.webhook_id} className="p-6 bg-card rounded-lg border">
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
												<span key={event} className="px-2 py-1 bg-primary text-primary-foreground text-xs rounded">
													{event}
												</span>
											))}
										</div>
										<p className="text-sm text-muted-foreground">
											Created: {new Date(webhook.created_at).toLocaleString()}
										</p>
										<p className="text-sm text-muted-foreground">
											Deliveries: {webhook.total_deliveries} total, {webhook.failed_deliveries} failed
											{webhook.total_deliveries > 0 && (
												<span className="ml-2">
													({((1 - webhook.failed_deliveries / webhook.total_deliveries) * 100).toFixed(1)}% success rate)
												</span>
											)}
										</p>
										{webhook.secret && (
											<div className="mt-2 flex items-center gap-2">
												<code className="text-xs bg-muted px-2 py-1 rounded">
													{webhook.secret.substring(0, 20)}...
												</code>
												<button
													onClick={() => copySecret(webhook.secret!, webhook.webhook_id)}
													className="p-1 hover:bg-muted rounded"
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
										<Button
											variant="outline"
											size="icon"
											onClick={() => handleTestWebhook(webhook.webhook_id)}
											title="Test webhook"
										>
											<TestTube className="h-4 w-4" />
										</Button>
										<Button
											variant="destructive"
											size="icon"
											onClick={() => handleDeleteWebhook(webhook.webhook_id)}
											title="Delete webhook"
										>
											<Trash2 className="h-4 w-4" />
										</Button>
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
		</AppLayout>
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
		<div className="fixed inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center z-50">
			<div className="bg-card border rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
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
						<p className="text-xs text-muted-foreground mt-1">
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
											? 'border-primary bg-primary/10'
											: 'border-border hover:border-muted-foreground'
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
											<div className="text-sm text-muted-foreground">{event.description}</div>
										</div>
									</div>
								</div>
							))}
						</div>
					</div>

					{/* Webhook signature info */}
					<div className="bg-muted p-4 rounded text-sm">
						<p className="font-medium mb-2">Webhook Signatures</p>
						<p className="text-muted-foreground mb-2">
							All webhook requests include an <code className="bg-background px-1 rounded">X-Snowscrape-Signature</code> header
							containing an HMAC SHA256 signature of the payload.
						</p>
						<p className="text-muted-foreground">
							Use the webhook secret (shown after creation) to verify the signature and ensure requests are authentic.
						</p>
					</div>
				</div>

				{/* Modal actions */}
				<div className="flex gap-2 mt-6">
					<Button
						onClick={handleCreate}
						disabled={creating}
						className="flex-1"
					>
						{creating ? "Creating..." : "Create Webhook"}
					</Button>
					<Button
						variant="outline"
						onClick={closeModal}
						disabled={creating}
						className="flex-1"
					>
						Cancel
					</Button>
				</div>
			</div>
		</div>
	);
}
