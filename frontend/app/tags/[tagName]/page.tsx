
import { getAllPosts } from '@/services/postService';
import PostCard from '@/components/common/PostCard';
import Link from 'next/link';

// This Server Component fetches and displays posts for a specific tag
export default async function PostsByTagPage({
  params,
}: {
  params: { tagName: string };
}) {
  // The tagName from the URL is automatically decoded
  const tagName = decodeURIComponent(params.tagName);
  const { items: posts } = await getAllPosts(10, 0, tagName);

  // console.log(posts)
  return (
    <main className="mx-auto max-w-5xl p-8 font-sans">
      <h1 className="mb-8 text-center text-4xl font-bold text-text">
        Posts tagged with "{tagName}"
      </h1>
      {posts.length > 0 ? (
        <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
          {posts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      ) : (
        <p className="text-center text-text-light">
          No posts found with this tag.
        </p>
      )}
    </main>
  );
}