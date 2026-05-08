/**
 * Service Worker amélioré pour DynSoft Pharma PWA
 * Supporte: Cache des ressources statiques, API GET, et queue des mutations offline
 */

const CACHE_VERSION = 2;
const CACHE_NAME = `dynsoft-pharma-v${CACHE_VERSION}`;
const API_CACHE_NAME = `dynsoft-pharma-api-v${CACHE_VERSION}`;
const OFFLINE_QUEUE_NAME = 'offline-queue';

// Ressources à mettre en cache immédiatement (App Shell)
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/favicon.ico',
  '/logo192.png',
  '/logo512.png',
];

// Patterns d'URL API à mettre en cache (GET)
const CACHEABLE_API_PATTERNS = [
  '/api/products',
  '/api/categories',
  '/api/customers',
  '/api/suppliers',
  '/api/settings',
  '/api/units',
  '/api/sales',
  '/api/supplies',
  '/api/returns',
  '/api/prescriptions',
];

// API endpoints qui peuvent être mis en queue pour offline
const QUEUEABLE_API_PATTERNS = [
  { pattern: '/api/sales', methods: ['POST'] },
  { pattern: '/api/customers', methods: ['POST', 'PUT'] },
  { pattern: '/api/products', methods: ['POST', 'PUT'] },
  { pattern: '/api/returns', methods: ['POST'] },
];

// Installation du service worker
self.addEventListener('install', (event) => {
  console.log('[SW] Installation v' + CACHE_VERSION);
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
  console.log('[SW] Activation v' + CACHE_VERSION);
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => {
            return name.startsWith('dynsoft-pharma') && 
                   name !== CACHE_NAME && 
                   name !== API_CACHE_NAME;
          })
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

  // Requêtes API
  if (url.pathname.startsWith('/api/')) {
    if (request.method === 'GET') {
      // GET: Network first avec cache fallback
      event.respondWith(networkFirstWithCache(request));
    } else if (['POST', 'PUT', 'DELETE'].includes(request.method)) {
      // Mutations: Essayer network, sinon queue
      event.respondWith(handleMutation(request));
    }
    return;
  }

  // Ressources statiques: Cache first
  if (request.method === 'GET') {
    event.respondWith(cacheFirstWithNetwork(request));
  }
});

/**
 * Stratégie Cache First avec fallback réseau
 */
async function cacheFirstWithNetwork(request) {
  const cache = await caches.open(CACHE_NAME);
  const cachedResponse = await cache.match(request);
  
  if (cachedResponse) {
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
    return new Response('Hors ligne', { status: 503 });
  }
}

/**
 * Stratégie Network First avec fallback cache pour GET API
 */
async function networkFirstWithCache(request) {
  const cache = await caches.open(API_CACHE_NAME);

  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
      console.log('[SW] Réponse depuis le cache:', request.url);
      // Ajouter un header pour indiquer que c'est du cache
      const headers = new Headers(cachedResponse.headers);
      headers.set('X-From-Cache', 'true');
      return new Response(cachedResponse.body, {
        status: cachedResponse.status,
        statusText: cachedResponse.statusText,
        headers
      });
    }
    return new Response(
      JSON.stringify({ 
        error: 'Offline', 
        message: 'Données non disponibles hors ligne',
        offline: true 
      }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

/**
 * Gestion des mutations (POST/PUT/DELETE)
 */
async function handleMutation(request) {
  try {
    // Essayer d'abord le réseau
    const networkResponse = await fetch(request.clone());
    return networkResponse;
  } catch (error) {
    // Offline: vérifier si cette requête peut être mise en queue
    const url = new URL(request.url);
    const canQueue = QUEUEABLE_API_PATTERNS.some(
      p => url.pathname.startsWith(p.pattern) && p.methods.includes(request.method)
    );

    if (canQueue) {
      // Lire le body de la requête
      const body = await request.clone().text();
      
      // Sauvegarder dans IndexedDB via message
      const queuedRequest = {
        id: `offline-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        url: request.url,
        method: request.method,
        headers: Object.fromEntries(request.headers.entries()),
        body: body,
        timestamp: new Date().toISOString(),
        status: 'pending'
      };

      // Notifier l'application
      const clients = await self.clients.matchAll();
      clients.forEach(client => {
        client.postMessage({
          type: 'OFFLINE_REQUEST_QUEUED',
          request: queuedRequest
        });
      });

      // Retourner une réponse simulée
      return new Response(
        JSON.stringify({
          success: true,
          offline: true,
          queued: true,
          message: 'Opération enregistrée localement. Elle sera synchronisée au retour en ligne.',
          tempId: queuedRequest.id
        }),
        { 
          status: 202, // Accepted
          headers: { 
            'Content-Type': 'application/json',
            'X-Offline-Queued': 'true'
          } 
        }
      );
    }

    // Non queueable: retourner erreur
    return new Response(
      JSON.stringify({
        error: 'Offline',
        message: 'Cette opération nécessite une connexion internet',
        offline: true
      }),
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
    // Ignorer les erreurs
  }
}

// Gestion des messages depuis l'application
self.addEventListener('message', async (event) => {
  const { type, data } = event.data || {};

  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;

    case 'CLEAR_CACHE':
      const cacheNames = await caches.keys();
      await Promise.all(cacheNames.map(name => caches.delete(name)));
      event.ports[0]?.postMessage({ success: true });
      break;

    case 'GET_CACHE_STATUS':
      const status = await getCacheStatus();
      event.ports[0]?.postMessage(status);
      break;

    case 'RETRY_QUEUED_REQUESTS':
      // Sera géré par l'application principale
      break;
  }
});

// Background Sync (pour les navigateurs supportés)
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-pending-changes') {
    console.log('[SW] Background sync triggered');
    event.waitUntil(notifyAppToSync());
  }
});

async function notifyAppToSync() {
  const clients = await self.clients.matchAll();
  clients.forEach(client => {
    client.postMessage({ type: 'BACKGROUND_SYNC_TRIGGERED' });
  });
}

async function getCacheStatus() {
  const apiCache = await caches.open(API_CACHE_NAME);
  const staticCache = await caches.open(CACHE_NAME);
  
  const apiKeys = await apiCache.keys();
  const staticKeys = await staticCache.keys();

  return {
    version: CACHE_VERSION,
    apiCacheSize: apiKeys.length,
    staticCacheSize: staticKeys.length,
    timestamp: new Date().toISOString()
  };
}

console.log('[SW] Service Worker v' + CACHE_VERSION + ' chargé - DynSoft Pharma PWA');
