import { addToQueue } from './offlineQueue';

export const getBaseUrl = (): string => {
  return localStorage.getItem('api_url') || 'http://127.0.0.1:8000';
};

export const apiRequest = async <T>(
  endpoint: string,
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET',
  body?: any
): Promise<T | { offline: true }> => {
  try {
    const response = await fetch(`${getBaseUrl()}${endpoint}`, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined
    });

    if (!response.ok) throw new Error('Server Error');
    return response.json();
  } catch (error) {
    // Если это мутирующий запрос и сеть недоступна
    if (method !== 'GET') {
      await addToQueue({ method, endpoint, body });
      console.warn('Network failed, request queued for sync:', endpoint);
      return { offline: true };
    }
    throw error;
  }
};
