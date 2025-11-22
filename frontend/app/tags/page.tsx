
export const dynamic = 'force-dynamic';
import { getAllTags } from '@/services/tagService';
import Link from 'next/link';
import React from 'react';

// This is a Server Component that fetches the list of all tags
export default async function AllTagsPage() {
  const { tags } = await getAllTags();

  return (
    <main className="mx-auto max-w-3xl p-8 font-sans">
      <h1 className="mb-8 text-center text-4xl font-bold text-text">
        Browse by Tag
      </h1>
      <div className="flex flex-wrap justify-center gap-4">
        {tags.map((tag) => (
          <Link
            key={tag.id}
            href={`/tags/${tag.name}`}
            className="rounded-full bg-primary/20 px-4 py-2 text-lg font-medium text-primary transition-colors hover:bg-primary hover:text-white"
          >
            {tag.name}
          </Link>
        ))}
      </div>
    </main>
  );
}