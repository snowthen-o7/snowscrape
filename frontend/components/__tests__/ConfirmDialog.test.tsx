/**
 * ConfirmDialog Component Test
 * Unit tests for confirmation dialog component
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfirmDialog } from '@snowforge/ui';

describe('ConfirmDialog', () => {
  const defaultProps = {
    open: true,
    onOpenChange: vi.fn(),
    onConfirm: vi.fn(),
    title: 'Delete Job',
    description: 'Are you sure you want to delete this job?',
  };

  it('should render title and description', () => {
    render(<ConfirmDialog {...defaultProps} />);

    expect(screen.getByText('Delete Job')).toBeInTheDocument();
    expect(screen.getByText('Are you sure you want to delete this job?')).toBeInTheDocument();
  });

  it('should render confirm and cancel buttons', () => {
    render(<ConfirmDialog {...defaultProps} />);

    expect(screen.getByRole('button', { name: /confirm/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });

  it('should render custom button labels', () => {
    render(
      <ConfirmDialog
        {...defaultProps}
        confirmLabel="Delete"
        cancelLabel="Nevermind"
      />
    );

    expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Nevermind' })).toBeInTheDocument();
  });

  it('should call onConfirm when confirm button is clicked', async () => {
    const handleConfirm = vi.fn();
    const user = userEvent.setup();

    render(<ConfirmDialog {...defaultProps} onConfirm={handleConfirm} />);

    await user.click(screen.getByRole('button', { name: /confirm/i }));
    expect(handleConfirm).toHaveBeenCalledTimes(1);
  });

  it('should call onOpenChange when cancel button is clicked', async () => {
    const handleOpenChange = vi.fn();
    const user = userEvent.setup();

    render(<ConfirmDialog {...defaultProps} onOpenChange={handleOpenChange} />);

    await user.click(screen.getByRole('button', { name: /cancel/i }));
    expect(handleOpenChange).toHaveBeenCalledWith(false);
  });

  it('should accept loading prop', () => {
    render(<ConfirmDialog {...defaultProps} loading={true} />);

    // Dialog should still render when loading
    expect(screen.getByText('Delete Job')).toBeInTheDocument();
  });

  it('should apply destructive variant', () => {
    render(<ConfirmDialog {...defaultProps} variant="destructive" />);

    const confirmButton = screen.getByRole('button', { name: /confirm/i });
    // Check for destructive class in the button classes
    expect(confirmButton.className).toMatch(/bg-destructive/);
  });

  it('should not render when open is false', () => {
    render(<ConfirmDialog {...defaultProps} open={false} />);

    expect(screen.queryByText('Delete Job')).not.toBeInTheDocument();
  });
});
