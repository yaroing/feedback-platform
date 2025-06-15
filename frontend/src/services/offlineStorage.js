/**
 * Service de gestion du stockage hors-ligne et de la synchronisation en arrière-plan
 */

// Nom de la base de données IndexedDB
const DB_NAME = 'feedback-platform-db';
const DB_VERSION = 2; // Incrémenté pour ajouter le store des pièces jointes
const OFFLINE_FEEDBACK_STORE = 'offline-feedback';
const PENDING_REQUESTS_STORE = 'pending-requests';
const ATTACHMENTS_STORE = 'attachments';

/**
 * Ouvre la base de données IndexedDB
 * @returns {Promise<IDBDatabase>} Instance de la base de données
 */
export const openDatabase = () => {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      const oldVersion = event.oldVersion;
      
      // Créer le store pour les feedbacks hors-ligne
      if (!db.objectStoreNames.contains(OFFLINE_FEEDBACK_STORE)) {
        db.createObjectStore(OFFLINE_FEEDBACK_STORE, { keyPath: 'id', autoIncrement: true });
      }
      
      // Créer le store pour les requêtes en attente
      if (!db.objectStoreNames.contains(PENDING_REQUESTS_STORE)) {
        db.createObjectStore(PENDING_REQUESTS_STORE, { keyPath: 'id', autoIncrement: true });
      }
      
      // Créer le store pour les pièces jointes (version 2+)
      if (oldVersion < 2 && !db.objectStoreNames.contains(ATTACHMENTS_STORE)) {
        const attachmentStore = db.createObjectStore(ATTACHMENTS_STORE, { keyPath: 'id', autoIncrement: true });
        // Créer des index pour faciliter la recherche
        attachmentStore.createIndex('feedbackId', 'feedbackId', { unique: false });
        attachmentStore.createIndex('filename', 'filename', { unique: false });
        attachmentStore.createIndex('status', 'status', { unique: false });
      }
    };
    
    request.onsuccess = (event) => {
      resolve(event.target.result);
    };
    
    request.onerror = (event) => {
      console.error('Erreur lors de l\'ouverture de la base de données:', event.target.error);
      reject(event.target.error);
    };
  });
};

/**
 * Sauvegarde un feedback en mode hors-ligne
 * @param {Object} feedback - Données du feedback à sauvegarder
 * @returns {Promise<number>} ID du feedback sauvegardé
 */
export const saveOfflineFeedback = async (feedback) => {
  try {
    const db = await openDatabase();
    const transaction = db.transaction(OFFLINE_FEEDBACK_STORE, 'readwrite');
    const store = transaction.objectStore(OFFLINE_FEEDBACK_STORE);
    
    // Ajouter des métadonnées pour la synchronisation
    const feedbackToSave = {
      ...feedback,
      createdAt: new Date().toISOString(),
      synced: false
    };
    
    return new Promise((resolve, reject) => {
      const request = store.add(feedbackToSave);
      
      request.onsuccess = (event) => {
        console.log('Feedback sauvegardé en mode hors-ligne:', event.target.result);
        resolve(event.target.result);
      };
      
      request.onerror = (event) => {
        console.error('Erreur lors de la sauvegarde du feedback hors-ligne:', event.target.error);
        reject(event.target.error);
      };
    });
  } catch (error) {
    console.error('Erreur lors de la sauvegarde du feedback hors-ligne:', error);
    throw error;
  }
};

/**
 * Récupère tous les feedbacks hors-ligne
 * @returns {Promise<Array>} Liste des feedbacks hors-ligne
 */
export const getOfflineFeedbacks = async () => {
  try {
    const db = await openDatabase();
    const transaction = db.transaction(OFFLINE_FEEDBACK_STORE, 'readonly');
    const store = transaction.objectStore(OFFLINE_FEEDBACK_STORE);
    
    return new Promise((resolve, reject) => {
      const request = store.getAll();
      
      request.onsuccess = (event) => {
        resolve(event.target.result);
      };
      
      request.onerror = (event) => {
        console.error('Erreur lors de la récupération des feedbacks hors-ligne:', event.target.error);
        reject(event.target.error);
      };
    });
  } catch (error) {
    console.error('Erreur lors de la récupération des feedbacks hors-ligne:', error);
    return [];
  }
};

/**
 * Enregistre une requête API pour synchronisation ultérieure
 * @param {string} url - URL de la requête
 * @param {string} method - Méthode HTTP (GET, POST, PUT, DELETE)
 * @param {Object} data - Données de la requête
 * @returns {Promise<number>} ID de la requête enregistrée
 */
export const saveRequestForSync = async (url, method, data) => {
  try {
    const db = await openDatabase();
    const transaction = db.transaction(PENDING_REQUESTS_STORE, 'readwrite');
    const store = transaction.objectStore(PENDING_REQUESTS_STORE);
    
    const requestData = {
      url,
      method,
      data,
      timestamp: Date.now()
    };
    
    return new Promise((resolve, reject) => {
      const request = store.add(requestData);
      
      request.onsuccess = (event) => {
        console.log('Requête enregistrée pour synchronisation:', event.target.result);
        
        // Enregistrer une tâche de synchronisation si le navigateur le supporte
        if ('serviceWorker' in navigator && 'SyncManager' in window) {
          navigator.serviceWorker.ready.then((registration) => {
            registration.sync.register('sync-feedback')
              .then(() => console.log('Tâche de synchronisation enregistrée'))
              .catch(err => console.error('Erreur lors de l\'enregistrement de la tâche de synchronisation:', err));
          });
        }
        
        resolve(event.target.result);
      };
      
      request.onerror = (event) => {
        console.error('Erreur lors de l\'enregistrement de la requête:', event.target.error);
        reject(event.target.error);
      };
    });
  } catch (error) {
    console.error('Erreur lors de l\'enregistrement de la requête:', error);
    throw error;
  }
};

/**
 * Récupère un feedback hors-ligne par son ID
 * @param {number} id - ID du feedback hors-ligne
 * @returns {Promise<Object|null>} Le feedback trouvé ou null
 */
export const getOfflineFeedbackById = async (id) => {
  try {
    // Extraire l'ID numérique si c'est un ID au format 'offline-123'
    const numericId = id.toString().startsWith('offline-') 
      ? parseInt(id.toString().replace('offline-', ''), 10)
      : parseInt(id, 10);
    
    if (isNaN(numericId)) {
      console.error('ID de feedback hors-ligne invalide:', id);
      return null;
    }
    
    const db = await openDatabase();
    const transaction = db.transaction(OFFLINE_FEEDBACK_STORE, 'readonly');
    const store = transaction.objectStore(OFFLINE_FEEDBACK_STORE);
    
    return new Promise((resolve, reject) => {
      const request = store.get(numericId);
      
      request.onsuccess = (event) => {
        resolve(event.target.result || null);
      };
      
      request.onerror = (event) => {
        console.error('Erreur lors de la récupération du feedback hors-ligne:', event.target.error);
        reject(event.target.error);
      };
    });
  } catch (error) {
    console.error('Erreur lors de la récupération du feedback hors-ligne:', error);
    return null;
  }
};

/**
 * Met à jour un feedback hors-ligne
 * @param {number} id - ID du feedback hors-ligne
 * @param {Object} data - Nouvelles données du feedback
 * @returns {Promise<Object>} Le feedback mis à jour
 */
export const updateOfflineFeedback = async (id, data) => {
  try {
    // Extraire l'ID numérique si c'est un ID au format 'offline-123'
    const numericId = id.toString().startsWith('offline-') 
      ? parseInt(id.toString().replace('offline-', ''), 10)
      : parseInt(id, 10);
    
    if (isNaN(numericId)) {
      throw new Error('ID de feedback hors-ligne invalide: ' + id);
    }
    
    // Récupérer le feedback existant
    const existingFeedback = await getOfflineFeedbackById(numericId);
    if (!existingFeedback) {
      throw new Error('Feedback hors-ligne non trouvé: ' + numericId);
    }
    
    // Fusionner les données
    const updatedFeedback = {
      ...existingFeedback,
      ...data,
      id: numericId, // Conserver l'ID original
      updatedAt: new Date().toISOString(),
      synced: false
    };
    
    const db = await openDatabase();
    const transaction = db.transaction(OFFLINE_FEEDBACK_STORE, 'readwrite');
    const store = transaction.objectStore(OFFLINE_FEEDBACK_STORE);
    
    return new Promise((resolve, reject) => {
      const request = store.put(updatedFeedback);
      
      request.onsuccess = (event) => {
        console.log('Feedback hors-ligne mis à jour:', numericId);
        resolve(updatedFeedback);
      };
      
      request.onerror = (event) => {
        console.error('Erreur lors de la mise à jour du feedback hors-ligne:', event.target.error);
        reject(event.target.error);
      };
    });
  } catch (error) {
    console.error('Erreur lors de la mise à jour du feedback hors-ligne:', error);
    throw error;
  }
};

/**
 * Synchronise les feedbacks hors-ligne avec le serveur
 * @param {Function} apiFunction - Fonction API à utiliser pour la synchronisation
 * @returns {Promise<Array>} Résultats de la synchronisation
 */
export const syncOfflineFeedbacks = async (apiFunction) => {
  try {
    const offlineFeedbacks = await getOfflineFeedbacks();
    if (!offlineFeedbacks.length) {
      return [];
    }
    
    console.log(`Synchronisation de ${offlineFeedbacks.length} feedbacks hors-ligne`);
    
    const results = [];
    const db = await openDatabase();
    
    for (const feedback of offlineFeedbacks) {
      try {
        // Envoyer le feedback au serveur
        const response = await apiFunction(feedback);
        
        // Marquer comme synchronisé ou supprimer
        const transaction = db.transaction(OFFLINE_FEEDBACK_STORE, 'readwrite');
        const store = transaction.objectStore(OFFLINE_FEEDBACK_STORE);
        
        await new Promise((resolve, reject) => {
          const request = store.delete(feedback.id);
          request.onsuccess = () => resolve();
          request.onerror = (event) => reject(event.target.error);
        });
        
        results.push({ success: true, feedback, response });
      } catch (error) {
        console.error(`Erreur lors de la synchronisation du feedback #${feedback.id}:`, error);
        results.push({ success: false, feedback, error });
      }
    }
    
    return results;
  } catch (error) {
    console.error('Erreur lors de la synchronisation des feedbacks hors-ligne:', error);
    return [];
  }
};

/**
 * Vérifie si l'application est en ligne
 * @returns {boolean} true si en ligne, false sinon
 */
export const isOnline = () => {
  return navigator.onLine;
};

/**
 * Ajoute des écouteurs d'événements pour détecter les changements de connectivité
 * @param {Function} onlineCallback - Fonction à appeler quand l'application est en ligne
 * @param {Function} offlineCallback - Fonction à appeler quand l'application est hors-ligne
 */
export const addConnectivityListeners = (onlineCallback, offlineCallback) => {
  window.addEventListener('online', () => {
    console.log('Application en ligne');
    if (onlineCallback) onlineCallback();
  });
  
  window.addEventListener('offline', () => {
    console.log('Application hors-ligne');
    if (offlineCallback) offlineCallback();
  });
};

/**
 * Supprime les écouteurs d'événements de connectivité
 * @param {Function} onlineCallback - Fonction appelée quand l'application est en ligne
 * @param {Function} offlineCallback - Fonction appelée quand l'application est hors-ligne
 */
export const removeConnectivityListeners = (onlineCallback, offlineCallback) => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('online', onlineCallback);
    window.removeEventListener('offline', offlineCallback);
  }
};
