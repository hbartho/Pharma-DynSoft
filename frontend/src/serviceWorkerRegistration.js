/**
 * Service Worker Registration pour DynSoft Pharma PWA
 * Gère l'enregistrement et la mise à jour du service worker
 */

// Vérifie si le service worker est supporté
const isServiceWorkerSupported = 'serviceWorker' in navigator;

// URLs à cacher en priorité (shell de l'application)
const APP_SHELL_URLS = [
  '/',
  '/index.html',
  '/static/js/main.chunk.js',
  '/static/css/main.chunk.css',
  '/manifest.json',
];

/**
 * Enregistre le service worker
 */
export function register(config) {
  if (!isServiceWorkerSupported) {
    console.log('[SW] Service Worker non supporté par ce navigateur');
    return;
  }

  if (process.env.NODE_ENV === 'production' || process.env.REACT_APP_ENABLE_SW === 'true') {
    const publicUrl = new URL(process.env.PUBLIC_URL, window.location.href);
    if (publicUrl.origin !== window.location.origin) {
      return;
    }

    window.addEventListener('load', () => {
      const swUrl = `${process.env.PUBLIC_URL}/service-worker.js`;
      registerValidSW(swUrl, config);
    });
  }
}

function registerValidSW(swUrl, config) {
  navigator.serviceWorker
    .register(swUrl)
    .then((registration) => {
      console.log('[SW] Service Worker enregistré avec succès');

      // Vérifie les mises à jour périodiquement
      registration.addEventListener('updatefound', () => {
        const installingWorker = registration.installing;
        if (installingWorker == null) {
          return;
        }
        installingWorker.addEventListener('statechange', () => {
          if (installingWorker.state === 'installed') {
            if (navigator.serviceWorker.controller) {
              // Nouvelle mise à jour disponible
              console.log('[SW] Nouvelle version disponible!');
              if (config && config.onUpdate) {
                config.onUpdate(registration);
              }
              // Notifier l'utilisateur
              if (window.confirm('Une nouvelle version est disponible. Voulez-vous rafraîchir?')) {
                window.location.reload();
              }
            } else {
              // Contenu mis en cache pour la première fois
              console.log('[SW] Contenu mis en cache pour utilisation hors ligne');
              if (config && config.onSuccess) {
                config.onSuccess(registration);
              }
            }
          }
        });
      });
    })
    .catch((error) => {
      console.error('[SW] Erreur lors de l\'enregistrement:', error);
    });
}

/**
 * Désenregistre le service worker
 */
export function unregister() {
  if (isServiceWorkerSupported) {
    navigator.serviceWorker.ready
      .then((registration) => {
        registration.unregister();
        console.log('[SW] Service Worker désenregistré');
      })
      .catch((error) => {
        console.error(error.message);
      });
  }
}

/**
 * Envoyer un message au service worker
 */
export function sendMessageToSW(message) {
  if (navigator.serviceWorker.controller) {
    navigator.serviceWorker.controller.postMessage(message);
  }
}

/**
 * Forcer la mise à jour du service worker
 */
export async function forceUpdate() {
  if (!isServiceWorkerSupported) return;

  const registration = await navigator.serviceWorker.ready;
  await registration.update();
  console.log('[SW] Mise à jour forcée');
}

/**
 * Nettoyer tous les caches
 */
export async function clearAllCaches() {
  if ('caches' in window) {
    const cacheNames = await caches.keys();
    await Promise.all(cacheNames.map((name) => caches.delete(name)));
    console.log('[SW] Tous les caches ont été supprimés');
  }
}

export default { register, unregister, sendMessageToSW, forceUpdate, clearAllCaches };
