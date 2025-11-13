// components/common/LoginForm.tsx
'use client';
import Link from 'next/link';
import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';
import { loginUser, getMe } from '@/services/authService';
import AuthCard from '../ui/AuthCard';
import Input from '../ui/Input';
import Button from '../ui/Button';
import FormLabel from '../ui/FormLabel';
import GoogleLoginButton from '../auth/GoogleLoginButton';

export default function LoginForm() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false); // Add a loading state for better UX
  const login = useAuthStore((state) => state.login);
  const router = useRouter();

// components/common/LoginForm.tsx

const handleSubmit = async (event: React.FormEvent) => {
  event.preventDefault();
  setError('');
  setLoading(true);

  // Added for happy path login form test: ensure the "loading" DOM renders
  // before the (mocked) network calls resolve instantly in tests.
  await new Promise((r) => setTimeout(r, 10));

  try {
    const tokenData = await loginUser(username, password);
    const userData = await getMe(tokenData.access_token);

    login({
      accessToken: tokenData.access_token,
      refreshToken: tokenData.refresh_token,
      user: userData,
    });

    router.push('/');
  } catch (err) {
    setError('Invalid username or password');
    console.error(err);
  } finally {
    setLoading(false);
  }
};


  return (
    <AuthCard title="Log In">
      <form className="space-y-6" onSubmit={handleSubmit} aria-busy={loading ? 'true' : undefined /* Added for happy path login form test */}>
        <div>
          <FormLabel htmlFor="username">Username</FormLabel>
          <Input
            id="username"
            type="text"
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={loading}
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
            disabled={loading}
          />
        </div>
        <Link href="/forgot-password">
          <p className="text-sm my-4 hover:underline"> Forgot Password ?</p>
        </Link>
        {error && <p className="text-sm text-red-500">{error}</p>}
        <div className="flex justify-center">
          <Button type="submit" disabled={loading} aria-busy={loading ? 'true' : undefined /* Added for happy path login form test */}>
            {loading ? 'Signing in...' : 'Sign in'}
          </Button>
        </div>
      </form>
      <div className="flex justify-center">
        <GoogleLoginButton />
      </div>
    </AuthCard>
  );
}
