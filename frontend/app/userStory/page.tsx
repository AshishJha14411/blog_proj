import { getAllPosts } from '@/services/postService';
import PostCard from '@/components/common/PostCard';
import Link from 'next/link';
import nextDynamic from 'next/dynamic';
import React from 'react';
export const dynamic = 'force-dynamic';
// Client-only AdSlot inside a Server Component
const AdSlot = nextDynamic(() => import('@/components/ads/AdSlot'), { ssr: true });

export default async function AllPostsPage({ searchParams }: { searchParams?: Record<string, string | string[] | undefined> }) {
  const limit = 10;
  const page = Number(searchParams?.page) || 1;
  const offset = (page - 1) * limit;

  const { total, items: posts } = await getAllPosts(limit, offset);
  const totalPages = Math.ceil(total / limit);

  return (
    <main className="mx-auto max-w-5xl p-8 font-sans">
      <h1 className="mb-8 text-center text-4xl font-bold text-text">All Articles</h1>

      {/* Banner ad above grid */}
      <div className="mb-6">
        <AdSlot />
      </div>

      {posts.length > 0 ? (
        <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
          {posts.map((post, idx) => (
            <React.Fragment key={post.id}>
              <PostCard post={post} />
              {/* Insert an ad every 6 cards */}
              {((idx + 1) % 6 === 0) && (
                <div className="md:col-span-2 lg:col-span-3">
                  <AdSlot />
                </div>
              )}
            </React.Fragment>
          ))}
        </div>
      ) : (
        <p className="text-center text-text-light">No posts found.</p>
      )}

      {/* Pagination */}
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

      {/* Footer banner */}
      <div className="mt-10">
        <AdSlot />
      </div>
    </main>
  );
}
