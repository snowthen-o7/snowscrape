/**
 * Job Card Component (Refactored)
 * Displays a job with actions using modern design system
 */

'use client';

import { useState } from 'react';
import { JobCardProps } from '@/lib/types';
import { capitalize, getNextRunTime } from '@/lib/utils';
import {
  Eye,
  Download,
  FileSearch,
  Trash2,
  PauseCircle,
  PlayCircle,
  MoreVertical,
} from 'lucide-react';
import { Card, CardContent } from '@snowforge/ui';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator, DropdownMenuLabel } from '@snowforge/ui';
import { StatusBadge } from '@/components/StatusBadge';
import { ConfirmDialog } from '@snowforge/ui';

export function JobCard({
  job,
  onClick,
  onPause,
  onResume,
  onDelete,
  onDownload,
  onPreview,
}: JobCardProps) {
  const nextRunTime = getNextRunTime(job.scheduling, job.status);
  const hasResults = job.results_s3_key || job.last_run;
  const [showFormatMenu, setShowFormatMenu] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const exportFormats = [
    { value: 'json', label: 'JSON', description: 'JavaScript Object Notation' },
    { value: 'csv', label: 'CSV', description: 'Comma-Separated Values' },
    {
      value: 'xlsx',
      label: 'Excel (XLSX)',
      description: 'Microsoft Excel format',
    },
    {
      value: 'parquet',
      label: 'Parquet',
      description: 'Apache Parquet (analytics)',
    },
    { value: 'sql', label: 'SQL', description: 'SQL INSERT statements' },
  ];

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await onDelete();
      setDeleteDialogOpen(false);
    } catch (error) {
      // Error is handled by the parent
    } finally {
      setIsDeleting(false);
    }
  };

  const isPaused = job.status === 'paused';

  return (
    <>
      <Card
        className="group transition-all hover:shadow-lg hover:border-accent/50 cursor-pointer"
        onClick={onClick}
      >
        <CardContent className="p-6">
          {/* Header */}
          <div className="mb-4 flex items-start justify-between">
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-foreground group-hover:text-accent-foreground transition-colors">
                {job.name}
              </h3>
              <p className="mt-1 text-sm text-muted-foreground">
                {job.link_count} link{job.link_count !== 1 ? 's' : ''}
              </p>
            </div>
            <StatusBadge status={job.status as any} size="md" />
          </div>

          {/* Info */}
          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2 text-muted-foreground">
              <span className="font-medium">Next Run:</span>
              <span>{nextRunTime}</span>
            </div>
            {job.last_run && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <span className="font-medium">Last Run:</span>
                <span>{new Date(job.last_run).toLocaleString()}</span>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="mt-4 flex items-center gap-2 border-t pt-4">
            <Button
              size="sm"
              variant="outline"
              onClick={(e) => {
                e.stopPropagation();
                onClick();
              }}
            >
              <Eye className="mr-2 h-4 w-4" />
              Details
            </Button>

            {hasResults && onPreview && (
              <Button
                size="sm"
                variant="outline"
                onClick={(e) => {
                  e.stopPropagation();
                  onPreview();
                }}
              >
                <FileSearch className="mr-2 h-4 w-4" />
                Preview
              </Button>
            )}

            {/* More actions dropdown */}
            <DropdownMenu open={showFormatMenu} onOpenChange={setShowFormatMenu}>
              <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                <Button size="sm" variant="ghost" className="ml-auto">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                {/* Pause/Resume */}
                <DropdownMenuItem
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowFormatMenu(false);
                    if (isPaused && onResume) {
                      onResume();
                    } else if (onPause) {
                      onPause();
                    }
                  }}
                >
                  {isPaused ? (
                    <>
                      <PlayCircle className="mr-2 h-4 w-4" />
                      Resume Job
                    </>
                  ) : (
                    <>
                      <PauseCircle className="mr-2 h-4 w-4" />
                      Pause Job
                    </>
                  )}
                </DropdownMenuItem>

                {/* Download results */}
                {hasResults && onDownload && (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuLabel>Download Results</DropdownMenuLabel>
                    {exportFormats.map((format) => (
                      <DropdownMenuItem
                        key={format.value}
                        onClick={(e) => {
                          e.stopPropagation();
                          setShowFormatMenu(false);
                          onDownload(format.value);
                        }}
                      >
                        <Download className="mr-2 h-4 w-4" />
                        <div>
                          <div className="font-medium">{format.label}</div>
                          <div className="text-xs text-muted-foreground">
                            {format.description}
                          </div>
                        </div>
                      </DropdownMenuItem>
                    ))}
                  </>
                )}

                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowFormatMenu(false);
                    setDeleteDialogOpen(true);
                  }}
                  className="text-destructive focus:text-destructive"
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete Job
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </CardContent>
      </Card>

      {/* Delete confirmation dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        onConfirm={handleDelete}
        title="Delete Job"
        description={`Are you sure you want to delete "${job.name}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        loading={isDeleting}
      />
    </>
  );
}
