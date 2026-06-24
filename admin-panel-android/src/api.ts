import { addToQueue } from './offlineQueue';

/**
 * API Client for Telegram Bot Admin REST API
 * Supports Offline Queue for POST/DELETE requests
 */

const getBaseUrl = () => {
  return localStorage.getItem('api_base_url') || 'http://10.0.2.2:8000';
};

export const apiRequest = async <T>(
  endpoint: string,
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET',
  body?: any
): Promise<T> => {
  const url = `${getBaseUrl()}${endpoint}`;

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 5000);

  const options: RequestInit = {
    method,
    headers,
    signal: controller.signal,
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  try {
    const response = await fetch(url, options);
    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }

    return response.json();
  } catch (error: any) {
    clearTimeout(timeoutId);
    // If it's a mutation and we are likely offline or server is down
    if (method !== 'GET') {
      console.warn(`Request to ${endpoint} failed, adding to offline queue`, error);
      await addToQueue({ method, endpoint, body });
      return { offline: true } as any;
    }
    throw error;
  }
};

export const api = {
  // Users
  getUsers: (query?: string) => apiRequest<any[]>(`/api/users${query ? `?query=${encodeURIComponent(query)}` : ''}`),
  updateUser: (data: any) => apiRequest('/api/users/update', 'POST', data),

  // Rooms
  getRooms: () => apiRequest<any[]>('/api/rooms'),
  deleteRoom: (chatId: number) => apiRequest(`/api/rooms/${chatId}`, 'DELETE'),

  // Store
  getItems: () => apiRequest<any[]>('/api/items'),
  addItem: (data: any) => apiRequest('/api/items', 'POST', data),
  updateItem: (data: any) => apiRequest('/api/items/update', 'POST', data),
  deleteItem: (itemId: number) => apiRequest(`/api/items/${itemId}`, 'DELETE'),

  // Reports
  getReports: () => apiRequest<any[]>('/api/reports'),
  updateReportStatus: (id: number, status: string) => apiRequest('/api/reports/status', 'POST', { id, status }),

  // Settings
  getSettings: () => apiRequest<Record<string, string>>('/api/settings'),
  updateSettings: (settings: Record<string, string>) => apiRequest('/api/settings', 'POST', { settings }),

  // Broadcast
  broadcast: (messageText: string, imagePath: string | null) =>
    apiRequest('/api/broadcast', 'POST', { message_text: messageText, image_path: imagePath }),

  // Admins
  getAdmins: () => apiRequest<any[]>('/api/admins'),
  getAdminLogs: () => apiRequest<any[]>('/api/admin_logs'),
  addAdmin: (data: any) => apiRequest('/api/admins', 'POST', data),
  deleteAdmin: (userId: number) => apiRequest(`/api/admins/${userId}`, 'DELETE'),

  // Metrics
  getMetrics: () => apiRequest<any[]>('/api/metrics'),
};
