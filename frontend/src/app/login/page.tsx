'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { setAuth } from '@/lib/auth';
import { loginUser, registerUser } from '@/lib/api';
import { Loader2, LogIn } from 'lucide-react';

export default function LoginPage() {
    const router = useRouter();
    const [isLogin, setIsLogin] = useState(true);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [msg, setMsg] = useState('');

    const [form, setForm] = useState({
        first_name: '',
        last_name: '',
        email: '',
        abhyasi_id: '',
        password: '',
    });

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setForm({ ...form, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        setMsg('');

        try {
            if (isLogin) {
                const data = await loginUser(form.email, form.password);
                setAuth(data.access_token, data.user);
                router.push('/');
            } else {
                const data = await registerUser({
                    first_name: form.first_name,
                    last_name: form.last_name,
                    email: form.email,
                    abhyasi_id: form.abhyasi_id,
                });
                setMsg(data.message || 'Registration successful. Waiting for approval.');
                setIsLogin(true); // switch to login view
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || err.message || 'Something went wrong');
        } finally {
            setLoading(false);
        }
    };

    return (
        <main className="min-h-screen relative flex items-center justify-center bg-[#F5F1E6] text-[#2c241b]">
            <div className="absolute inset-0 z-0 opacity-10 pointer-events-none" style={{
                backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M54.627 0l.83.83v58.34h-58.34v-.83l.83-.83h55.85v-55.85z' fill='%23C5A065' fill-opacity='0.4' fill-rule='evenodd'/%3E%3C/svg%3E")`
            }}></div>

            <div className="w-full max-w-md bg-white p-8 rounded-xl shadow-lg border border-[#e6dece] z-10 relative">
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#C5A065] to-[#8C6D3F] rounded-t-xl"></div>
                
                <h1 className="text-3xl font-serif text-center mb-2 font-bold text-[#8C6D3F]">SAGE</h1>
                <p className="text-center text-sm text-[#735e3b] mb-6 italic border-b border-[#e6dece] pb-4">
                    Spiritual Archive Guidance Engine
                </p>

                <div className="flex mb-6 border-b border-[#e6dece]">
                    <button 
                        className={`flex-1 py-2 text-sm font-medium transition-colors ${isLogin ? 'text-[#8C6D3F] border-b-2 border-[#8C6D3F]' : 'text-gray-400 hover:text-gray-600'}`}
                        onClick={() => { setIsLogin(true); setError(''); setMsg(''); }}
                        type="button"
                    >
                        Login
                    </button>
                    <button 
                        className={`flex-1 py-2 text-sm font-medium transition-colors ${!isLogin ? 'text-[#8C6D3F] border-b-2 border-[#8C6D3F]' : 'text-gray-400 hover:text-gray-600'}`}
                        onClick={() => { setIsLogin(false); setError(''); setMsg(''); }}
                        type="button"
                    >
                        Register
                    </button>
                </div>

                {error && <div className="mb-4 p-3 bg-red-50 text-red-700 border border-red-200 rounded text-sm">{error}</div>}
                {msg && <div className="mb-4 p-3 bg-green-50 text-green-700 border border-green-200 rounded text-sm">{msg}</div>}

                <form onSubmit={handleSubmit} className="space-y-4">
                    {!isLogin && (
                        <>
                            <div className="flex gap-4">
                                <div className="flex-1">
                                    <label className="block text-xs uppercase tracking-wider text-gray-500 mb-1">First Name</label>
                                    <input required name="first_name" value={form.first_name} onChange={handleChange}
                                        className="w-full px-3 py-2 border border-[#e6dece] rounded focus:outline-none focus:border-[#C5A065] bg-[#faf8f5]" />
                                </div>
                                <div className="flex-1">
                                    <label className="block text-xs uppercase tracking-wider text-gray-500 mb-1">Last Name</label>
                                    <input required name="last_name" value={form.last_name} onChange={handleChange}
                                        className="w-full px-3 py-2 border border-[#e6dece] rounded focus:outline-none focus:border-[#C5A065] bg-[#faf8f5]" />
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs uppercase tracking-wider text-gray-500 mb-1">Abhyasi ID</label>
                                <input required name="abhyasi_id" value={form.abhyasi_id} onChange={handleChange} placeholder="e.g. IN012345"
                                    className="w-full px-3 py-2 border border-[#e6dece] rounded focus:outline-none focus:border-[#C5A065] bg-[#faf8f5]" />
                            </div>
                        </>
                    )}

                    <div>
                        <label className="block text-xs uppercase tracking-wider text-gray-500 mb-1">Email</label>
                        <input required type="email" name="email" value={form.email} onChange={handleChange}
                            className="w-full px-3 py-2 border border-[#e6dece] rounded focus:outline-none focus:border-[#C5A065] bg-[#faf8f5]" />
                    </div>

                    {isLogin &&                            <div>
                                <label className="block text-sm font-heading tracking-widest uppercase text-ink/60 mb-2">Password</label>
                                <input
                                    type="password"
                                    name="password" // Added name attribute
                                    placeholder="Enter your Abhyasi ID"
                                    value={form.password} // Changed to form.password
                                    onChange={handleChange} // Changed to handleChange
                                    className="w-full px-4 py-3 rounded-xl border border-gold-accent/20 bg-white/50 focus:outline-none focus:ring-1 focus:ring-gold-accent transition-all"
                                    required
                                />
                                <p className="mt-2 text-xs text-ink/50 italic font-serif">
                                    Your initial password is your Abhyasi ID.
                                </p>
                            </div>
                    }

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full py-4 bg-gold-accent hover:bg-gold-accent/90 text-white rounded-xl font-heading tracking-widest uppercase shadow-lg shadow-gold-accent/20 transition-all flex items-center justify-center gap-2 group"
                    >
                        {loading ? (
                            <Loader2 className="animate-spin" size={20} />
                        ) : (
                            <>
                                <span>Enter the Sanctuary</span>
                                <LogIn size={18} className="group-hover:translate-x-1 transition-transform" />
                            </>
                        )}
                    </button>
                </form>
            </div>
        </main>
    );
}
