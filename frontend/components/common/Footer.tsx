// components/common/Footer.tsx
import Link from 'next/link';

/**
 * NOTE: no /profile, /login or /signup links down here on purpose. The e2e
 * suite asserts those hrefs exist *only* in the signed-in / signed-out states,
 * and a footer copy that renders unconditionally would make "not.exist" false
 * on every page. The navbar owns those.
 */
const COLUMNS = [
  {
    heading: 'Read',
    links: [
      { href: '/userStory', label: 'Browse the feed' },
      { href: '/tags', label: 'Browse tags' },
      { href: '/bookmarks', label: 'Your bookmarks' },
    ],
  },
  {
    heading: 'Write',
    links: [
      { href: '/userStory/create', label: 'New story' },
      { href: '/stories/generate', label: 'Write with AI' },
      { href: '/myposts', label: 'Your drafts' },
    ],
  },
  {
    heading: 'Account',
    links: [
      { href: '/notifications', label: 'Notifications' },
      { href: '/change-password', label: 'Password' },
    ],
  },
];

export default function Footer() {
  return (
    <footer className="relative mt-24 border-t border-border-soft bg-surface-muted/40">
      {/* Rose hairline picking up the same gradient as the navbar's bottom edge. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent"
      />
      <div className="mx-auto max-w-7xl px-6 py-14">
        <div className="grid gap-10 md:grid-cols-[1.4fr_repeat(3,1fr)]">
          <div>
            <Link href="/" className="flex items-center gap-2.5">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/Logo.png" alt="" className="h-10 w-10 rounded-xl" />
              <span className="font-display text-lg font-semibold text-text">Quill &amp; Code</span>
            </Link>
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-text-light">
              Write your own stories, or bring an idea and let AI draft it with you — then publish
              it to readers.
            </p>
          </div>

          {COLUMNS.map((col) => (
            <div key={col.heading}>
              <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-text-subtle">
                {col.heading}
              </h3>
              <ul className="space-y-2.5">
                {col.links.map((l) => (
                  <li key={l.href}>
                    <Link
                      href={l.href}
                      className="text-sm text-text-light transition-colors hover:text-primary-strong"
                    >
                      {l.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-center justify-between gap-3 border-t border-border-soft pt-6 sm:flex-row">
          <p className="text-sm text-text-subtle">
            &copy; {new Date().getFullYear()} Pixel Point. All rights reserved.
          </p>
          <p className="text-sm text-text-subtle">
            Built with Next.js &amp; FastAPI — by Ashish Kr Jha
          </p>
        </div>
      </div>
    </footer>
  );
}
