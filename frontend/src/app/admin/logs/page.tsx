'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { ArrowLeft, MessageSquare, Search, ChevronDown, ChevronUp, User, Trash2 } from 'lucide-react';
import { getAllChatLogs, adminDeleteChatLog } from '@/lib/api';
import { AuthGuard } from '@/components/AuthGuard';

interface ChatLog {
    id: string;
    session_id: string;
    user_id: string;
    question: string;
    response: string;
    metadata: string;
    created_at: string;
    first_name: string;
    last_name: string;
    email: string;
    abhyasi_id: string;
}

export default function AdminLogsPage() {
    const [logs, setLogs] = useState<ChatLog[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [expandedId, setExpandedId] = useState<string | null>(null);
    const [page, setPage] = useState(0);
    const PAGE_SIZE = 50;

    useEffect(() => {
        const fetch = async () => {
            setIsLoading(true);
            try {
                const data = await getAllChatLogs(PAGE_SIZE, page * PAGE_SIZE);
                setLogs(data);
            } catch (e) {
                console.error('Failed to fetch logs:', e);
            } finally {
                setIsLoading(false);
            }
        };
        fetch();
    }, [page]);

    const handleDelete = async (logId: string) => {
        if (!confirm("Are you sure you want to delete this log entry? This action cannot be undone.")) return;
        
        try {
            await adminDeleteChatLog(logId);
            setLogs(prev => prev.filter(log => log.id !== logId));
            if (expandedId === logId) setExpandedId(null);
        } catch (error) {
            console.error("Failed to delete log:", error);
            alert("Failed to delete log entry.");
        }
    };

    const filtered = logs.filter(log =>
        log.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
        log.response.toLowerCase().includes(searchQuery.toLowerCase()) ||
        `${log.first_name} ${log.last_name}`.toLowerCase().includes(searchQuery.toLowerCase()) ||
        log.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
        log.abhyasi_id.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <AuthGuard requireAdmin>
            <div className="min-h-screen bg-parchment-light">
                {/* Header */}
                <header className="bg-white/80 backdrop-blur-md sticky top-0 z-10 border-b border-gold-accent/20">
                    <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <Link href="/dashboard" className="p-2 hover:bg-gold-accent/10 rounded-full transition-colors text-sepia-dark">
                                <ArrowLeft className="w-5 h-5" />
                            </Link>
                            <div className="flex items-center gap-2">
                                <MessageSquare className="w-6 h-6 text-gold-accent" />
                                <h1 className="text-xl font-heading font-bold text-sepia-dark uppercase tracking-wider">
                                    Chat Logs
                                </h1>
                            </div>
                        </div>
                        <div className="relative w-72">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-sepia-light" />
                            <input
                                type="text"
                                placeholder="Search by user, question, or response..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full pl-9 pr-4 py-2 rounded-full border border-gold-accent/30 bg-white/70 focus:outline-none focus:ring-1 focus:ring-gold-accent text-sm"
                            />
                        </div>
                    </div>
                </header>

                <main className="max-w-7xl mx-auto px-4 py-8 space-y-3">
                    {isLoading ? (
                        <div className="text-center py-24 text-sepia-light italic">
                            Consulting the Akashic records...
                        </div>
                    ) : filtered.length === 0 ? (
                        <div className="text-center py-24 text-sepia-light italic">
                            No interactions found.
                        </div>
                    ) : filtered.map((log) => (
                        <div
                            key={log.id}
                            className="bg-white border border-gold-accent/20 rounded-xl overflow-hidden shadow-sm"
                        >
                            {/* Summary row */}
                            <button
                                className="w-full text-left px-6 py-4 flex items-start gap-4 hover:bg-gold-accent/5 transition-colors"
                                onClick={() => setExpandedId(expandedId === log.id ? null : log.id)}
                            >
                                {/* User avatar */}
                                <div className="w-9 h-9 rounded-full bg-gold-accent/10 flex items-center justify-center text-gold-accent font-bold text-sm shrink-0 mt-0.5">
                                    {log.first_name?.[0]}{log.last_name?.[0]}
                                </div>

                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 flex-wrap">
                                        <span className="font-heading font-bold text-sepia-dark text-sm">
                                            {log.first_name} {log.last_name}
                                        </span>
                                        <span className="text-xs text-sepia-light">·</span>
                                        <span className="text-xs text-sepia-light font-mono">{log.abhyasi_id}</span>
                                        <span className="text-xs text-sepia-light">·</span>
                                        <span className="text-xs text-sepia-light">
                                            {new Date(log.created_at).toLocaleString()}
                                        </span>
                                        <span className="text-xs bg-gold-accent/10 text-gold-accent px-2 py-0.5 rounded-full font-mono truncate max-w-[200px]" title={log.session_id}>
                                            {log.session_id?.slice(0, 8)}...
                                        </span>
                                    </div>
                                    <p className="text-sm text-sepia-dark mt-1 truncate font-medium">
                                        Q: {log.question}
                                    </p>
                                    <p className="text-sm text-sepia-light mt-0.5 truncate italic">
                                        A: {log.response?.slice(0, 120)}...
                                    </p>
                                </div>

                                <div className="shrink-0 text-sepia-light ml-2">
                                    {expandedId === log.id
                                        ? <ChevronUp className="w-4 h-4" />
                                        : <ChevronDown className="w-4 h-4" />}
                                </div>
                            </button>

                            {/* Expanded detail */}
                            {expandedId === log.id && (
                                <div className="px-6 pb-6 border-t border-gold-accent/10 pt-4 space-y-4">
                                    <div className="flex items-center justify-between gap-2 text-xs text-sepia-light">
                                        <div className="flex items-center gap-2">
                                            <User className="w-3 h-3" />
                                            {log.email} · Session: <span className="font-mono">{log.session_id}</span>
                                        </div>
                                        <button 
                                            onClick={() => handleDelete(log.id)}
                                            className="flex items-center gap-1 text-red-500 hover:text-red-700 transition-colors font-heading uppercase tracking-tighter font-bold"
                                        >
                                            <Trash2 className="w-3 h-3" />
                                            Delete Log
                                        </button>
                                    </div>

                                    <div className="rounded-lg bg-gold-accent/5 border border-gold-accent/20 p-4">
                                        <p className="text-xs font-heading font-bold uppercase tracking-wider text-gold-accent mb-2">Question</p>
                                        <p className="text-sm text-sepia-dark leading-relaxed">{log.question}</p>
                                    </div>

                                    <div className="rounded-lg bg-parchment-light border border-gold-accent/10 p-4">
                                        <p className="text-xs font-heading font-bold uppercase tracking-wider text-sepia-light mb-2">Response</p>
                                        <p className="text-sm text-sepia-dark leading-relaxed whitespace-pre-wrap">{log.response}</p>
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}

                    {/* Pagination */}
                    <div className="flex justify-between items-center pt-4">
                        <button
                            disabled={page === 0}
                            onClick={() => setPage(p => Math.max(0, p - 1))}
                            className="px-4 py-2 rounded-lg border border-gold-accent/30 text-gold-accent disabled:opacity-30 hover:bg-gold-accent hover:text-white transition-colors text-sm font-heading"
                        >
                            Previous
                        </button>
                        <span className="text-sm text-sepia-light">Page {page + 1}</span>
                        <button
                            disabled={logs.length < PAGE_SIZE}
                            onClick={() => setPage(p => p + 1)}
                            className="px-4 py-2 rounded-lg border border-gold-accent/30 text-gold-accent disabled:opacity-30 hover:bg-gold-accent hover:text-white transition-colors text-sm font-heading"
                        >
                            Next
                        </button>
                    </div>
                </main>
            </div>
        </AuthGuard>
    );
}
