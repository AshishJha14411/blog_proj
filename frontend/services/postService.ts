import axios from 'axios'
import { Tag } from './tagService'
import { useAuthStore } from '@/stores/authStore'
// import { headers } from 'next/headers';
import axiosInstance from '@/lib/axios'
const API_ROOT = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_URL = `${API_ROOT}/stories`;

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
    tag_names: string[];
}
export interface Post {
  id: string;
  title: string;
  header?: string;
  content: string;
  cover_image_url?: string;
  created_at: string;
  updated_at: string;
  deleted_at?: string | null;
  // Relations
  user: {
    id: string;
    username: string;
  };
  tags: Tag[];

  // Flags & status
  is_liked_by_user: boolean;
  is_bookmarked_by_user: boolean;
  is_published: boolean;
  is_flagged: boolean;
  flag_source: 'ai' | 'user' | 'none';

  // AI Story-specific metadata
  source?: 'user' | 'ai';
  summary?: string;
  genre?: string;
  tone?: string;
  length_label?: string; // e.g., "short", "medium", "long"
  status?: 'draft' | 'generated' | 'published' | 'rejected';
  version?: number;
  last_feedback?: string;
}

export interface PaginatedPosts {
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

export const getAllPosts = async (limit=10, offset=0, tag: string | null = null):Promise<PaginatedPosts> => {
    const response  = await axiosInstance.get(`${API_URL}`,{
        params: {limit,offset, tag}
    })
    // console.log(response)
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