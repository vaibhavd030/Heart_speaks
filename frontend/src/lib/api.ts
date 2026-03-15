import axios from 'axios';
import { getToken } from './auth';

export const api = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || 'https://sage-backend-34833003999.europe-west2.run.app',
    headers: {
        'Content-Type': 'application/json',
    },
});

api.interceptors.request.use((config) => {
    const token = getToken();
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

export const registerUser = async (data: {
    first_name: string; last_name: string; email: string; abhyasi_id: string;
}) => {
    const response = await api.post('/auth/register', data);
    return response.data;
};

export const loginUser = async (email: string, password: string) => {
    const response = await api.post('/auth/login', { email, password });
    return response.data;
};

export const sendMessage = async (message: string) => {
    try {
        const response = await api.post('/chat', { message });
        return response.data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
};

export const sendMessageStream = async (
    message: string,
    onContent: (text: string) => void,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onSources: (sources: any[]) => void,
    onError: (error: string) => void
) => {
    try {
        const token = getToken();
        const response = await fetch(`${api.defaults.baseURL}/chat/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
            },
            body: JSON.stringify({ message })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder('utf-8');

        if (!reader) throw new Error("No reader available");

        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop() || ''; // keep the last partial chunk in buffer

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.slice(6);
                    try {
                        const data = JSON.parse(dataStr);
                        if (data.type === 'content') {
                            onContent(data.text);
                        } else if (data.type === 'sources') {
                            onSources(data.sources);
                        } else if (data.type === 'error') {
                            onError(data.message);
                        }
                    } catch (e) {
                        console.error("Error parsing stream chunk", e, dataStr);
                    }
                }
            }
        }
    } catch (error) {
        console.error('Streaming API Error:', error);
        onError(error instanceof Error ? error.message : "Unknown error");
    }
};

export const checkHealth = async () => {
    try {
        const response = await api.get('/health');
        return response.data;
    } catch (error) {
        console.error('Health Check Error:', error);
        return { status: 'error' };
    }
};

// Reader Features
export const getReaderSequence = async () => {
    const response = await api.get('/reader/messages');
    return response.data;
};

export const getReaderProgress = async () => {
    const response = await api.get('/reader/progress');
    return response.data;
};

export const updateReaderProgress = async (source_file: string, messages_read: number) => {
    const response = await api.post('/reader/progress', { source_file, messages_read });
    return response.data;
};

export const getBookmarks = async () => {
    const response = await api.get('/reader/bookmarks');
    return response.data;
};

export const saveBookmark = async (source_file: string, notes: string) => {
    const response = await api.post('/reader/bookmarks', { source_file, notes });
    return response.data;
};

export const removeBookmark = async (source_file: string) => {
    const response = await api.delete(`/reader/bookmarks/${encodeURIComponent(source_file)}`);
    return response.data;
};
// Admin Features
export const getAllUsers = async () => {
    const response = await api.get('/admin/users/all');
    return response.data;
};

export const getPendingUsers = async () => {
    const response = await api.get('/admin/users/pending');
    return response.data;
};

export const approveUser = async (email: string, action: 'approve' | 'reject') => {
    const response = await api.post('/admin/users/approve', { email, action });
    return response.data;
};

export const getAllChatLogs = async (limit: number = 100, offset: number = 0) => {
    const response = await api.get('/admin/logs', { params: { limit, offset } });
    return response.data;
};

export const getUserChatLogs = async () => {
    const response = await api.get('/chat/logs');
    return response.data;
};

export const deleteChatLog = async (logId: string) => {
    const response = await api.delete(`/chat/logs/${logId}`);
    return response.data;
};

export const adminDeleteChatLog = async (logId: string) => {
    const response = await api.delete(`/admin/logs/${logId}`);
    return response.data;
};

export const suspendUser = async (userId: string) => {
    const response = await api.post(`/admin/users/suspend?user_id=${userId}`);
    return response.data;
};

export const deleteUser = async (userId: string) => {
    const response = await api.delete(`/admin/users/${userId}`);
    return response.data;
};
