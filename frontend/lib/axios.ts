// src/lib/axios.ts

import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '@/stores/authStore';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const axiosInstance = axios.create({
  baseURL: API_URL,
  // --- CRITICAL: This tells axios to send cookies with every request ---
  withCredentials: true,
});

// --- Attach access token on every request (This part is still correct) ---
axiosInstance.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().accessToken;
    if (token) {
      config.headers = config.headers ?? {};
      (config.headers as any).Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// --- Refresh logic (single-flight) ---
let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;

  const { setAccessToken, logout } = useAuthStore.getState();

  refreshPromise = (async () => {
    try {
      const resp = await axios.post(`${API_URL}/auth/refresh`, {}, {
        withCredentials: true, // Be explicit for this call
      });
      
      const newAccess = resp.data?.access_token as string | undefined;
      if (!newAccess) {
        logout();
        return null;
      }
      setAccessToken(newAccess);
      return newAccess;
    } catch (err) {
      logout();
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

// --- Response interceptor with retry on 401 (This part remains the same) ---
axiosInstance.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest: any = error.config;

    if (!error.response || error.response.status !== 401) {
      return Promise.reject(error);
    }

    const url = (originalRequest?.url || '') as string;
    if (url.includes('/auth/login') || url.includes('/auth/refresh')) {
      useAuthStore.getState().logout();
      return Promise.reject(error);
    }
    if (originalRequest._retry) {
      useAuthStore.getState().logout();
      return Promise.reject(error);
    }
    originalRequest._retry = true;

    const newToken = await refreshAccessToken();
    if (!newToken) {
      return Promise.reject(error);
    }

    originalRequest.headers = originalRequest.headers ?? {};
    originalRequest.headers.Authorization = `Bearer ${newToken}`;
    return axiosInstance(originalRequest);
  }
);

export default axiosInstance;