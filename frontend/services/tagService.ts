import axiosInstance from "@/lib/axios";

export interface Tag {
    id: string;
    name: string;
    description?: string;
}

interface TagCreate {
    name: string,
    description?: string
}

interface TagUpdate {
    name?: string,
    description?: string
}

export const getAllTags = async (): Promise<{ tags: Tag[] }> => {
    const response = await axiosInstance.get('/tags');
    return response.data;
}

export const createTag = async (tagData: TagCreate): Promise<Tag> => {
    const response = await axiosInstance.post('/tags', tagData);
    return response.data;
}

// G25: tag ids are UUID strings, not numbers.
export const updateTag = async (tagId: string, tagData: TagUpdate): Promise<Tag> => {
    const response = await axiosInstance.patch(`/tags/${tagId}`, tagData);
    return response.data;
}

export const deleteTag = async (tagId: string): Promise<void> => {
    await axiosInstance.delete(`/tags/${tagId}`);
}
