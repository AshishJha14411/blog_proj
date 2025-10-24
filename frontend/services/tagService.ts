import axiosInstance from "@/lib/axios";
import {Post, PaginatedPosts} from './postService'
import axios from "axios";

export interface Tag {
    id: string;
    name: string;
    description?: string;
}

interface TagCreate{
    name: string,
    description?: string
}

interface TagUpdate {
    name?: string,
    description?: string
}
const API_URL = 'http://localhost:8000/tags'

export const getAllTags = async(): Promise<{ tags: Tag[] }> => {
    const response = await axiosInstance.get(API_URL)
    return response.data
}

export const createTag = async(tagData:TagCreate): Promise<Tag> => {
    const response =await axiosInstance.post(API_URL, tagData)
    return response.data
}

export const updateTag = async(tagId: number, tagData:TagUpdate): Promise<Tag> => {
    const response = await axiosInstance.patch(`${API_URL}/${tagId}`, tagData)
    return response.data
}

export const deleteTag = async(tagId:number): Promise<void> => {
    await axiosInstance.delete(`${API_URL}/${tagId}`)
}