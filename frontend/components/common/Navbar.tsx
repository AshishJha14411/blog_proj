// components/common/Navbar.tsx
"use client"
import Link from "next/link";
import logo from "../../public/Logo.png"

import { useHydratedAuth } from '@/hooks/useHydratedAuth';
import { logoutUser } from "@/services/authService";
import { useAuthStore } from "@/stores/authStore";
import { useRouter } from "next/navigation";
export default function Navbar() {
  const { isAuthenticated, isHydrated } = useHydratedAuth();
  const logout = useAuthStore((state) => state.logout)
  const router = useRouter()
  const handleLogout = async () => {
    try {
      await logoutUser(); 
    } catch (error) {
      console.error("Logout failed on server, proceeding with client-side logout.", error);
    } finally {
      logout(); 

      useAuthStore.persist.clearStorage();

      router.push('/'); 
    }
  };
  if (!isHydrated) {
    return null; // or a loading skeleton
  }
  return (
    <header className="sticky top-0 bg-primary p-2 shadow-md backdrop-blur-sm">
      <nav className="px-4 flex w-full justify-between">
        <Link href="/" className="text-xl font-bold text-primary">
          <img src="/Logo.png" alt="nav logo" className="h-[2rem] w-[5rem]" />
        </Link>
        <div className="flex items-center gap-4">
          <Link href="/" className="text-text hover:text-white">Home</Link>
          <Link href="/posts" className="text-text hover:text-white">Blogs</Link>
          {isAuthenticated ? <div className="">
            <Link href="/posts/create" className="rounded-md px-4 py-2 mx-1  bg-secondary text-black hover:bg-text hover:text-white transition-colors ease-in delay-60">Create Post</Link>

            <Link href="/bookmarks" className="rounded-md px-4 py-2 mx-1  bg-secondary text-black hover:bg-text hover:text-white transition-colors ease-in delay-60">Bookmarked</Link>
            <Link href="/profile" className="rounded-md px-4 py-2 mx-1  bg-secondary text-black hover:bg-text hover:text-white transition-colors ease-in delay-60">Profile</Link>
            <Link href="/" className="rounded-md px-4 py-2 mx-1 bg-secondary text-black hover:bg-text hover:text-white transition-colors ease-in delay-60" onClick={handleLogout}>Log Out</Link>
          </div> : <div>

            <Link href="/login" className="rounded-md  px-4 py-2 mx-1 bg-secondary text-black hover:bg-text hover:text-white transition-colors ease-in delay-60" >Login</Link>
            <Link href="/signup" className="rounded-md px-4 py-2 mx-1 bg-secondary text-black hover:bg-text hover:text-white transition-colors ease-in delay-60">Sign Up</Link>
          </div>}
        </div>
      </nav>
    </header>
  );
}