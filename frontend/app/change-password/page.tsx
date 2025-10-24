// src/app/change-password/page.tsx

'use client';
import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { changePassword } from '@/services/authService';
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
            setTimeout(() => router.push('/profile'), 2000);
        } catch (err) {
            setError(err.message || 'Failed to change password. Check your old password.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex justify-center items-center min-h-[calc(100vh-10rem)]">
            <AuthCard title="Change Your Password">
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <FormLabel htmlFor="old-password">Current Password</FormLabel>
                        <Input id="old-password" type="password" required value={oldPassword} onChange={(e) => setOldPassword(e.target.value)} />
                    </div>
                    <div>
                        <FormLabel htmlFor="new-password">New Password</FormLabel>
                        <Input id="new-password" type="password" required minLength={8} value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
                    </div>
                    <div>
                        <FormLabel htmlFor="confirm-password">Confirm New Password</FormLabel>
                        <Input id="confirm-password" type="password" required minLength={8} value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
                    </div>
                    {error && <p className="text-sm text-red-500">{error}</p>}
                    {success && <p className="text-sm text-green-500">{success}</p>}
                    <div className="pt-2">
                        <Button type="submit" disabled={loading}>{loading ? 'Saving...' : 'Save New Password'}</Button>
                    </div>
                </form>
            </AuthCard>
        </div>
    );
}