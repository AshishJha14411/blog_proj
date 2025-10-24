'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
// You would create a 'signupUser' function in your authService.ts
import { signupUser } from '@/services/authService';
import AuthCard from '../ui/AuthCard';
import Input from '../ui/Input';
import Button from '../ui/Button';
import FormLabel from '../ui/FormLabel';
import GoogleLoginButton from '../auth/GoogleLoginButton';

export default function SignupForm() {
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const router = useRouter();

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    try {
      await signupUser({ email, username, password });
      console.log('Signing up with:', { email, username, password });
      router.push('/'); // Redirect to login after successful signup
    } catch (err) {
      setError('Failed to create account. Please try again.');
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
          />
        </div>
        {error && <p className="text-sm text-red-500">{error}</p>}
        <div className='flex justify-center'>
          <Button type="submit">Sign Up</Button>
        </div>
      </form>
      {/* <div className='flex justify-center'>
        <GoogleLoginButton />
      </div> */}
    </AuthCard>
  );
}