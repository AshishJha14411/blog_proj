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
  user: User | null;
  isAuthenticated: boolean;

  // NEW: logout guard so AuthInitializer won’t immediately refresh after logout
  recentlyLoggedOut: boolean;

  // keep the same signature you already use:
  login: (data: { accessToken: string; refreshToken: string; user: User }) => void;
  logout: () => void;
  setAccessToken: (token: string) => void;

  // helper to clear the guard (e.g., after a deliberate login flow)
  clearLogoutFlag: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      user: null,
      isAuthenticated: false,
      recentlyLoggedOut: false,

      login: (data) =>
        set({
          accessToken: data.accessToken,
          user: data.user,
          isAuthenticated: true,
          recentlyLoggedOut: false, // reset guard on successful login
        }),

      logout: () =>
        set({
          accessToken: null,
          user: null,
          isAuthenticated: false,
          recentlyLoggedOut: true, // set guard so AuthInitializer skips refresh
        }),

      setAccessToken: (token) => set({ accessToken: token }),

      clearLogoutFlag: () => set({ recentlyLoggedOut: false }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        accessToken: state.accessToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        recentlyLoggedOut: state.recentlyLoggedOut, // persist the guard
      }),
      storage: createJSONStorage(() => localStorage),
    }
  )
);
