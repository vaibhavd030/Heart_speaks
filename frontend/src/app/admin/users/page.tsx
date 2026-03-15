'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { ArrowLeft, Users, CheckCircle, XCircle, Shield, Mail, User, Calendar, PauseCircle, Trash2 } from 'lucide-react';
import { getAllUsers, approveUser, suspendUser, deleteUser } from '@/lib/api';
import { AuthGuard } from '@/components/AuthGuard';
import { clsx } from 'clsx';

interface UserData {
    user_id: string;
    first_name: string;
    last_name: string;
    email: string;
    abhyasi_id: string;
    status: 'pending' | 'approved' | 'rejected' | 'suspended';
    is_admin: boolean;
    created_at: string;
}

export default function AdminUsersPage() {
    const [users, setUsers] = useState<UserData[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

    const fetchUsers = async () => {
        try {
            setIsLoading(true);
            const data = await getAllUsers();
            setUsers(data);
        } catch (error) {
            console.error("Failed to fetch users:", error);
            setMessage({ type: 'error', text: 'Failed to load users' });
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => { fetchUsers(); }, []);

    const showMsg = (type: 'success' | 'error', text: string) => {
        setMessage({ type, text });
        setTimeout(() => setMessage(null), 3000);
    };

    const handleApproveReject = async (email: string, action: 'approve' | 'reject') => {
        try {
            await approveUser(email, action);
            showMsg('success', `User ${action}ed successfully`);
            fetchUsers();
        } catch (error) {
            console.error(`Failed to ${action} user:`, error);
            showMsg('error', `Failed to ${action} user`);
        }
    };

    const handleSuspend = async (userId: string, name: string) => {
        if (!window.confirm(`Suspend ${name}? They will not be able to log in.`)) return;
        try {
            await suspendUser(userId);
            showMsg('success', `${name} has been suspended`);
            fetchUsers();
        } catch (error) {
            console.error('Failed to suspend user:', error);
            showMsg('error', 'Failed to suspend user');
        }
    };

    const handleDelete = async (userId: string, name: string) => {
        if (!window.confirm(`⚠️ Permanently delete ${name} and ALL their data (bookmarks, chat history, progress)? This cannot be undone.`)) return;
        try {
            await deleteUser(userId);
            showMsg('success', `${name} and all their data have been deleted`);
            fetchUsers();
        } catch (error) {
            console.error('Failed to delete user:', error);
            showMsg('error', 'Failed to delete user');
        }
    };

    const statusBadge = (status: string) => clsx(
        "px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest",
        status === 'approved' ? "bg-green-100 text-green-700" :
        status === 'pending' ? "bg-yellow-100 text-yellow-700" :
        status === 'suspended' ? "bg-orange-100 text-orange-700" :
        "bg-red-100 text-red-700"
    );

    return (
        <AuthGuard requireAdmin>
            <div className="min-h-screen bg-parchment-light">
                {/* Header */}
                <header className="bg-white/80 backdrop-blur-md sticky top-0 z-10 border-b border-gold-accent/20">
                    <div className="max-w-7xl mx-auto px-4 h-16 flex items-center gap-4">
                        <Link href="/dashboard" className="p-2 hover:bg-gold-accent/10 rounded-full transition-colors text-sepia-dark">
                            <ArrowLeft className="w-5 h-5" />
                        </Link>
                        <div className="flex items-center gap-2">
                            <Users className="w-6 h-6 text-gold-accent" />
                            <h1 className="text-xl font-heading font-bold text-sepia-dark uppercase tracking-wider">User Management</h1>
                        </div>
                    </div>
                </header>

                <main className="max-w-7xl mx-auto px-4 py-8">
                    {message && (
                        <div className={clsx(
                            "mb-6 p-4 rounded-lg flex items-center gap-3 animate-in fade-in slide-in-from-top-4 duration-300",
                            message.type === 'success' ? "bg-green-100 text-green-800 border border-green-200" : "bg-red-100 text-red-800 border border-red-200"
                        )}>
                            {message.type === 'success' ? <CheckCircle className="w-5 h-5" /> : <XCircle className="w-5 h-5" />}
                            <p className="font-medium">{message.text}</p>
                        </div>
                    )}

                    <div className="bg-white border border-gold-accent/20 rounded-xl overflow-hidden shadow-sm">
                        <div className="overflow-x-auto">
                            <table className="w-full text-left border-collapse">
                                <thead>
                                    <tr className="bg-gold-accent/5 border-b border-gold-accent/20">
                                        <th className="px-6 py-4 text-xs font-heading font-bold uppercase tracking-wider text-sepia-dark">User</th>
                                        <th className="px-6 py-4 text-xs font-heading font-bold uppercase tracking-wider text-sepia-dark">Abhyasi ID</th>
                                        <th className="px-6 py-4 text-xs font-heading font-bold uppercase tracking-wider text-sepia-dark">Status</th>
                                        <th className="px-6 py-4 text-xs font-heading font-bold uppercase tracking-wider text-sepia-dark">Role</th>
                                        <th className="px-6 py-4 text-xs font-heading font-bold uppercase tracking-wider text-sepia-dark">Joined</th>
                                        <th className="px-6 py-4 text-xs font-heading font-bold uppercase tracking-wider text-sepia-dark">Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {isLoading ? (
                                        <tr><td colSpan={6} className="px-6 py-12 text-center text-sepia-light italic">Consulting the registers...</td></tr>
                                    ) : users.length === 0 ? (
                                        <tr><td colSpan={6} className="px-6 py-12 text-center text-sepia-light italic">No spiritual seekers found in the records.</td></tr>
                                    ) : (
                                        users.map((user) => (
                                            <tr key={user.user_id} className="border-b border-gold-accent/10 hover:bg-gold-accent/5 transition-colors">
                                                <td className="px-6 py-4">
                                                    <div className="flex items-center gap-3">
                                                        <div className="w-10 h-10 rounded-full bg-gold-accent/10 flex items-center justify-center text-gold-accent font-bold">
                                                            {user.first_name[0]}{user.last_name[0]}
                                                        </div>
                                                        <div>
                                                            <div className="font-heading font-bold text-sepia-dark">{user.first_name} {user.last_name}</div>
                                                            <div className="text-sm text-sepia-light flex items-center gap-1">
                                                                <Mail className="w-3 h-3" /> {user.email}
                                                            </div>
                                                        </div>
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 text-sm font-medium text-sepia-dark uppercase tracking-tight font-mono">{user.abhyasi_id}</td>
                                                <td className="px-6 py-4">
                                                    <span className={statusBadge(user.status)}>{user.status}</span>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <div className="flex items-center gap-1 text-sm text-sepia-dark">
                                                        {user.is_admin ? (
                                                            <><Shield className="w-3 h-3 text-gold-accent" /><span className="font-semibold text-gold-accent">Admin</span></>
                                                        ) : (
                                                            <><User className="w-3 h-3 text-sepia-light" /><span>Seeker</span></>
                                                        )}
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 text-sm text-sepia-light whitespace-nowrap">
                                                    <div className="flex items-center gap-1">
                                                        <Calendar className="w-3 h-3" />
                                                        {new Date(user.created_at).toLocaleDateString()}
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4">
                                                    {!user.is_admin && (
                                                        <div className="flex gap-2 flex-wrap">
                                                            {user.status === 'pending' && (
                                                                <>
                                                                    <button onClick={() => handleApproveReject(user.email, 'approve')}
                                                                        className="p-1.5 bg-green-500 hover:bg-green-600 text-white rounded transition-colors" title="Approve">
                                                                        <CheckCircle className="w-4 h-4" />
                                                                    </button>
                                                                    <button onClick={() => handleApproveReject(user.email, 'reject')}
                                                                        className="p-1.5 bg-red-400 hover:bg-red-500 text-white rounded transition-colors" title="Reject">
                                                                        <XCircle className="w-4 h-4" />
                                                                    </button>
                                                                </>
                                                            )}
                                                            {user.status === 'approved' && (
                                                                <button onClick={() => handleSuspend(user.user_id, `${user.first_name} ${user.last_name}`)}
                                                                    className="p-1.5 bg-amber-500 hover:bg-amber-600 text-white rounded transition-colors" title="Suspend">
                                                                    <PauseCircle className="w-4 h-4" />
                                                                </button>
                                                            )}
                                                            {user.status === 'suspended' && (
                                                                <button onClick={() => handleApproveReject(user.email, 'approve')}
                                                                    className="p-1.5 bg-green-500 hover:bg-green-600 text-white rounded transition-colors" title="Reinstate">
                                                                    <CheckCircle className="w-4 h-4" />
                                                                </button>
                                                            )}
                                                            <button onClick={() => handleDelete(user.user_id, `${user.first_name} ${user.last_name}`)}
                                                                className="p-1.5 bg-red-600 hover:bg-red-700 text-white rounded transition-colors" title="Delete permanently">
                                                                <Trash2 className="w-4 h-4" />
                                                            </button>
                                                        </div>
                                                    )}
                                                </td>
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </main>
            </div>
        </AuthGuard>
    );
}
