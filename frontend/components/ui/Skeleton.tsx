import { cn } from '@/lib/cn';

/** Shimmering placeholder. `.skeleton` carries the animation (globals.css). */
export default function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn('skeleton', className)} />;
}

/** The loading shape of a PostCard grid — same rhythm, so nothing jumps. */
export function CardSkeleton() {
  return (
    <div className="rounded-2xl border border-border-soft bg-surface p-6 shadow-soft">
      <Skeleton className="h-5 w-3/4" />
      <Skeleton className="mt-3 h-3 w-full" />
      <Skeleton className="mt-2 h-3 w-11/12" />
      <Skeleton className="mt-2 h-3 w-2/3" />
      <div className="mt-6 flex gap-2">
        <Skeleton className="h-5 w-16 rounded-full" />
        <Skeleton className="h-5 w-12 rounded-full" />
      </div>
      <Skeleton className="mt-6 h-3 w-1/2" />
    </div>
  );
}

export function CardGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  );
}
