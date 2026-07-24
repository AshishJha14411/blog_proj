'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import { signupUser } from '@/services/authService';
import AuthCard from '../ui/AuthCard';
import Input from '../ui/Input';
import Button from '../ui/Button';
import FormLabel from '../ui/FormLabel';

// --- 1. Import the store and the login function ---
import { useAuthStore } from '@/stores/authStore';

export default function SignupForm() {
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false); // <-- Good addition for UX
  const router = useRouter();
  
  // --- 2. Get the login action from the store ---
  const login = useAuthStore((state) => state.login);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setLoading(true); // <-- Start loading
    
    try {
      // --- 3. Capture the response from the service ---
      const loginData = await signupUser({ email, username, password, message: '' }); // 'message' is a fix for your TS interface

      // --- 4. Call the store's login action ---
      // This saves the token and user to state/localStorage
      login({
        accessToken: loginData.access_token,
        refreshToken: loginData.refresh_token,
        user: loginData.user,
      });

      router.push('/'); // Redirect to homepage *after* logging in
      
    } catch (err) {
      // Set a more specific error from the backend if possible — deliberately
      // NOT falling back to a generic error.message (a network/client error
      // wouldn't have a useful one); only the backend's own detail is shown.
      const detail = axios.isAxiosError(err) ? (err.response?.data as { detail?: string } | undefined)?.detail : undefined;
      setError(detail || 'Failed to create account. Please try again.');
    } finally {
      setLoading(false); // <-- Stop loading
    }
  };

  return (
    <AuthCard title="Create Account">
      <form className="space-y-6" onSubmit={handleSubmit}>
        <div>
          <FormLabel htmlFor="email">Email Address</FormLabel>
          <Input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={loading} // <-- Disable on load
          />
        </div>
        <div>
          <FormLabel htmlFor="username">Username</FormLabel>
          <Input
            id="username"
            type="text"
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={loading} // <-- Disable on load
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
            disabled={loading} // <-- Disable on load
          />
        </div>
        {error && <p className="text-sm text-red-500">{error}</p>}
        <div className='flex justify-center'>
          <Button type="submit" disabled={loading}>
            {loading ? "Creating Account..." : "Sign Up"}
          </Button>
        </div>
      </form>
      {/* <div className='flex justify-center'>
        <GoogleLoginButton />
      </div> */}
    </AuthCard>
  );
}