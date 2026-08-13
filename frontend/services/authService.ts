import axiosInstance from '../lib/axios';
import { UserProfile } from './userService';
import { useAuthStore } from '@/stores/authStore';

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

/**
 * WHY the token argument is now USED: LoginForm calls
 *   loginUser() -> getMe() -> store.login() -> router.push('/')
 * so at getMe() time the store is still empty. The request interceptor reads the
 * token from the store, found none, and sent an unauthenticated request — which
 * 401'd, logged a red error in the console on EVERY login, and only recovered by
 * burning a full refresh round-trip (which also rotates the refresh token for no
 * reason). Passing the freshly-minted token explicitly makes the first call
 * succeed: no console error, one less round-trip, and less token churn.
 *
 * The argument stays optional so callers that rely on the interceptor (any
 * already-authenticated context) are unaffected.
 */
export const getMe = async (token?: string) => {
    const response = await axiosInstance.get(
        '/auth/me',
        token ? { headers: { Authorization: `Bearer ${token}` } } : undefined,
    );
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
    refresh_token: string;
    user: UserProfile;
}

/**
 * Calls the backend's refresh endpoint. Sends the stored refresh token in the
 * body (the HttpOnly cookie is also sent when same-site, but on a split-domain
 * deploy it's a blocked third-party cookie — the body is the reliable path).
 */
export const refreshSession = async (): Promise<RefreshResponse> => {
    const refreshToken = useAuthStore.getState().refreshToken;
    const response = await axiosInstance.post('/auth/refresh', { refresh_token: refreshToken });
    return response.data;
};
