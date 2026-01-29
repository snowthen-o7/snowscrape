import type { Metadata } from "next";
import localFont from "next/font/local";
import { ClerkProvider } from '@clerk/nextjs';
import { ThemeProvider } from '@snowforge/ui';
import { QueryProvider } from '@/components/providers/QueryProvider';
import { ToastProvider } from '@/components/providers/ToastProvider';
import "./globals.css";

const geistSans = localFont({
	src: "./fonts/GeistVF.woff",
	variable: "--font-geist-sans",
	weight: "100 900",
});
const geistMono = localFont({
	src: "./fonts/GeistMonoVF.woff",
	variable: "--font-geist-mono",
	weight: "100 900",
});

export const metadata: Metadata = {
	metadataBase: new URL('https://snowscrape.com'),
	title: {
		default: 'SnowScrape - Modern Web Scraping Platform',
		template: '%s | SnowScrape',
	},
	description:
		'Extract web data with ease. No coding required. Schedule jobs, handle JavaScript rendering, rotate proxies, and export to any format. Start free today.',
	keywords: [
		'web scraping',
		'data extraction',
		'web crawler',
		'price monitoring',
		'data mining',
		'api scraping',
		'javascript rendering',
		'proxy rotation',
		'scheduled scraping',
	],
	authors: [{ name: 'SnowScrape Team' }],
	creator: 'SnowScrape',
	publisher: 'SnowScrape',
	formatDetection: {
		email: false,
		address: false,
		telephone: false,
	},
	openGraph: {
		type: 'website',
		locale: 'en_US',
		url: 'https://snowscrape.com',
		siteName: 'SnowScrape',
		title: 'SnowScrape - Modern Web Scraping Platform',
		description:
			'Extract web data with ease. No coding required. Start your free trial today.',
		images: [
			{
				url: '/og-image.png',
				width: 1200,
				height: 630,
				alt: 'SnowScrape - Web Scraping Platform',
			},
		],
	},
	twitter: {
		card: 'summary_large_image',
		title: 'SnowScrape - Modern Web Scraping Platform',
		description:
			'Extract web data with ease. No coding required. Start your free trial today.',
		images: ['/og-image.png'],
		creator: '@snowscrape',
	},
	robots: {
		index: true,
		follow: true,
		googleBot: {
			index: true,
			follow: true,
			'max-video-preview': -1,
			'max-image-preview': 'large',
			'max-snippet': -1,
		},
	},
	verification: {
		google: 'your-google-site-verification-code',
		yandex: 'your-yandex-verification-code',
	},
};

export default function RootLayout({
	children,
}: {
	children: React.ReactNode
}) {
	return (
		<ClerkProvider>
			<QueryProvider>
				<html lang="en" suppressHydrationWarning>
					<head>
						{/* Structured Data - Organization */}
						<script
							type="application/ld+json"
							dangerouslySetInnerHTML={{
								__html: JSON.stringify({
									'@context': 'https://schema.org',
									'@type': 'SoftwareApplication',
									name: 'SnowScrape',
									applicationCategory: 'DeveloperApplication',
									offers: {
										'@type': 'Offer',
										price: '0',
										priceCurrency: 'USD',
									},
									aggregateRating: {
										'@type': 'AggregateRating',
										ratingValue: '4.8',
										ratingCount: '1250',
									},
									operatingSystem: 'Web',
									description:
										'Modern web scraping platform. Extract data from websites with no coding required.',
								}),
							}}
						/>
					</head>
					<body
						className={`${geistSans.variable} ${geistMono.variable} antialiased`}
					>
						<ThemeProvider
							attribute="class"
							defaultTheme="system"
							enableSystem
							disableTransitionOnChange
						>
							{children}
							<ToastProvider />
						</ThemeProvider>
					</body>
				</html>
			</QueryProvider>
		</ClerkProvider>
	)
}