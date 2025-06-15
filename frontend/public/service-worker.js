// Nom du cache
const CACHE_NAME = 'feedback-platform-v1';

// Liste des ressources à mettre en cache
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/favicon.ico',
  '/logo192.png',
  '/logo512.png',
  '/static/js/main.js',
  '/static/css/main.css'
];

// Ressources API à mettre en cache
const API_ROUTES = [
  '/api/categories/',
  '/api/feedback/'
];

// Installation du service worker
self.addEventListener('install', (event) => {
  console.log('[Service Worker] Installation');
  
  // Mettre en cache les ressources statiques
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[Service Worker] Mise en cache des ressources statiques');
        return cache.addAll(STATIC_ASSETS);
      })
  );
});

// Activation du service worker
self.addEventListener('activate', (event) => {
  console.log('[Service Worker] Activation');
  
  // Supprimer les anciens caches
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('[Service Worker] Suppression de l\'ancien cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  
  return self.clients.claim();
});

// Interception des requêtes
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  
  // Stratégie pour les ressources statiques: Cache First
  if (STATIC_ASSETS.includes(url.pathname)) {
    event.respondWith(
      caches.match(event.request)
        .then((response) => {
          if (response) {
            return response;
          }
          
          // Si pas en cache, récupérer depuis le réseau et mettre en cache
          return fetch(event.request).then((networkResponse) => {
            if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
              return networkResponse;
            }
            
            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, responseToCache);
            });
            
            return networkResponse;
          });
        })
    );
    return;
  }
  
  // Stratégie pour les API: Network First, puis cache
  if (url.pathname.startsWith('/api/')) {
    // Pour les requêtes GET uniquement
    if (event.request.method === 'GET') {
      event.respondWith(
        fetch(event.request)
          .then((networkResponse) => {
            // Mettre en cache la réponse
            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, responseToCache);
            });
            
            return networkResponse;
          })
          .catch(() => {
            // Si le réseau échoue, essayer depuis le cache
            return caches.match(event.request);
          })
      );
    } else {
      // Pour les requêtes POST, PUT, DELETE: utiliser la synchronisation en arrière-plan
      if (!navigator.onLine) {
        event.respondWith(
          new Response(JSON.stringify({ 
            success: false, 
            message: 'Vous êtes hors ligne. Votre action sera synchronisée lorsque vous serez de nouveau en ligne.' 
          }), {
            headers: { 'Content-Type': 'application/json' }
          })
        );
        
        // Stocker la requête pour synchronisation ultérieure
        storeRequestForSync(event.request.clone());
        return;
      }
    }
  }
  
  // Stratégie par défaut: Network First
  event.respondWith(
    fetch(event.request)
      .catch(() => {
        return caches.match(event.request);
      })
  );
});

// Gestion de la synchronisation en arrière-plan
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-feedback') {
    event.waitUntil(syncPendingRequests());
  }
});

// Stockage des requêtes pour synchronisation ultérieure
async function storeRequestForSync(request) {
  try {
    const db = await openDatabase();
    const clone = request.clone();
    const requestData = {
      url: clone.url,
      method: clone.method,
      headers: Array.from(clone.headers.entries()),
      body: await clone.text(),
      timestamp: Date.now()
    };
    
    const tx = db.transaction('pending-requests', 'readwrite');
    await tx.objectStore('pending-requests').add(requestData);
    
    // Enregistrer une tâche de synchronisation
    if ('serviceWorker' in navigator && 'SyncManager' in window) {
      const registration = await navigator.serviceWorker.ready;
      await registration.sync.register('sync-feedback');
    }
  } catch (error) {
    console.error('Erreur lors du stockage de la requête:', error);
  }
}

// Synchronisation des requêtes en attente
async function syncPendingRequests() {
  try {
    const db = await openDatabase();
    const tx = db.transaction('pending-requests', 'readwrite');
    const store = tx.objectStore('pending-requests');
    const requests = await store.getAll();
    
    for (const requestData of requests) {
      try {
        const response = await fetch(requestData.url, {
          method: requestData.method,
          headers: new Headers(requestData.headers),
          body: requestData.method !== 'GET' ? requestData.body : null
        });
        
        if (response.ok) {
          // Supprimer la requête synchronisée
          await store.delete(requestData.id);
        }
      } catch (error) {
        console.error('Erreur lors de la synchronisation de la requête:', error);
      }
    }
  } catch (error) {
    console.error('Erreur lors de la synchronisation des requêtes:', error);
  }
}

// Ouverture de la base de données IndexedDB
function openDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('feedback-platform-db', 1);
    
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains('pending-requests')) {
        db.createObjectStore('pending-requests', { keyPath: 'id', autoIncrement: true });
      }
      if (!db.objectStoreNames.contains('offline-feedback')) {
        db.createObjectStore('offline-feedback', { keyPath: 'id', autoIncrement: true });
      }
    };
    
    request.onsuccess = (event) => {
      resolve(event.target.result);
    };
    
    request.onerror = (event) => {
      reject(event.target.error);
    };
  });
}

// Notification de mise à jour disponible
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
