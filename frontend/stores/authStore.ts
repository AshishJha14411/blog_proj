// src/stores/authStore.ts
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

// Define the shape of the user object (you can expand this)
interface Role { id: number; name: string }
interface User { id: number; username: string; email: string; role?: Role } 

// Update the AuthState interface
interface AuthState {
  accessToken: string | null;
  user: User | null; 
  refreshToken: string | null; 
  isAuthenticated: boolean;
  login: (data: {accessToken: string; refreshToken: string; user: User}) => void; // <-- UPDATE THIS
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      user: null, // <-- ADD THIS
      isAuthenticated: false,
      refreshToken: null,
      login: (data) => // <-- UPDATE THIS
        set({
          accessToken: data.accessToken,
          refreshToken: data.refreshToken,
          user: data.user, 
          isAuthenticated: true,
        }),
      logout: () =>
        set({
          accessToken: null,
          refreshToken: null,
          user: null, 
          isAuthenticated: false,
        }),
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
    }
  )
);