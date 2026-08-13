'use client';

/**
 * Interactive parts of the story page (likes, comments, owner controls).
 * Split out of page.tsx so the page itself can be a SERVER component that
 * exports generateMetadata() for SEO/OG tags. This client component still
 * fetches the full post (for per-viewer like/bookmark flags + owner checks).
 */
import { getPostById, Post } from '@/services/postService';
import React, { useState, useEffect } from 'react';
import PostActions from '@/components/common/PostActions';
import CommentList from '@/components/common/CommentList';
import InteractionButtons from '@/components/common/InteractionButtons';
import RegenerateWithFeedback from '@/components/story/RegenrateWithFeedback';
import PublishControls from '@/components/story/PublishControls';
import Avatar from '@/components/ui/Avatar';
import Badge from '@/components/ui/Badge';
import DOMPurify from 'isomorphic-dompurify';
import Link from 'next/link';
import { useHydratedAuth } from '@/hooks/useHydratedAuth';
import AdSlot from '@/components/ads/AdSlot';

/** ~200 wpm on the text content, rounded up. Cheap, and readers use it. */
function readingMinutes(html: string | undefined | null): number {
  if (!html) return 1;
  const words = html.replace(/<[^>]+>/g, ' ').trim().split(/\s+/).length;
  return Math.max(1, Math.round(words / 200));
}

export default function StoryDetailClient({ postId }: { postId: string }) {
  const [post, setPost] = useState<Post | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { user, isAuthenticated, isHydrated } = useHydratedAuth();

  useEffect(() => {
    if (!postId) return;
    let cancelled = false;
    (async () => {
      try {
        const postData = await getPostById(postId);
        if (!cancelled) setPost(postData);
      } catch {
        if (!cancelled) setError('Story not found or you do not have permission to view it.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [postId]);

  const canModify =
    isHydrated &&
    isAuthenticated && post !== null &&
    (
      user?.id === post.user?.id ||
      ['moderator', 'superadmin'].includes(user?.role?.name ?? '')
    );

  if (loading) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-14">
        <div className="skeleton h-4 w-24" />
        <div className="skeleton mt-6 h-10 w-4/5" />
        <div className="skeleton mt-3 h-10 w-3/5" />
        <div className="skeleton mt-8 h-4 w-40" />
        <div className="mt-10 space-y-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="skeleton h-4" style={{ width: `${92 - (i % 3) * 12}%` }} />
          ))}
        </div>
      </main>
    );
  }
  if (error) {
    return (
      <main className="mx-auto max-w-lg px-6 py-24 text-center">
        <p className="font-display text-2xl font-bold text-text">Story not found</p>
        <p className="mt-3 text-sm text-text-light">{error}</p>
        <Link
          href="/userStory"
          className="mt-8 inline-flex rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-on-primary transition-colors hover:bg-primary-light"
        >
          Back to stories
        </Link>
      </main>
    );
  }
  if (!post) return <p className="p-8 text-center">Story not found.</p>;

  return (
    <main className="font-sans">
      {/* Masthead: warm wash behind the title so the article opens on
          something, then the body drops onto the plain page. */}
      <div className="relative overflow-hidden border-b border-border-soft">
        <div aria-hidden="true" className="aurora opacity-60" />
        <div
          aria-hidden="true"
          className="bg-grid mask-fade-b pointer-events-none absolute inset-0"
        />
        <div className="relative mx-auto max-w-3xl px-6 pt-10 pb-12">
          <Link
            href="/userStory"
            className="inline-flex items-center gap-1.5 text-sm text-text-subtle transition-colors hover:text-primary-strong"
          >
            ← All stories
          </Link>

          <div className="mt-6 flex flex-wrap items-center gap-2">
            {post.source === 'ai' && (
              <Badge tone="rose">✦ AI-assisted</Badge>
            )}
            {post.is_flagged && <Badge tone="warning" dot>Under review</Badge>}
            {!post.is_published && <Badge tone="neutral" dot>Draft</Badge>}
          </div>

          <h1 className="mt-4 font-display text-4xl leading-tight font-bold text-text sm:text-5xl">
            {post.title}
          </h1>

          <div className="mt-6 flex flex-wrap items-center gap-x-4 gap-y-3">
            <div className="flex items-center gap-2.5">
              <Avatar name={post.user?.username} size="md" />
              <div>
                <p className="text-sm font-semibold text-text">
                  {post.user?.username ?? 'Unknown'}
                </p>
                <p className="text-xs text-text-subtle">
                  {new Date(post.created_at).toLocaleDateString(undefined, {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}
                  <span className="mx-1.5">·</span>
                  {readingMinutes(post.content)} min read
                </p>
              </div>
            </div>
            <div className="ml-auto">
              <PostActions
                postAuthorId={post.user?.id ?? ''}
                postId={post.id}
                isAI={post.source === 'ai'}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-3xl px-6 py-12">
        <AdSlot className="mb-10" />

        <article>
          {post.cover_image_url && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={post.cover_image_url}
              alt=""
              className="mb-10 w-full rounded-2xl border border-border-soft object-cover"
            />
          )}

          <div
            className="prose-story"
            dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(post.content || '') }}
          />

          {(post.tags ?? []).length > 0 && (
            <div className="mt-10 flex flex-wrap gap-2 border-t border-border-soft pt-8">
              {(post.tags ?? []).map((tag) => (
                <Link
                  href={`/tags/${tag.name}`}
                  key={tag.id}
                  className="rounded-full border border-primary/25 bg-primary/10 px-3 py-1 text-sm font-medium text-primary-strong transition-colors hover:bg-primary hover:text-on-primary"
                >
                  #{tag.name}
                </Link>
              ))}
            </div>
          )}
        </article>

        {post.source === 'ai' && (
          <div className="mt-8 rounded-2xl border border-border-soft bg-surface-muted/60 px-4 py-3 text-sm text-text-light">
            <span className="font-medium text-text">Generated by AI</span> · version{' '}
            {post.version ?? 1}
            <span className="mx-1.5">·</span>
            Genre: {post.genre || '—'}
            <span className="mx-1.5">·</span>
            Tone: {post.tone || '—'}
            <span className="mx-1.5">·</span>
            Length: {post.length_label || '—'}
          </div>
        )}

        {canModify && <PublishControls postId={post.id} isPublished={post.is_published} />}
        {post.source === 'ai' && canModify && (
          <div className="mt-8">
            <RegenerateWithFeedback postId={post.id} />
          </div>
        )}

        <div className="mt-10 flex flex-wrap items-center justify-between gap-4 border-t border-border-soft pt-8">
          <InteractionButtons
            postId={post.id}
            initialLiked={post.is_liked_by_user}
            initialBookmarked={post.is_bookmarked_by_user}
          />
          {!isAuthenticated && isHydrated && (
            <p className="text-sm text-text-subtle">
              <Link href="/login" className="font-medium text-primary-strong hover:underline">
                Log in
              </Link>{' '}
              to like, save and comment.
            </p>
          )}
        </div>

        <AdSlot className="my-10" />

        <CommentList postId={postId} />
      </div>
    </main>
  );
}
