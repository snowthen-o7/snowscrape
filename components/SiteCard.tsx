import Link from 'next/link';

interface SiteCardProps {
	site: { id: number; name: string };
}

export function SiteCard({ site }: SiteCardProps) {
	return (
		<Link href={`/dashboard/${site.id}`}>
			<div className="p-6 bg-gray-800 rounded-lg cursor-pointer">
				<h2 className="text-2xl">{site.name}</h2>
			</div>
		</Link>
	);
}
