import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

const PrivateRoute = ({ children, requiredRole }) => {
  const { currentUser, loading, isModerator } = useAuth();
  const location = useLocation();

  if (loading) {
    // Afficher un indicateur de chargement pendant la vérification de l'authentification
    return (
      <div className="d-flex justify-content-center align-items-center" style={{ height: '50vh' }}>
        <div className="loading-spinner"></div>
      </div>
    );
  }

  // Si l'utilisateur n'est pas connecté, rediriger vers la page de connexion
  if (!currentUser) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Si un rôle spécifique est requis, vérifier si l'utilisateur a ce rôle
  if (requiredRole === 'moderator' && !isModerator()) {
    return <Navigate to="/unauthorized" replace />;
  }

  // L'utilisateur est authentifié et a les autorisations nécessaires
  return children;
};

export default PrivateRoute;
