import axios from 'axios'

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
