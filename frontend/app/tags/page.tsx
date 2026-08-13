
export const dynamic = 'force-dynamic';
import { getAllTags } from '@/services/tagService';
import EmptyState from '@/components/ui/EmptyState';
import PageHeader from '@/components/ui/PageHeader';
import Link from 'next/link';
import React from 'react';

// This is a Server Component that fetches the list of all tags
export default async function AllTagsPage() {
  const { tags } = await getAllTags();

  return (
    <main className="relative overflow-hidden font-sans">
      <div
        aria-hidden="true"
        className="bg-dots mask-radial pointer-events-none absolute inset-0 opacity-60"
      />
      <div className="relative mx-auto max-w-4xl px-6 py-16">
        <PageHeader
          align="center"
          eyebrow="Discover"
          title="Browse by Tag"
          description="Every subject anyone has written about here."
        />

        {tags.length > 0 ? (
          <div className="flex flex-wrap justify-center gap-3">
            {tags.map((tag) => (
              <Link
                key={tag.id}
                href={`/tags/${tag.name}`}
                className="rounded-full border border-border-soft bg-surface px-5 py-2.5 text-base font-medium text-text shadow-soft transition-all hover:-translate-y-0.5 hover:border-primary/50 hover:bg-primary/10 hover:text-primary-strong"
              >
                {tag.name}
              </Link>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No tags yet"
            description="Tags appear as soon as stories are published with them."
          />
        )}
      </div>
    </main>
  );
}
