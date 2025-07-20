// components/common/Navbar.tsx
"use client"
import Link from "next/link";
import logo from "../../public/Logo.png"

import { useHydratedAuth } from '@/hooks/useHydratedAuth';
export default function Navbar() {
      const { isAuthenticated, isHydrated } = useHydratedAuth();

  // Don't render auth-dependent UI until hydration is complete
  if (!isHydrated) {
    return null; // or a loading skeleton
  }
  return (
    <header className="sticky top-0 bg-primary p-2 shadow-md backdrop-blur-sm">
      <nav className="px-4 flex w-full justify-between">
        <Link href="/" className="text-xl font-bold text-primary">
          <img src="/Logo.png" alt="nav logo" className="h-[2rem] w-[5rem]"/>
        </Link>
        <div className="flex items-center gap-4">
          <Link href="/" className="text-text hover:text-white">Home</Link>
          <Link href="/about" className="text-text hover:text-white">Blogs</Link>
          {isAuthenticated? <div>
            
          <Link href="/signup" className="rounded-md px-4 py-2  bg-secondary text-black hover:bg-text hover:text-white transition-colors ease-in delay-60">Log Out</Link></div>:  <div>

          <Link href="/login" className="rounded-md  px-4 py-2 bg-secondary text-black hover:bg-text hover:text-white transition-colors ease-in delay-60">Login</Link>
          <Link href="/signup" className="rounded-md px-4 py-2  bg-secondary text-black hover:bg-text hover:text-white transition-colors ease-in delay-60">Sign Up</Link>
          </div> }
        </div>
      </nav>
    </header>
  );
}