/**
 * DestinationSelector Component Test
 * Pins the client-side 10-destination cap (mirrors backend/utils.py) and the
 * count indicator, so a user discovers the limit before submitting (issue #9).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@/lib/test-utils';
import userEvent from '@testing-library/user-event';
import { DestinationSelector } from '@/components/destinations/DestinationSelector';
import type { ExportDestination } from '@/lib/api/destinations';

// Drive the component via a mutable hook return so each test controls the list.
let hookState: { data: ExportDestination[] | undefined; isLoading: boolean };

vi.mock('@/lib/hooks/useDestinations', () => ({
  useDestinations: () => hookState,
}));

function makeDestination(i: number): ExportDestination {
  return {
    destination_id: `dest-${i}`,
    user_id: 'user-1',
    name: `Destination ${i}`,
    type: 'google_docs',
    drive_folder_id: `folder-${i}`,
    naming_template: 'Run {date}',
    mode: 'new_doc_per_run',
    format_template: 'structured_log',
    google_user_id: 'g-1',
    created_at: '2026-06-08T00:00:00Z',
  };
}

function makeDestinations(n: number): ExportDestination[] {
  return Array.from({ length: n }, (_, i) => makeDestination(i));
}

beforeEach(() => {
  hookState = { data: makeDestinations(12), isLoading: false };
});

describe('DestinationSelector cap', () => {
  it('shows the selected count out of the max', () => {
    render(<DestinationSelector value={['dest-0', 'dest-1']} onChange={() => {}} />);
    expect(screen.getByText('2 / 10 selected')).toBeInTheDocument();
  });

  it('leaves unchecked boxes enabled and adds an id below the cap', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<DestinationSelector value={['dest-0']} onChange={onChange} />);

    const boxes = screen.getAllByRole('checkbox');
    expect(boxes[1]).not.toBeDisabled();

    await user.click(boxes[1]);
    expect(onChange).toHaveBeenCalledWith(['dest-0', 'dest-1']);
  });

  it('disables unchecked boxes and shows the cap message at the limit', () => {
    const selected = Array.from({ length: 10 }, (_, i) => `dest-${i}`);
    render(<DestinationSelector value={selected} onChange={() => {}} />);

    expect(screen.getByText('10 / 10 selected')).toBeInTheDocument();
    expect(screen.getByText('Maximum 10 destinations per job')).toBeInTheDocument();

    const boxes = screen.getAllByRole('checkbox');
    // The 11th destination (dest-10) is unchecked -> disabled at the cap.
    expect(boxes[10]).toBeDisabled();
    // An already-selected destination stays enabled so it can be unchecked.
    expect(boxes[0]).not.toBeDisabled();
  });

  it('does not add a new id when at the cap even if toggle fires', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    const selected = Array.from({ length: 10 }, (_, i) => `dest-${i}`);
    render(<DestinationSelector value={selected} onChange={onChange} />);

    const boxes = screen.getAllByRole('checkbox');
    await user.click(boxes[10]); // disabled, must not fire
    expect(onChange).not.toHaveBeenCalled();
  });

  it('still allows unchecking a selected destination at the cap', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    const selected = Array.from({ length: 10 }, (_, i) => `dest-${i}`);
    render(<DestinationSelector value={selected} onChange={onChange} />);

    const boxes = screen.getAllByRole('checkbox');
    await user.click(boxes[0]);
    expect(onChange).toHaveBeenCalledWith(selected.filter((id) => id !== 'dest-0'));
  });
});
