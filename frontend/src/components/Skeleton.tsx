/**
 * Skeleton loading components — grey placeholders during data fetch.
 */

export function SkeletonLine({ className = '' }: { className?: string }) {
  return (
    <div className={`animate-pulse rounded-lg bg-stone-200 ${className}`} />
  );
}

export function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl border border-stone-200 px-4 py-3 animate-pulse">
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <SkeletonLine className="h-4 w-2/3 mb-2" />
          <SkeletonLine className="h-3 w-1/3" />
        </div>
        <SkeletonLine className="h-6 w-16 ml-2" />
      </div>
    </div>
  );
}

export function SkeletonDashboard() {
  return (
    <div className="space-y-4">
      {/* Title */}
      <SkeletonLine className="h-6 w-32" />

      {/* Big card */}
      <div className="bg-white rounded-xl border border-stone-200 p-6 text-center animate-pulse">
        <SkeletonLine className="h-3 w-24 mx-auto mb-3" />
        <SkeletonLine className="h-10 w-20 mx-auto mb-2" />
        <SkeletonLine className="h-3 w-16 mx-auto" />
      </div>

      {/* Three counters */}
      <div className="grid grid-cols-3 gap-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-white rounded-xl border border-stone-200 p-3 animate-pulse">
            <SkeletonLine className="h-8 w-8 mx-auto mb-1" />
            <SkeletonLine className="h-3 w-10 mx-auto" />
          </div>
        ))}
      </div>

      {/* List */}
      <SkeletonLine className="h-4 w-40 mt-2" />
      {[1, 2, 3, 4, 5].map((i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}

export function SkeletonList({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}
