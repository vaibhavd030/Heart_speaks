'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { ArrowLeft, BookOpen, ChevronLeft, ChevronRight, Bookmark, BookmarkCheck, Loader2 } from 'lucide-react';
import { getReaderSequence, getReaderProgress, updateReaderProgress, saveBookmark, getBookmarks, removeBookmark, api } from '@/lib/api';
import { clsx } from 'clsx';
import { AuthGuard } from '@/components/AuthGuard';

interface ReaderMessage {
    source_file: string;
    date: string;
    preview: string;
    page_count: number;
    author: string;
}

export default function ReaderPage() {
    const [messages, setMessages] = useState<ReaderMessage[]>([]);
    const [currentIndex, setCurrentIndex] = useState<number>(0);
    const [isLoading, setIsLoading] = useState(true);
    const [notes, setNotes] = useState('');
    const [isSaving, setIsSaving] = useState(false);
    const [bookmarked, setBookmarked] = useState(false);
    const [pdfLoading, setPdfLoading] = useState(true);

    useEffect(() => {
        const initReader = async () => {
            setIsLoading(true);
            try {
                const sequenceData = await getReaderSequence();
                setMessages(sequenceData);

                // Fetch progress and bookmarks separately to avoid blocking rendering
                const [progressData, bookmarksData] = await Promise.all([
                    getReaderProgress().catch(e => { console.error("Progress fetch failed:", e); return null; }),
                    getBookmarks().catch(e => { console.error("Bookmarks fetch failed:", e); return []; })
                ]);

                // Find the starting index
                let startIndex = 0;
                if (progressData?.last_read_source_file) {
                    const idx = sequenceData.findIndex((m: ReaderMessage) => m.source_file === progressData.last_read_source_file);
                    if (idx !== -1) startIndex = idx;
                }
                setCurrentIndex(startIndex);

                // Check if current is bookmarked
                if (bookmarksData && sequenceData[startIndex]) {
                    const currentSource = sequenceData[startIndex].source_file;
                    const existingBookmark = bookmarksData.find((b: { source_file: string; notes: string }) => b.source_file === currentSource);
                    if (existingBookmark) {
                        setBookmarked(true);
                        setNotes(existingBookmark.notes || '');
                    }
                }
            } catch (error) {
                console.error("Failed to fetch sequence data:", error);
            } finally {
                setIsLoading(false);
            }
        };

        initReader();
    }, []);

    const fetchBookmarkState = async (sourceFile: string) => {
        try {
            const bookmarksData = await getBookmarks();
            const existingBookmark = bookmarksData.find((b: { source_file: string; notes: string }) => b.source_file === sourceFile);
            setBookmarked(!!existingBookmark);
            setNotes(existingBookmark?.notes || '');
        } catch (error) {
            console.error("Failed to fetch bookmark state:", error);
        }
    };

    const handleNavigate = async (newIndex: number) => {
        if (newIndex < 0 || newIndex >= messages.length) return;

        setPdfLoading(true);
        setCurrentIndex(newIndex);

        const nextMessage = messages[newIndex];

        // Update progress in background
        updateReaderProgress(nextMessage.source_file, newIndex + 1).catch(console.error);

        // Fetch bookmark state for new message
        await fetchBookmarkState(nextMessage.source_file);
    };

    const handleSaveNote = async () => {
        if (!messages[currentIndex]) return;
        setIsSaving(true);
        try {
            const currentSource = messages[currentIndex].source_file;
            if (!notes.trim() && bookmarked) {
                // If notes are empty but it was bookmarked, just save empty notes
                // Or user can unbookmark using the icon. Here we just save notes.
                await saveBookmark(currentSource, notes);
            } else if (notes.trim()) {
                await saveBookmark(currentSource, notes);
                setBookmarked(true);
            }
        } catch (error) {
            console.error("Error saving note:", error);
        } finally {
            setIsSaving(false);
            setTimeout(() => {
            }, 2000);
        }
    };

    const toggleBookmark = async () => {
        if (!messages[currentIndex]) return;
        const currentSource = messages[currentIndex].source_file;

        try {
            if (bookmarked) {
                await removeBookmark(currentSource);
                setBookmarked(false);
                setNotes('');
            } else {
                await saveBookmark(currentSource, notes);
                setBookmarked(true);
            }
        } catch (error) {
            console.error("Error toggling bookmark:", error);
        }
    };

    if (isLoading) {
        return (
            <div className="flex h-screen items-center justify-center bg-paper text-ink">
                <Loader2 size={32} className="animate-spin text-gold-accent" />
            </div>
        );
    }

    if (messages.length === 0) {
        return (
            <div className="flex h-screen flex-col items-center justify-center bg-paper text-ink p-8 text-center">
                <BookOpen size={48} className="text-gold-accent mb-4 opacity-50" />
                <h1 className="text-3xl font-serif mb-2">The Archive is Empty</h1>
                <p className="font-heading italic opacity-70 mb-8">No teachings have been ingested into the repository yet.</p>
                <Link href="/" className="text-gold-accent hover:text-ink underline flex items-center gap-2">
                    <ArrowLeft size={16} /> Return to SAGE
                </Link>
            </div>
        );
    }

    const currentMessage = messages[currentIndex];

    return (
        <AuthGuard>
        <div className="flex h-screen bg-paper text-ink font-body relative overflow-hidden flex-col md:flex-row">
            {/* Background Texture & Pattern */}
            <div className="absolute inset-0 bg-[url('/parchment-bg.svg')] opacity-60 pointer-events-none z-0 mix-blend-multiply"></div>

            {/* Left Panel: PDF Viewer */}
            <div className="flex-1 flex flex-col relative z-10 border-r border-ink/10 bg-white/40 md:h-screen h-[60vh]">
                <header className="p-4 border-b border-ink/10 flex items-center justify-between bg-white/60 backdrop-blur-sm shadow-sm">
                    <Link href="/" className="flex items-center gap-2 text-gold-accent hover:text-ink transition-colors font-heading text-sm font-semibold uppercase tracking-wider group">
                        <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
                        Back to SAGE
                    </Link>
                    <div className="text-center w-full max-w-[200px] absolute left-1/2 -translate-x-1/2 hidden md:block">
                        <h2 className="font-serif italic text-lg truncate" title={currentMessage.date}>{currentMessage.date}</h2>
                        <p className="text-[10px] uppercase tracking-widest opacity-60 font-heading shrink-0">Whisper</p>
                    </div>
                </header>

                <div className="flex-1 relative bg-[#525659]"> {/* standard pdf viewer background */}
                    {pdfLoading && (
                        <div className="absolute inset-0 flex items-center justify-center bg-paper/50 backdrop-blur-sm z-20">
                            <Loader2 size={32} className="animate-spin text-gold-accent" />
                        </div>
                    )}
                    <iframe
                        key={currentMessage.source_file}
                        src={`${api.defaults.baseURL}/data/${currentMessage.source_file}`}
                        className="w-full h-full border-none shadow-inner"
                        onLoad={() => setPdfLoading(false)}
                        title="PDF Viewer"
                    />
                </div>

                {/* Mobile Info Bar */}
                <div className="md:hidden border-t border-ink/10 p-3 flex justify-between items-center bg-white/80 backdrop-blur">
                    <h2 className="font-serif italic text-md">{currentMessage.date}</h2>
                    <p className="text-xs uppercase tracking-widest opacity-60 font-heading">Whisper</p>
                </div>
            </div>

            {/* Right Panel: Controls & Notes */}
            <div className="w-full md:w-96 flex flex-col relative z-10 bg-white/50 backdrop-blur-md h-[40vh] md:h-screen shadow-[-4px_0_15px_-5px_rgba(0,0,0,0.05)]">

                {/* Top tracking / Nav */}
                <div className="p-6 border-b border-ink/10 flex flex-col items-center bg-gradient-to-b from-white/80 to-transparent">
                    <div className="text-sm font-heading tracking-widest uppercase opacity-60 mb-2">Reading Progress</div>
                    <div className="text-3xl font-serif mb-4 flex items-baseline gap-1">
                        {currentIndex + 1} <span className="text-lg opacity-50 italic font-heading">of</span> <span className="text-xl font-heading">{messages.length}</span>
                    </div>

                    <div className="flex items-center gap-2 w-full">
                        <button
                            onClick={() => handleNavigate(currentIndex - 1)}
                            disabled={currentIndex === 0}
                            className="flex-1 flex justify-center items-center py-2.5 px-4 rounded-lg bg-white border border-ink/10 hover:border-gold-accent hover:text-gold-accent disabled:opacity-30 transition-all font-heading text-sm group shadow-sm"
                        >
                            <ChevronLeft size={16} className="group-hover:-translate-x-1 transition-transform" /> Prev
                        </button>
                        <button
                            onClick={() => handleNavigate(currentIndex + 1)}
                            disabled={currentIndex === messages.length - 1}
                            className="flex-1 flex justify-center items-center py-2.5 px-4 rounded-lg bg-ink text-paper hover:bg-gold-accent disabled:opacity-30 transition-all font-heading text-sm group shadow-sm"
                        >
                            Next <ChevronRight size={16} className="group-hover:translate-x-1 transition-transform" />
                        </button>
                    </div>
                </div>

                {/* Notes Section */}
                <div className="flex-1 p-6 flex flex-col overflow-hidden">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="font-heading font-semibold uppercase tracking-widest text-sm flex items-center gap-2">
                            Personal Notes
                        </h3>
                        <button
                            onClick={toggleBookmark}
                            className={clsx(
                                "p-2 rounded-full transition-all duration-300",
                                bookmarked
                                    ? "bg-gold-accent text-white shadow-md hover:bg-red-500"
                                    : "bg-white border border-ink/10 text-ink/40 hover:text-gold-accent hover:border-gold-accent shadow-sm"
                            )}
                            title={bookmarked ? "Remove Bookmark" : "Bookmark this message"}
                        >
                            {bookmarked ? <BookmarkCheck size={18} /> : <Bookmark size={18} />}
                        </button>
                    </div>

                    <div className="flex-1 flex flex-col relative group">
                        <textarea
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            placeholder="Jot down your reflections, thoughts, or key takeaways from this whisper..."
                            className="flex-1 w-full resize-none rounded-xl border border-ink/10 bg-white/60 p-4 font-serif text-[15px] leading-relaxed text-ink/90 placeholder-ink/30 focus:border-gold-accent focus:bg-white focus:outline-none focus:ring-1 focus:ring-gold-accent shadow-inner transition-all scrollbar-thin scrollbar-thumb-ink/10"
                        />
                    </div>

                    <div className="mt-4 pt-4 border-t border-ink/10">
                        <button
                            onClick={handleSaveNote}
                            disabled={isSaving}
                            className="w-full py-3 rounded-lg bg-white border border-gold-accent/40 text-gold-accent hover:bg-gold-accent hover:text-white transition-all font-heading tracking-wide uppercase text-sm font-semibold flex items-center justify-center shadow-sm relative overflow-hidden group"
                        >
                            <span className={clsx("transition-transform duration-300", isSaving ? "-translate-y-8 absolute" : "")}>
                                Save Notes
                            </span>
                            <span className={clsx("transition-transform duration-300 absolute flex items-center gap-2", isSaving ? "translate-y-0" : "translate-y-8")}>
                                <Loader2 size={16} className="animate-spin" /> Saving...
                            </span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
        </AuthGuard>
    );
}

