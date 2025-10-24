'use client'; // This marks the component as a Client Component
import Link from 'next/link';
import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';
// Import both loginUser and getMe from your service
import { loginUser, getMe } from '@/services/authService'; 
import AuthCard from '../ui/AuthCard';
import Input from '../ui/Input';
import Button from '../ui/Button';
import FormLabel from '../ui/FormLabel';
import { GoogleLogin } from '@react-oauth/google';
import GoogleLoginButton from '../auth/GoogleLoginButton';

export default function LoginForm() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false); // Add a loading state for better UX
  const login = useAuthStore((state) => state.login);
  const router = useRouter();

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setLoading(true); // Start loading
    
    try {
      // Step 1: Get the tokens from the login endpoint
      const tokenData = await loginUser(username, password);
      
      // Step 2: Use the new access token to fetch the user's profile
      const userData = await getMe(tokenData.access_token);
      
      // Step 3: Save both the token and the user profile to the Zustand store
        login({ 
        accessToken: tokenData.access_token, 
        refreshToken: tokenData.refresh_token, // <-- ADDED THIS LINE
        user: userData 
      });
      
      router.push('/'); // Redirect to homepage on successful login

    } catch (err) {
      setError('Invalid username or password');
      console.error(err);
    } finally {
      setLoading(false); // Stop loading
    }
  };

  return (
    <AuthCard title="Log In" >
      <form className="space-y-6" onSubmit={handleSubmit}>
        <div>
          <FormLabel htmlFor="username">Username</FormLabel>
          <Input
            id="username"
            type="text"
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={loading} // Disable input while loading
          />
        </div>
        <div>
          <FormLabel htmlFor="password">Password</FormLabel>
          <Input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading} // Disable input while loading
          />
        </div>
        <Link href="/forgot-password">
        <p className='text-sm my-4 hover:underline'> Forgot Password ?</p>
        </Link>
        {error && <p className="text-sm text-red-500">{error}</p>}
        <div className='flex justify-center'>
          <Button type="submit" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign in'}
          </Button>
        </div>
      </form>
        <div className='flex justify-center'>
          <GoogleLoginButton />
        </div>
    </AuthCard>
  );
}
