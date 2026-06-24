import { useEffect } from 'react';
import { getQueue, removeFromQueue } from '../offlineQueue';

export default function SyncManager() {
  useEffect(() => {
    const sync = async () => {
      if (!navigator.onLine) return;

      const queue = await getQueue();
      if (queue.length === 0) return;

      console.log(`[SyncManager] Found ${queue.length} pending requests. Starting sync...`);

      const baseUrl = localStorage.getItem('api_base_url') || 'http://localhost:8000';

      for (const req of queue) {
        try {
          const response = await fetch(`${baseUrl}${req.endpoint}`, {
            method: req.method,
            headers: {
              'Content-Type': 'application/json',
            },
            body: req.body ? JSON.stringify(req.body) : undefined,
          });

          if (response.ok || (response.status >= 400 && response.status < 500)) {
            // Success or client error (invalid data) -> remove from queue
            // We remove 4xx errors to avoid blocking the queue with broken requests
            await removeFromQueue(req.id!);
            console.log(`[SyncManager] Synchronized ${req.method} ${req.endpoint}`);
          } else {
            // Server error (5xx) -> stop and retry later
            console.warn(`[SyncManager] Server error ${response.status} for ${req.endpoint}. Stopping sync.`);
            break;
          }
        } catch (error) {
          console.error(`[SyncManager] Failed to sync ${req.endpoint}:`, error);
          break; // Still offline or server unreachable
        }
      }
    };

    // Listen for online status
    window.addEventListener('online', sync);

    // Periodic check every 30 seconds
    const interval = setInterval(sync, 30000);

    // Initial sync check
    sync();

    return () => {
      window.removeEventListener('online', sync);
      clearInterval(interval);
    };
  }, []);

  return null; // This component doesn't render anything
}
