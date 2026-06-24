import { useEffect } from 'react';
import { getQueue, removeFromQueue } from '../offlineQueue';
import { getBaseUrl } from '../api';

export default function SyncManager() {
  useEffect(() => {
    const sync = async () => {
      if (!navigator.onLine) return;

      try {
        const queue = await getQueue();
        if (queue.length === 0) return;
        
        console.log(`Syncing ${queue.length} offline requests...`);
        for (const req of queue) {
          try {
            const res = await fetch(`${getBaseUrl()}${req.endpoint}`, {
              method: req.method,
              headers: { 'Content-Type': 'application/json' },
              body: req.body ? JSON.stringify(req.body) : undefined
            });
            
            if (res.ok) {
              await removeFromQueue(req.id!);
              console.log(`Synced request: ${req.method} ${req.endpoint}`);
            } else {
              // Если ошибка клиента (4xx), удаляем запрос, чтобы не блокировать очередь
              if (res.status >= 400 && res.status < 500) {
                await removeFromQueue(req.id!);
                console.warn(`Deleted bad queued request (${res.status}): ${req.method} ${req.endpoint}`);
              } else {
                break; // Ошибка сервера (5xx), попробуем позже
              }
            }
          } catch (e) {
            break; // Сервер всё еще недоступен
          }
        }
      } catch (err) {
        console.error('Offline queue sync error:', err);
      }
    };

    window.addEventListener('online', sync);
    const interval = setInterval(sync, 15000); // Проверка каждые 15 секунд

    // Синхронизируем сразу при запуске
    sync();

    return () => {
      window.removeEventListener('online', sync);
      clearInterval(interval);
    };
  }, []);

  return null;
}
