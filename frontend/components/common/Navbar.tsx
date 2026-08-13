"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import NotificationsBell from "./NotificationsBell";
import ThemeToggle from "@/components/theme/ThemeToggle";
import Avatar from "@/components/ui/Avatar";
import { useAuth } from "@/hooks/useAuth"; // Using our safe, definitive auth hook
import { cn } from "@/lib/cn";
import { logoutUser, requestCreatorAccess } from "@/services/authService";
import { useAuthStore } from "@/stores/authStore";

/** Links everyone sees, in the bar itself. */
const PRIMARY_LINKS = [
  { href: "/", label: "Home" },
  { href: "/userStory", label: "Stories" },
  { href: "/tags", label: "Tags" },
];

export default function Navbar() {
  const { user, isAuthenticated, accessToken, isHydrated } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const [requestStatus, setRequestStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [requestMessage, setRequestMessage] = useState('');
  const [moreOpen, setMoreOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);

  const role = user?.role?.name;
  const isCreator = isAuthenticated && role !== 'user';
  const isMod = role === 'moderator' || role === 'superadmin';

  // Any navigation should leave the menus behind — otherwise the panel hangs
  // over the page you just moved to.
  useEffect(() => {
    setMoreOpen(false);
    setMobileOpen(false);
  }, [pathname]);

  // Click-outside / Escape, same contract as the notifications dropdown.
  useEffect(() => {
    if (!moreOpen) return;
    const onPointerDown = (e: MouseEvent) => {
      if (moreRef.current && !moreRef.current.contains(e.target as Node)) {
        setMoreOpen(false);
      }
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMoreOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [moreOpen]);

  const handleLogout = async () => {
    try {
        await logoutUser();
    } catch (error) {
      console.error("Server-side logout failed, proceeding with client-side cleanup.", error);
    }
    useAuthStore.getState().logout();
    router.push('/');
    // A full page reload can sometimes help ensure all state is cleared.
    window.location.href = '/';
  };

  const handleCreatorRequest = async () => {
    if (!accessToken) return;

    setRequestStatus('loading');
    setRequestMessage('');
    try {
      // We pass an empty reason as requested
      await requestCreatorAccess('', accessToken);
      setRequestStatus('success');
      setRequestMessage('Request Submitted!');
    } catch (error) {
      setRequestStatus('error');
      setRequestMessage(error instanceof Error ? error.message : 'Failed to submit request.');
    }
  };

  // The safety gate to prevent hydration errors
  if (!isHydrated) {
    return null;
  }

  /**
   * Secondary destinations. These used to sit in the bar as a flat row of up to
   * ten links, which overflowed the moment a superadmin logged in. Profile and
   * Log Out deliberately stay *outside* this menu and visible at all times —
   * they're the two controls a signed-in user reaches for without thinking.
   */
  const moreLinks: { href: string; label: string }[] = [
    ...(isCreator
      ? [
          { href: '/userStory/create', label: 'Create Story' },
          { href: '/stories/generate', label: 'Generate Story' },
          { href: '/myposts', label: 'My Stories' },
        ]
      : []),
    { href: '/bookmarks', label: 'Bookmarks' },
    { href: '/notifications', label: 'Notifications' },
    ...(isMod
      ? [
          { href: '/admin/mod/queue', label: 'Mod Queue' },
          { href: '/admin/analytics', label: 'Analytics' },
        ]
      : []),
    ...(role === 'superadmin'
      ? [
          { href: '/admin/requests', label: 'Creator Requests' },
          { href: '/admin/ads', label: 'Ads' },
        ]
      : []),
  ];

  const navLinkClass = (href: string) =>
    cn(
      'rounded-full px-3.5 py-2 text-sm font-medium transition-colors duration-200',
      pathname === href
        ? 'bg-white/12 text-on-dark'
        : 'text-on-dark/70 hover:bg-white/8 hover:text-on-dark',
    );

  return (
    <header className="sticky top-0 z-50">
      {/*
        The espresso bar stays espresso in both themes — it is the frame the
        logo was chosen against. Dark mode only deepens it, so the brand reads
        the same at 2pm and at midnight.
      */}
      <div className="relative border-b border-white/10 bg-[var(--nav-bg)] backdrop-blur-xl backdrop-saturate-150">
        {/* Hairline of rose along the bottom edge — the one bit of colour on
            an otherwise monochrome bar. */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent"
        />
        <nav className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-2.5 sm:px-6">
          <Link href="/" className="group flex shrink-0 items-center gap-2.5">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/Logo.png"
              alt="nav logo"
              className="h-11 w-11 rounded-xl transition-transform duration-300 group-hover:scale-105"
            />
            <span className="hidden font-display text-lg font-semibold tracking-tight text-on-dark sm:block">
              Quill &amp; Code
            </span>
          </Link>

          {/* Desktop primary nav. `md` and not `lg` on purpose: the bar has to
              be usable — and testable — at a 1000px viewport. */}
          <div className="hidden items-center gap-1 md:flex">
            {PRIMARY_LINKS.map((l) => (
              <Link key={l.href} href={l.href} className={navLinkClass(l.href)}>
                {l.label}
              </Link>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <ThemeToggle />

            {isAuthenticated ? (
              <>
                <NotificationsBell />

                {isCreator && (
                  <Link
                    href="/userStory/create"
                    className="hidden rounded-full bg-primary px-4 py-2 text-sm font-semibold text-on-primary transition-all hover:bg-primary-light hover:shadow-[0_0_24px_-6px_var(--glow-color)] lg:inline-flex"
                  >
                    Write
                  </Link>
                )}

                {/* "More" menu — everything that isn't Profile or Log Out.
                    The panel stays mounted and hides with `visibility` so the
                    open/close transition can animate; visibility:hidden already
                    removes it from the tab order and the a11y tree. */}
                <div className="relative hidden md:block" ref={moreRef}>
                  <button
                    type="button"
                    onClick={() => setMoreOpen((s) => !s)}
                    aria-expanded={moreOpen}
                    aria-haspopup="menu"
                    className="inline-flex items-center gap-1.5 rounded-full px-3 py-2 text-sm font-medium text-on-dark/70 transition-colors hover:bg-white/8 hover:text-on-dark"
                  >
                    More
                    <svg
                      aria-hidden="true"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth={2}
                      strokeLinecap="round"
                      className={cn('h-3.5 w-3.5 transition-transform duration-200', moreOpen && 'rotate-180')}
                    >
                      <path d="m6 9 6 6 6-6" />
                    </svg>
                  </button>

                  <div
                    className={cn(
                      'absolute right-0 mt-2 w-56 origin-top-right rounded-2xl border border-border-soft',
                      'bg-surface p-1.5 shadow-lift transition-all duration-200',
                      moreOpen
                        ? 'visible translate-y-0 opacity-100'
                        : 'invisible -translate-y-1 opacity-0',
                    )}
                  >
                    {moreLinks.map((l) => (
                      <Link
                        key={l.href}
                        href={l.href}
                        className="block rounded-lg px-3 py-2 text-sm text-text-light transition-colors hover:bg-primary/10 hover:text-primary-strong"
                      >
                        {l.label}
                      </Link>
                    ))}

                    {role === 'user' && (
                      <div className="mt-1 border-t border-border-soft px-3 pt-2 pb-1">
                        {requestStatus === 'success' ? (
                          <span className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">
                            {requestMessage}
                          </span>
                        ) : (
                          <>
                            <button
                              onClick={handleCreatorRequest}
                              className="text-sm font-medium text-primary-strong transition-colors hover:underline"
                              disabled={requestStatus === 'loading'}
                            >
                              {requestStatus === 'loading' ? 'Submitting...' : 'Become a Creator'}
                            </button>
                            {requestStatus === 'error' && (
                              <span className="ml-2 text-sm text-red-500">{requestMessage}</span>
                            )}
                          </>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                <Link
                  href="/profile"
                  aria-label="Profile"
                  className="hidden items-center gap-2 rounded-full border border-white/10 bg-white/5 py-1 pr-3 pl-1 transition-colors hover:border-primary/40 hover:bg-white/10 md:flex"
                >
                  <Avatar name={user?.username} src={user?.profile_image_url} size="sm" />
                  <span className="max-w-[8rem] truncate text-sm font-medium text-on-dark/85">
                    {user?.username ?? 'Profile'}
                  </span>
                </Link>

                <button
                  onClick={handleLogout}
                  className="hidden rounded-full px-3 py-2 text-sm font-medium text-on-dark/70 transition-colors hover:bg-white/8 hover:text-on-dark md:inline-flex"
                >
                  Log Out
                </button>
              </>
            ) : (
              <div className="hidden items-center gap-2 md:flex">
                <Link
                  href="/login"
                  className="rounded-full px-4 py-2 text-sm font-medium text-on-dark/80 transition-colors hover:bg-white/10 hover:text-on-dark"
                >
                  Login
                </Link>
                <Link
                  href="/signup"
                  className="rounded-full bg-primary px-4 py-2 text-sm font-semibold text-on-primary transition-all hover:bg-primary-light hover:shadow-[0_0_24px_-6px_var(--glow-color)]"
                >
                  Sign Up
                </Link>
              </div>
            )}

            {/* Mobile trigger */}
            <button
              type="button"
              onClick={() => setMobileOpen((s) => !s)}
              aria-expanded={mobileOpen}
              aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
              className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 text-on-dark/80 transition-colors hover:bg-white/10 md:hidden"
            >
              <svg
                aria-hidden="true"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={1.8}
                strokeLinecap="round"
                className="h-[18px] w-[18px]"
              >
                {mobileOpen ? (
                  <path d="M6 6l12 12M18 6L6 18" />
                ) : (
                  <path d="M4 7h16M4 12h16M4 17h16" />
                )}
              </svg>
            </button>
          </div>
        </nav>
      </div>

      {/*
        Mobile sheet. Rendered only while open — on a narrow screen these are
        the *same* destinations as the desktop bar, and leaving a second copy
        permanently in the DOM would mean duplicate matches for anything that
        queries the page by link text.
      */}
      {mobileOpen && (
        <div className="rise-in border-b border-border-soft bg-surface/95 backdrop-blur-xl md:hidden">
          <div className="mx-auto max-w-7xl space-y-1 px-4 py-4 sm:px-6">
            {PRIMARY_LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="block rounded-xl px-3 py-2.5 text-sm font-medium text-text-light transition-colors hover:bg-primary/10 hover:text-primary-strong"
              >
                {l.label}
              </Link>
            ))}

            {isAuthenticated ? (
              <>
                <div className="my-2 border-t border-border-soft" />
                {[{ href: '/profile', label: 'Profile' }, ...moreLinks].map((l) => (
                  <Link
                    key={l.href}
                    href={l.href}
                    className="block rounded-xl px-3 py-2.5 text-sm font-medium text-text-light transition-colors hover:bg-primary/10 hover:text-primary-strong"
                  >
                    {l.label}
                  </Link>
                ))}
                {role === 'user' && requestStatus !== 'success' && (
                  <button
                    onClick={handleCreatorRequest}
                    disabled={requestStatus === 'loading'}
                    className="block w-full rounded-xl px-3 py-2.5 text-left text-sm font-medium text-primary-strong transition-colors hover:bg-primary/10"
                  >
                    {requestStatus === 'loading' ? 'Submitting...' : 'Become a Creator'}
                  </button>
                )}
                <button
                  onClick={handleLogout}
                  className="block w-full rounded-xl px-3 py-2.5 text-left text-sm font-medium text-red-500 transition-colors hover:bg-red-500/10"
                >
                  Log Out
                </button>
              </>
            ) : (
              <div className="flex gap-2 pt-2">
                <Link
                  href="/login"
                  className="flex-1 rounded-full border border-border-soft px-4 py-2.5 text-center text-sm font-medium text-text"
                >
                  Login
                </Link>
                <Link
                  href="/signup"
                  className="flex-1 rounded-full bg-primary px-4 py-2.5 text-center text-sm font-semibold text-on-primary"
                >
                  Sign Up
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
