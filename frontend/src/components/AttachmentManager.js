import React, { useState, useEffect, useCallback } from 'react';
import { attachmentAPI } from '../services/api';
import { isOnline } from '../services/offlineStorage';
import { Button, Spinner, Alert, ListGroup, Badge } from 'react-bootstrap';
import { FiPaperclip, FiUpload, FiTrash2, FiWifi, FiWifiOff, FiCheck, FiAlertTriangle } from 'react-icons/fi';
import './AttachmentManager.css';

/**
 * Composant de gestion des pièces jointes avec support hors ligne
 * @param {Object} props - Propriétés du composant
 * @param {string} props.feedbackId - ID du feedback associé aux pièces jointes
 * @param {boolean} props.readOnly - Mode lecture seule (défaut: false)
 * @param {Function} props.onAttachmentsChange - Callback appelé quand la liste des pièces jointes change
 */
const AttachmentManager = ({ feedbackId, readOnly = false, onAttachmentsChange }) => {
  const [attachments, setAttachments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState(isOnline());

  // Fonction pour formater la taille du fichier
  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    else return (bytes / 1048576).toFixed(1) + ' MB';
  };

  // Surveiller les changements de connexion
  useEffect(() => {
    const handleOnline = () => setConnectionStatus(true);
    const handleOffline = () => setConnectionStatus(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Charger les pièces jointes
  const loadAttachments = useCallback(async () => {
    if (!feedbackId) return;

    setLoading(true);
    setError(null);
    
    try {
      const response = await attachmentAPI.getAll(feedbackId);
      setAttachments(response.data || []);
      
      if (onAttachmentsChange) {
        onAttachmentsChange(response.data || []);
      }
    } catch (err) {
      console.error('Erreur lors du chargement des pièces jointes:', err);
      setError('Impossible de charger les pièces jointes. Veuillez réessayer.');
    } finally {
      setLoading(false);
    }
  }, [feedbackId, onAttachmentsChange]);

  // Charger les pièces jointes au montage du composant
  useEffect(() => {
    loadAttachments();
  }, [loadAttachments]);

  // Synchroniser les pièces jointes en attente lorsque la connexion est rétablie
  useEffect(() => {
    if (connectionStatus) {
      const syncPendingAttachments = async () => {
        try {
          const results = await attachmentAPI.syncPending();
          if (results && results.length > 0) {
            setSuccess(`${results.length} pièce(s) jointe(s) synchronisée(s) avec succès.`);
            // Recharger les pièces jointes après synchronisation
            loadAttachments();
            
            // Effacer le message de succès après 5 secondes
            setTimeout(() => setSuccess(null), 5000);
          }
        } catch (err) {
          console.error('Erreur lors de la synchronisation des pièces jointes:', err);
        }
      };

      syncPendingAttachments();
    }
  }, [connectionStatus, loadAttachments]);

  // Gérer l'upload d'une pièce jointe
  const handleUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setUploading(true);
    setError(null);
    setSuccess(null);

    try {
      // Vérifier la taille du fichier (limite à 10 Mo)
      if (file.size > 10 * 1024 * 1024) {
        throw new Error('La taille du fichier ne doit pas dépasser 10 Mo.');
      }

      const response = await attachmentAPI.upload(feedbackId, file);
      
      // Ajouter la nouvelle pièce jointe à la liste
      setAttachments(prev => [...prev, response.data]);
      
      if (onAttachmentsChange) {
        onAttachmentsChange([...attachments, response.data]);
      }

      setSuccess('Pièce jointe ajoutée avec succès' + (!connectionStatus ? ' (sera synchronisée quand la connexion sera rétablie)' : ''));
      
      // Effacer le message de succès après 5 secondes
      setTimeout(() => setSuccess(null), 5000);
      
      // Réinitialiser le champ de fichier
      event.target.value = null;
    } catch (err) {
      console.error('Erreur lors de l\'upload de la pièce jointe:', err);
      setError(err.message || 'Erreur lors de l\'ajout de la pièce jointe. Veuillez réessayer.');
    } finally {
      setUploading(false);
    }
  };

  // Gérer la suppression d'une pièce jointe
  const handleDelete = async (attachmentId) => {
    if (!window.confirm('Êtes-vous sûr de vouloir supprimer cette pièce jointe ?')) {
      return;
    }

    setError(null);
    setSuccess(null);

    try {
      await attachmentAPI.delete(feedbackId, attachmentId);
      
      // Mettre à jour la liste des pièces jointes
      const updatedAttachments = attachments.filter(a => a.id !== attachmentId);
      setAttachments(updatedAttachments);
      
      if (onAttachmentsChange) {
        onAttachmentsChange(updatedAttachments);
      }

      setSuccess('Pièce jointe supprimée avec succès');
      
      // Effacer le message de succès après 5 secondes
      setTimeout(() => setSuccess(null), 5000);
    } catch (err) {
      console.error('Erreur lors de la suppression de la pièce jointe:', err);
      setError('Erreur lors de la suppression de la pièce jointe. Veuillez réessayer.');
    }
  };

  // Télécharger une pièce jointe
  const handleDownload = (attachment) => {
    // Si la pièce jointe est hors ligne, créer un blob à partir des données
    if (attachment._offline && attachment.data) {
      const blob = new Blob([attachment.data], { type: attachment.type });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = attachment.filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } else if (attachment.url) {
      // Sinon, utiliser l'URL de la pièce jointe
      window.open(attachment.url, '_blank');
    }
  };

  return (
    <div className="attachment-manager">
      <div className="attachment-header">
        <h5>
          <FiPaperclip /> Pièces jointes 
          {connectionStatus ? 
            <Badge bg="success" className="ms-2"><FiWifi /> En ligne</Badge> : 
            <Badge bg="warning" text="dark" className="ms-2"><FiWifiOff /> Hors ligne</Badge>
          }
        </h5>
        
        {!readOnly && (
          <div className="attachment-upload">
            <input
              type="file"
              id="attachment-upload"
              onChange={handleUpload}
              disabled={uploading}
              style={{ display: 'none' }}
            />
            <label htmlFor="attachment-upload" className="btn btn-primary btn-sm">
              {uploading ? (
                <>
                  <Spinner animation="border" size="sm" /> Envoi en cours...
                </>
              ) : (
                <>
                  <FiUpload /> Ajouter une pièce jointe
                </>
              )}
            </label>
          </div>
        )}
      </div>

      {error && (
        <Alert variant="danger" onClose={() => setError(null)} dismissible>
          <FiAlertTriangle /> {error}
        </Alert>
      )}

      {success && (
        <Alert variant="success" onClose={() => setSuccess(null)} dismissible>
          <FiCheck /> {success}
        </Alert>
      )}

      {loading ? (
        <div className="text-center my-3">
          <Spinner animation="border" />
          <p>Chargement des pièces jointes...</p>
        </div>
      ) : attachments.length === 0 ? (
        <p className="text-muted">Aucune pièce jointe</p>
      ) : (
        <ListGroup className="attachment-list">
          {attachments.map(attachment => (
            <ListGroup.Item key={attachment.id} className="d-flex justify-content-between align-items-center">
              <div className="attachment-info" onClick={() => handleDownload(attachment)} style={{ cursor: 'pointer' }}>
                <div className="attachment-name">{attachment.filename}</div>
                <div className="attachment-meta">
                  {formatFileSize(attachment.size || 0)}
                  {attachment._pendingSync && (
                    <Badge bg="warning" text="dark" className="ms-2">
                      <FiWifiOff /> En attente de synchronisation
                    </Badge>
                  )}
                  {attachment._offline && !attachment._pendingSync && (
                    <Badge bg="info" className="ms-2">
                      <FiWifiOff /> Hors ligne
                    </Badge>
                  )}
                </div>
              </div>
              
              {!readOnly && (
                <Button 
                  variant="danger" 
                  size="sm" 
                  onClick={() => handleDelete(attachment.id)}
                  disabled={uploading}
                >
                  <FiTrash2 />
                </Button>
              )}
            </ListGroup.Item>
          ))}
        </ListGroup>
      )}
    </div>
  );
};

export default AttachmentManager;
