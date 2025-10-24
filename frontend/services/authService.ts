import { useAuthStore } from '@/stores/authStore';
import axios from 'axios'
import  axiosInstance  from '../lib/axios'
import { UserProfile } from './userService';
const API_ROOT = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_URL = `${API_ROOT}/auth`;
interface LoginResponse{
    access_token: string;
    refresh_token: string;
}
export const requestCreatorAccess = async (reason: string, token: string) => {
    try {
        // The backend endpoint for this is under the user_router, not /admin
        const response = await axios.post(`${API_ROOT}/admin/creator-requests`, 
            { reason }, // The request body
            { 
                headers: { Authorization: `Bearer ${token}` } // The auth header
            }
        );
        return response.data;
    } catch (error) {
        // Pass along the specific error message from the backend
        throw new Error(error.response?.data?.detail || 'Failed to submit creator request.');
    }
};
export const verifyUserEmail = async (token: string) => {
    try {
        // The backend expects the token as a URL query parameter, named 'token'.
        const response = await axios.get(`${API_URL}/verify-email`, {
            params: { token }
        });
        return response.data; // Should return { message: "..." } on success
    } catch (error) {
        throw new Error(error.response?.data?.detail || 'Email verification failed.');
    }
};

export const loginUser = async (username:string, password:string): Promise<LoginResponse> => {
    const response = await axios.post(`${API_URL}/login`, {
        username,
        password,
        })
        return response.data
}


export const getMe = async (token: string) => {
  const response = await axios.get(`${API_URL}/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return response.data;
};


export const logoutUser = async () => {
  const response = await axiosInstance.post(`/auth/logout`);
  return response.data;

}

interface SignUpData {
  email;
  username;
  password;
  message;
}

export const signupUser = async (data: SignUpData) => {
    const response = await axios.post(`${API_URL}/signup`, data);
    return response.data;
}

interface PasswordChangeData {
    old_password:string;
    new_password:string;
}
export const changePassword = async (data: PasswordChangeData) => {
    const { accessToken } = useAuthStore.getState();
    if (!accessToken) throw new Error("User not authenticated");

    const response = await axios.patch(`${API_URL}/me/password`, data, {
        headers: { Authorization: `Bearer ${accessToken}` },
    });
    return response.data;
};

export const forgotPassword = async (email: string) => {
    const response = await axios.post(`${API_URL}/forgot-password`, { email });
    return response.data;
};

interface ResetPasswordData {
    token:string;
    new_password:string;
}
export const resetPassword = async (data: ResetPasswordData) => {
    const response = await axios.post(`${API_URL}/reset-password`, data);
    return response.data;
};

export const handleGoogleLogin = async (code: string) => {
    try {
        const response = await axios.post(`${API_URL}/google/login`, { code });
        // The backend will return the same LoginResponse as a regular login
        return response.data;
    } catch (error) {
        throw new Error(error.response?.data?.detail || "Google login failed.");
    }
};


interface RefreshResponse {
  access_token: string;
  user: UserProfile;
}

/**
 * Calls the backend's refresh endpoint. The browser's HttpOnly cookie is sent automatically.
 * If successful, returns a new access token and the user's profile.
 */
export const refreshSession = async (): Promise<RefreshResponse> => {
  // We need to refactor the backend /refresh to return the user object as well
  const response = await axiosInstance.post('/auth/refresh');
  return response.data;
};