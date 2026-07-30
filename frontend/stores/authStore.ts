// src/stores/authStore.ts
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

interface Role { id: string; name: string }
export interface User {
  id: string;
  username: string;
  email: string;
  role?: Role;
  bio?: string | null;
  profile_image_url?: string | null;
  social_links?: { [key: string]: string } | null;
}

interface AuthState {
  accessToken: string | null;
  // Persisted (see partialize) so cross-site refresh works without relying on
  // a third-party cookie the browser may block. Trade-off vs the F4 design:
  // an XSS script could read this. Accepted for a split-domain deploy.
  refreshToken: string | null;
  user: User | null;
  isAuthenticated: boolean;

  // NEW: logout guard so AuthInitializer won’t immediately refresh after logout
  recentlyLoggedOut: boolean;

  // keep the same signature you already use:
  login: (data: { accessToken: string; refreshToken: string; user: User }) => void;
  logout: () => void;
  setAccessToken: (token: string) => void;
  // Store both after a rotation (refresh returns a fresh refresh token).
  setTokens: (accessToken: string, refreshToken: string) => void;

  // helper to clear the guard (e.g., after a deliberate login flow)
  clearLogoutFlag: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,
      recentlyLoggedOut: false,

      login: (data) =>
        set({
          accessToken: data.accessToken,
          refreshToken: data.refreshToken,
          user: data.user,
          isAuthenticated: true,
          recentlyLoggedOut: false, // reset guard on successful login
        }),

      logout: () =>
        set({
          accessToken: null,
          refreshToken: null,
          user: null,
          isAuthenticated: false,
          recentlyLoggedOut: true, // set guard so AuthInitializer skips refresh
        }),

      setAccessToken: (token) => set({ accessToken: token }),

      setTokens: (accessToken, refreshToken) => set({ accessToken, refreshToken }),

      clearLogoutFlag: () => set({ recentlyLoggedOut: false }),
    }),
    {
      name: 'auth-storage',
      // F4: accessToken is DELIBERATELY excluded from partialize — it stays
      // in memory only. On page reload, AuthInitializer uses the HttpOnly
      // refresh_token cookie to mint a fresh one via /auth/refresh. This
      // means an XSS-injected script can't `localStorage.getItem` a token
      // it can walk out the door with.
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        recentlyLoggedOut: state.recentlyLoggedOut, // persist the guard
        // Persist the refresh token so a page reload can mint a new access
        // token cross-site (the third-party cookie can't be relied on). The
        // access token itself is still memory-only (F4).
        refreshToken: state.refreshToken,
      }),
      storage: createJSONStorage(() => localStorage),
    }
  )
);

// ---------------------------------------------------------------------------
// CROSS-TAB TOKEN SYNC
// ---------------------------------------------------------------------------
/**
 * WHY: refresh tokens are ROTATED server-side — each /auth/refresh blacklists
 * the token it was given and returns a new one. localStorage is shared between
 * tabs, but each tab holds its own IN-MEMORY copy of the store, and zustand's
 * persist middleware does not watch for external writes. So:
 *
 *   tab B refreshes -> R1 is blacklisted, R2 written to localStorage
 *   tab A still holds R1 in memory -> next refresh sends a revoked token
 *   -> 401 -> tab A gets logged out
 *
 * That is exactly the "logging in on one tab kicks me out of the other" bug.
 *
 * WHAT: the `storage` event fires in OTHER tabs whenever this origin's
 * localStorage changes. Re-hydrating on that event makes every tab pick up the
 * newest refresh token, so no tab is ever holding a revoked one. It also makes
 * logout propagate: clearing auth in one tab logs the others out consistently
 * instead of leaving them in a broken half-authenticated state.
 *
 * WHY-THIS-WAY: `accessToken` is excluded from `partialize` (F4 — memory only),
 * and rehydrate merges persisted fields over current state, so a tab keeps its
 * own valid in-memory access token and only the shared refresh token is synced.
 */
if (typeof window !== 'undefined') {
  window.addEventListener('storage', (event) => {
    if (event.key === 'auth-storage') {
      void useAuthStore.persist.rehydrate();
    }
  });
}
