import axiosInstance from "@/lib/axios";

interface ToggleResponse {
    success: boolean;
    liked?: boolean;
    bookmarked: boolean
}

const API_URL = 'http://127.0.0.1:8000/posts'
export const toggleLike = async(postId:number): Promise<ToggleResponse> => {
    const response = await axiosInstance.post(`${API_URL}/${postId}/like`)
    return response.data
}

export const toggleBookmark = async(postId:number): Promise<ToggleResponse> => {
    const response = await axiosInstance.post(`${API_URL}/${postId}/bookmark`)
    return response.data
}