import Link from 'next/link';

import Avatar from '@/components/ui/Avatar';
import Badge from '@/components/ui/Badge';
import Card from '@/components/ui/Card';
import { Post } from '@/services/postService';

interface PostCardProps {
  post: Post;
  /**
   * Show like/comment counts. Off by default: the list endpoints don't compute
   * them, so rendering zeros everywhere would state something false. Only
   * `/stories/popular` populates these, and that's the one place the numbers
   * are the reason the card is on screen.
   */
  showEngagement?: boolean;
}

/**
 * Story content is HTML. The old card dropped it straight into the excerpt, so
 * AI-generated stories (which always come back wrapped in markup) previewed as
 * "<p>Once upon a…". Strip to text for the teaser; the full markup is rendered
 * properly, and sanitised, on the story page.
 */
function toExcerpt(html: string | undefined | null): string {
  if (!html) return '';
  return html
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, ' ')
    .trim();
}

export default function PostCard({ post, showEngagement = false }: PostCardProps) {
  // --- Conditional Logic for Status ---
  const status = post.is_flagged
    ? { text: 'Under Review', tone: 'warning' as const, ring: 'border-amber-400/50' }
    : !post.is_published
      ? { text: 'Draft', tone: 'neutral' as const, ring: 'border-border-strong' }
      : null;

  return (
    <Link href={`/userStory/${post.id}`} className="group block h-full">
      <Card
        as="article"
        spotlight
        interactive
        className={`flex h-full flex-col p-6 ${status ? status.ring : ''}`}
      >
        <div className="mb-3 flex items-start justify-between gap-3">
          <h3 className="font-display text-xl leading-snug font-bold text-text transition-colors duration-200 group-hover:text-primary-strong">
            {post.title}
          </h3>
          {status && (
            <Badge tone={status.tone} dot className="mt-0.5 shrink-0">
              {status.text}
            </Badge>
          )}
        </div>

        <p className="mb-5 line-clamp-3 text-sm leading-relaxed text-text-light">
          {toExcerpt(post.content)}
        </p>

        {(post.tags ?? []).length > 0 && (
          <div className="mb-5 flex flex-wrap gap-1.5">
            {(post.tags ?? []).slice(0, 3).map((tag) => (
              <span
                key={tag.id}
                className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary-strong"
              >
                {tag.name}
              </span>
            ))}
            {(post.tags ?? []).length > 3 && (
              <span className="px-1 py-0.5 text-xs text-text-subtle">
                +{(post.tags ?? []).length - 3}
              </span>
            )}
          </div>
        )}

        {/* mt-auto pins the byline to the bottom, so cards in a row line up
            along their footer no matter how long the excerpt runs. */}
        <div className="mt-auto flex items-center gap-2.5 border-t border-border-soft pt-4">
          {/* UserSummary (what list endpoints embed) carries id + username only,
              so the monogram fallback is the avatar here by design. */}
          <Avatar name={post.user?.username} size="sm" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-text">
              {post.user?.username ?? 'Unknown'}
            </p>
            <p className="text-xs text-text-subtle">
              {new Date(post.created_at).toLocaleDateString(undefined, {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
              })}
            </p>
          </div>

          {showEngagement ? (
            <div className="flex items-center gap-3 text-xs text-text-subtle">
              <span title={`${post.likes_count ?? 0} likes`} className="flex items-center gap-1">
                <svg
                  aria-hidden="true"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  className="h-3.5 w-3.5 text-primary"
                >
                  <path d="M12 21s-6.7-4.35-9.33-8.06C.86 10.3 1.6 6.9 4.3 5.6c1.9-.9 4.2-.3 5.5 1.4L12 9.3l2.2-2.3c1.3-1.7 3.6-2.3 5.5-1.4 2.7 1.3 3.44 4.7 1.63 7.34C18.7 16.65 12 21 12 21Z" />
                </svg>
                {post.likes_count ?? 0}
              </span>
              {(post.comments_count ?? 0) > 0 && (
                <span
                  title={`${post.comments_count} comments`}
                  className="flex items-center gap-1"
                >
                  <svg
                    aria-hidden="true"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={2}
                    strokeLinejoin="round"
                    className="h-3.5 w-3.5"
                  >
                    <path d="M21 12a8 8 0 0 1-11.6 7.1L3 21l1.9-6.4A8 8 0 1 1 21 12Z" />
                  </svg>
                  {post.comments_count}
                </span>
              )}
            </div>
          ) : (
            <span
              aria-hidden="true"
              className="translate-x-1 text-primary opacity-0 transition-all duration-300 group-hover:translate-x-0 group-hover:opacity-100"
            >
              →
            </span>
          )}
        </div>
      </Card>
    </Link>
  );
}
