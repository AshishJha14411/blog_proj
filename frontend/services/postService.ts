import axios from 'axios'

import { useAuthStore } from '@/stores/authStore'
// import { headers } from 'next/headers';
import axiosInstance from '@/lib/axios'
const API_URL = 'http://localhost:8000/posts'

const getAuthHeaders = () => {
    const accessToken = useAuthStore.getState().accessToken;
    return {
        headers:{
            Authorization: `Bearer ${accessToken}`
        }
    }
}

interface PostCreateData{
    title: string;
    content: string;
}
export interface Post {
    id: number,
    title:string,
    content: string,
    created_at: string,
    user: {
        id: number,
        username: string
    }
  is_liked_by_user: boolean;
  is_bookmarked_by_user: boolean;
  is_published: boolean;
  is_flagged: boolean;
}

interface PaginatedPosts {
    total: number;
    items: Post[]
}

export const createPost = async (postData: PostCreateData) => {
    const response = await axiosInstance.post(API_URL, postData,)
    return response.data
}

export const getPostById = async (postId: string) => {
    const response = await axiosInstance.get(`${API_URL}/${postId}`,)
    return response.data
}

export const getAllPosts = async (limit=10, offset=0):Promise<PaginatedPosts> => {
    const response  = await axiosInstance.get(`${API_URL}`,{
        params: {limit,offset}
    })
    console.log(response)
    return response.data
}


export const updatePost = async (postId: string, postData: { title: string; content: string }) => {
  const response = await axiosInstance.patch(`${API_URL}/${postId}`, postData, );
  return response.data;
};

export const deletePost = async (postId: string) => {
  await axiosInstance.delete(`${API_URL}/${postId}`,);
};

export const getMyPost = async(limit = 10, offset = 0): Promise<PaginatedPosts> => {
    const response = await axiosInstance.get(`${API_URL}/me`, {
params:{limit, offset},
    })
    return response.data
}