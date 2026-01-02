/**
 * Service Worker pour DynSoft Pharma PWA
 * Stratégie: Cache First avec fallback réseau
 */

const CACHE_NAME = 'dynsoft-pharma-v1';
const API_CACHE_NAME = 'dynsoft-pharma-api-v1';

// Ressources à mettre en cache immédiatement (App Shell)
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/favicon.ico',
  '/logo192.png',
  '/logo512.png',
];

// Patterns d'URL API à mettre en cache
const API_PATTERNS = [
  '/api/products',
  '/api/categories',
  '/api/customers',
  '/api/suppliers',
  '/api/settings',
  '/api/units',
];

// Installation du service worker
self.addEventListener('install', (event) => {
  console.log('[SW] Installation en cours...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Mise en cache des ressources statiques');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// Activation du service worker
self.addEventListener('activate', (event) => {
  console.log('[SW] Activation en cours...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME && name !== API_CACHE_NAME)
          .map((name) => {
            console.log('[SW] Suppression du cache obsolète:', name);
            return caches.delete(name);
          })
      );
    }).then(() => self.clients.claim())
  );
});

// Interception des requêtes
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Ignorer les requêtes non-GET
  if (request.method !== 'GET') {
    return;
  }

  // Stratégie pour les requêtes API
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirstWithCache(request));
    return;
  }

  // Stratégie pour les ressources statiques
  event.respondWith(cacheFirstWithNetwork(request));
});

/**
 * Stratégie Cache First avec fallback réseau
 * Pour les ressources statiques
 */
async function cacheFirstWithNetwork(request) {
  const cache = await caches.open(CACHE_NAME);
  const cachedResponse = await cache.match(request);
  
  if (cachedResponse) {
    // Mise à jour en arrière-plan
    updateCacheInBackground(request, cache);
    return cachedResponse;
  }

  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    // Retourner une page offline si disponible
    const offlineResponse = await cache.match('/offline.html');
    if (offlineResponse) {
      return offlineResponse;
    }
    return new Response('Hors ligne', { status: 503, statusText: 'Service Unavailable' });
  }
}

/**
 * Stratégie Network First avec fallback cache
 * Pour les requêtes API
 */
async function networkFirstWithCache(request) {
  const cache = await caches.open(API_CACHE_NAME);

  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      // Mettre en cache la réponse API
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    // Fallback sur le cache
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
      console.log('[SW] Réponse depuis le cache API:', request.url);
      return cachedResponse;
    }
    // Retourner une erreur JSON pour les API
    return new Response(
      JSON.stringify({ error: 'Offline', message: 'Données non disponibles hors ligne' }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

/**
 * Mise à jour du cache en arrière-plan
 */
async function updateCacheInBackground(request, cache) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
  } catch (error) {
    // Ignorer les erreurs de mise à jour en arrière-plan
  }
}

// Gestion des messages depuis l'application
self.addEventListener('message', (event) => {
  if (event.data === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data === 'CLEAR_CACHE') {
    caches.keys().then((names) => {
      names.forEach((name) => caches.delete(name));
    });
  }
});

// Sync en arrière-plan (pour les navigateurs supportés)
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-pending-changes') {
    console.log('[SW] Synchronisation des changements en attente...');
    event.waitUntil(syncPendingChanges());
  }
});

async function syncPendingChanges() {
  // Cette fonction sera appelée quand la connexion est rétablie
  // Notifier l'application pour qu'elle synchronise
  const clients = await self.clients.matchAll();
  clients.forEach((client) => {
    client.postMessage({ type: 'SYNC_REQUIRED' });
  });
}

console.log('[SW] Service Worker chargé - DynSoft Pharma PWA');
