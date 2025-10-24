'use client';

import { useState, useEffect } from 'react';
import { useAuthStore } from '@/stores/authStore';

// This is the default, "logged-out" state. It's what the server will always see.
const initialState = {
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
};

/**
 * A safe hook for accessing auth state that prevents hydration mismatches.
 * It always returns an initial, logged-out state on the server.
 * On the client, it waits for hydration and then returns the true, live state from the store.
 */
export const useAuth = () => {
  // 1. Get the real state directly from the Zustand store.
  const storeState = useAuthStore((state) => state);
  
  // 2. Create a local React state that defaults to our safe, initial state.
  const [hydratedState, setHydratedState] = useState(initialState);
  
  // 3. A flag to tell our components if hydration is complete.
  const [isHydrated, setIsHydrated] = useState(false);

  // 4. This effect runs ONLY on the client, after the component has mounted.
  useEffect(() => {
    // Sync the local state with the real, hydrated store state.
    setHydratedState(storeState);
    // Mark hydration as complete.
    setIsHydrated(true);
  }, [storeState]); // This effect re-runs if the actual store state changes.

  // On the server render, isHydrated is false, so we return the safe initialState.
  // On the client, after the useEffect runs, we return the real, hydrated state.
  return { ...hydratedState, isHydrated };
};

