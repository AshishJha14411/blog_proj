import type { Metadata } from "next";
import { Fraunces, Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/common/Navbar";
import Footer from "@/components/common/Footer";
import { AuthInitializer } from "@/services/authInitializer";
import ChatWidget from "@/components/support/ChatWidget";
import Providers from "./providers";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// A quill deserves a serif. Used for display headings and story bodies only —
// the UI itself stays on Geist so the chrome reads as an app, not a pamphlet.
const fraunces = Fraunces({
  variable: "--font-display-serif",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Quill & Code",
  description: "Created By Ashish Kr Jha",
};

/**
 * Applies the saved theme before first paint.
 *
 * WHY inline and blocking: React can only set the class after hydration, which
 * is at least one paint too late — the page would flash parchment-white before
 * turning espresso. This runs synchronously in <head>, so the very first paint
 * is already correct. It's also why <html> carries suppressHydrationWarning:
 * the class it adds is invisible to the server render.
 */
const THEME_SCRIPT = `(function(){try{var s=localStorage.getItem('theme');var d=s?s==='dark':window.matchMedia('(prefers-color-scheme: dark)').matches;if(d){document.documentElement.classList.add('dark');}document.documentElement.style.colorScheme=d?'dark':'light';}catch(e){}})();`;

// Google login uses the backend redirect flow (/auth/google/login → cookie →
// /auth/callback → refreshSession()); GoogleOAuthProvider isn't needed.
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} ${fraunces.variable} antialiased`}
      >
        <Providers>
          <AuthInitializer />
          <div className="relative flex min-h-screen flex-col">
            {/* Page-wide texture: a faint warm grid that fades out before it
                reaches the content. Fixed + -z-10 so it never intercepts
                clicks or scrolls with the page. */}
            <div
              aria-hidden="true"
              className="bg-grid mask-fade-b pointer-events-none fixed inset-0 -z-10 h-[60vh] opacity-70"
            />
            <Navbar />
            {/* A div, not a <main>: the pages each render their own <main>,
                and nesting them would put two landmarks on every screen. */}
            <div className="flex-1">{children}</div>
            <Footer />
          </div>
          <ChatWidget />
        </Providers>
      </body>
    </html>
  );
}
