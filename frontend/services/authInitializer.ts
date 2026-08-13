'use client';

import { useEffect, useRef } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { refreshSession } from '@/services/authService';

/**
 * Runs once on app load to bootstrap the in-memory access token from the
 * HttpOnly refresh_token cookie. Since F4, accessToken is not persisted to
 * localStorage — so after a page reload we always start with `accessToken=null`
 * and need to mint a fresh one before the UI can make authenticated calls.
 */
export function AuthInitializer() {
  // A ref keeps this effect from running twice under React strict mode.
  const hasRun = useRef(false);

  useEffect(() => {
    if (hasRun.current) return;
    hasRun.current = true;

    const state = useAuthStore.getState();
    // Nothing persisted → nothing to rehydrate.
    if (!state.isAuthenticated) return;
    // Already have a token in memory (e.g. same tab after login) → skip.
    if (state.accessToken) return;
    // User explicitly logged out; don't immediately re-authenticate.
    if (state.recentlyLoggedOut) return;

    (async () => {
      try {
        const { access_token, refresh_token, user } = await refreshSession();
        useAuthStore.getState().login({
          accessToken: access_token,
          // Store the rotated refresh token so the NEXT reload can refresh too.
          refreshToken: refresh_token,
          user,
        });
      } catch {
        // Refresh token is gone/expired/rejected — treat this session as ended.
        useAuthStore.getState().logout();
      }
    })();
  }, []);

  return null;
}
