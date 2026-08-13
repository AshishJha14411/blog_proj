// src/app/reset-password/page.tsx

'use client';
import React, { useState, useEffect, useRef, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { resetPassword } from '@/services/authService';
import { getErrorMessage } from '@/lib/errors';
import AuthCard from '@/components/ui/AuthCard';
import Input from '@/components/ui/Input';
import Button from '@/components/ui/Button';
import FormLabel from '@/components/ui/FormLabel';

function ResetPasswordForm() {
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [loading, setLoading] = useState(false);
    const router = useRouter();
    const searchParams = useSearchParams();
    const token = searchParams.get('token');

    // Track the redirect timer so we can cancel it if the user navigates away
    // before the 3s countdown completes.
    const redirectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

    useEffect(() => {
        if (!token) {
            setError('Invalid or missing password reset token in URL.');
        }
    }, [token]);

    useEffect(() => {
        return () => {
            if (redirectTimer.current) clearTimeout(redirectTimer.current);
        };
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!token) {
            setError('Cannot reset password. The token is missing from the URL.');
            return;
        }
        if (newPassword !== confirmPassword) {
            setError('The new passwords do not match.');
            return;
        }
        setLoading(true);
        setError('');
        setSuccess('');
        try {
            await resetPassword({ token, new_password: newPassword });
            setSuccess('Your password has been reset successfully! Redirecting to login...');
            redirectTimer.current = setTimeout(() => router.push('/login'), 3000);
        } catch (err) {
            setError(getErrorMessage(err, 'Failed to reset password. The token may be invalid or expired.'));
        } finally {
            setLoading(false);
        }
    };

    return (
        <AuthCard title="Set a New Password" subtitle="At least 8 characters.">
            {success ? (
                <p className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-3 text-center text-sm text-emerald-700 dark:text-emerald-300">
                    {success}
                </p>
            ) : (
                <form onSubmit={handleSubmit} className="space-y-5">
                    <div>
                        <FormLabel htmlFor="new-password">New Password</FormLabel>
                        <Input id="new-password" type="password" required minLength={8} autoComplete="new-password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} disabled={loading} />
                    </div>
                    <div>
                        <FormLabel htmlFor="confirm-password">Confirm New Password</FormLabel>
                        <Input id="confirm-password" type="password" required minLength={8} autoComplete="new-password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} disabled={loading} />
                    </div>
                    {error && (
                        <p className="rounded-xl border border-red-500/25 bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-300">
                            {error}
                        </p>
                    )}
                    <Button type="submit" disabled={loading || !token} className="w-full">{loading ? 'Resetting...' : 'Set New Password'}</Button>
                </form>
            )}
        </AuthCard>
    );
}

// We wrap the form in a Suspense boundary because useSearchParams() requires it.
export default function ResetPasswordPage() {
    return (
        <Suspense fallback={<div className="p-8 text-center">Loading...</div>}>
            <ResetPasswordForm />
        </Suspense>
    );
}