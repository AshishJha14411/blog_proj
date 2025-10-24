// src/services/adminService.ts

import axiosInstance from '@/lib/axios';

// Define the shape of a creator request object for the frontend
export interface CreatorRequest {
    id: string;
    user: {
        id: string;
        username: string;
    };
    status: 'pending' | 'approved' | 'rejected';
    reason?: string;
}

/**
 * Fetches the list of pending creator requests.
 * Requires admin/moderator privileges.
 */
export const getPendingCreatorRequests = async (): Promise<CreatorRequest[]> => {
    const response = await axiosInstance.get('/admin/creator-requests/pending');
    return response.data;
};

/**
 * Approves or rejects a specific creator request.
 * @param requestId The ID of the request to review.
 * @param action The action to take: 'approve' or 'reject'.
 */
export const reviewCreatorRequest = async (requestId: string, action: 'approve' | 'reject'): Promise<CreatorRequest> => {
    const response = await axiosInstance.post(`/admin/creator-requests/${requestId}/review`, { action });
    return response.data;
};