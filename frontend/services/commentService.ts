import axios from 'axios'
import { useAuthStore } from '@/stores/authStore'
// import { headers } from 'next/headers';
import axiosInstance from '@/lib/axios'
const API_URL = 'http://127.0.0.1:8000/stories'
const getAuthHeaders = () => {
    const access_token = useAuthStore.getState().accessToken
    if(!access_token) return {};

    return {
        headers:{
            Authorization: `Bearer ${access_token}`
        }
    }
}

export interface Comment {
    id: string,
    content: string,
    created_at: string,
    user: {
        id: string;
        username: string
    }
}

export const getCommentsForPost = async (postId: string): Promise<Comment[]> => {
    const response = await axiosInstance.get(`${API_URL}/${postId}/comments`);
    console.log(response)
    return response.data.items
}

export const createComment = async (postId: string, content: string): Promise<Comment> => {
  console.log(content)
  const response = await axiosInstance.post(
    `${API_URL}/${postId}/comments`,
    { content },
   
  );
  return response.data;
};

export const deleteComment = async (commentId: string): Promise<void> => {
  await axiosInstance.delete(`http://127.0.0.1:8000/comments/${commentId}`);
};
