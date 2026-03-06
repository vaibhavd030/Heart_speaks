'use client';

import React, { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { Send, User, Bot, Loader2, BookOpen, Feather, FileDown, BarChart3 } from 'lucide-react';
import { sendMessageStream } from '@/lib/api';
import ReactMarkdown from 'react-markdown';
import { clsx } from 'clsx';
import Image from 'next/image';

interface Message {
    role: 'user' | 'assistant';
    content: string;
    sources?: Source[];
}

interface Source {
    author: string;
    date: string;
    citation: string;
    preview: string;
    full_text: string;
}

const SourceCard = ({ source }: { source: Source }) => {
    const [isExpanded, setIsExpanded] = useState(false);

    return (
        <div
            onClick={() => setIsExpanded(!isExpanded)}
            className={clsx(
                "group border border-ink/10 rounded-md shadow-sm hover:shadow-md transition-all duration-300 cursor-pointer overflow-hidden bg-paper/80 text-left",
                isExpanded ? "bg-white ring-1 ring-gold-accent" : "hover:bg-white"
            )}
        >
            <div className="p-2.5 flex justify-between items-start gap-2">
                <div className="flex items-start gap-2 max-w-[75%]">
                    <Feather className="w-3.5 h-3.5 text-gold-accent mt-0.5 shrink-0" />
                    <div className="flex flex-col">
                        <span className="font-heading font-bold text-sm text-ink leading-tight flex items-center gap-1.5">{source.author} <span className="opacity-50 text-[10px] font-normal uppercase tracking-wider">Whispers</span></span>
                        <span className="text-xs font-mono text-ink/50 mt-0.5">{source.date}</span>
                    </div>
                </div>

                <a
                    href={`http://localhost:8000/data/${source.citation}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="shrink-0 flex items-center gap-1 text-[10px] uppercase tracking-wider font-heading font-bold text-gold-accent hover:text-white hover:bg-gold-accent border border-gold-accent/30 bg-gold-accent/5 px-2 py-1 rounded transition-colors"
                    onClick={(e) => e.stopPropagation()}
                    title="Read Original PDF"
                >
                    <BookOpen className="w-3 h-3" />
                    PDF
                </a>
            </div>

            <div className={clsx(
                "px-2.5 pb-2.5 text-sm text-ink/90 font-serif italic transition-all duration-500 ease-in-out",
                isExpanded ? "max-h-[500px] opacity-100 overflow-y-auto" : "max-h-0 opacity-0 overflow-hidden pb-0"
            )}>
                <div className="pt-2 border-t border-ink/5 mt-1 leading-relaxed">
                    {source.full_text}
                </div>
            </div>

            {!isExpanded && (
                <div className="px-2.5 pb-2.5 text-xs italic font-serif text-ink/70 line-clamp-2 leading-relaxed">
                    "{source.preview}..."
                </div>
            )}
        </div>
    );
};

export function ChatInterface() {
    const [messages, setMessages] = useState<Message[]>([
        { role: 'assistant', content: 'Dear Soul,\n\nI am here to guide you through the whispers of the brighter world. How may I be of service to your heart today?' }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isUserScrolling, setIsUserScrolling] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const scrollContainerRef = useRef<HTMLDivElement>(null);
    const currentDate = new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

    const handleScroll = () => {
        if (!scrollContainerRef.current) return;
        const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
        const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
        setIsUserScrolling(!isAtBottom);
    };

    const scrollToBottom = () => {
        if (!isUserScrolling) {
            messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
        }
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = async (text: string) => {
        if (!text.trim() || isLoading) return;

        setMessages(prev => [...prev, { role: 'user', content: text }]);
        setIsLoading(true);
        // Add minimal empty assistant message placeholder
        setMessages(prev => [...prev, { role: 'assistant', content: '', sources: [] }]);

        try {
            await sendMessageStream(
                text,
                (textChunk) => {
                    setIsLoading(false); // Stop loading spinner as soon as tokens arrive
                    setMessages(prev => {
                        const newMessages = [...prev];
                        const lastIndex = newMessages.length - 1;
                        newMessages[lastIndex] = {
                            ...newMessages[lastIndex],
                            content: newMessages[lastIndex].content + textChunk
                        };
                        return newMessages;
                    });
                },
                (sources) => {
                    setMessages(prev => {
                        const newMessages = [...prev];
                        const lastIndex = newMessages.length - 1;
                        newMessages[lastIndex] = {
                            ...newMessages[lastIndex],
                            sources: sources
                        };
                        return newMessages;
                    });
                },
                (error) => {
                    console.error("Stream Error:", error);
                    setMessages(prev => {
                        const newMessages = [...prev];
                        const lastIndex = newMessages.length - 1;
                        if (!newMessages[lastIndex].content) {
                            newMessages[lastIndex].content = 'I apologize, but I encountered an error with the spiritual archive. Please try again later.';
                        }
                        return newMessages;
                    });
                }
            );
        } catch (error) {
            console.error("Catch block:", error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        const text = input.trim();
        setInput('');
        await handleSend(text);
    };

    const handleDownloadPDF = (question: string, content: string, sources?: Source[]) => {
        import('jspdf').then(({ jsPDF }) => {
            const doc = new jsPDF();
            const pageWidth = doc.internal.pageSize.getWidth();
            const pageHeight = doc.internal.pageSize.getHeight();
            const margin = 20;
            const contentWidth = pageWidth - (margin * 2);
            let yPosition = 20;

            // Background color (paper/parchment mimic)
            doc.setFillColor(245, 241, 230); // #F5F1E6 Tailwind var
            doc.rect(0, 0, pageWidth, pageHeight, "F");

            // Text Color (ink mimic)
            doc.setTextColor(62, 62, 62); // #3E3E3E Tailwind var

            // Title
            doc.setFont("times", "italic");
            doc.setFontSize(28);
            doc.text("SAGE", pageWidth / 2, yPosition, { align: "center" });
            yPosition += 10;

            doc.setFontSize(12);
            doc.text("Spiritual Archive Guidance Engine", pageWidth / 2, yPosition, { align: "center" });

            // Divider Line
            yPosition += 8;
            doc.setDrawColor(197, 160, 101); // #C5A065 (gold accent)
            doc.setLineWidth(0.5);
            doc.line(pageWidth / 2 - 20, yPosition, pageWidth / 2 + 20, yPosition);
            yPosition += 20;

            // User Question Area
            // User Question Area
            doc.setFont("helvetica", "normal");
            doc.setFontSize(14);
            const splitQuestion = doc.splitTextToSize(question, contentWidth);
            const questionHeight = (splitQuestion.length * 7) + 15;

            // Lighter bubble overlay
            doc.setFillColor(235, 230, 218);
            doc.roundedRect(margin - 5, yPosition - 8, contentWidth + 10, questionHeight, 3, 3, "F");

            doc.setFont("times", "italic");
            doc.setTextColor(197, 160, 101); // gold accent
            doc.text(`Seeker asks:`, margin, yPosition);
            yPosition += 8;

            doc.setFont("helvetica", "normal");
            doc.setTextColor(62, 62, 62);
            doc.text(splitQuestion, margin, yPosition);
            yPosition += questionHeight - 5;

            // Response Content
            doc.setFontSize(12);

            const lines = content.split('\n');
            lines.forEach(line => {
                if (!line.trim()) {
                    yPosition += 4;
                    return;
                }

                let isBold = false;
                let cleanLine = line.trim();

                // If it's a bold heading
                if (cleanLine.startsWith('**') && cleanLine.endsWith('**')) {
                    isBold = true;
                    cleanLine = cleanLine.substring(2, cleanLine.length - 2);
                } else {
                    // Strip asterisks if they appear anywhere else inline
                    cleanLine = cleanLine.replace(/\*\*/g, '');
                }

                if (isBold) {
                    doc.setFont("times", "bold");
                } else {
                    doc.setFont("helvetica", "normal");
                }
                const splitContent = doc.splitTextToSize(cleanLine, contentWidth);

                // Auto-page wrapping for long responses
                if (yPosition + (splitContent.length * 7) > pageHeight - 40) {
                    doc.addPage();
                    doc.setFillColor(245, 241, 230); // #F5F1E6
                    doc.rect(0, 0, pageWidth, pageHeight, "F");
                    yPosition = 20;
                }

                doc.text(splitContent, margin, yPosition);
                yPosition += (splitContent.length * 7) + 4;
            });

            yPosition += 6;

            // Sources
            if (sources && sources.length > 0) {
                // Check if we need a new page
                if (yPosition > doc.internal.pageSize.getHeight() - 60) {
                    doc.addPage();
                    doc.setFillColor(253, 251, 247); // Refill background for new page
                    doc.rect(0, 0, pageWidth, pageHeight, "F");
                    yPosition = 20;
                }

                doc.setFont("times", "bold");
                doc.text("Sources Used:", margin, yPosition);
                yPosition += 10;
                doc.setFont("times", "normal");
                doc.setFontSize(10);

                sources.forEach((src) => {
                    const formattedTitle = src.citation.startsWith('whisper_')
                        ? `Whispers ${src.date}`
                        : src.citation;
                    const sourceText = `• ${formattedTitle} - ${src.author}`;
                    const splitSource = doc.splitTextToSize(sourceText, contentWidth);

                    if (yPosition + (splitSource.length * 5) > doc.internal.pageSize.getHeight() - 20) {
                        doc.addPage();
                        doc.setFillColor(245, 241, 230); // #F5F1E6
                        doc.rect(0, 0, pageWidth, pageHeight, "F");
                        yPosition = 20;
                    }

                    doc.text(splitSource, margin, yPosition);
                    yPosition += (splitSource.length * 5) + 5;
                });
            }

            // Footer
            const dateStr = new Date().toLocaleDateString();
            doc.setFontSize(10);
            doc.setFont("times", "italic");
            doc.setTextColor(150, 150, 150);
            doc.text(`Generated on ${dateStr}`, pageWidth / 2, doc.internal.pageSize.getHeight() - 10, { align: "center" });

            doc.save(`SAGE-Guidance-${dateStr.replace(/\//g, '-')}.pdf`);
        });
    };

    return (
        <div className="flex flex-col h-screen bg-paper text-ink font-body relative overflow-hidden">
            {/* Background Texture & Pattern */}
            <div className="absolute inset-0 bg-[url('/parchment-bg.svg')] opacity-60 pointer-events-none z-0 mix-blend-multiply"></div>
            <div className="absolute inset-0 bg-[url('/floral-pattern.svg')] bg-[length:400px_400px] opacity-10 pointer-events-none z-0"></div>

            {/* Corner Florals */}
            <div className="absolute top-0 left-0 w-64 h-64 pointer-events-none z-10 opacity-80">
                <Image src="/floral-corner.svg" alt="Decorative Corner" width={256} height={256} className="object-contain" />
            </div>
            <div className="absolute top-0 right-0 w-64 h-64 pointer-events-none z-10 -scale-x-100 opacity-80">
                <Image src="/floral-corner.svg" alt="Decorative Corner" width={256} height={256} className="object-contain" />
            </div>
            <div className="absolute bottom-0 left-0 w-64 h-64 pointer-events-none z-10 -scale-y-100 opacity-80">
                <Image src="/floral-corner.svg" alt="Decorative Corner" width={256} height={256} className="object-contain" />
            </div>
            <div className="absolute bottom-0 right-0 w-64 h-64 pointer-events-none z-10 -scale-x-100 -scale-y-100 opacity-80">
                <Image src="/floral-corner.svg" alt="Decorative Corner" width={256} height={256} className="object-contain" />
            </div>

            {/* Header Area */}
            <header className="relative z-20 pt-12 pb-4 px-8 text-center bg-transparent">
                <h1 className="text-5xl md:text-7xl font-serif italic text-ink drop-shadow-sm mb-4">
                    SAGE
                </h1>
                <p className="text-xl font-heading italic text-ink/70">
                    Spiritual Archive Guidance Engine
                </p>
                <div className="flex justify-center items-center gap-4 mb-2">
                    <Image src="/floral-divider.svg" alt="Divider" width={300} height={40} className="object-contain opacity-70" />
                </div>
                <div className="block text-center md:absolute md:top-8 md:right-12">
                    <p className="font-heading italic text-xl text-ink/70">{currentDate}</p>
                    <Link href="/dashboard" className="flex flex-col sm:flex-row items-center gap-2 mt-4 justify-center md:justify-end text-gold-accent hover:text-ink transition-colors font-heading italic text-sm border border-gold-accent/30 bg-gold-accent/5 px-4 py-2 rounded-full">
                        <BarChart3 size={16} />
                        <span>Explore Archives & Stats</span>
                    </Link>
                </div>
            </header>

            {/* Main Chat Area */}
            <div
                ref={scrollContainerRef}
                onScroll={handleScroll}
                className="flex-1 overflow-y-auto p-4 sm:p-8 relative z-20 scrollbar-thin scrollbar-thumb-ink/20 scrollbar-track-transparent"
            >
                <div className="max-w-4xl mx-auto space-y-8 pb-32">
                    {messages.map((msg, idx) => (
                        <div
                            key={idx}
                            className={clsx(
                                "flex flex-col gap-2 transition-all duration-500 ease-in-out",
                                msg.role === 'user' ? "items-end ml-12" : "items-start mr-12"
                            )}
                        >
                            {/* Message Bubble */}
                            <div className={clsx(
                                "group relative p-6 md:p-8 shadow-sm transition-transform hover:scale-[1.01] hover:shadow-md",
                                msg.role === 'user'
                                    ? "bg-white/40 backdrop-blur-sm rounded-3xl rounded-br-none border border-floral-pink/30"
                                    : "bg-white/60 backdrop-blur-sm rounded-3xl rounded-bl-none border border-gold-accent/30"
                            )}>
                                <div className={clsx(
                                    "text-lg md:text-xl leading-relaxed font-heading text-ink",
                                    msg.role === 'user' ? "italic text-ink/80" : "text-justify"
                                )}>
                                    {msg.role === 'assistant' && idx !== 0 ? (
                                        <div className="relative">
                                            {/* Download Button */}
                                            <button
                                                onClick={() => {
                                                    const previousMessage = messages[idx - 1];
                                                    const questionText = previousMessage && previousMessage.role === 'user'
                                                        ? previousMessage.content
                                                        : "Seeker's guidance inquiry";
                                                    handleDownloadPDF(questionText, msg.content, msg.sources);
                                                }}
                                                className="absolute -top-2 -right-2 p-2 text-ink/40 hover:text-gold-accent transition-colors"
                                                title="Download as PDF"
                                            >
                                                <FileDown size={18} />
                                            </button>
                                            <ReactMarkdown
                                                components={{
                                                    p: ({ node, ...props }) => <p className="mb-4 last:mb-0" {...props} />,
                                                    strong: ({ node, ...props }) => <span className="font-bold text-ink" {...props} />,
                                                    em: ({ node, ...props }) => <span className="italic text-ink/80" {...props} />
                                                }}
                                            >
                                                {msg.content}
                                            </ReactMarkdown>
                                        </div>
                                    ) : (
                                        msg.content
                                    )}
                                </div>
                            </div>

                            {/* Sources Section */}
                            {msg.sources && msg.sources.length > 0 && (
                                <div className="mt-2 w-full max-w-2xl mx-auto">
                                    <div className="flex items-center gap-2 mb-2 justify-center opacity-60">
                                        <div className="h-px w-12 bg-ink/30"></div>
                                        <span className="font-script text-xl text-ink">Whispers from the Archive</span>
                                        <div className="h-px w-12 bg-ink/30"></div>
                                    </div>
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                        {msg.sources.map((src, i) => (
                                            <SourceCard key={i} source={src} />
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}

                    {messages.length === 1 && (
                        <div className="flex flex-wrap justify-center gap-3 mt-8 opacity-80">
                            {["Tell me about meditation", "How to find inner peace", "What is the purpose of suffering?", "How to deepen my practice"].map((suggestion, i) => (
                                <button
                                    key={i}
                                    onClick={() => handleSend(suggestion)}
                                    className="px-5 py-2.5 rounded-full border border-gold-accent/40 bg-white/50 hover:bg-white/80 text-ink/90 text-sm font-heading italic transition-all shadow-sm hover:shadow-md hover:text-ink hover:border-gold-accent"
                                >
                                    {suggestion}
                                </button>
                            ))}
                        </div>
                    )}

                    {isLoading && (
                        <div className="flex justify-center items-center py-4 opacity-70">
                            <Loader2 size={24} className="text-floral-pink animate-spin mr-2" />
                            <span className="font-heading italic">Referring to Whispers From the Brighter World Archives...</span>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>
            </div>

            {/* Input Area */}
            <div className="absolute bottom-0 left-0 right-0 z-30 p-6 md:p-8 bg-gradient-to-t from-paper via-paper/90 to-transparent pt-12">
                <div className="max-w-3xl mx-auto relative">
                    <form onSubmit={handleSubmit} className="relative group">
                        <div className="absolute inset-0 bg-white/70 backdrop-blur-md rounded-full shadow-lg border border-ink/5"></div>
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="Write your message here..."
                            className="w-full py-4 pl-8 pr-16 bg-transparent relative z-10 text-xl font-heading text-ink placeholder-ink/40 focus:outline-none focus:ring-0 rounded-full"
                        />
                        <button
                            type="submit"
                            disabled={!input.trim() || isLoading}
                            className="absolute right-2 top-1/2 -translate-y-1/2 z-20 p-3 text-gold-accent hover:text-floral-pink disabled:opacity-30 transition-colors"
                        >
                            <Send size={24} />
                        </button>
                    </form>
                    <p className="text-center text-xs font-heading italic text-ink/40 mt-3">
                        Everything has a raison d'être
                    </p>
                </div>
            </div>
        </div>
    );
}
