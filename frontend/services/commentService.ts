import axiosInstance from '@/lib/axios'

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
    const response = await axiosInstance.get(`/stories/${postId}/comments`);
    return response.data.items
}

export const createComment = async (postId: string, content: string): Promise<Comment> => {
    const response = await axiosInstance.post(`/stories/${postId}/comments`, { content });
    return response.data;
};

export const deleteComment = async (commentId: string): Promise<void> => {
    await axiosInstance.delete(`/comments/${commentId}`);
};
