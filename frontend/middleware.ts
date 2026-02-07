import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';

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

export default clerkMiddleware(async (auth, request) => {
	const authObject = await auth();

	if (!isPublicRoute(request) && !authObject.userId) {
		return authObject.redirectToSignIn();
	}
})

export const config = {
	matcher: [
		// Skip Next.js internals and all static files, unless found in search params
		'/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
		// Always run for API routes
		'/(api|trpc)(.*)',
	],
}