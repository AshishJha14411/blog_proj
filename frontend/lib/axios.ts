// src/lib/axios.ts

import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '@/stores/authStore';

interface RetryableRequestConfig extends InternalAxiosRequestConfig {
  _networkRetry?: boolean;
  _retry?: boolean;
}

// Server Components / route handlers run inside the frontend's own Node
// process (in Docker, a separate container from the backend), so the
// browser-facing NEXT_PUBLIC_API_URL (localhost:8000, published to the host)
// isn't reachable from there — that's a connection to the frontend
// container itself, not the backend one. API_URL_INTERNAL (e.g.
// http://backend:8080, the Docker-network service name) is server-only, so
// it's deliberately NOT prefixed with NEXT_PUBLIC_. `typeof window` is safe
// to branch on at module scope: Next.js bundles this file separately for
// the server runtime and the browser, so each side evaluates its own case.
export const API_URL = typeof window === 'undefined'
  ? (process.env.API_URL_INTERNAL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')
  : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000');

// The REST API is versioned under /api/v1 (see backend main.py). The shared
// axios instance targets that base, so every service call is automatically
// versioned. `API_URL` (bare host) is kept for things that are NOT under the
// versioned prefix: the WebSocket handshake + its /ws/ticket mint.
export const API_V1_URL = `${API_URL}/api/v1`;

const axiosInstance = axios.create({
  baseURL: API_V1_URL,
  // --- CRITICAL: This tells axios to send cookies with every request ---
  withCredentials: true,
  timeout: 30000,               // free-tier cold starts can take ~20s
});

// --- Attach access token on every request (This part is still correct) ---
axiosInstance.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().accessToken;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// --- Refresh logic (single-flight) ---
let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;

  const { setTokens, logout, refreshToken } = useAuthStore.getState();

  refreshPromise = (async () => {
    try {
      // Send the stored refresh token in the body — the third-party cookie
      // can't be relied on across domains (see authStore/refreshSession).
      const resp = await axios.post(`${API_V1_URL}/auth/refresh`, { refresh_token: refreshToken }, {
        withCredentials: true, // Be explicit for this call
        timeout: 30000,        // raw axios stays outside the interceptor chain
      });

      const newAccess = resp.data?.access_token as string | undefined;
      const newRefresh = resp.data?.refresh_token as string | undefined;
      if (!newAccess) {
        logout();
        return null;
      }
      // Refresh rotates the refresh token, so store both.
      setTokens(newAccess, newRefresh ?? refreshToken ?? '');
      return newAccess;
    } catch {
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
    const originalRequest = error.config as RetryableRequestConfig | undefined;

    // One retry on network error / timeout (free-tier cold starts).
    if (!error.response && originalRequest && !originalRequest._networkRetry) {
      originalRequest._networkRetry = true;
      await new Promise((r) => setTimeout(r, 2000));
      return axiosInstance(originalRequest);
    }

    if (!error.response || error.response.status !== 401 || !originalRequest) {
      return Promise.reject(error);
    }

    const url = originalRequest.url || '';
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

    originalRequest.headers.Authorization = `Bearer ${newToken}`;
    return axiosInstance(originalRequest);
  }
);

export default axiosInstance;