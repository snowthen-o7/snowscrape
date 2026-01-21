/**
 * EmptyState Component Test
 * Example component test with user interactions
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/lib/test-utils';
import userEvent from '@testing-library/user-event';
import { EmptyState } from '@/components/EmptyState';
import { BriefcaseIcon } from 'lucide-react';

describe('EmptyState', () => {
  it('should render title and description', () => {
    render(
      <EmptyState title="No jobs yet" description="Create your first job" />
    );

    expect(screen.getByText('No jobs yet')).toBeInTheDocument();
    expect(screen.getByText('Create your first job')).toBeInTheDocument();
  });

  it('should render with icon', () => {
    render(
      <EmptyState
        icon={<BriefcaseIcon data-testid="icon" />}
        title="No jobs"
        description="Start creating"
      />
    );

    expect(screen.getByTestId('icon')).toBeInTheDocument();
  });

  it('should render action button when provided', () => {
    const handleClick = vi.fn();

    render(
      <EmptyState
        title="No jobs"
        description="Start now"
        action={{
          label: 'Create Job',
          onClick: handleClick,
        }}
      />
    );

    expect(screen.getByRole('button', { name: 'Create Job' })).toBeInTheDocument();
  });

  it('should call onClick when action button is clicked', async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();

    render(
      <EmptyState
        title="No jobs"
        description="Start now"
        action={{
          label: 'Create Job',
          onClick: handleClick,
        }}
      />
    );

    const button = screen.getByRole('button', { name: 'Create Job' });
    await user.click(button);

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('should not render action button when action is not provided', () => {
    render(<EmptyState title="No jobs" description="Start now" />);

    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('should apply custom className', () => {
    const { container } = render(
      <EmptyState
        title="No jobs"
        description="Start now"
        className="custom-class"
      />
    );

    const emptyState = container.firstChild;
    expect(emptyState).toHaveClass('custom-class');
  });
});
