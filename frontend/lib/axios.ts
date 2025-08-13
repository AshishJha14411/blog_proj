// src/lib/axios.ts
import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '@/stores/authStore';

const API_URL = 'http://127.0.0.1:8000';

const axiosInstance = axios.create({
  baseURL: API_URL,
});

// --- Attach token on every request ---
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
  // If a refresh is already in-flight, reuse it
  if (refreshPromise) return refreshPromise;

  const { refreshToken, setAccessToken, logout } = useAuthStore.getState();

  refreshPromise = (async () => {
    if (!refreshToken) {
      logout();
      return null;
    }
    try {
      const resp = await axios.post(`${API_URL}/auth/refresh`, {
        refresh_token: refreshToken,
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
      // allow new refresh attempts next time
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

// --- Response interceptor with retry on 401 ---
axiosInstance.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest: any = error.config;

    // If no response or not 401, just fail
    if (!error.response || error.response.status !== 401) {
      return Promise.reject(error);
    }

    // Avoid refresh loops on auth endpoints
    const url = (originalRequest?.url || '') as string;
    if (url.includes('/auth/login') || url.includes('/auth/refresh')) {
      useAuthStore.getState().logout();
      return Promise.reject(error);
    }

    // Prevent infinite retry loops
    if (originalRequest._retry) {
      useAuthStore.getState().logout();
      return Promise.reject(error);
    }
    originalRequest._retry = true;

    // Try to refresh
    const newToken = await refreshAccessToken();
    if (!newToken) {
      // refresh failed → user logged out already
      return Promise.reject(error);
    }

    // Retry original request with new token
    originalRequest.headers = originalRequest.headers ?? {};
    originalRequest.headers.Authorization = `Bearer ${newToken}`;
    return axiosInstance(originalRequest);
  }
);

export default axiosInstance;
