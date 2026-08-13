"use client"
import Link from "next/link";

import CreatePostForm from "@/components/common/CreatePostForm";
import EmptyState from "@/components/ui/EmptyState";
import { useAuth } from "@/hooks/useAuth";

export default function CreatePostPage () {
    const { isAuthenticated } = useAuth();

    return (
        <main className="mx-auto max-w-4xl px-6 py-14">
            {isAuthenticated ? (
                <CreatePostForm />
            ) : (
                // Was a bare sentence positioned with mx-[35vw]/mt-[20%], which
                // fell off the screen on anything narrower than a desktop.
                <EmptyState
                    title="You need an account to write"
                    description="Log in to start a new story. It takes a moment, and your drafts stay yours until you publish."
                    action={
                        <Link
                            href="/login"
                            className="rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-on-primary transition-colors hover:bg-primary-light"
                        >
                            Log in to continue
                        </Link>
                    }
                    className="mt-10"
                />
            )}
        </main>
    );
}
