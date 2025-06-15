import axios from 'axios';
import { isOnline, saveOfflineFeedback, updateOfflineFeedback, syncOfflineFeedbacks, saveRequestForSync } from './offlineStorage';
import { saveAttachment, getAttachmentsByFeedbackId, syncAttachments } from './attachmentStorage';

// Créer une instance axios avec une configuration de base
const api = axios.create({
  baseURL: (process.env.REACT_APP_API_URL || 'http://localhost:8000/api'),
  headers: {
    'Content-Type': 'application/json',
  },
});

// Intercepteur pour les requêtes
api.interceptors.request.use(
  (config) => {
    // Récupérer le token depuis le localStorage
    const token = localStorage.getItem('token');

    // Si le token existe, l'ajouter aux en-têtes
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Intercepteur pour les réponses
api.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // Si l'erreur est 401 (non autorisé) et que nous n'avons pas déjà essayé de rafraîchir le token
    if (error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Essayer de rafraîchir le token
        const refreshToken = localStorage.getItem('refreshToken');
        if (!refreshToken) {
          throw new Error('Pas de token de rafraîchissement disponible');
        }

        const response = await axios.post('/api/auth/refresh/', { refresh: refreshToken });
        const { access } = response.data;

        // Mettre à jour le token dans le localStorage
        localStorage.setItem('token', access);

        // Mettre à jour l'en-tête d'autorisation pour la requête originale
        originalRequest.headers.Authorization = `Bearer ${access}`;

        // Réessayer la requête originale
        return api(originalRequest);
      } catch (refreshError) {
        // Si le rafraîchissement échoue, déconnecter l'utilisateur
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');

        // Rediriger vers la page de connexion
        window.location.href = '/login';

        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// Fonctions API pour les feedbacks
export const feedbackAPI = {
  // Récupérer tous les feedbacks (avec filtres optionnels)
  getAll: async (filters = {}) => {
    const queryParams = new URLSearchParams();

    // Ajouter les filtres à l'URL avec traitement spécial pour certains champs
    Object.entries(filters).forEach(([key, value]) => {
      // Ne pas ajouter les valeurs vides ou null
      if (value === null || value === undefined || value === '') return;

      // Traitement spécial pour la catégorie (s'assurer qu'elle est un nombre)
      if (key === 'category' && !isNaN(value)) {
        // S'assurer que c'est bien un nombre
        queryParams.append(key, Number(value));
      } else {
        queryParams.append(key, value);
      }
    });

    // Log pour le débogage
    console.log('Filtres appliqués:', Object.fromEntries(queryParams.entries()));

    try {
      // Vérifier si nous sommes en ligne
      if (!isOnline()) {
        console.log('Mode hors-ligne: utilisation des données en cache');
        // Retourner une réponse vide compatible avec l'API
        // Le service worker interceptera cette requête et retournera les données en cache si disponibles
        throw new Error('Hors-ligne');
      }

      // Essayer d'abord avec l'API principale
      return await api.get(`/api/inbound/feedback/?${queryParams.toString()}`);
    } catch (error) {
      console.error('Erreur lors de la récupération des feedbacks:', error);

      // Si nous sommes hors-ligne, le service worker devrait intercepter et retourner les données en cache
      // Sinon, essayer avec l'API alternative
      try {
        return await api.get(`/api/feedback/?${queryParams.toString()}`);
      } catch (fallbackError) {
        console.error('Erreur lors de la récupération des feedbacks (fallback):', fallbackError);

        // Si toutes les tentatives échouent, retourner une structure compatible
        return {
          data: {
            results: [],
            count: 0
          }
        };
      }
    }
  },

  // Synchroniser les feedbacks hors-ligne
  syncOfflineFeedbacks: async () => {
    if (!isOnline()) {
      console.log('Impossible de synchroniser les feedbacks: hors-ligne');
      return { success: false, message: 'Hors-ligne' };
    }

    try {
      // Utiliser la fonction create comme callback pour syncOfflineFeedbacks
      const results = await syncOfflineFeedbacks(feedbackAPI.create);
      console.log('Résultats de la synchronisation:', results);

      return {
        success: true,
        syncedCount: results.filter(r => r.success).length,
        failedCount: results.filter(r => !r.success).length,
        results
      };
    } catch (error) {
      console.error('Erreur lors de la synchronisation des feedbacks:', error);
      return { success: false, message: error.message };
    }
  },

  // Récupérer un feedback par son ID
  getById: (id) => api.get(`/api/feedback/${id}/`),
  // Version alternative pour compatibilité
  getByIdLegacy: (id) => api.get(`/api/inbound/feedback/${id}/`),

  // Créer un nouveau feedback
  create: async (data) => {
    try {
      // Vérifier si nous sommes en ligne
      if (!isOnline()) {
        console.log('Mode hors-ligne: sauvegarde locale du feedback');

        // Sauvegarder le feedback en mode hors-ligne
        const offlineId = await saveOfflineFeedback(data);

        // Retourner une réponse compatible avec l'API
        return {
          data: {
            ...data,
            id: `offline-${offlineId}`,
            created_at: new Date().toISOString(),
            status: 'new',
            _offline: true
          }
        };
      }

      // Si en ligne, envoyer au serveur
      const response = await api.post('/api/inbound/feedback/', data);
      return response;
    } catch (error) {
      console.error('Erreur lors de la création du feedback:', error);

      // En cas d'erreur réseau, essayer de sauvegarder en mode hors-ligne
      try {
        const offlineId = await saveOfflineFeedback(data);
        await saveRequestForSync('/api/inbound/feedback/', 'POST', data);

        // Retourner une réponse compatible avec l'API
        return {
          data: {
            ...data,
            id: `offline-${offlineId}`,
            created_at: new Date().toISOString(),
            status: 'new',
            _offline: true
          }
        };
      } catch (offlineError) {
        console.error('Erreur lors de la sauvegarde hors-ligne:', offlineError);
        throw error; // Rethrow l'erreur originale
      }
    }
  },

  // Mettre à jour un feedback
  update: async (id, data) => {
    try {
      // Vérifier si l'ID est un ID hors-ligne
      if (id.toString().startsWith('offline-')) {
        console.log('Mise à jour d\'un feedback hors-ligne:', id);

        try {
          // Utiliser la nouvelle fonction pour mettre à jour le feedback hors-ligne
          const updatedFeedback = await updateOfflineFeedback(id, data);

          // Retourner une réponse compatible avec l'API
          return {
            data: {
              ...updatedFeedback,
              id: `offline-${updatedFeedback.id}`,
              _offline: true,
              _pendingSync: true
            }
          };
        } catch (offlineError) {
          console.error('Erreur lors de la mise à jour du feedback hors-ligne:', offlineError);
          throw offlineError;
        }
      }

      // Vérifier si nous sommes en ligne
      if (!isOnline()) {
        console.log('Mode hors-ligne: enregistrement de la mise à jour pour synchronisation ultérieure');

        // Enregistrer la requête pour synchronisation ultérieure
        await saveRequestForSync(`/api/feedback/${id}/`, 'PATCH', data);

        // Indiquer visuellement que la mise à jour est en attente de synchronisation
        return {
          data: {
            ...data,
            id,
            _pendingSync: true,
            updatedAt: new Date().toISOString()
          }
        };
      }

      // Si en ligne, essayer d'abord l'API principale
      try {
        const response = await api.patch(`/api/feedback/${id}/`, data);
        console.log('Mise à jour réussie via l\'API principale:', response.data);
        return response;
      } catch (mainApiError) {
        console.error('Erreur avec l\'API principale, tentative avec l\'API alternative:', mainApiError);

        // Essayer avec l'API alternative
        try {
          const response = await api.patch(`/api/inbound/feedback/${id}/`, data);
          console.log('Mise à jour réussie via l\'API alternative:', response.data);
          return response;
        } catch (alternativeApiError) {
          console.error('Erreur avec l\'API alternative:', alternativeApiError);
          throw alternativeApiError;
        }
      }
    } catch (error) {
      console.error('Erreur lors de la mise à jour du feedback:', error);

      // En cas d'erreur réseau, enregistrer pour synchronisation ultérieure
      try {
        await saveRequestForSync(`/api/feedback/${id}/`, 'PATCH', data);
        return {
          data: {
            ...data,
            id,
            _pendingSync: true,
            updatedAt: new Date().toISOString()
          }
        };
      } catch (offlineError) {
        console.error('Erreur lors de l\'enregistrement pour synchronisation:', offlineError);
        throw error; // Rethrow l'erreur originale
      }
    }
  },

  // Ajouter une réponse à un feedback
  respond: async (id, content) => {
    // S'assurer que le contenu est une chaîne de caractères
    const cleanContent = typeof content === 'string' ? content.trim() : String(content).trim();

    try {
      console.log('Envoi de réponse pour le feedback', id, 'avec contenu:', content);

      // Format exact attendu par le backend: { content: string, feedback: id }
      const payload = {
        content: cleanContent,
        feedback: id
      };
      console.log('Payload exact envoyé:', JSON.stringify(payload));

      // Vérifier si l'ID est un ID hors-ligne
      if (id.toString().startsWith('offline-')) {
        console.log('Impossible de répondre à un feedback hors-ligne');
        throw new Error('Impossible de répondre à un feedback hors-ligne');
      }

      // Vérifier si nous sommes en ligne
      if (!isOnline()) {
        console.log('Mode hors-ligne: enregistrement de la réponse pour synchronisation ultérieure');
        await saveRequestForSync(`/api/feedback/${id}/respond/`, 'POST', payload);

        // Retourner une réponse compatible avec l'API
        return {
          data: {
            content: cleanContent,
            feedback: id,
            created_at: new Date().toISOString(),
            _pendingSync: true
          }
        };
      }

      // Définir explicitement les headers pour s'assurer que le Content-Type est correct
      const response = await api.post(`/api/feedback/${id}/respond/`, payload, {
        headers: {
          'Content-Type': 'application/json'
        }
      });

      console.log('Réponse réussie:', response.data);
      return response;
    } catch (error) {
      // Si c'est une erreur liée au mode hors-ligne, la propager directement
      if (error.message === 'Impossible de répondre à un feedback hors-ligne') {
        throw error;
      }

      console.error('Erreur détaillée lors de l\'envoi de réponse:', error.response?.data);
      console.error('Status code:', error.response?.status);
      console.error('Headers de la réponse:', error.response?.headers);
      console.error('Erreur complète:', error);

      // En cas d'erreur réseau, essayer d'enregistrer pour synchronisation ultérieure
      try {
        if (isOnline()) { // Ne pas essayer de sauvegarder si déjà hors-ligne
          const payload = { content: cleanContent, feedback: id };
          await saveRequestForSync(`/api/feedback/${id}/respond/`, 'POST', payload);

          // Retourner une réponse compatible avec l'API
          return {
            data: {
              content: cleanContent,
              feedback: id,
              created_at: new Date().toISOString(),
              _pendingSync: true
            }
          };
        }
      } catch (offlineError) {
        console.error('Erreur lors de l\'enregistrement pour synchronisation:', offlineError);
      }

      throw error;
    }
  },

  // Récupérer les statistiques
  getStats: () => api.get('/api/inbound/feedback/stats/'),
};

// Fonctions API pour les catégories
export const categoryAPI = {
  // Récupérer toutes les catégories (méthode simplifiée sans traitement spécial)
  getAll: () => api.get('/api/categories/'),

  // Récupérer toutes les catégories (sans pagination)
  getAllFlat: async () => {
    try {
      const response = await api.get('/api/categories/');
      if (response.data && response.data.results) {
        // Format paginé - retourner directement les résultats
        return response.data.results;
      } else if (Array.isArray(response.data)) {
        // Déjà un tableau - retourner tel quel
        return response.data;
      } else {
        // Format inconnu
        console.error('Format de réponse catégories inconnu:', response.data);
        return [];
      }
    } catch (error) {
      console.error('Erreur lors de la récupération des catégories:', error);
      return [];
    }
  },
  getById: (id) => api.get(`/api/categories/${id}/`),
  create: (data) => api.post('/api/categories/', data),
  update: (id, data) => api.put(`/api/categories/${id}/`, data),
  delete: (id) => api.delete(`/api/categories/${id}/`),
};

// Fonctions API pour l'authentification
export const authAPI = {
  login: (credentials) => api.post('/auth/login/', credentials),
  refreshToken: (refresh) => api.post('/auth/refresh/', { refresh }),
  getCurrentUser: () => api.get('/auth/user/'),
};

// Fonctions API pour les pièces jointes
export const attachmentAPI = {
  /**
   * Upload une pièce jointe pour un feedback
   * @param {string} feedbackId - ID du feedback
   * @param {File} file - Fichier à uploader
   * @returns {Promise<Object>} Réponse de l'API
   */
  upload: async (feedbackId, file) => {
    try {
      // Vérifier si l'ID est un ID hors-ligne
      if (feedbackId.toString().startsWith('offline-')) {
        // Sauvegarder la pièce jointe en mode hors-ligne
        const attachment = await saveAttachment(feedbackId, file, {
          maxWidth: 1200,
          maxHeight: 1200,
          quality: 0.8
        });

        return { data: { ...attachment, _offline: true } };
      }

      // Vérifier si nous sommes en ligne
      if (!isOnline()) {
        // Sauvegarder la pièce jointe en mode hors-ligne et l'associer au feedback
        const attachment = await saveAttachment(feedbackId, file, {
          maxWidth: 1200,
          maxHeight: 1200,
          quality: 0.8
        });

        // Enregistrer une requête pour synchronisation ultérieure
        await saveRequestForSync(`/api/feedback/${feedbackId}/attachments/`, 'POST', { attachment_id: attachment.id });

        return { data: { ...attachment, _pendingSync: true } };
      }

      // Si en ligne, créer un FormData pour l'upload
      const formData = new FormData();
      formData.append('file', file);

      // Configurer les headers pour l'upload de fichier
      const config = {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      };

      // Essayer d'abord l'API principale
      try {
        const response = await api.post(`/api/feedback/${feedbackId}/attachments/`, formData, config);
        console.log('Pièce jointe uploadée via l\'API principale:', response.data);
        return response;
      } catch (mainApiError) {
        console.error('Erreur avec l\'API principale, tentative avec l\'API alternative:', mainApiError);

        // Essayer avec l'API alternative
        try {
          const response = await api.post(`/api/inbound/feedback/${feedbackId}/attachments/`, formData, config);
          console.log('Pièce jointe uploadée via l\'API alternative:', response.data);
          return response;
        } catch (alternativeApiError) {
          console.error('Erreur avec l\'API alternative:', alternativeApiError);
          throw alternativeApiError;
        }
      }
    } catch (error) {
      console.error('Erreur lors de l\'upload de la pièce jointe:', error);

      // En cas d'erreur réseau, sauvegarder en mode hors-ligne
      try {
        const attachment = await saveAttachment(feedbackId, file, {
          maxWidth: 1200,
          maxHeight: 1200,
          quality: 0.8
        });

        return { data: { ...attachment, _pendingSync: true } };
      } catch (offlineError) {
        console.error('Erreur lors de la sauvegarde hors-ligne de la pièce jointe:', offlineError);
        throw error; // Rethrow l'erreur originale
      }
    }
  },

  /**
   * Récupère les pièces jointes d'un feedback
   * @param {string} feedbackId - ID du feedback
   * @returns {Promise<Array>} Liste des pièces jointes
   */
  getAll: async (feedbackId) => {
    try {
      // Vérifier si l'ID est un ID hors-ligne
      if (feedbackId.toString().startsWith('offline-')) {
        const attachments = await getAttachmentsByFeedbackId(feedbackId);
        return { data: attachments.map(a => ({ ...a, _offline: true })) };
      }

      // Vérifier si nous sommes en ligne
      if (!isOnline()) {
        // Récupérer les pièces jointes stockées localement
        const attachments = await getAttachmentsByFeedbackId(feedbackId);
        return { data: attachments };
      }

      // Si en ligne, essayer d'abord l'API principale
      try {
        const response = await api.get(`/api/feedback/${feedbackId}/attachments/`);

        // Récupérer également les pièces jointes locales
        const localAttachments = await getAttachmentsByFeedbackId(feedbackId);
        const pendingAttachments = localAttachments.filter(a => a.status === 'pending' || a.status === 'error');

        // Combiner les pièces jointes du serveur et les pièces jointes locales en attente
        const combinedAttachments = [
          ...response.data,
          ...pendingAttachments.map(a => ({ ...a, _pendingSync: true }))
        ];

        return { data: combinedAttachments };
      } catch (mainApiError) {
        console.error('Erreur avec l\'API principale, tentative avec l\'API alternative:', mainApiError);

        // Essayer avec l'API alternative
        try {
          const response = await api.get(`/api/inbound/feedback/${feedbackId}/attachments/`);

          // Récupérer également les pièces jointes locales
          const localAttachments = await getAttachmentsByFeedbackId(feedbackId);
          const pendingAttachments = localAttachments.filter(a => a.status === 'pending' || a.status === 'error');

          // Combiner les pièces jointes du serveur et les pièces jointes locales en attente
          const combinedAttachments = [
            ...response.data,
            ...pendingAttachments.map(a => ({ ...a, _pendingSync: true }))
          ];

          return { data: combinedAttachments };
        } catch (alternativeApiError) {
          console.error('Erreur avec l\'API alternative:', alternativeApiError);

          // En cas d'erreur, retourner uniquement les pièces jointes locales
          const localAttachments = await getAttachmentsByFeedbackId(feedbackId);
          return { data: localAttachments.map(a => ({ ...a, _pendingSync: true })) };
        }
      }
    } catch (error) {
      console.error('Erreur lors de la récupération des pièces jointes:', error);

      // En cas d'erreur, retourner un tableau vide
      return { data: [] };
    }
  },

  /**
   * Synchronise les pièces jointes en attente
   * @returns {Promise<Array>} Résultats de la synchronisation
   */
  syncPending: async () => {
    try {
      if (!isOnline()) {
        console.log('Impossible de synchroniser les pièces jointes : hors-ligne');
        return [];
      }

      console.log('Début de la synchronisation des pièces jointes en attente');
      const results = await syncAttachments((feedbackId, file) => attachmentAPI.upload(feedbackId, file));
      console.log('Synchronisation des pièces jointes terminée:', results);

      return results;
    } catch (error) {
      console.error('Erreur lors de la synchronisation des pièces jointes:', error);
      return [];
    }
  },

  /**
   * Supprime une pièce jointe
   * @param {string} feedbackId - ID du feedback
   * @param {string} attachmentId - ID de la pièce jointe
   * @returns {Promise<Object>} Réponse de l'API
   */
  delete: async (feedbackId, attachmentId) => {
    try {
      // Vérifier si l'ID commence par 'offline-'
      if (attachmentId.toString().startsWith('offline-')) {
        // Supprimer localement la pièce jointe hors ligne
        const actualId = attachmentId.toString().replace('offline-', '');
        const { deleteAttachment } = await import('./attachmentStorage');
        await deleteAttachment(actualId);
        return { data: { success: true } };
      }

      // Vérifier si nous sommes en ligne
      if (!isOnline()) {
        // Enregistrer une requête pour synchronisation ultérieure
        await saveRequestForSync(`/api/feedback/${feedbackId}/attachments/${attachmentId}/`, 'DELETE', {});
        return { data: { success: true, _pendingSync: true } };
      }

      // Si en ligne, essayer d'abord l'API principale
      try {
        const response = await api.delete(`/api/feedback/${feedbackId}/attachments/${attachmentId}/`);
        return response;
      } catch (mainApiError) {
        console.error('Erreur avec l\'API principale, tentative avec l\'API alternative:', mainApiError);

        // Essayer avec l'API alternative
        try {
          const response = await api.delete(`/api/inbound/feedback/${feedbackId}/attachments/${attachmentId}/`);
          return response;
        } catch (alternativeApiError) {
          console.error('Erreur avec l\'API alternative:', alternativeApiError);
          throw alternativeApiError;
        }
      }
    } catch (error) {
      console.error('Erreur lors de la suppression de la pièce jointe:', error);
      throw error;
    }
  }
};

export default api;
