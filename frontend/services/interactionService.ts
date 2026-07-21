import axiosInstance from "@/lib/axios";

interface ToggleResponse {
    success: boolean;
    liked?: boolean;
    bookmarked: boolean
}

export const toggleLike = async (postId: string): Promise<ToggleResponse> => {
    const response = await axiosInstance.post(`/stories/${postId}/like`);
    return response.data;
}

export const toggleBookmark = async (postId: string): Promise<ToggleResponse> => {
    const response = await axiosInstance.post(`/stories/${postId}/bookmark`);
    return response.data;
}