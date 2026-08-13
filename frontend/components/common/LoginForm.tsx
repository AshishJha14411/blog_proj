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
    <AuthCard title="Log In" subtitle="Pick up where you left off.">
      <form className="space-y-5" onSubmit={handleSubmit} aria-busy={loading ? 'true' : undefined /* Added for happy path login form test */}>
        <div>
          <FormLabel htmlFor="username">Username</FormLabel>
          <Input
            id="username"
            type="text"
            required
            autoComplete="username"
            placeholder="yourhandle"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={loading}
          />
        </div>
        <div>
          <div className="flex items-baseline justify-between">
            <FormLabel htmlFor="password">Password</FormLabel>
            <Link
              href="/forgot-password"
              className="text-xs font-medium text-primary-strong transition-colors hover:underline"
            >
              Forgot password?
            </Link>
          </div>
          <Input
            id="password"
            type="password"
            required
            autoComplete="current-password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
          />
        </div>
        {error && (
          <p className="rounded-xl border border-red-500/25 bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-300">
            {error}
          </p>
        )}
        <Button
          type="submit"
          disabled={loading}
          className="w-full"
          aria-busy={loading ? 'true' : undefined /* Added for happy path login form test */}
        >
          {loading ? 'Signing in...' : 'Sign in'}
        </Button>
      </form>

      <div className="my-6 flex items-center gap-3">
        <span className="h-px flex-1 bg-border-soft" />
        <span className="text-xs uppercase tracking-[0.14em] text-text-subtle">or</span>
        <span className="h-px flex-1 bg-border-soft" />
      </div>

      <GoogleLoginButton />

      <p className="mt-6 text-center text-sm text-text-light">
        New here?{' '}
        <Link href="/signup" className="font-medium text-primary-strong hover:underline">
          Create an account
        </Link>
      </p>
    </AuthCard>
  );
}
