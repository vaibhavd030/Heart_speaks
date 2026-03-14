'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { isLoggedIn, getUser } from '@/lib/auth';

export function AuthGuard({ children, requireAdmin = false }: { children: React.ReactNode, requireAdmin?: boolean }) {
    const router = useRouter();
    const [checked, setChecked] = useState(false);

    useEffect(() => {
        const user = getUser();
        if (!isLoggedIn()) {
            router.replace('/login');
        } else if (requireAdmin && !user?.is_admin) {
            router.replace('/dashboard');
        } else {
            setChecked(true);
        }
    }, [router, requireAdmin]);

    if (!checked) return null;
    return <>{children}</>;
}
