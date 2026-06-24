/**
 * Offline Queue Manager using IndexedDB
 */

const DB_NAME = 'AdminOfflineDB';
const STORE_NAME = 'pending_requests';
const DB_VERSION = 1;

export interface PendingRequest {
  id?: number;
  method: string;
  endpoint: string;
  body: any;
  timestamp: number;
}

const openDB = (): Promise<IDBDatabase> => {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event: any) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
      }
    };
  });
};

export const addToQueue = async (req: Omit<PendingRequest, 'id' | 'timestamp'>) => {
  const db = await openDB();
  return new Promise<void>((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, 'readwrite');
    const store = transaction.objectStore(STORE_NAME);
    const item = { ...req, timestamp: Date.now() };

    const request = store.add(item);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
};

export const getQueue = async (): Promise<PendingRequest[]> => {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, 'readonly');
    const store = transaction.objectStore(STORE_NAME);
    const request = store.getAll();

    request.onsuccess = () => {
      // Sort by timestamp just in case, though autoIncrement usually handles it
      const sorted = (request.result as PendingRequest[]).sort((a, b) => a.timestamp - b.timestamp);
      resolve(sorted);
    };
    request.onerror = () => reject(request.error);
  });
};

export const removeFromQueue = async (id: number) => {
  const db = await openDB();
  return new Promise<void>((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, 'readwrite');
    const store = transaction.objectStore(STORE_NAME);
    const request = store.delete(id);

    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
};
