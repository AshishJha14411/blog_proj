"use client"
import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/hooks/useAuth"; // Using our safe, definitive auth hook
import { logoutUser, requestCreatorAccess } from "@/services/authService"; // 1. Import the new service function
import { useAuthStore } from "@/stores/authStore";
import { useRouter } from "next/navigation";
import NotificationsBell from "./NotificationsBell";

export default function Navbar() {
  const { user, isAuthenticated, accessToken, refreshToken, isHydrated } = useAuth();
  const router = useRouter();
  
  // 2. Add state to manage the creator request button's UI
  const [requestStatus, setRequestStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [requestMessage, setRequestMessage] = useState('');

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

  // 3. Create the click handler function for the new button
  const handleCreatorRequest = async () => {
    if (!accessToken) return;

    setRequestStatus('loading');
    setRequestMessage('');
    try {
      // We pass an empty reason as requested
      const response = await requestCreatorAccess('', accessToken);
      setRequestStatus('success');
      setRequestMessage('Request Submitted!');
    } catch (error) {
      setRequestStatus('error');
      setRequestMessage(error.message || 'Failed to submit request.');
    }
  };

  // The safety gate to prevent hydration errors
  if (!isHydrated) {
    return null;
  }

  return (
    <header className="sticky top-0 bg-[var(--nav-background)] p-2 shadow-md">
      <nav className="px-4 flex w-full justify-between items-center">
        <Link href="/">
          <img src="/Logo.png" alt="nav logo" className="h-16 w-16" />
        </Link>
        <div className="flex items-center font-normal text-base">
          <Link href="/" className="mx-2 text-[var(--text-on-dark)] hover:text-[var(--accent-primary)]">Home</Link>
          <Link href="/userStory" className="mx-2 text-[var(--text-on-dark)] hover:text-[var(--accent-primary)]">Stories</Link>
          <Link href="/tags" className="mx-2 text-[var(--text-on-dark)] hover:text-[var(--accent-primary)]">Tags</Link>
          
          {isAuthenticated ? (
            <div className="flex items-center gap-4 ml-4">
              <NotificationsBell />

              {/* --- 4. THE CORE LOGIC: Conditionally render the button --- */}
              {user?.role?.name === 'user' && (
                <div>
                  {/* If the request was successful, just show the message */}
                  {requestStatus === 'success' ? (
                    <span className="text-sm text-green-400 font-semibold">{requestMessage}</span>
                  ) : (
                    <>
                      <button
                        onClick={handleCreatorRequest}
                        className="text-sm text-[var(--text-on-dark)] hover:text-[var(--accent-primary)] transition-colors"
                        disabled={requestStatus === 'loading'}
                      >
                        {requestStatus === 'loading' ? 'Submitting...' : 'Become a Creator'}
                      </button>
                      {requestStatus === 'error' && <span className="ml-2 text-sm text-red-400">{requestMessage}</span>}
                    </>
                  )}
                </div>
              )}

              {/* Show creator-specific links only if the user is a creator or higher */}
              {user?.role?.name !== 'user' && (
                <>
                  <Link href="/userStory/create" className="mx-2 text-[var(--text-on-dark)] hover:text-[var(--accent-primary)]">Create Story</Link>
                  <Link href="/stories/generate" className="mx-2 text-[var(--text-on-dark)] hover:text-[var(--accent-primary)]">Generate Story</Link>

                  <Link href="/myposts" className="mx-2 text-[var(--text-on-dark)] hover:text-[var(--accent-primary)]">My Stories</Link>
                </>
              )}

              <Link href="/bookmarks" className="mx-2 text-[var(--text-on-dark)] hover:text-[var(--accent-primary)]">Bookmarks</Link>
              <Link href="/profile" className="mx-2 text-[var(--text-on-dark)] hover:text-[var(--accent-primary)]">Profile</Link>
              <button onClick={handleLogout} className="ml-2 rounded-md px-3 py-2 text-sm bg-[var(--accent-primary)] text-black hover:bg-[var(--accent-primary-light)] transition-colors">Log Out</button>
            </div>
          ) : (
            <div className="ml-4">
              <Link href="/login" className="rounded-md px-4 py-2 mx-1 bg-[var(--accent-primary)] text-black hover:bg-[var(--accent-primary-light)] transition-colors">Login</Link>
              <Link href="/signup" className="rounded-md px-4 py-2 mx-1 bg-white text-black hover:bg-gray-200 transition-colors">Sign Up</Link>
            </div>
          )}
        </div>
      </nav>
    </header>
  );
}

