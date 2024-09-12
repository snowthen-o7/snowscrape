import { SiteCard } from "@/components/SiteCard";

export default function Dashboard() {
	const sites = [
		{ id: 1, name: 'Example Site 1' },
		{ id: 2, name: 'Example Site 2' },
	];

	return (
		<div className="p-8 text-white">
			<h1 className="text-4xl mb-6">Dashboard</h1>
			<div className="grid grid-cols-1 md:grid-cols-2 gap-6">
				{sites.map(site => (
					<SiteCard key={site.id} site={site} />
				))}
			</div>
		</div>
	);
}
