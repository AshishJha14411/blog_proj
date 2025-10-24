// hooks/useHydratedAuth.ts
"use client"
import { useState, useEffect } from 'react';
import { useAuthStore } from '@/stores/authStore';

export const useHydratedAuth = () => {
  const [hydrated, setHydrated] = useState(false);
  const authState = useAuthStore();

  useEffect(() => {
    setHydrated(true);
  }, []);

  return { ...authState, isHydrated: hydrated };
};