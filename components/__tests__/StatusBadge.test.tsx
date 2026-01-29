/**
 * StatusBadge Component Test
 * Example component test with React Testing Library
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@/lib/test-utils';
import { StatusBadge } from '@/components/StatusBadge';

describe('StatusBadge', () => {
  it('should render running status', () => {
    render(<StatusBadge status="running" />);
    expect(screen.getByText('Running')).toBeInTheDocument();
  });

  it('should render success status', () => {
    render(<StatusBadge status="success" />);
    expect(screen.getByText('Success')).toBeInTheDocument();
  });

  it('should render failed status', () => {
    render(<StatusBadge status="failed" />);
    expect(screen.getByText('Failed')).toBeInTheDocument();
  });

  it('should render paused status', () => {
    render(<StatusBadge status="paused" />);
    expect(screen.getByText('Paused')).toBeInTheDocument();
  });

  it('should render scheduled status', () => {
    render(<StatusBadge status="scheduled" />);
    expect(screen.getByText('Scheduled')).toBeInTheDocument();
  });

  it('should apply correct CSS class for running status', () => {
    const { container } = render(<StatusBadge status="running" />);
    const badge = container.firstChild;
    expect(badge).toHaveClass('status-running');
  });

  it('should apply correct CSS class for success status', () => {
    const { container } = render(<StatusBadge status="success" />);
    const badge = container.firstChild;
    expect(badge).toHaveClass('status-success');
  });

  it('should render small size', () => {
    const { container } = render(<StatusBadge status="running" size="sm" />);
    const badge = container.firstChild;
    expect(badge).toHaveClass('text-xs');
  });

  it('should render large size', () => {
    const { container } = render(<StatusBadge status="running" size="lg" />);
    const badge = container.firstChild;
    expect(badge).toHaveClass('text-base');
  });

  it('should show icon when showIcon is true', () => {
    render(<StatusBadge status="running" showIcon />);
    // Check if SVG icon is present
    const badge = screen.getByText('Running').parentElement;
    expect(badge?.querySelector('svg')).toBeInTheDocument();
  });

  it('should apply custom className', () => {
    const { container } = render(
      <StatusBadge status="running" className="custom-class" />
    );
    const badge = container.firstChild;
    expect(badge).toHaveClass('custom-class');
  });
});
