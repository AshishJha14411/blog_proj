
import Link from 'next/link';

import { getAllPosts } from '@/services/postService';
import PostCard from '@/components/common/PostCard';
import EmptyState from '@/components/ui/EmptyState';
import PageHeader from '@/components/ui/PageHeader';

// This Server Component fetches and displays posts for a specific tag
export default async function PostsByTagPage({
  params,
}: {
  params: Promise<{ tagName: string }>;
}) {
  // The tagName from the URL is automatically decoded
  const { tagName: rawTagName } = await params;
  const tagName = decodeURIComponent(rawTagName);
  const { items: posts } = await getAllPosts(10, 0, tagName);

  return (
    <main className="mx-auto max-w-6xl px-6 py-14 font-sans">
      <PageHeader
        align="center"
        eyebrow={`#${tagName}`}
        title={`Stories tagged “${tagName}”`}
        description={
          posts.length > 0
            ? `${posts.length} ${posts.length === 1 ? 'story' : 'stories'} under this tag.`
            : undefined
        }
      />

      {posts.length > 0 ? (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {posts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      ) : (
        <EmptyState
          title="No stories found with this tag"
          description="Nothing has been published under this tag yet."
          action={
            <Link
              href="/tags"
              className="rounded-full border border-border-strong px-5 py-2.5 text-sm font-medium text-text transition-colors hover:border-primary/50 hover:text-primary-strong"
            >
              Browse all tags
            </Link>
          }
        />
      )}
    </main>
  );
}
