import { useAuthStore } from '@/stores/authStore';
import axios from 'axios'
import  axiosInstance  from '../lib/axios'
const API_URL = 'http://127.0.0.1:8000/auth'

interface LoginResponse{
    access_token: string;
    refresh_token: string;
}

export const loginUser = async (username, password): Promise<LoginResponse> => {
    const response = await axios.post(`${API_URL}/login`, {
        username,
        password,
        })
        return response.data
}


export const getMe = async (token: string) => {
  const response = await axios.get(`${API_URL}/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return response.data;
};


export const logoutUser = async () => {
  const {refreshToken} = useAuthStore.getState()
  if(!refreshToken) return;

  await axiosInstance.post(`${API_URL}/auth/logout`, {refresh_token: refreshToken})

}

interface SignUpData {
  email;
  username;
  password;
  message;
}

export const signupUser = async (data: SignUpData) => {
    const response = await axios.post(`${API_URL}/signup`, data);
    return response.data;
}