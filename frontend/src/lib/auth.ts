import Cookies from 'js-cookie';

const TOKEN_KEY = 'sage_token';
const USER_KEY = 'sage_user';

export interface User {
    user_id: string;
    first_name: string;
    last_name: string;
    email: string;
    is_admin: boolean;
}

export function getToken(): string | undefined {
    return Cookies.get(TOKEN_KEY);
}

export function getUser(): User | null {
    const raw = Cookies.get(USER_KEY);
    if (!raw) return null;
    try { return JSON.parse(raw); } catch { return null; }
}

export function setAuth(token: string, user: User): void {
    Cookies.set(TOKEN_KEY, token, { expires: 3 }); // 3 days
    Cookies.set(USER_KEY, JSON.stringify(user), { expires: 3 });
}

export function clearAuth(): void {
    Cookies.remove(TOKEN_KEY);
    Cookies.remove(USER_KEY);
}

export function isLoggedIn(): boolean {
    return !!getToken();
}
