import axiosInstance from '@/lib/axios';
import { Post } from './postService'; // Reuse the Post interface

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
    const response = await axiosInstance.patch('/auth/me', data);
    return response.data;
};

/**
 * Uploads a new profile image for the current user.
 * Handles even extremely long filenames automatically.
 */
export const uploadProfileImage = async (file: File): Promise<UserProfile> => {
    // We must use FormData to send a file. Do NOT set Content-Type — the browser
    // sets it (with the multipart boundary) automatically.
    const formData = new FormData();
    formData.append('file', file);

    const response = await axiosInstance.post('/auth/me/avatar', formData);
    return response.data;
};
