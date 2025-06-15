import React, { createContext, useState, useEffect, useContext } from 'react';
import jwt_decode from 'jwt-decode';
import api from '../services/api';

const AuthContext = createContext();

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
  const [currentUser, setCurrentUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Vérifier si le token est valide et le décode
  useEffect(() => {
    const initAuth = async () => {
      if (token) {
        try {
          // Vérifier si le token est expiré
          const decodedToken = jwt_decode(token);
          const currentTime = Date.now() / 1000;

          if (decodedToken.exp < currentTime) {
            // Token expiré
            logout();
          } else {
            // Token valide, configurer l'en-tête d'autorisation
            api.defaults.headers.common['Authorization'] = `Bearer ${token}`;

            // Récupérer les informations de l'utilisateur
            const response = await api.get('/api/auth/user/');
            setCurrentUser(response.data);
          }
        } catch (err) {
          console.error('Erreur lors de l\'initialisation de l\'authentification:', err);
          logout();
        }
      }
      setLoading(false);
    };

    initAuth();
  }, [token]);

  // Fonction de connexion
  const login = async (username, password) => {
    try {
      setError(null);
      const response = await api.post('/api/auth/login/', { username, password });
      const { access, refresh } = response.data;

      // Stocker le token dans le localStorage
      localStorage.setItem('token', access);
      localStorage.setItem('refreshToken', refresh);

      // Mettre à jour le state
      setToken(access);

      return true;
    } catch (err) {
      console.error('Erreur de connexion:', err);
      setError(err.response?.data?.detail || 'Erreur de connexion');
      return false;
    }
  };

  // Fonction de déconnexion
  const logout = () => {
    // Supprimer les tokens du localStorage
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');

    // Réinitialiser le state
    setToken(null);
    setCurrentUser(null);

    // Supprimer l'en-tête d'autorisation
    delete api.defaults.headers.common['Authorization'];
  };

  // Fonction pour rafraîchir le token
  const refreshToken = async () => {
    try {
      const refreshToken = localStorage.getItem('refreshToken');
      if (!refreshToken) {
        throw new Error('Pas de token de rafraîchissement disponible');
      }

      const response = await api.post('/api/auth/refresh/', { refresh: refreshToken });
      const { access } = response.data;

      // Mettre à jour le token
      localStorage.setItem('token', access);
      setToken(access);

      return access;
    } catch (err) {
      console.error('Erreur lors du rafraîchissement du token:', err);
      logout();
      return null;
    }
  };

  // Vérifier si l'utilisateur est modérateur
  const isModerator = () => {
    return currentUser && currentUser.groups && currentUser.groups.includes('Moderators');
  };

  const value = {
    currentUser,
    token,
    loading,
    error,
    login,
    logout,
    refreshToken,
    isModerator
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
