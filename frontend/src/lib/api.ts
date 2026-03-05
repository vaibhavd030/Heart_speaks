import axios from 'axios';

const api = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000',
    headers: {
        'Content-Type': 'application/json',
    },
});

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
    onSources: (sources: any[]) => void,
    onError: (error: string) => void
) => {
    try {
        const response = await fetch(`${api.defaults.baseURL}/chat/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
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
