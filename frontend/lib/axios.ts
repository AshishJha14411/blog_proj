
import axios from 'axios';
import { useAuthStore } from '@/stores/authStore';

const API_URL = 'http://127.0.0.1:8000';

const axiosInstance = axios.create({
  baseURL: API_URL,
});

// --- Request Interceptor ---
// This runs before every request is sent.
axiosInstance.interceptors.request.use(
  (config) => {
    const accessToken = useAuthStore.getState().accessToken;
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// --- Response Interceptor ---
// This runs after a response is received.
axiosInstance.interceptors.response.use(
  (response) => response, 
  async (error) => {
    const originalRequest = error.config;
    const { logout, refreshToken, setAccessToken } = useAuthStore.getState();

    // If the error is 401 and it's not a retry request
    if (error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true; // Mark it as a retry

      if (!refreshToken) {
        logout();
        return Promise.reject(error);
      }

      try {
        // 1. Call the refresh token endpoint
        const response = await axios.post(`${API_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });
        
        const { access_token: newAccessToken } = response.data;

        // 2. Update the store with the new access token
        setAccessToken(newAccessToken);

        // 3. Update the header of the original request and retry it
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return axiosInstance(originalRequest);

      } catch (refreshError) {
        // If the refresh token is invalid, log the user out
        logout();
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default axiosInstance;
