import React, { createContext, useState, useEffect, useContext } from 'react';
import { isOnline as checkIsOnline, getOfflineFeedbacks, addConnectivityListeners, removeConnectivityListeners } from '../services/offlineStorage';
import { feedbackAPI } from '../services/api';

const OfflineContext = createContext();

export const useOffline = () => useContext(OfflineContext);

export const OfflineProvider = ({ children }) => {
  const [isOnline, setIsOnline] = useState(checkIsOnline());
  const [offlineFeedbacks, setOfflineFeedbacks] = useState([]);
  const [syncPending, setSyncPending] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSyncResult, setLastSyncResult] = useState(null);

  // Charger les feedbacks hors ligne depuis IndexedDB au démarrage
  useEffect(() => {
    loadOfflineFeedbacks();
    
    // Gérer les changements de connectivité
    const handleOnlineChange = () => {
      const online = checkIsOnline();
      setIsOnline(online);
      if (online && syncPending) {
        // Tenter une synchronisation automatique quand on revient en ligne
        syncOfflineFeedbacks();
      }
    };
    
    // Ajouter les écouteurs d'événements pour la connectivité
    addConnectivityListeners(handleOnlineChange, handleOnlineChange);
    
    return () => {
      // Nettoyer les écouteurs d'événements
      removeConnectivityListeners(handleOnlineChange, handleOnlineChange);
    };
  }, [syncPending]);

  // Fonction pour charger les feedbacks stockés localement
  const loadOfflineFeedbacks = async () => {
    try {
      const feedbacks = await getOfflineFeedbacks();
      setOfflineFeedbacks(feedbacks);
      setSyncPending(feedbacks.length > 0);
    } catch (error) {
      console.error('Erreur lors du chargement des feedbacks hors ligne:', error);
    }
  };

  // Fonction pour synchroniser les feedbacks hors ligne lorsque la connexion est rétablie
  const syncOfflineFeedbacks = async () => {
    if (!isOnline || isSyncing) return;
    
    setIsSyncing(true);
    setLastSyncResult(null);
    
    try {
      // Utiliser la fonction de synchronisation de l'API
      const result = await feedbackAPI.syncOfflineFeedbacks();
      
      // Mettre à jour l'état avec le résultat de la synchronisation
      setLastSyncResult(result);
      
      // Recharger les feedbacks restants
      await loadOfflineFeedbacks();
      
      return result;
    } catch (error) {
      console.error('Erreur lors de la synchronisation des feedbacks:', error);
      setLastSyncResult({
        success: false,
        message: error.message || 'Erreur lors de la synchronisation'
      });
    } finally {
      setIsSyncing(false);
    }
  };

  // Fonction pour vérifier si un feedback est en mode hors-ligne
  const isOfflineFeedback = (feedbackId) => {
    return typeof feedbackId === 'string' && feedbackId.startsWith('offline-');
  };

  const value = {
    isOnline,
    offlineFeedbacks,
    syncPending,
    isSyncing,
    lastSyncResult,
    syncOfflineFeedbacks,
    isOfflineFeedback,
    loadOfflineFeedbacks
  };

  return (
    <OfflineContext.Provider value={value}>
      {children}
    </OfflineContext.Provider>
  );
};

export default OfflineContext;
