
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
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

export const metadata: Metadata = {
  title: "Quill & Code",
  description: "Created By Ashish Kr Jha",
};

// Google login uses the backend redirect flow (/auth/google/login → cookie →
// /auth/callback → refreshSession()); GoogleOAuthProvider isn't needed.
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <Providers>
          <AuthInitializer />
          <Navbar />
          {children}
          <Footer />
          <ChatWidget />
        </Providers>
      </body>
    </html>
  );
}
