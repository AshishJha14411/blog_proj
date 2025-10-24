import axiosInstance from '@/lib/axios';
import { Post } from './postService'; // Reuse the Post interface
import { useAuthStore } from '@/stores/authStore';
import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
interface BookmarksResponse {
  items: Post[];
}

export const getMyBookmarks = async (): Promise<BookmarksResponse> => {
  const response = await axiosInstance.get('/users/me/bookmarks');
  return response.data;
};

interface Role {
    id: string;
    name: string;
}

interface UserUpdateData {
    bio?: string;
    social_links?: object;
}
export interface UserProfile {
    id: string;
    email: string;
    username: string;
    is_verified: boolean;
    profile_image_url?: string | null;
    bio?: string | null; // Added to match the profile page's form data
    social_links?: { [key: string]: string } | null;
    total_posts: number;
    total_likes: number;
    total_comments: number;
    role: Role;
}

/**
 * Updates the current user's text-based profile data (bio, social links).
 */
export const updateUserProfile = async (data: UserUpdateData): Promise<UserProfile> => {
    const { accessToken } = useAuthStore.getState();
    if (!accessToken) throw new Error("User not authenticated");
    console.log(data,"data above request")
    const response = await axios.patch(`${API_URL}/auth/me`, data, {
        headers: { Authorization: `Bearer ${accessToken}` },
    });
    console.log(response, "data below request")
    return response.data;
};

/**
 * Uploads a new profile image for the current user.
 * Handles even extremely long filenames automatically.
 */
export const uploadProfileImage = async (file: File): Promise<UserProfile> => {
    const { accessToken } = useAuthStore.getState();
    if (!accessToken) throw new Error("User not authenticated");

    // We must use FormData to send a file.
    const formData = new FormData();
    formData.append('file', file);

    const response = await axios.post(`${API_URL}/auth/me/avatar`, formData, {
        headers: {
            Authorization: `Bearer ${accessToken}`,
            // IMPORTANT: Do NOT set 'Content-Type'. The browser will set it
            // correctly for FormData, including the boundary.
        },
    });
    return response.data;
};
