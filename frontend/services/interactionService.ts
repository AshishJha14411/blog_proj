import axiosInstance from "@/lib/axios";

interface ToggleResponse {
    success: boolean;
    liked?: boolean;
    bookmarked: boolean
}

const API_URL = 'http://127.0.0.1:8000/stories'
export const toggleLike = async(postId:string): Promise<ToggleResponse> => {
    const response = await axiosInstance.post(`${API_URL}/${postId}/like`)
    return response.data
}

export const toggleBookmark = async(postId:string): Promise<ToggleResponse> => {
    const response = await axiosInstance.post(`${API_URL}/${postId}/bookmark`)
    return response.data
}