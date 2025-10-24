'use client';

import React, { useState, useEffect, ChangeEvent } from 'react';
import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import { updateUserProfile, uploadProfileImage } from '@/services/userService';
import { useAuthStore } from '@/stores/authStore';
import Input from '@/components/ui/Input';
import Textarea from '@/components/ui/Textarea';
import Button from '@/components/ui/Button';
import FormLabel from '@/components/ui/FormLabel';

export default function ProfilePage() {
    const { user, isHydrated } = useAuth();
    const [isEditing, setIsEditing] = useState(false);
    
    // This state is now ONLY used for the edit form
    const [formData, setFormData] = useState({ bio: '', social_links: { twitter: '', github: '' } });
    
    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    // When the component loads or the user object changes, sync the form data
    useEffect(() => {
        console.log(user)
        if (user) {
            setFormData({
                bio: user.bio || '',
                social_links: user.social_links || { twitter: '', github: '' },
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
            setError(err.message || 'Image upload failed.');
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
            setError(err.message || 'Failed to update profile.');
        } finally {
            setLoading(false);
        }
    };

    const handleCancel = () => {
        // Revert form data back to the original user state
        if (user) {
             setFormData({
                bio: user.bio || '',
                social_links: user.social_links || { twitter: '', github: '' },
            });
        }
        setIsEditing(false);
        setError('');
        setSuccess('');
    };

    if (!isHydrated) {
        return <div className="p-8 text-center">Loading profile...</div>;
    }
    if (!user) {
        return <div className="p-8 text-center">Please log in to view your profile.</div>;
    }

    return (
        <div className="max-w-2xl mx-auto p-8">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-3xl font-bold text-[var(--text-main)]">Your Profile</h1>
                {!isEditing && (
                    <Button onClick={() => setIsEditing(true)}>Edit Profile</Button>
                )}
            </div>

            <div className="flex items-center gap-6 mb-8">
                <img 
                    src={user.profile_image_url || `https://ui-avatars.com/api/?name=${user.username}&background=random`}
                    alt="Profile Avatar"
                    className="w-24 h-24 rounded-full object-cover border-4 border-[var(--border-color)]"
                />
                 {isEditing && (
                    <div>
                        <FormLabel htmlFor="avatar-upload">Update Profile Picture</FormLabel>
                        <input 
                            id="avatar-upload"
                            type="file"
                            accept="image/png, image/jpeg, image/gif"
                            onChange={handleFileChange}
                            disabled={uploading}
                            className="text-sm file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-[var(--accent-primary-light)] file:text-[var(--accent-primary)] hover:file:bg-[var(--accent-primary)] hover:file:text-white"
                        />
                         {uploading && <p className="text-sm text-[var(--text-subtle)] mt-2">Uploading...</p>}
                    </div>
                 )}
            </div>

            <form onSubmit={handleSave} className="space-y-6">
                <div>
                    <FormLabel htmlFor="bio">Bio</FormLabel>
                    {isEditing ? (
                        <Textarea id="bio" name="bio" rows={4} value={formData.bio} onChange={handleTextChange} placeholder="Tell us a little about yourself..." />
                    ) : (
                        // --- FIX: Display data directly from the 'user' object in view mode ---
                        <p className="p-2 text-[var(--text-body)] min-h-[6rem]">{user.bio || 'No bio yet.'}</p>
                    )}
                </div>
                <div>
                    <FormLabel htmlFor="twitter">Twitter</FormLabel>
                    {isEditing ? (
                        <Input id="twitter" name="twitter" type="text" value={formData.social_links.twitter} onChange={handleTextChange} placeholder="yourhandle" />
                    ) : (
                        // --- FIX: Use an anchor tag for clickable links ---
                        <div className="p-2 min-h-[2.5rem]">
                            {user.social_links?.twitter ? (
                                <a href={`https://twitter.com/${user.social_links.twitter}`} target="_blank" rel="noopener noreferrer" className="text-[var(--accent-primary)] hover:underline">
                                    {user.social_links.twitter}
                                </a>
                            ) : (
                                <p className="text-[var(--text-subtle)]">Not provided.</p>
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
                        <div className="p-2 min-h-[2.5rem]">
                             {user.social_links?.github ? (
                                <a href={`https://github.com/${user.social_links.github}`} target="_blank" rel="noopener noreferrer" className="text-[var(--accent-primary)] hover:underline">
                                    {user.social_links.github}
                                </a>
                            ) : (
                                <p className="text-[var(--text-subtle)]">Not provided.</p>
                            )}
                        </div>
                    )}
                </div>
                
                {error && <p className="text-sm text-red-500">{error}</p>}
                {success && <p className="text-sm text-green-500">{success}</p>}

                <div className="pt-4 flex items-center gap-4">
                    {isEditing ? (
                        <>
                            <Button type="submit" onClick={handleSave} disabled={loading}> {loading ? 'Saving...' : 'Save Changes'} </Button>
                            <Button variant="secondary" type="button" onClick={handleCancel}> Cancel </Button>
                        </>
                    ) : (
                        <Link href="/change-password">
                            <Button variant="secondary">Change Password</Button>
                        </Link>
                    )}
                </div>
            </form>
        </div>
    );
}

