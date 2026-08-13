import { cn } from '@/lib/cn';

const sizes = {
  xs: 'h-6 w-6 text-[10px]',
  sm: 'h-8 w-8 text-xs',
  md: 'h-10 w-10 text-sm',
  lg: 'h-24 w-24 text-2xl',
} as const;

/**
 * Avatar with an initial fallback.
 *
 * Falls back to a rose-tinted monogram rather than a remote placeholder
 * service: no third-party request on every card, and it still renders when
 * the user has no image.
 */
export default function Avatar({
  name,
  src,
  size = 'md',
  className,
}: {
  name?: string | null;
  src?: string | null;
  size?: keyof typeof sizes;
  className?: string;
}) {
  const initial = (name ?? '?').trim().charAt(0).toUpperCase() || '?';

  return src ? (
    // Avatars come from arbitrary user-supplied hosts; next/image would need
    // every one of them allow-listed in next.config.
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={name ? `${name}'s avatar` : 'Avatar'}
      className={cn(
        'shrink-0 rounded-full border border-border-soft object-cover',
        sizes[size],
        className,
      )}
    />
  ) : (
    <span
      aria-hidden="true"
      className={cn(
        'inline-flex shrink-0 items-center justify-center rounded-full',
        'border border-primary/25 bg-primary/15 font-semibold text-primary-strong',
        sizes[size],
        className,
      )}
    >
      {initial}
    </span>
  );
}
