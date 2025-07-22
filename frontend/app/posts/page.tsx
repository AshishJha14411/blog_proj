
import { getAllPosts } from '@/services/postService';
import PostCard from '@/components/common/PostCard';
import Link from 'next/link';

// This is a Server Component that fetches data
export default async function AllPostsPage({
  searchParams,
}: {
  searchParams?: { [key: string]: string | string[] | undefined };
}) {
  const limit = 10;
  const page = Number(searchParams?.page) || 1;
  const offset = (page - 1) * limit;

  const { total, items: posts } = await getAllPosts(limit, offset);

  const totalPages = Math.ceil(total / limit);

  return (
    <main className="mx-auto max-w-5xl p-8 font-sans">
      <h1 className="mb-8 text-center text-4xl font-bold text-text">
        All Articles
      </h1>

      {posts.length > 0 ? (
        <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
          {posts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      ) : (
        <p className="text-center text-text-light">No posts found.</p>
      )}

      {/* Pagination Controls */}
      <div className="mt-12 flex justify-center gap-4">
        {page > 1 && (
          <Link href={`/posts?page=${page - 1}`} className="rounded-md bg-primary px-4 py-2 text-white">
            Previous
          </Link>
        )}
        {page < totalPages && (
          <Link href={`/posts?page=${page + 1}`} className="rounded-md bg-primary px-4 py-2 text-white">
            Next
          </Link>
        )}
      </div>
    </main>
  );
}
