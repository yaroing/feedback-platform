import React from 'react';
import { Alert } from 'react-bootstrap';
import { useOffline } from '../../context/OfflineContext';

const OfflineIndicator = () => {
  const { syncPending } = useOffline();
  
  return (
    <div className="offline-indicator">
      <Alert variant="warning" className="mb-0 d-flex align-items-center">
        <span className="me-2">📶</span>
        <div>
          <strong>Mode hors ligne</strong>
          <div className="small">
            {syncPending 
              ? 'Des feedbacks sont en attente de synchronisation.' 
              : 'Vos actions seront synchronisées lorsque vous serez de nouveau en ligne.'}
          </div>
        </div>
      </Alert>
    </div>
  );
};

export default OfflineIndicator;
