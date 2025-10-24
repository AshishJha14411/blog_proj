'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { verifyUserEmail } from '@/services/authService';
import Link from 'next/link';

// This is a smaller "client component" that contains all the logic.
// It's wrapped in a <Suspense> boundary because useSearchParams() requires it.
function VerificationProcessor() {
  const searchParams = useSearchParams();
  const router = useRouter();
  
  // State to manage the UI: loading, success, or error
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('Verifying your email, please wait...');

  useEffect(() => {
    // 1. Get the token from the URL (e.g., ?token=...)
    const token = searchParams.get('token');

    if (!token) {
      setStatus('error');
      setMessage('Verification token not found. Please check the link from your email.');
      return;
    }

    // 2. Define an async function to call our API service
    const verify = async () => {
      try {
        // Call the function from authService.ts
        const response = await verifyUserEmail(token);
        
        // On success, update the UI
        setStatus('success');
        setMessage(response.message || 'Your email has been successfully verified!');
        
        // Optional: Automatically redirect the user to the login page after 3 seconds
        setTimeout(() => {
          router.push('/login');
        }, 3000);

      } catch (error) {
        // On failure, update the UI with the error message
        setStatus('error');
        setMessage(error.message || 'An error occurred. The link may be invalid or expired.');
      }
    };

    // 3. Call the verification function
    verify();
  }, [searchParams, router]); // This effect runs once when the component mounts

  // Helper to determine the color of the title text based on the status
  const getStatusColor = () => {
    if (status === 'success') return 'text-green-500';
    if (status === 'error') return 'text-red-500';
    return 'text-[var(--text-body)]'; // Use the default theme color
  };

  return (
    <div className="text-center">
      <h1 className={`text-2xl font-bold mb-4 ${getStatusColor()}`}>
        {status === 'loading' && 'Verifying Your Email...'}
        {status === 'success' && 'Verification Successful!'}
        {status === 'error' && 'Verification Failed'}
      </h1>
      <p className="text-[var(--text-subtle)]">{message}</p>
      
      {status === 'success' && (
        <p className="mt-4 text-sm text-[var(--text-subtle)]">
          You will be redirected to the login page shortly...
        </p>
      )}

      {/* Show a manual link to login in case the redirect fails or for immediate action */}
      {status !== 'loading' && (
         <Link href="/login" className="mt-6 inline-block rounded-md bg-[var(--accent-primary)] px-6 py-2 text-sm font-semibold text-white shadow-sm hover:bg-[var(--accent-primary-light)] transition-colors">
            Proceed to Login
        </Link>
      )}
    </div>
  );
}


// This is the main page component that Next.js will render.
// It sets up the overall page layout and includes the Suspense boundary
// which is required for components that use `useSearchParams`.
export default function VerifyEmailPage() {
  return (
    <div className="min-h-screen flex flex-col justify-center items-center bg-[var(--page-background)] p-4">
      <div className="w-full max-w-md p-8 bg-[var(--ui-background)] rounded-lg shadow-md border border-[var(--border-color)]">
        <Suspense fallback={<div className="text-center">Loading...</div>}>
          <VerificationProcessor />
        </Suspense>
      </div>
    </div>
  );
}

