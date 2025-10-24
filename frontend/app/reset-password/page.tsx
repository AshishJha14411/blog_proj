// src/app/reset-password/page.tsx

'use client';
import React, { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { resetPassword } from '@/services/authService';
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

    useEffect(() => {
        if (!token) {
            setError('Invalid or missing password reset token in URL.');
        }
    }, [token]);

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
            setTimeout(() => router.push('/login'), 3000);
        } catch (err) {
            setError(err.message || 'Failed to reset password. The token may be invalid or expired.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <AuthCard title="Set a New Password">
            {success ? (
                <p className="text-center text-green-600">{success}</p>
            ) : (
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <FormLabel htmlFor="new-password">New Password</FormLabel>
                        <Input id="new-password" type="password" required minLength={8} value={newPassword} onChange={(e) => setNewPassword(e.target.value)} disabled={loading} />
                    </div>
                    <div>
                        <FormLabel htmlFor="confirm-password">Confirm New Password</FormLabel>
                        <Input id="confirm-password" type="password" required minLength={8} value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} disabled={loading} />
                    </div>
                    {error && <p className="text-sm text-red-500">{error}</p>}
                    <Button type="submit" disabled={loading || !token}>{loading ? 'Resetting...' : 'Set New Password'}</Button>
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