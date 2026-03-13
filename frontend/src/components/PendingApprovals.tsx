'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Check, X, UserX, Loader2, Clock } from 'lucide-react';

interface PendingUser {
    user_id: string;
    first_name: string;
    last_name: string;
    email: string;
    abhyasi_id: string;
    created_at: string;
}

export function PendingApprovals() {
    const [users, setUsers] = useState<PendingUser[]>([]);
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState<string | null>(null);

    const fetchPending = async () => {
        try {
            const res = await api.get('/admin/users/pending');
            setUsers(res.data);
        } catch (err) {
            console.error('Failed to fetch pending users:', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchPending();
    }, []);

    const handleAction = async (email: string, action: 'approve' | 'reject') => {
        setActionLoading(email);
        try {
            await api.post('/admin/users/approve', { email, action });
            setUsers(users.filter(u => u.email !== email));
        } catch (err) {
            console.error(`Failed to ${action} user:`, err);
        } finally {
            setActionLoading(null);
        }
    };

    if (loading) return (
        <div className="flex justify-center p-8">
            <Loader2 className="animate-spin text-gold-accent" />
        </div>
    );

    if (users.length === 0) return null;

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-3">
                <Clock className="text-gold-accent" />
                <h2 className="text-3xl font-serif italic">Pending Approvals</h2>
            </div>
            
            <div className="bg-white/60 backdrop-blur-sm rounded-2xl border border-gold-accent/20 shadow-sm overflow-hidden">
                <table className="w-full text-left">
                    <thead className="bg-gold-accent/5 border-b border-gold-accent/20 text-ink/70 uppercase text-xs tracking-wider">
                        <tr>
                            <th className="px-6 py-4 font-heading font-medium">Name</th>
                            <th className="px-6 py-4 font-heading font-medium">Email</th>
                            <th className="px-6 py-4 font-heading font-medium">Abhyasi ID</th>
                            <th className="px-6 py-4 font-heading font-medium text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-ink/5">
                        {users.map((user) => (
                            <tr key={user.user_id} className="hover:bg-white/50 transition-colors">
                                <td className="px-6 py-4 text-sm font-heading text-ink">
                                    {user.first_name} {user.last_name}
                                </td>
                                <td className="px-6 py-4 text-sm font-mono text-ink/70">
                                    {user.email}
                                </td>
                                <td className="px-6 py-4 text-sm font-body text-ink/80">
                                    {user.abhyasi_id}
                                </td>
                                <td className="px-6 py-4 text-right space-x-2">
                                    <button
                                        onClick={() => handleAction(user.email, 'approve')}
                                        disabled={!!actionLoading}
                                        className="p-2 text-green-600 hover:bg-green-50 rounded-full transition-colors disabled:opacity-30"
                                        title="Approve"
                                    >
                                        {actionLoading === user.email ? <Loader2 className="animate-spin w-5 h-5" /> : <Check size={20} />}
                                    </button>
                                    <button
                                        onClick={() => handleAction(user.email, 'reject')}
                                        disabled={!!actionLoading}
                                        className="p-2 text-red-600 hover:bg-red-50 rounded-full transition-colors disabled:opacity-30"
                                        title="Reject"
                                    >
                                        <X size={20} />
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
