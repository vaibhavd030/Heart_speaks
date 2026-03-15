'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Search, BookOpen, BarChart3, Loader2, Users, MessageSquare, Shield, Clock } from 'lucide-react';
import { getIsAdmin } from '@/lib/auth';
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    LineChart,
    Line,
} from 'recharts';
import Image from 'next/image';
import { AuthGuard } from '@/components/AuthGuard';
import { PendingApprovals } from '@/components/PendingApprovals';
import { api } from '@/lib/api';

interface Stats {
    total_messages: number;
    total_pages: number;
    by_year: { year: string; count: number }[];
    by_month: { month: string; count: number }[];
    by_author: { author: string; count: number }[];
}

interface Message {
    message_id: string;
    source_file: string;
    author: string;
    date: string;
    preview: string;
    page_count: number;
}

interface MessagesResponse {
    total: number;
    page: number;
    limit: number;
    messages: Message[];
}

export default function Dashboard() {
    const [stats, setStats] = useState<Stats | null>(null);
    const [messagesData, setMessagesData] = useState<MessagesResponse | null>(null);
    const [loadingStats, setLoadingStats] = useState(true);
    const [loadingMessages, setLoadingMessages] = useState(true);
    const [isAdmin] = useState(() => getIsAdmin());

    const [searchQuery, setSearchQuery] = useState('');
    const [page, setPage] = useState(1);



    useEffect(() => {
        api.get('/stats')
            .then((res) => {
                setStats(res.data);
                setLoadingStats(false);
            })
            .catch((err) => {
                console.error('Failed to fetch stats:', err);
                setLoadingStats(false);
            });
    }, []);

    useEffect(() => {
        const fetchMessages = async () => {
            setLoadingMessages(true);
            try {
                const queryParam = searchQuery ? `&query=${encodeURIComponent(searchQuery)}` : '';
                const res = await api.get(`/messages?page=${page}&limit=10${queryParam}`);
                setMessagesData(res.data);
            } catch (err) {
                console.error('Failed to fetch messages:', err);
            } finally {
                setLoadingMessages(false);
            }
        };

        // Debounce search
        const timer = setTimeout(() => {
            fetchMessages();
        }, 300);

        return () => clearTimeout(timer);
    }, [searchQuery, page]);

    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const formattedMonthData = stats?.by_month.map(item => ({
        ...item,
        monthName: monthNames[parseInt(item.month) - 1] || item.month
    })) || [];

    return (
        <AuthGuard>
        <div className="min-h-screen bg-paper text-ink font-body relative overflow-x-hidden pb-12">
            {/* Background Texture & Pattern */}
            <div className="fixed inset-0 bg-[url('/parchment-bg.svg')] opacity-60 pointer-events-none z-0 mix-blend-multiply"></div>
            <div className="fixed inset-0 bg-[url('/floral-pattern.svg')] bg-[length:400px_400px] opacity-10 pointer-events-none z-0"></div>

            {/* Header */}
            <header className="relative z-20 pt-8 pb-4 px-8 max-w-7xl mx-auto flex items-center justify-between">
                <Link href="/" className="flex items-center gap-2 text-ink/70 hover:text-gold-accent transition-colors">
                    <ArrowLeft size={20} />
                    <span className="font-heading italic">Back to Sanctuary</span>
                </Link>
                <div className="text-center">
                    <h1 className="text-4xl font-serif italic text-ink drop-shadow-sm">Archive Dashboard</h1>
                </div>
                <div className="w-32"></div> {/* Spacer for alignment */}
            </header>

            <main className="relative z-20 max-w-7xl mx-auto px-4 sm:px-8 mt-8 space-y-12">
                {/* Statistics Section */}
                <section>
                    <div className="flex items-center gap-3 mb-6">
                        <BarChart3 className="text-gold-accent" />
                        <h2 className="text-3xl font-serif italic">Exploratory Data Analysis</h2>
                    </div>

                    {loadingStats ? (
                        <div className="flex items-center justify-center p-12">
                            <Loader2 className="animate-spin text-gold-accent" size={32} />
                        </div>
                    ) : stats ? (
                        <div className="space-y-8">
                            {/* KPI Cards */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                <div className="bg-white/60 backdrop-blur-sm p-6 rounded-2xl border border-gold-accent/20 shadow-sm text-center">
                                    <p className="text-ink/60 font-heading tracking-widest uppercase text-xs mb-2">Total Messages</p>
                                    <p className="text-4xl font-serif text-ink">{stats.total_messages.toLocaleString()}</p>
                                </div>
                                <div className="bg-white/60 backdrop-blur-sm p-6 rounded-2xl border border-gold-accent/20 shadow-sm text-center">
                                    <p className="text-ink/60 font-heading tracking-widest uppercase text-xs mb-2">Total Pages Scanned</p>
                                    <p className="text-4xl font-serif text-ink">{stats.total_pages.toLocaleString()}</p>
                                </div>
                                <div className="bg-white/60 backdrop-blur-sm p-6 rounded-2xl border border-gold-accent/20 shadow-sm text-center">
                                    <p className="text-ink/60 font-heading tracking-widest uppercase text-xs mb-2">Primary Author</p>
                                    <p className="text-2xl font-serif text-ink tracking-wide mt-2">
                                        {stats.by_author.length > 0 ? stats.by_author[0].author : "Unknown"}
                                    </p>
                                </div>
                            </div>

                            {/* Charts */}
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                                {/* Yearly Distribution */}
                                <div className="bg-white/60 backdrop-blur-sm p-6 rounded-2xl border border-gold-accent/20 shadow-sm">
                                    <h3 className="font-heading italic text-xl mb-6 text-center text-ink/80">Messages by Year</h3>
                                    <div className="h-64">
                                        <ResponsiveContainer width="100%" height="100%">
                                            <BarChart data={stats.by_year}>
                                                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
                                                <XAxis dataKey="year" stroke="#4b5563" fontSize={12} tickLine={false} axisLine={false} />
                                                <YAxis stroke="#4b5563" fontSize={12} tickLine={false} axisLine={false} />
                                                <Tooltip
                                                    cursor={{ fill: 'rgba(197, 160, 101, 0.1)' }}
                                                    contentStyle={{ backgroundColor: 'rgba(255,255,255,0.9)', borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                                                />
                                                <Bar dataKey="count" fill="#C5A065" radius={[4, 4, 0, 0]} />
                                            </BarChart>
                                        </ResponsiveContainer>
                                    </div>
                                </div>

                                {/* Monthly Distribution */}
                                <div className="bg-white/60 backdrop-blur-sm p-6 rounded-2xl border border-gold-accent/20 shadow-sm">
                                    <h3 className="font-heading italic text-xl mb-6 text-center text-ink/80">Seasonal Distribution (All Years)</h3>
                                    <div className="h-64">
                                        <ResponsiveContainer width="100%" height="100%">
                                            <LineChart data={formattedMonthData}>
                                                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
                                                <XAxis dataKey="monthName" stroke="#4b5563" fontSize={12} tickLine={false} axisLine={false} />
                                                <YAxis stroke="#4b5563" fontSize={12} tickLine={false} axisLine={false} />
                                                <Tooltip
                                                    contentStyle={{ backgroundColor: 'rgba(255,255,255,0.9)', borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                                                />
                                                <Line type="monotone" dataKey="count" stroke="#10b981" strokeWidth={3} dot={{ fill: '#10b981', strokeWidth: 2, r: 4 }} />
                                            </LineChart>
                                        </ResponsiveContainer>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <p className="text-center text-red-500">Failed to load statistics.</p>
                    )}
                </section>

                {/* Pending Approvals Section */}
                {stats && (
                    <section className="mt-12">
                        <PendingApprovals />
                    </section>
                )}

                {/* Seeker Features */}
                <section>
                    <div className="flex items-center gap-3 mb-6">
                        <MessageSquare className="text-gold-accent" />
                        <h2 className="text-3xl font-serif italic">My Personal Journey</h2>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <Link
                            href="/history"
                            className="bg-white/60 backdrop-blur-sm p-6 rounded-2xl border border-gold-accent/20 shadow-sm hover:shadow-md hover:border-gold-accent/50 transition-all group flex items-center gap-5"
                        >
                            <div className="w-14 h-14 rounded-full bg-gold-accent/10 flex items-center justify-center group-hover:bg-gold-accent/20 transition-colors">
                                <Clock className="w-7 h-7 text-gold-accent" />
                            </div>
                            <div>
                                <p className="font-heading font-bold text-sepia-dark uppercase tracking-wider text-sm">Inquiry History</p>
                                <p className="text-sepia-light text-xs mt-1">Review all your past questions and the guidance shared by SAGE</p>
                            </div>
                        </Link>
                        <Link
                            href="/bookmarks"
                            className="bg-white/60 backdrop-blur-sm p-6 rounded-2xl border border-gold-accent/20 shadow-sm hover:shadow-md hover:border-gold-accent/50 transition-all group flex items-center gap-5"
                        >
                            <div className="w-14 h-14 rounded-full bg-gold-accent/10 flex items-center justify-center group-hover:bg-gold-accent/20 transition-colors">
                                <BookOpen className="w-7 h-7 text-gold-accent" />
                            </div>
                            <div>
                                <p className="font-heading font-bold text-sepia-dark uppercase tracking-wider text-sm">Saved Reflections</p>
                                <p className="text-sepia-light text-xs mt-1">Access your bookmarked whispers and personal study notes</p>
                            </div>
                        </Link>
                    </div>
                </section>

                {/* Admin Sanctum — only for admins */}
                {isAdmin && (
                    <section>
                        <div className="flex items-center gap-3 mb-6">
                            <Shield className="text-gold-accent" />
                            <h2 className="text-3xl font-serif italic">Admin Sanctum</h2>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <Link
                                href="/admin/users"
                                className="bg-white/60 backdrop-blur-sm p-6 rounded-2xl border border-gold-accent/20 shadow-sm hover:shadow-md hover:border-gold-accent/50 transition-all group flex items-center gap-5"
                            >
                                <div className="w-14 h-14 rounded-full bg-gold-accent/10 flex items-center justify-center group-hover:bg-gold-accent/20 transition-colors">
                                    <Users className="w-7 h-7 text-gold-accent" />
                                </div>
                                <div>
                                    <p className="font-heading font-bold text-sepia-dark uppercase tracking-wider text-sm">All Seekers</p>
                                    <p className="text-sepia-light text-xs mt-1">View all registered users, their Abhyasi IDs, roles, and approval status</p>
                                </div>
                            </Link>
                            <Link
                                href="/admin/logs"
                                className="bg-white/60 backdrop-blur-sm p-6 rounded-2xl border border-gold-accent/20 shadow-sm hover:shadow-md hover:border-gold-accent/50 transition-all group flex items-center gap-5"
                            >
                                <div className="w-14 h-14 rounded-full bg-gold-accent/10 flex items-center justify-center group-hover:bg-gold-accent/20 transition-colors">
                                    <MessageSquare className="w-7 h-7 text-gold-accent" />
                                </div>
                                <div>
                                    <p className="font-heading font-bold text-sepia-dark uppercase tracking-wider text-sm">Chat Logs</p>
                                    <p className="text-sepia-light text-xs mt-1">Browse all seeker interactions — questions, responses, session IDs, and timestamps</p>
                                </div>
                            </Link>
                        </div>
                    </section>
                )}

                {/* Repository Search Section */}
                <section>
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center gap-3">
                            <BookOpen className="text-gold-accent" />
                            <h2 className="text-3xl font-serif italic">Repository Search</h2>
                        </div>

                        {/* Search Input */}
                        <div className="relative w-full max-w-md">
                            <input
                                type="text"
                                placeholder="Search messages, authors, or files..."
                                value={searchQuery}
                                onChange={(e) => {
                                    setSearchQuery(e.target.value);
                                    setPage(1); // Reset to first page on search
                                }}
                                className="w-full pl-10 pr-4 py-2 rounded-full border border-gold-accent/40 bg-white/70 backdrop-blur-sm focus:outline-none focus:ring-1 focus:ring-gold-accent shadow-sm"
                            />
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-ink/40 w-4 h-4" />
                        </div>
                    </div>

                    <div className="bg-white/60 backdrop-blur-sm rounded-2xl border border-gold-accent/20 shadow-sm overflow-hidden">
                        <div className="overflow-x-auto">
                            <table className="w-full text-left border-collapse">
                                <thead>
                                    <tr className="bg-gold-accent/5 border-b border-gold-accent/20 text-ink/70 uppercase text-xs tracking-wider">
                                        <th className="px-6 py-4 font-heading font-medium">Date</th>
                                        <th className="px-6 py-4 font-heading font-medium">Author</th>
                                        <th className="px-6 py-4 font-heading font-medium w-1/2">Message Preview</th>
                                        <th className="px-6 py-4 font-heading font-medium text-right">PDF</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-ink/5">
                                    {loadingMessages ? (
                                        <tr>
                                            <td colSpan={4} className="px-6 py-12 text-center">
                                                <Loader2 className="animate-spin text-gold-accent mx-auto" size={24} />
                                            </td>
                                        </tr>
                                    ) : messagesData && messagesData.messages.length > 0 ? (
                                        messagesData.messages.map((msg) => (
                                            <tr key={msg.message_id} className="hover:bg-white/50 transition-colors">
                                                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-ink/70">
                                                    {msg.date}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm font-heading font-bold text-ink">
                                                    {msg.author}
                                                </td>
                                                <td className="px-6 py-4 text-sm font-serif italic text-ink/80 text-justify">
                                                    {msg.preview}...
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                    <a
                                                        href={`${api.defaults.baseURL}/data/${msg.source_file}`}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="text-gold-accent hover:text-white hover:bg-gold-accent border border-gold-accent/30 px-3 py-1 rounded transition-colors inline-block"
                                                        title="Download PDF"
                                                    >
                                                        PDF
                                                    </a>
                                                </td>
                                            </tr>
                                        ))
                                    ) : (
                                        <tr>
                                            <td colSpan={4} className="px-6 py-12 text-center text-ink/50 italic font-serif">
                                                No messages found for your search query.
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>

                        {/* Pagination */}
                        {messagesData && messagesData.total > messagesData.limit && (
                            <div className="px-6 py-4 flex items-center justify-between border-t border-gold-accent/20 bg-gold-accent/5">
                                <span className="text-sm text-ink/60 font-heading">
                                    Showing {((page - 1) * messagesData.limit) + 1} to {Math.min(page * messagesData.limit, messagesData.total)} of {messagesData.total}
                                </span>
                                <div className="flex gap-2">
                                    <button
                                        disabled={page === 1}
                                        onClick={() => setPage(p => Math.max(1, p - 1))}
                                        className="px-3 py-1 rounded border border-gold-accent/30 text-gold-accent disabled:opacity-30 disabled:hover:bg-transparent hover:bg-gold-accent hover:text-white transition-colors text-sm"
                                    >
                                        Previous
                                    </button>
                                    <button
                                        disabled={page * messagesData.limit >= messagesData.total}
                                        onClick={() => setPage(p => p + 1)}
                                        className="px-3 py-1 rounded border border-gold-accent/30 text-gold-accent disabled:opacity-30 disabled:hover:bg-transparent hover:bg-gold-accent hover:text-white transition-colors text-sm"
                                    >
                                        Next
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </section>
            </main>
        </div>
        </AuthGuard>
    );
}
