import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';
import { NextResponse } from 'next/server';

const isPublicRoute = createRouteMatcher([
	'/',
	'/sign-in(.*)',
	'/sign-up(.*)',
	'/api/health',
	'/pricing',
	'/features',
	'/contact',
	'/about',
	'/docs(.*)',
	'/blog(.*)',
	'/use-cases',
	'/privacy-policy',
	'/terms-conditions',
]);

const isBillingExempt = createRouteMatcher([
	'/onboarding/checkout',
	'/billing/locked',
]);

const SUBSCRIPTION_COOKIE = 'sf_sub_status';
const COOKIE_TTL_SECONDS = 60;

interface SubStatusCookie {
	status: string;
	fetched_at: number;
}

export const proxy = clerkMiddleware(async (auth, req) => {
	if (isPublicRoute(req)) {
		return NextResponse.next();
	}

	const { userId, getToken, redirectToSignIn } = await auth();
	if (!userId) {
		return redirectToSignIn();
	}

	if (isBillingExempt(req)) {
		return NextResponse.next();
	}

	// Read cached status cookie if fresh.
	const cookieValue = req.cookies.get(SUBSCRIPTION_COOKIE)?.value;
	let cached: SubStatusCookie | null = null;
	if (cookieValue) {
		try {
			cached = JSON.parse(cookieValue) as SubStatusCookie;
			const age = Math.floor(Date.now() / 1000) - cached.fetched_at;
			if (age > COOKIE_TTL_SECONDS) {
				cached = null;
			}
		} catch {
			cached = null;
		}
	}

	let status = cached?.status;

	if (!status) {
		const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL;
		if (!apiBase) {
			// No API configured (e.g. local without env) — let the user through;
			// app will show error states from useSubscription instead.
			return NextResponse.next();
		}
		const token = await getToken();
		if (!token) {
			return redirectToSignIn();
		}
		try {
			const resp = await fetch(`${apiBase}/billing/subscription`, {
				headers: { Authorization: `Bearer ${token}` },
				cache: 'no-store',
			});
			if (resp.ok) {
				const data = (await resp.json()) as { status?: string };
				status = data.status ?? 'no_subscription';
			} else {
				status = 'no_subscription';
			}
		} catch {
			// Network error — fail-open to avoid lockout from infra hiccups.
			return NextResponse.next();
		}
	}

	const res = redirectForStatus(status ?? 'no_subscription', req);
	if (!cached) {
		const cookiePayload: SubStatusCookie = {
			status: status ?? 'no_subscription',
			fetched_at: Math.floor(Date.now() / 1000),
		};
		res.cookies.set(SUBSCRIPTION_COOKIE, JSON.stringify(cookiePayload), {
			httpOnly: true,
			sameSite: 'lax',
			maxAge: COOKIE_TTL_SECONDS,
			path: '/',
		});
	}
	return res;
});

function redirectForStatus(status: string, req: Request) {
	if (status === 'trialing' || status === 'active') {
		return NextResponse.next();
	}
	if (status === 'past_due' || status === 'incomplete') {
		return NextResponse.redirect(
			new URL('/billing/locked?reason=payment_failed', req.url),
		);
	}
	if (status === 'canceled') {
		return NextResponse.redirect(new URL('/billing/locked?reason=canceled', req.url));
	}
	// no_subscription, unpaid, incomplete_expired
	return NextResponse.redirect(new URL('/onboarding/checkout', req.url));
}

export const config = {
	matcher: [
		// Skip Next.js internals and all static files, unless found in search params
		'/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
		// Always run for API routes
		'/(api|trpc)(.*)',
	],
}
