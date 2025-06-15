/* eslint-disable no-restricted-globals */

// Ce service worker peut être personnalisé!
// Voir https://developers.google.com/web/tools/workbox/modules
// pour la liste des modules Workbox disponibles, ou ajoutez n'importe quel autre
// code que vous souhaitez.
// Vous pouvez également supprimer ce fichier si vous préférez ne pas utiliser de service worker,
// ou le remplacer par votre propre code de service worker.

import { clientsClaim } from 'workbox-core';
import { ExpirationPlugin } from 'workbox-expiration';
import { precacheAndRoute, createHandlerBoundToURL } from 'workbox-precaching';
import { registerRoute } from 'workbox-routing';
import { StaleWhileRevalidate } from 'workbox-strategies';

clientsClaim();

// Précache tous les actifs générés par votre processus de construction.
// Leur URL est injectée dans le manifeste de précache généré automatiquement.
// Voir https://cra.link/PWA
precacheAndRoute(self.__WB_MANIFEST);

// Configurer le gestionnaire de navigation d'application pour retourner l'index.html depuis
// précache pour les requêtes de navigation.
const fileExtensionRegexp = new RegExp('/[^/?]+\\.[^/]+$');
registerRoute(
  // Retourner index.html pour toutes les requêtes de navigation (premier chargement de page)
  ({ request, url }) => {
    if (request.mode !== 'navigate') {
      return false;
    }

    // Si c'est une URL comme /quelque-chose/XXXXX.html, on suppose que c'est une demande d'un fichier HTML
    if (url.pathname.match(fileExtensionRegexp)) {
      return false;
    }

    // Retourner true pour envoyer la requête à la route d'index.html
    return true;
  },
  createHandlerBoundToURL(process.env.PUBLIC_URL + '/index.html')
);

// Une stratégie de mise en cache pour toutes les autres requêtes. Ici, nous utilisons
// une stratégie StaleWhileRevalidate, qui est utile pour les actifs qui ne changent pas souvent.
registerRoute(
  // Ajoutez ici les expressions régulières pour les routes que vous souhaitez mettre en cache,
  // ou les routes qui correspondent aux fichiers de navigation (voir ci-dessus)
  ({ url }) => url.origin === self.location.origin && url.pathname.startsWith('/api/'),
  new StaleWhileRevalidate({
    cacheName: 'api-responses',
    plugins: [
      // Assurez-vous que les réponses mises en cache ne sont pas conservées indéfiniment
      new ExpirationPlugin({
        maxEntries: 50,
        maxAgeSeconds: 30 * 24 * 60 * 60, // 30 jours
      }),
    ],
  })
);

// Ce permet au service worker d'être mis à jour immédiatement par tous les clients qui
// le contrôlent actuellement.
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// Synchronisation en arrière-plan pour les soumissions de feedback en mode hors ligne
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-feedback') {
    event.waitUntil(syncFeedback());
  }
});

// Fonction pour synchroniser les feedbacks stockés localement lorsque la connexion est rétablie
async function syncFeedback() {
  try {
    const db = await openDB();
    const tx = db.transaction('offlineFeedbacks', 'readonly');
    const store = tx.objectStore('offlineFeedbacks');
    const feedbacks = await store.getAll();
    
    for (const feedback of feedbacks) {
      try {
        const response = await fetch('/api/feedback/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(feedback),
        });
        
        if (response.ok) {
          // Supprimer le feedback synchronisé de la base de données locale
          const deleteTx = db.transaction('offlineFeedbacks', 'readwrite');
          const deleteStore = deleteTx.objectStore('offlineFeedbacks');
          await deleteStore.delete(feedback.id);
          await deleteTx.complete;
        }
      } catch (error) {
        console.error('Erreur lors de la synchronisation du feedback:', error);
      }
    }
    
    await tx.complete;
  } catch (error) {
    console.error('Erreur lors de l\'accès à la base de données IndexedDB:', error);
  }
}

// Fonction pour ouvrir la base de données IndexedDB
function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('FeedbackDB', 1);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains('offlineFeedbacks')) {
        db.createObjectStore('offlineFeedbacks', { keyPath: 'id', autoIncrement: true });
      }
    };
  });
}
