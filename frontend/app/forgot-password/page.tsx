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
        } catch {
            // Even on error, show a generic success message for security
            setMessage('If an account with that email exists, a password reset link has been sent.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <AuthCard
            title="Reset Your Password"
            subtitle="We'll email you a link to set a new one."
        >
            {message ? (
                <div className="text-center">
                    <p className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-700 dark:text-emerald-300">
                        {message}
                    </p>
                    <Link href="/login" className="mt-6 inline-block text-sm font-medium text-primary-strong hover:underline">
                        Back to Login
                    </Link>
                </div>
            ) : (
                <form onSubmit={handleSubmit} className="space-y-5">
                    <div>
                        <FormLabel htmlFor="email">Email Address</FormLabel>
                        <Input id="email" type="email" required placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} disabled={loading} />
                    </div>
                    <Button type="submit" disabled={loading} className="w-full">{loading ? 'Sending Link...' : 'Send Reset Link'}</Button>
                    <p className="text-center text-sm text-text-light">
                        <Link href="/login" className="font-medium text-primary-strong hover:underline">
                            Back to Login
                        </Link>
                    </p>
                </form>
            )}
        </AuthCard>
    );
}