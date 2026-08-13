// src/app/change-password/page.tsx

'use client';
import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { changePassword } from '@/services/authService';
import { getErrorMessage } from '@/lib/errors';
import AuthCard from '@/components/ui/AuthCard';
import Input from '@/components/ui/Input';
import Button from '@/components/ui/Button';
import FormLabel from '@/components/ui/FormLabel';

export default function ChangePasswordPage() {
    const [oldPassword, setOldPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [loading, setLoading] = useState(false);
    const router = useRouter();

    const redirectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

    useEffect(() => {
        return () => {
            if (redirectTimer.current) clearTimeout(redirectTimer.current);
        };
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (newPassword !== confirmPassword) {
            setError('New passwords do not match.');
            return;
        }
        setLoading(true);
        setError('');
        setSuccess('');
        try {
            await changePassword({ old_password: oldPassword, new_password: newPassword });
            setSuccess('Password changed successfully! Redirecting to your profile...');
            redirectTimer.current = setTimeout(() => router.push('/profile'), 2000);
        } catch (err) {
            setError(getErrorMessage(err, 'Failed to change password. Check your old password.'));
        } finally {
            setLoading(false);
        }
    };

    return (
        // AuthCard already centres itself in a full-height frame; the extra
        // wrapper used to add a second one and pushed the card off-centre.
        <AuthCard title="Change Your Password" subtitle="You'll stay signed in on this device.">
            <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                    <FormLabel htmlFor="old-password">Current Password</FormLabel>
                    <Input id="old-password" type="password" required autoComplete="current-password" value={oldPassword} onChange={(e) => setOldPassword(e.target.value)} />
                </div>
                <div>
                    <FormLabel htmlFor="new-password">New Password</FormLabel>
                    <Input id="new-password" type="password" required minLength={8} autoComplete="new-password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
                </div>
                <div>
                    <FormLabel htmlFor="confirm-password">Confirm New Password</FormLabel>
                    <Input id="confirm-password" type="password" required minLength={8} autoComplete="new-password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
                </div>
                {error && (
                    <p className="rounded-xl border border-red-500/25 bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-300">
                        {error}
                    </p>
                )}
                {success && (
                    <p className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-300">
                        {success}
                    </p>
                )}
                <Button type="submit" disabled={loading} className="w-full">{loading ? 'Saving...' : 'Save New Password'}</Button>
            </form>
        </AuthCard>
    );
}