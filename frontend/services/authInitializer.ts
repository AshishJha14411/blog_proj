'use client';

import { useEffect, useRef } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { getMe } from '@/services/authService';

/**
 * A client-side-only component that runs once on app load to validate the user's session.
 */
export function AuthInitializer() {
  // We use a ref to ensure this effect runs only once, even in React's strict mode.
  const hasRun = useRef(false);

  useEffect(() => {
    if (hasRun.current) {
      return;
    }
    hasRun.current = true;

    const validateSession = async () => {
      // 1. Get the current token and user from the store
      const { accessToken, user } = useAuthStore.getState();
      const logout = useAuthStore.getState().logout;

      // 2. If there's a token but no user object, it's a new session. Let's get the user.
      if (accessToken && !user) {
        console.log("Validating session on app load...");
        try {
          // 3. Call the /me endpoint
          const userData = await getMe(accessToken);
          // If successful, update the store with the fresh user data
          useAuthStore.setState({ user: userData });
        } catch (error) {
          // 4. If it fails, we have a "ghost session". Clear it.
          console.error("Session validation failed. Logging out.");
          logout();
        }
      }
    };

    validateSession();
  }, []);

  // This component renders nothing. It's purely for logic.
  return null;
}
