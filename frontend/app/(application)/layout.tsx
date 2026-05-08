// Authenticated routes: skip static prerender. These pages need
// the user's Clerk session at request time, so static generation
// would either render an empty shell or crash on undefined data.
export const dynamic = 'force-dynamic';

export default function ApplicationLayout({ children }: { children: React.ReactNode }) {
  return children;
}
