/**
 * Next.js Loading Page
 * Global loading UI for the application
 */

import { LoadingSpinnerFullPage } from '@/components/LoadingSpinner';

export default function LoadingPage() {
  return <LoadingSpinnerFullPage text="Loading..." />;
}
