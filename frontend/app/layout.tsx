
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/common/Navbar";
import Footer from "@/components/common/Footer";
import { AuthInitializer } from "@/services/authInitializer";
import { GoogleOAuthProvider } from "@react-oauth/google";
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
// const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

// if (!googleClientId) {
//   console.error("FATAL: NEXT_PUBLIC_GOOGLE_CLIENT_ID is not defined in .env.local");
//   // You could render an error page here in a real app
// }
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
        {/* <GoogleOAuthProvider clientId={googleClientId!}> */}
          <AuthInitializer />
          <Navbar />
          {children}
          <Footer />
        {/* </GoogleOAuthProvider> */}
      </body>
    </html>
  );
}
