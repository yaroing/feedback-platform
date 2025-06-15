/**
 * Service de gestion des pièces jointes hors-ligne
 */

import { openDatabase, isOnline } from './offlineStorage';

// Constantes
const ATTACHMENTS_STORE = 'attachments';

/**
 * Compresse une image pour réduire sa taille
 * @param {File|Blob} file - Fichier image à compresser
 * @param {Object} options - Options de compression
 * @param {number} options.maxWidth - Largeur maximale de l'image compressée
 * @param {number} options.maxHeight - Hauteur maximale de l'image compressée
 * @param {number} options.quality - Qualité de compression (0-1)
 * @returns {Promise<Blob>} Image compressée
 */
export const compressImage = (file, options = {}) => {
  const {
    maxWidth = 1024,
    maxHeight = 1024,
    quality = 0.8
  } = options;
  
  return new Promise((resolve, reject) => {
    // Vérifier que le fichier est une image
    if (!file.type.startsWith('image/')) {
      // Si ce n'est pas une image, retourner le fichier tel quel
      return resolve(file);
    }
    
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = (event) => {
      const img = new Image();
      img.src = event.target.result;
      
      img.onload = () => {
        // Calculer les dimensions pour maintenir le ratio
        let width = img.width;
        let height = img.height;
        
        if (width > maxWidth) {
          height = (height * maxWidth) / width;
          width = maxWidth;
        }
        
        if (height > maxHeight) {
          width = (width * maxHeight) / height;
          height = maxHeight;
        }
        
        // Créer un canvas pour la compression
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, width, height);
        
        // Convertir en blob
        canvas.toBlob(
          (blob) => {
            if (!blob) {
              reject(new Error('Erreur lors de la compression de l\'image'));
              return;
            }
            
            // Créer un nouveau fichier avec les mêmes propriétés que l'original
            const compressedFile = new Blob([blob], { type: file.type });
            resolve(compressedFile);
          },
          file.type,
          quality
        );
      };
      
      img.onerror = () => {
        reject(new Error('Erreur lors du chargement de l\'image'));
      };
    };
    
    reader.onerror = () => {
      reject(new Error('Erreur lors de la lecture du fichier'));
    };
  });
};

/**
 * Sauvegarde une pièce jointe en mode hors-ligne
 * @param {number|string} feedbackId - ID du feedback associé (peut être un ID hors-ligne)
 * @param {File|Blob} file - Fichier à sauvegarder
 * @param {Object} options - Options de compression
 * @returns {Promise<Object>} Pièce jointe sauvegardée
 */
export const saveAttachment = async (feedbackId, file, options = {}) => {
  try {
    // Extraire l'ID numérique si c'est un ID au format 'offline-123'
    const numericFeedbackId = feedbackId.toString().startsWith('offline-')
      ? parseInt(feedbackId.toString().replace('offline-', ''), 10)
      : feedbackId;
    
    // Compresser l'image si c'est une image
    let processedFile = file;
    if (file.type.startsWith('image/')) {
      processedFile = await compressImage(file, options);
    }
    
    // Convertir le fichier en ArrayBuffer pour le stockage
    const fileBuffer = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsArrayBuffer(processedFile);
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(reader.error);
    });
    
    const db = await openDatabase();
    const transaction = db.transaction(ATTACHMENTS_STORE, 'readwrite');
    const store = transaction.objectStore(ATTACHMENTS_STORE);
    
    const attachment = {
      feedbackId: numericFeedbackId,
      filename: file.name,
      type: file.type,
      size: processedFile.size,
      data: fileBuffer,
      status: 'pending', // pending, synced, error
      createdAt: new Date().toISOString()
    };
    
    return new Promise((resolve, reject) => {
      const request = store.add(attachment);
      
      request.onsuccess = (event) => {
        const id = event.target.result;
        console.log('Pièce jointe sauvegardée en mode hors-ligne:', id);
        resolve({ ...attachment, id });
      };
      
      request.onerror = (event) => {
        console.error('Erreur lors de la sauvegarde de la pièce jointe:', event.target.error);
        reject(event.target.error);
      };
    });
  } catch (error) {
    console.error('Erreur lors de la sauvegarde de la pièce jointe:', error);
    throw error;
  }
};

/**
 * Récupère toutes les pièces jointes associées à un feedback
 * @param {number|string} feedbackId - ID du feedback
 * @returns {Promise<Array>} Liste des pièces jointes
 */
export const getAttachmentsByFeedbackId = async (feedbackId) => {
  try {
    // Extraire l'ID numérique si c'est un ID au format 'offline-123'
    const numericFeedbackId = feedbackId.toString().startsWith('offline-')
      ? parseInt(feedbackId.toString().replace('offline-', ''), 10)
      : feedbackId;
    
    const db = await openDatabase();
    const transaction = db.transaction(ATTACHMENTS_STORE, 'readonly');
    const store = transaction.objectStore(ATTACHMENTS_STORE);
    const index = store.index('feedbackId');
    
    return new Promise((resolve, reject) => {
      const request = index.getAll(numericFeedbackId);
      
      request.onsuccess = (event) => {
        resolve(event.target.result || []);
      };
      
      request.onerror = (event) => {
        console.error('Erreur lors de la récupération des pièces jointes:', event.target.error);
        reject(event.target.error);
      };
    });
  } catch (error) {
    console.error('Erreur lors de la récupération des pièces jointes:', error);
    return [];
  }
};

/**
 * Synchronise les pièces jointes en attente avec le serveur
 * @param {Function} uploadFunction - Fonction API à utiliser pour l'upload
 * @returns {Promise<Array>} Résultats de la synchronisation
 */
export const syncAttachments = async (uploadFunction) => {
  try {
    const db = await openDatabase();
    const transaction = db.transaction(ATTACHMENTS_STORE, 'readonly');
    const store = transaction.objectStore(ATTACHMENTS_STORE);
    const index = store.index('status');
    
    // Récupérer toutes les pièces jointes en attente
    const pendingAttachments = await new Promise((resolve, reject) => {
      const request = index.getAll('pending');
      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => reject(request.error);
    });
    
    if (!pendingAttachments.length) {
      return [];
    }
    
    console.log(`Synchronisation de ${pendingAttachments.length} pièces jointes en attente`);
    
    const results = [];
    
    for (const attachment of pendingAttachments) {
      try {
        // Convertir l'ArrayBuffer en Blob pour l'upload
        const blob = new Blob([attachment.data], { type: attachment.type });
        const file = new File([blob], attachment.filename, { type: attachment.type });
        
        // Uploader la pièce jointe
        const response = await uploadFunction(attachment.feedbackId, file);
        
        // Mettre à jour le statut de la pièce jointe avec la nouvelle fonction
        await updateAttachmentStatus(attachment.id, 'synced', {
          syncedAt: new Date().toISOString(),
          remoteId: response.data?.id, // ID de la pièce jointe sur le serveur
          lastSyncAttempt: new Date().toISOString()
        });
        
        results.push({ success: true, attachment, response });
      } catch (error) {
        console.error(`Erreur lors de la synchronisation de la pièce jointe #${attachment.id}:`, error);
        
        // Marquer comme en erreur avec la nouvelle fonction
        try {
          await updateAttachmentStatus(attachment.id, 'error', {
            error: error.message,
            lastSyncAttempt: new Date().toISOString(),
            retryCount: (attachment.retryCount || 0) + 1
          });
        } catch (markError) {
          console.error('Erreur lors du marquage de la pièce jointe en erreur:', markError);
        }
        
        results.push({ success: false, attachment, error });
      }
    }
    
    return results;
  } catch (error) {
    console.error('Erreur lors de la synchronisation des pièces jointes:', error);
    return [];
  }
};

/**
 * Récupère une pièce jointe par son ID
 * @param {number} attachmentId - ID de la pièce jointe à récupérer
 * @returns {Promise<Object|null>} Pièce jointe ou null si non trouvée
 */
export const getAttachmentById = async (attachmentId) => {
  try {
    const db = await openDatabase();
    const transaction = db.transaction(ATTACHMENTS_STORE, 'readonly');
    const store = transaction.objectStore(ATTACHMENTS_STORE);
    
    return new Promise((resolve, reject) => {
      const request = store.get(attachmentId);
      
      request.onsuccess = () => {
        resolve(request.result || null);
      };
      
      request.onerror = (event) => {
        console.error('Erreur lors de la récupération de la pièce jointe:', event.target.error);
        reject(event.target.error);
      };
    });
  } catch (error) {
    console.error('Erreur lors de la récupération de la pièce jointe:', error);
    return null;
  }
};

/**
 * Met à jour le statut d'une pièce jointe
 * @param {number} attachmentId - ID de la pièce jointe à mettre à jour
 * @param {string} status - Nouveau statut ('pending', 'synced', 'error')
 * @param {Object} additionalData - Données supplémentaires à mettre à jour
 * @returns {Promise<Object>} Pièce jointe mise à jour
 */
export const updateAttachmentStatus = async (attachmentId, status, additionalData = {}) => {
  try {
    const db = await openDatabase();
    const transaction = db.transaction(ATTACHMENTS_STORE, 'readwrite');
    const store = transaction.objectStore(ATTACHMENTS_STORE);
    
    return new Promise((resolve, reject) => {
      const request = store.get(attachmentId);
      
      request.onsuccess = () => {
        const attachment = request.result;
        if (!attachment) {
          reject(new Error(`Pièce jointe non trouvée: ${attachmentId}`));
          return;
        }
        
        const updatedAttachment = {
          ...attachment,
          status,
          ...additionalData,
          updatedAt: new Date().toISOString()
        };
        
        const putRequest = store.put(updatedAttachment);
        
        putRequest.onsuccess = () => {
          console.log(`Statut de la pièce jointe ${attachmentId} mis à jour: ${status}`);
          resolve(updatedAttachment);
        };
        
        putRequest.onerror = (event) => {
          console.error('Erreur lors de la mise à jour du statut de la pièce jointe:', event.target.error);
          reject(event.target.error);
        };
      };
      
      request.onerror = (event) => {
        console.error('Erreur lors de la récupération de la pièce jointe:', event.target.error);
        reject(event.target.error);
      };
    });
  } catch (error) {
    console.error('Erreur lors de la mise à jour du statut de la pièce jointe:', error);
    throw error;
  }
};

/**
 * Supprime une pièce jointe hors-ligne
 * @param {number} attachmentId - ID de la pièce jointe à supprimer
 * @returns {Promise<boolean>} true si la suppression a réussi, false sinon
 */
export const deleteAttachment = async (attachmentId) => {
  try {
    const db = await openDatabase();
    const transaction = db.transaction(ATTACHMENTS_STORE, 'readwrite');
    const store = transaction.objectStore(ATTACHMENTS_STORE);
    
    return new Promise((resolve, reject) => {
      const request = store.delete(attachmentId);
      
      request.onsuccess = () => {
        console.log('Pièce jointe supprimée avec succès:', attachmentId);
        resolve(true);
      };
      
      request.onerror = (event) => {
        console.error('Erreur lors de la suppression de la pièce jointe:', event.target.error);
        reject(event.target.error);
      };
    });
  } catch (error) {
    console.error('Erreur lors de la suppression de la pièce jointe:', error);
    return false;
  }
};
