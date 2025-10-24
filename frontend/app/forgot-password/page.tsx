// src/app/forgot-password/page.tsx

'use client';
import React, { useState } from 'react';
import { forgotPassword } from '@/services/authService';
import AuthCard from '@/components/ui/AuthCard';
import Input from '@/components/ui/Input';
import Button from '@/components/ui/Button';
import FormLabel from '@/components/ui/FormLabel';
import Link from 'next/link';

export default function ForgotPasswordPage() {
    const [email, setEmail] = useState('');
    const [message, setMessage] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setMessage('');
        try {
            const response = await forgotPassword(email);
            // Always show a success message to prevent user enumeration
            setMessage(response.message);
        } catch (err) {
            // Even on error, show a generic success message for security
            setMessage('If an account with that email exists, a password reset link has been sent.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <AuthCard title="Reset Your Password">
            {message ? (
                <div className="text-center">
                    <p className="text-green-600">{message}</p>
                    <Link href="/login" className="mt-4 inline-block text-sm text-[var(--accent-primary)] hover:underline">
                        Back to Login
                    </Link>
                </div>
            ) : (
                <form onSubmit={handleSubmit} className="space-y-4">
                    <p className="text-sm text-gray-600">Enter your email address and we will send you a link to reset your password.</p>
                    <div>
                        <FormLabel htmlFor="email">Email Address</FormLabel>
                        <Input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} disabled={loading} />
                    </div>
                    <Button type="submit" disabled={loading}>{loading ? 'Sending Link...' : 'Send Reset Link'}</Button>
                </form>
            )}
        </AuthCard>
    );
}