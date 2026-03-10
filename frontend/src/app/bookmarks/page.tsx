'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { ArrowLeft, BookOpen, Clock, FileText, Trash2 } from 'lucide-react';
import { getBookmarks, removeBookmark } from '@/lib/api';

interface BookmarkMsg {
    source_file: string;
    notes: string;
    created_at: string;
    date: string;
    preview: string;
    author: string;
    page_count: number;
}

export default function BookmarksPage() {
    const [bookmarks, setBookmarks] = useState<BookmarkMsg[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        fetchBookmarks();
    }, []);

    const fetchBookmarks = async () => {
        setIsLoading(true);
        try {
            const data = await getBookmarks();
            setBookmarks(data);
        } catch (error) {
            console.error("Failed to fetch bookmarks:", error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleDelete = async (source_file: string) => {
        try {
            await removeBookmark(source_file);
            setBookmarks(prev => prev.filter(b => b.source_file !== source_file));
        } catch (error) {
            console.error("Failed to delete bookmark:", error);
        }
    };

    return (
        <div className="min-h-screen bg-paper text-ink font-body relative overflow-y-auto pb-24">
            {/* Background Texture Line */}
            <div className="fixed inset-0 bg-[url('/parchment-bg.svg')] opacity-60 pointer-events-none z-0 mix-blend-multiply"></div>

            <header className="relative z-10 pt-16 pb-8 px-8 text-center bg-transparent">
                <h1 className="text-4xl md:text-5xl font-serif italic text-ink drop-shadow-sm mb-4 flex items-center justify-center gap-3">
                    <BookOpen className="text-gold-accent opacity-80" />
                    Saved Reflections
                </h1>
                <p className="text-lg font-heading italic text-ink/70 max-w-2xl mx-auto">
                    A collection of your bookmarked whispers and personal notes, ordered by the whispers' chronological date.
                </p>

                <Link href="/" className="inline-flex items-center gap-2 mt-8 text-gold-accent hover:text-ink transition-colors font-heading text-sm uppercase tracking-wider font-semibold border border-gold-accent/30 bg-gold-accent/5 px-5 py-2.5 rounded-full group">
                    <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
                    Return to SAGE
                </Link>
            </header>

            <main className="relative z-10 max-w-4xl mx-auto px-4 sm:px-8">
                {isLoading ? (
                    <div className="flex justify-center items-center py-20 opacity-70">
                        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-gold-accent"></div>
                    </div>
                ) : bookmarks.length === 0 ? (
                    <div className="bg-white/40 backdrop-blur-sm border border-gold-accent/20 rounded-2xl p-12 text-center text-ink/60 font-serif italic">
                        <p className="text-xl">You haven&apos;t saved any reflections yet.</p>
                        <p className="mt-2 text-base font-sans not-italic font-light">Explore the Reader Mode to bookmark meaningful messages.</p>
                        <Link href="/reader" className="inline-block mt-6 px-6 py-2 bg-white rounded-full shadow-sm text-gold-accent border border-gold-accent/30 hover:bg-gold-accent hover:text-white transition-all not-italic font-heading font-semibold uppercase text-xs tracking-wider">
                            Go to Reader
                        </Link>
                    </div>
                ) : (
                    <div className="relative border-l border-gold-accent/30 ml-4 sm:ml-6 pl-6 sm:pl-8 space-y-12 pb-12">
                        {bookmarks.map((bookmark) => (
                            <div key={bookmark.source_file} className="relative group">
                                {/* Timeline Dot */}
                                <div className="absolute -left-[31px] sm:-left-[39px] top-6 w-3 h-3 bg-gold-accent rounded-full shadow-[0_0_10px_rgba(197,160,101,0.5)] ring-4 ring-paper"></div>

                                <div className="bg-white/60 backdrop-blur-sm border border-ink/5 rounded-2xl shadow-sm hover:shadow-md transition-all group-hover:-translate-y-1 overflow-hidden flex flex-col sm:flex-row">

                                    {/* Left: Metadata */}
                                    <div className="sm:w-1/3 p-6 border-b sm:border-b-0 sm:border-r border-ink/5 flex flex-col justify-between bg-white/40">
                                        <div>
                                            <div className="font-heading font-bold text-lg text-ink flex flex-col mb-1 whitespace-pre-wrap">
                                                {bookmark.date}
                                            </div>
                                            <div className="text-xs uppercase tracking-widest text-ink/40 mb-4">{bookmark.author} • Whisper</div>

                                            <p className="font-serif italic text-sm text-ink/70 leading-relaxed line-clamp-4">
                                                "{bookmark.preview}..."
                                            </p>
                                        </div>

                                        <div className="mt-6 flex flex-col gap-2">
                                            <a
                                                href={`http://localhost:8000/data/${bookmark.source_file}`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="flex items-center justify-center gap-2 w-full py-2 bg-gold-accent/10 hover:bg-gold-accent text-gold-accent hover:text-white rounded-lg transition-colors font-heading text-xs uppercase tracking-wider font-semibold"
                                            >
                                                <FileText size={14} /> Open PDF
                                            </a>
                                            <button
                                                onClick={() => handleDelete(bookmark.source_file)}
                                                className="flex items-center justify-center gap-2 w-full py-2 bg-transparent text-ink/30 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors font-heading text-xs uppercase tracking-wider font-semibold"
                                            >
                                                <Trash2 size={14} /> Remove
                                            </button>
                                        </div>
                                    </div>

                                    {/* Right: Notes */}
                                    <div className="sm:w-2/3 p-6 flex flex-col">
                                        <div className="flex items-center gap-2 mb-4 text-xs font-heading uppercase tracking-widest text-gold-accent font-semibold border-b border-gold-accent/10 pb-2">
                                            <BookOpen size={14} /> Your Notes
                                        </div>

                                        {bookmark.notes ? (
                                            <div className="font-serif text-[15px] leading-relaxed text-ink/90 whitespace-pre-wrap">
                                                {bookmark.notes}
                                            </div>
                                        ) : (
                                            <div className="font-serif italic text-ink/40 m-auto">
                                                No personal notes added.
                                            </div>
                                        )}

                                        <div className="mt-auto pt-4 flex items-center justify-end">
                                            <span className="flex items-center gap-1 text-[10px] text-ink/40 uppercase tracking-widest font-heading">
                                                <Clock size={10} /> Saved {new Date(bookmark.created_at).toLocaleDateString()}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </main>
        </div>
    );
}
