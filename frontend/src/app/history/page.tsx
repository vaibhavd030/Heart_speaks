'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { ArrowLeft, MessageSquare, Clock, Trash2, Calendar, User, Search, RefreshCw, AlertCircle } from 'lucide-react';
import { getUserChatLogs, deleteChatLog } from '@/lib/api';
import { AuthGuard } from '@/components/AuthGuard';

interface ChatLog {
    id: string;
    question: string;
    response: string;
    created_at: string;
    session_id: string;
}

export default function HistoryPage() {
    const [logs, setLogs] = useState<ChatLog[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [searchQuery, setSearchQuery] = useState('');

    useEffect(() => {
        fetchLogs();
    }, []);

    const fetchLogs = async () => {
        setIsLoading(true);
        setErrorMessage(null);
        try {
            const data = await getUserChatLogs();
            setLogs(data);
        } catch (error) {
            console.error("Failed to fetch chat logs:", error);
            setErrorMessage("The records of your journey are currently beyond reach. Please try again in a moment.");
        } finally {
            setIsLoading(false);
        }
    };

    const handleDelete = async (logId: string) => {
        if (!confirm("Are you sure you want to delete this chat entry?")) return;
        
        try {
            await deleteChatLog(logId);
            setLogs(prev => prev.filter(log => log.id !== logId));
        } catch (error) {
            console.error("Failed to delete chat log:", error);
            alert("Failed to delete log entry.");
        }
    };

    const filteredLogs = logs.filter(log => 
        log.question.toLowerCase().includes(searchQuery.toLowerCase()) || 
        log.response.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <AuthGuard>
        <div className="min-h-screen bg-paper text-ink font-body relative overflow-y-auto pb-24">
            <div className="fixed inset-0 bg-[url('/parchment-bg.svg')] opacity-60 pointer-events-none z-0 mix-blend-multiply"></div>

            <header className="relative z-10 pt-16 pb-8 px-8 text-center bg-transparent">
                <h1 className="text-4xl md:text-5xl font-serif italic text-ink drop-shadow-sm mb-4 flex items-center justify-center gap-3">
                    <MessageSquare className="text-gold-accent opacity-80" />
                    Journey History
                </h1>
                <p className="text-lg font-heading italic text-ink/70 max-w-2xl mx-auto">
                    A record of your inquiries and the whispers received in return.
                </p>

                <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mt-8">
                    <Link href="/dashboard" className="inline-flex items-center gap-2 text-gold-accent hover:text-ink transition-colors font-heading text-sm uppercase tracking-wider font-semibold border border-gold-accent/30 bg-gold-accent/5 px-5 py-2.5 rounded-full group">
                        <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
                        Dashboard
                    </Link>
                    
                    <div className="relative w-full max-w-xs">
                        <input
                            type="text"
                            placeholder="Search your history..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 rounded-full border border-gold-accent/30 bg-white/50 backdrop-blur-sm focus:outline-none focus:ring-1 focus:ring-gold-accent text-sm"
                        />
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gold-accent/50" size={16} />
                    </div>
                </div>
            </header>

            <main className="relative z-10 max-w-4xl mx-auto px-4 sm:px-8 mt-4">
                {isLoading ? (
                    <div className="flex justify-center items-center py-20 opacity-70">
                        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-gold-accent"></div>
                    </div>
                ) : errorMessage ? (
                    <div className="bg-white/40 backdrop-blur-sm border border-red-500/20 rounded-2xl p-12 text-center text-red-500 font-serif italic">
                        <AlertCircle className="mx-auto mb-4 opacity-50" size={32} />
                        <p className="text-xl">{errorMessage}</p>
                        <button 
                            onClick={fetchLogs}
                            className="mt-6 inline-flex items-center gap-2 text-gold-accent hover:text-sepia-dark transition-colors font-heading text-sm uppercase font-bold"
                        >
                            <RefreshCw size={16} />
                            Retry Search
                        </button>
                    </div>
                ) : filteredLogs.length === 0 ? (
                    <div className="bg-white/40 backdrop-blur-sm border border-gold-accent/20 rounded-2xl p-12 text-center text-ink/60 font-serif italic">
                        <p className="text-xl">Your journey is just beginning.</p>
                        <p className="mt-2 text-base font-sans not-italic font-light">
                            {searchQuery ? "No inquiries match your search." : "Ask SAGE a question to start your record."}
                        </p>
                    </div>
                ) : (
                    <div className="space-y-6">
                        {filteredLogs.map((log) => (
                            <div key={log.id} className="bg-white/60 backdrop-blur-sm border border-gold-accent/10 rounded-2xl shadow-sm hover:shadow-md transition-all overflow-hidden">
                                <div className="p-6">
                                    <div className="flex items-center justify-between mb-4 border-b border-gold-accent/10 pb-3">
                                        <div className="flex items-center gap-4 text-[10px] uppercase tracking-widest font-heading text-ink/40">
                                            <span className="flex items-center gap-1">
                                                <Calendar size={12} className="text-gold-accent/50" />
                                                {log.created_at ? new Date(log.created_at).toLocaleDateString() : "Date Unknown"}
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <Clock size={12} className="text-gold-accent/50" />
                                                {log.created_at ? new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "Time Unknown"}
                                            </span>
                                        </div>
                                        <button 
                                            onClick={() => handleDelete(log.id)}
                                            className="text-ink/20 hover:text-red-500 transition-colors"
                                            title="Delete this entry"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </div>

                                    <div className="space-y-4">
                                        <div>
                                            <p className="text-[10px] uppercase tracking-widest font-heading text-gold-accent font-bold mb-1">Inquiry</p>
                                            <p className="font-serif text-lg text-ink/90 leading-tight">{log.question}</p>
                                        </div>
                                        <div className="pl-4 border-l-2 border-gold-accent/20 py-1">
                                            <p className="text-[10px] uppercase tracking-widest font-heading text-ink/40 mb-1">The Response</p>
                                            <p className="font-serif italic text-ink/70 leading-relaxed text-sm">
                                                {log.response}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </main>
        </div>
        </AuthGuard>
    );
}
