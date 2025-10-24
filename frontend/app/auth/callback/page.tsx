// src/app/auth/callback/page.tsx
'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { refreshSession } from '@/services/authService';
import { useAuthStore } from '@/stores/authStore';

export default function AuthCallback() {
  const router = useRouter();

  useEffect(() => {
    (async () => {
      // 1) Clear any stale token/state from a previous user
      useAuthStore.getState().logout(); // clears accessToken + user

      try {
        // 2) Finalize the session for the *new* Google user (cookie-based)
        const { access_token, user } = await refreshSession();

        // 3) Store X's token and user
        useAuthStore.getState().login({ accessToken: access_token, refreshToken: '', user });

        // 4) Go home
        router.replace('/');
      } catch {
        router.replace('/login?error=oauth');
      }
    })();
  }, [router]);

  return <p className="p-6">Signing you in…</p>;
}
