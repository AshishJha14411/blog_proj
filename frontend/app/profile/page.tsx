'use client';

import React, { useState, useEffect, ChangeEvent } from 'react';
import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import { updateUserProfile, uploadProfileImage } from '@/services/userService';
import { useAuthStore } from '@/stores/authStore';
import Avatar from '@/components/ui/Avatar';
import Badge from '@/components/ui/Badge';
import Input from '@/components/ui/Input';
import Textarea from '@/components/ui/Textarea';
import Button from '@/components/ui/Button';
import FormLabel from '@/components/ui/FormLabel';

interface ProfileFormData {
    bio: string;
    social_links: { twitter: string; github: string };
}

export default function ProfilePage() {
    const { user, isHydrated } = useAuth();
    const [isEditing, setIsEditing] = useState(false);

    // This state is now ONLY used for the edit form
    const [formData, setFormData] = useState<ProfileFormData>({ bio: '', social_links: { twitter: '', github: '' } });

    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    // When the component loads or the user object changes, sync the form data
    useEffect(() => {
        if (user) {
            setFormData({
                bio: user.bio || '',
                social_links: {
                    twitter: user.social_links?.twitter || '',
                    github: user.social_links?.github || '',
                },
            });
        }
    }, [user]);

    const handleTextChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        const { name, value } = e.target;
        if (name === 'twitter' || name === 'github') {
            setFormData(prev => ({ ...prev, social_links: { ...prev.social_links, [name]: value } }));
        } else {
            setFormData(prev => ({ ...prev, [name]: value }));
        }
    };

    const handleFileChange = async (e: ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setUploading(true);
        setError('');
        setSuccess('');
        try {
            const updatedUser = await uploadProfileImage(file);
            useAuthStore.setState({ user: updatedUser });
            setSuccess('Profile picture updated!');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Image upload failed.');
        } finally {
            setUploading(false);
        }
    };

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        setSuccess('');
        try {
            const updatedUser = await updateUserProfile(formData);
            useAuthStore.setState({ user: updatedUser });
            setSuccess('Profile updated successfully!');
            setIsEditing(false);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to update profile.');
        } finally {
            setLoading(false);
        }
    };

    const handleCancel = () => {
        // Revert form data back to the original user state
        if (user) {
             setFormData({
                bio: user.bio || '',
                social_links: {
                    twitter: user.social_links?.twitter || '',
                    github: user.social_links?.github || '',
                },
            });
        }
        setIsEditing(false);
        setError('');
        setSuccess('');
    };

    if (!isHydrated) {
        return (
            <div className="mx-auto max-w-3xl px-6 py-14">
                <div className="skeleton h-40 w-full rounded-3xl" />
                <div className="skeleton mt-8 h-64 w-full rounded-2xl" />
            </div>
        );
    }
    if (!user) {
        return (
            <div className="mx-auto max-w-lg px-6 py-24 text-center">
                <p className="font-display text-2xl font-bold text-text">You&apos;re signed out</p>
                <p className="mt-3 text-sm text-text-light">Please log in to view your profile.</p>
                <Link
                    href="/login"
                    className="mt-8 inline-flex rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-on-primary transition-colors hover:bg-primary-light"
                >
                    Log in
                </Link>
            </div>
        );
    }

    return (
        <main className="mx-auto max-w-3xl px-6 py-14">
            {/* Identity band — avatar, name, role, and the one primary action. */}
            <div className="relative overflow-hidden rounded-3xl border border-border-soft bg-surface p-8 shadow-soft">
                <div aria-hidden="true" className="aurora opacity-70" />
                <div className="relative flex flex-wrap items-center gap-6">
                    <Avatar name={user.username} src={user.profile_image_url} size="lg" />
                    <div className="min-w-0 flex-1">
                        <h1 className="font-display text-3xl font-bold text-text">{user.username}</h1>
                        <p className="mt-1 truncate text-sm text-text-light">{user.email}</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                            <Badge tone="rose" className="capitalize">{user.role?.name ?? 'reader'}</Badge>
                        </div>
                    </div>
                    {!isEditing && (
                        <Button onClick={() => setIsEditing(true)}>Edit Profile</Button>
                    )}
                </div>

                {isEditing && (
                    <div className="relative mt-8 border-t border-border-soft pt-6">
                        <FormLabel htmlFor="avatar-upload">Update Profile Picture</FormLabel>
                        <input
                            id="avatar-upload"
                            type="file"
                            accept="image/png, image/jpeg, image/gif"
                            onChange={handleFileChange}
                            disabled={uploading}
                            className="mt-2 text-sm text-text-light file:mr-4 file:rounded-full file:border-0 file:bg-primary/15 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-primary-strong hover:file:bg-primary hover:file:text-on-primary"
                        />
                        {uploading && <p className="mt-2 text-sm text-text-subtle">Uploading...</p>}
                    </div>
                )}
            </div>

            <form
                onSubmit={handleSave}
                className="mt-8 space-y-6 rounded-2xl border border-border-soft bg-surface p-8 shadow-soft"
            >
                <div>
                    <FormLabel htmlFor="bio">Bio</FormLabel>
                    {isEditing ? (
                        <Textarea id="bio" name="bio" rows={4} value={formData.bio} onChange={handleTextChange} placeholder="Tell us a little about yourself..." />
                    ) : (
                        // --- FIX: Display data directly from the 'user' object in view mode ---
                        <p className="mt-2 min-h-[3rem] text-sm leading-relaxed text-text-light">
                            {user.bio || 'No bio yet.'}
                        </p>
                    )}
                </div>

                <div className="grid gap-6 sm:grid-cols-2">
                    <div>
                        <FormLabel htmlFor="twitter">Twitter</FormLabel>
                        {isEditing ? (
                            <Input id="twitter" name="twitter" type="text" value={formData.social_links.twitter} onChange={handleTextChange} placeholder="yourhandle" />
                        ) : (
                            // --- FIX: Use an anchor tag for clickable links ---
                            <div className="mt-2 min-h-[1.75rem] text-sm">
                                {user.social_links?.twitter ? (
                                    <a href={`https://twitter.com/${user.social_links.twitter}`} target="_blank" rel="noopener noreferrer" className="font-medium text-primary-strong hover:underline">
                                        @{user.social_links.twitter}
                                    </a>
                                ) : (
                                    <p className="text-text-subtle">Not provided.</p>
                                )}
                            </div>
                        )}
                    </div>
                    <div>
                        <FormLabel htmlFor="github">GitHub</FormLabel>
                        {isEditing ? (
                            <Input id="github" name="github" type="text" value={formData.social_links.github} onChange={handleTextChange} placeholder="your-github" />
                        ) : (
                            // --- FIX: Use an anchor tag for clickable links ---
                            <div className="mt-2 min-h-[1.75rem] text-sm">
                                {user.social_links?.github ? (
                                    <a href={`https://github.com/${user.social_links.github}`} target="_blank" rel="noopener noreferrer" className="font-medium text-primary-strong hover:underline">
                                        {user.social_links.github}
                                    </a>
                                ) : (
                                    <p className="text-text-subtle">Not provided.</p>
                                )}
                            </div>
                        )}
                    </div>
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

                <div className="flex items-center gap-3 border-t border-border-soft pt-6">
                    {isEditing ? (
                        <>
                            <Button type="submit" disabled={loading}> {loading ? 'Saving...' : 'Save Changes'} </Button>
                            <Button variant="secondary" type="button" onClick={handleCancel}> Cancel </Button>
                        </>
                    ) : (
                        <Button variant="secondary" asChild>
                            <Link href="/change-password">Change Password</Link>
                        </Button>
                    )}
                </div>
            </form>
        </main>
    );
}
