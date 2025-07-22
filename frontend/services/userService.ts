import axiosInstance from '@/lib/axios';
import { Post } from './postService'; // Reuse the Post interface

interface BookmarksResponse {
  items: Post[];
}

export const getMyBookmarks = async (): Promise<BookmarksResponse> => {
  const response = await axiosInstance.get('/users/me/bookmarks');
  return response.data;
};
