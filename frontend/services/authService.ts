import axiosInstance from '../lib/axios';
import { UserProfile } from './userService';

interface LoginResponse {
    access_token: string;
    refresh_token: string;
}

export const requestCreatorAccess = async (reason: string, _token?: string) => {
    try {
        const response = await axiosInstance.post('/admin/creator-requests', { reason });
        return response.data;
    } catch (error: any) {
        throw new Error(error.response?.data?.detail || 'Failed to submit creator request.');
    }
};

export const verifyUserEmail = async (token: string) => {
    try {
        const response = await axiosInstance.get('/auth/verify-email', {
            params: { token },
        });
        return response.data;
    } catch (error: any) {
        throw new Error(error.response?.data?.detail || 'Email verification failed.');
    }
};

export const loginUser = async (username: string, password: string): Promise<LoginResponse> => {
    const response = await axiosInstance.post('/auth/login', { username, password });
    return response.data;
};

export const getMe = async (_token?: string) => {
    const response = await axiosInstance.get('/auth/me');
    return response.data;
};

export const logoutUser = async () => {
    const response = await axiosInstance.post('/auth/logout');
    return response.data;
};

interface SignUpData {
    email: string;
    username: string;
    password: string;
    message?: string;
}

export const signupUser = async (data: SignUpData) => {
    const response = await axiosInstance.post('/auth/signup', data);
    return response.data;
};

interface PasswordChangeData {
    old_password: string;
    new_password: string;
}
export const changePassword = async (data: PasswordChangeData) => {
    const response = await axiosInstance.patch('/auth/me/password', data);
    return response.data;
};

export const forgotPassword = async (email: string) => {
    const response = await axiosInstance.post('/auth/forgot-password', { email });
    return response.data;
};

interface ResetPasswordData {
    token: string;
    new_password: string;
}
export const resetPassword = async (data: ResetPasswordData) => {
    const response = await axiosInstance.post('/auth/reset-password', data);
    return response.data;
};

export const handleGoogleLogin = async (code: string) => {
    try {
        const response = await axiosInstance.post('/auth/google/login', { code });
        return response.data;
    } catch (error: any) {
        throw new Error(error.response?.data?.detail || 'Google login failed.');
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
    const response = await axiosInstance.post('/auth/refresh');
    return response.data;
};
