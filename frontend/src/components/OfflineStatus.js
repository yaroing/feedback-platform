import React, { useState, useEffect } from 'react';
import { Alert, Button, Badge } from 'react-bootstrap';
import { isOnline, getOfflineFeedbacks, addConnectivityListeners, removeConnectivityListeners } from '../services/offlineStorage';
import { feedbackAPI } from '../services/api';

/**
 * Composant affichant l'état de la connexion et permettant de synchroniser les données hors-ligne
 */
const OfflineStatus = () => {
  const [online, setOnline] = useState(isOnline());
  const [offlineFeedbackCount, setOfflineFeedbackCount] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState(null);

  // Vérifier le nombre de feedbacks hors-ligne
  const checkOfflineFeedbacks = async () => {
    try {
      const feedbacks = await getOfflineFeedbacks();
      setOfflineFeedbackCount(feedbacks.length);
    } catch (error) {
      console.error('Erreur lors de la vérification des feedbacks hors-ligne:', error);
    }
  };

  // Gérer le changement d'état de la connexion
  const handleOnlineStatusChange = () => {
    const isCurrentlyOnline = isOnline();
    setOnline(isCurrentlyOnline);
    
    if (isCurrentlyOnline) {
      checkOfflineFeedbacks();
    }
  };

  // Synchroniser les feedbacks hors-ligne
  const handleSync = async () => {
    if (!online) {
      alert('Impossible de synchroniser en mode hors-ligne. Veuillez vous connecter à Internet.');
      return;
    }

    setSyncing(true);
    setSyncResult(null);

    try {
      const result = await feedbackAPI.syncOfflineFeedbacks();
      setSyncResult(result);
      checkOfflineFeedbacks();
    } catch (error) {
      console.error('Erreur lors de la synchronisation:', error);
      setSyncResult({
        success: false,
        message: error.message || 'Erreur lors de la synchronisation'
      });
    } finally {
      setSyncing(false);
    }
  };

  // Effet pour initialiser les écouteurs d'événements et vérifier les feedbacks hors-ligne
  useEffect(() => {
    // Vérifier les feedbacks hors-ligne au chargement
    checkOfflineFeedbacks();

    // Ajouter les écouteurs d'événements pour la connectivité
    addConnectivityListeners(handleOnlineStatusChange, handleOnlineStatusChange);

    // Nettoyer les écouteurs d'événements lors du démontage
    return () => {
      removeConnectivityListeners(handleOnlineStatusChange, handleOnlineStatusChange);
    };
  }, []);

  // Si aucun feedback hors-ligne et en ligne, ne rien afficher
  if (online && offlineFeedbackCount === 0 && !syncResult) {
    return null;
  }

  return (
    <div className="offline-status-container" style={{ position: 'fixed', bottom: '20px', right: '20px', zIndex: 1050 }}>
      {!online && (
        <Alert variant="warning" className="mb-2">
          <i className="bi bi-wifi-off me-2"></i>
          Mode hors-ligne
        </Alert>
      )}

      {offlineFeedbackCount > 0 && (
        <Alert variant={online ? "info" : "secondary"} className="d-flex align-items-center justify-content-between">
          <div>
            <Badge bg="primary" className="me-2">{offlineFeedbackCount}</Badge>
            feedback{offlineFeedbackCount > 1 ? 's' : ''} en attente de synchronisation
          </div>
          <Button 
            variant="outline-primary" 
            size="sm" 
            onClick={handleSync} 
            disabled={!online || syncing}
          >
            {syncing ? 'Synchronisation...' : 'Synchroniser'}
          </Button>
        </Alert>
      )}

      {syncResult && (
        <Alert 
          variant={syncResult.success ? "success" : "danger"} 
          dismissible 
          onClose={() => setSyncResult(null)}
          className="mt-2"
        >
          {syncResult.success ? (
            <>
              <i className="bi bi-check-circle me-2"></i>
              {syncResult.syncedCount} feedback{syncResult.syncedCount > 1 ? 's' : ''} synchronisé{syncResult.syncedCount > 1 ? 's' : ''}
              {syncResult.failedCount > 0 && `, ${syncResult.failedCount} échec${syncResult.failedCount > 1 ? 's' : ''}`}
            </>
          ) : (
            <>
              <i className="bi bi-exclamation-triangle me-2"></i>
              {syncResult.message || 'Erreur lors de la synchronisation'}
            </>
          )}
        </Alert>
      )}
    </div>
  );
};

export default OfflineStatus;
