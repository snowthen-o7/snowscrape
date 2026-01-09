import { Skeleton } from "@/components/ui/skeleton"

export function JobCardSkeleton() {
  return (
    <div className="p-6 bg-gray-800 rounded-lg flex items-center justify-between">
      <div className="flex-1 space-y-3">
        {/* Job name skeleton */}
        <Skeleton className="h-7 w-48" />

        {/* Status and link count skeleton */}
        <div className="space-y-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-32" />
        </div>

        {/* Next run time skeleton */}
        <Skeleton className="h-4 w-40" />
      </div>

      {/* Action buttons skeleton */}
      <div className="flex space-x-2">
        <Skeleton className="h-10 w-10 rounded-md" />
        <Skeleton className="h-10 w-10 rounded-md" />
        <Skeleton className="h-10 w-10 rounded-md" />
      </div>
    </div>
  )
}
