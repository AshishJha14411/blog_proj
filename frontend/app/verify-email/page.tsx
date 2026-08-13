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
        setMessage(error instanceof Error ? error.message : 'An error occurred. The link may be invalid or expired.');
      }
    };

    // 3. Call the verification function
    verify();
  }, [searchParams, router]); // This effect runs once when the component mounts

  // Helper to determine the color of the title text based on the status
  const getStatusColor = () => {
    if (status === 'success') return 'text-emerald-600 dark:text-emerald-400';
    if (status === 'error') return 'text-red-500';
    return 'text-text'; // Use the default theme color
  };

  return (
    <div className="text-center">
      <h1 className={`mb-4 font-display text-2xl font-bold ${getStatusColor()}`}>
        {status === 'loading' && 'Verifying Your Email...'}
        {status === 'success' && 'Verification Successful!'}
        {status === 'error' && 'Verification Failed'}
      </h1>
      <p className="text-sm leading-relaxed text-text-light">{message}</p>

      {status === 'success' && (
        <p className="mt-4 text-sm text-text-subtle">
          You will be redirected to the login page shortly...
        </p>
      )}

      {/* Show a manual link to login in case the redirect fails or for immediate action */}
      {status !== 'loading' && (
         <Link href="/login" className="mt-8 inline-block rounded-full bg-primary px-6 py-2.5 text-sm font-semibold text-on-primary shadow-soft transition-colors hover:bg-primary-light">
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
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-background p-4">
      <div aria-hidden="true" className="aurora" />
      <div
        aria-hidden="true"
        className="bg-dots mask-radial pointer-events-none absolute inset-0 opacity-60"
      />
      <div className="relative w-full max-w-md rounded-2xl border border-border-soft bg-surface/90 p-8 shadow-lift backdrop-blur-sm">
        <Suspense fallback={<div className="text-center text-text-light">Loading...</div>}>
          <VerificationProcessor />
        </Suspense>
      </div>
    </div>
  );
}

