/**
 * StatCard Component Test
 * Unit tests for statistics card component
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatCard } from '@/components/StatCard';
import { BriefcaseIcon } from 'lucide-react';

describe('StatCard', () => {
  it('should render title and value', () => {
    render(<StatCard title="Total Jobs" value={42} />);

    expect(screen.getByText('Total Jobs')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
  });

  it('should render string values', () => {
    render(<StatCard title="Status" value="Active" />);

    expect(screen.getByText('Status')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('should render icon when provided', () => {
    render(
      <StatCard
        title="Total Jobs"
        value={42}
        icon={<BriefcaseIcon data-testid="icon" />}
      />
    );

    expect(screen.getByTestId('icon')).toBeInTheDocument();
  });

  it('should render trend indicator when provided', () => {
    render(
      <StatCard
        title="Total Jobs"
        value={42}
        trend="up"
        change={12}
      />
    );

    expect(screen.getByText('+12%')).toBeInTheDocument();
  });

  it('should render negative change', () => {
    render(
      <StatCard
        title="Failed Jobs"
        value={5}
        trend="down"
        change={-3}
      />
    );

    expect(screen.getByText('-3%')).toBeInTheDocument();
  });

  it('should render change label', () => {
    render(
      <StatCard
        title="Total Jobs"
        value={42}
        trend="up"
        change={12}
        changeLabel="vs last month"
      />
    );

    expect(screen.getByText('vs last month')).toBeInTheDocument();
  });

  it('should handle neutral trend', () => {
    render(
      <StatCard
        title="Total Jobs"
        value={42}
        trend="neutral"
      />
    );

    expect(screen.getByText('Total Jobs')).toBeInTheDocument();
  });

  it('should apply custom className', () => {
    const { container } = render(
      <StatCard
        title="Total Jobs"
        value={42}
        className="custom-class"
      />
    );

    expect(container.firstChild).toHaveClass('custom-class');
  });
});
