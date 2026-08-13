import axiosInstance from '@/lib/axios'
import type { StoryOut, StoryList, StoryCreate } from '@/lib/api'

// Post / PaginatedPosts ARE the backend's generated StoryOut / StoryList — see
// lib/api.ts. Kept as aliases (not hand-rolled duplicates) so any schema drift
// becomes a compile error at the point of use. Regenerate: `npm run gen:api`.
export type Post = StoryOut;
export type PaginatedPosts = StoryList;

type PostCreateData = Pick<StoryCreate, 'title' | 'content' | 'tag_names'>;

export const createPost = async (postData: PostCreateData): Promise<StoryOut> => {
    const response = await axiosInstance.post<StoryOut>('/stories', postData);
    return response.data;
}

export const getPostById = async (postId: string): Promise<StoryOut> => {
    const response = await axiosInstance.get<StoryOut>(`/stories/${postId}`);
    return response.data;
}

export const getAllPosts = async (limit = 10, offset = 0, tag: string | null = null): Promise<PaginatedPosts> => {
    const response = await axiosInstance.get<StoryList>('/stories', {
        params: { limit, offset, tag },
    });
    return response.data;
}

/**
 * Most-engaged published stories, ranked server-side by likes + comments +
 * bookmarks. Returns a bare array (not a paginated envelope) because it backs a
 * fixed home-page rail. An empty array is a normal answer — it means nothing has
 * been engaged with yet, and the caller should hide the section rather than
 * falling back to "newest" under a "most loved" heading.
 */
export const getPopularPosts = async (limit = 6, days?: number): Promise<StoryOut[]> => {
    const response = await axiosInstance.get<StoryOut[]>('/stories/popular', {
        params: { limit, ...(days ? { days } : {}) },
    });
    return response.data;
}

export const updatePost = async (postId: string, postData: { title: string; content: string }): Promise<StoryOut> => {
    const response = await axiosInstance.patch<StoryOut>(`/stories/${postId}`, postData);
    return response.data;
};

export const deletePost = async (postId: string) => {
    await axiosInstance.delete(`/stories/${postId}`);
};

export const getMyPost = async (limit = 10, offset = 0): Promise<PaginatedPosts> => {
    const response = await axiosInstance.get<StoryList>('/stories/me', {
        params: { limit, offset },
    });
    return response.data;
}
