import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css';

// Contextes
import { AuthProvider } from './context/AuthContext';
import { OfflineProvider } from './context/OfflineContext';

// Composants
import Header from './components/layout/Header';
import Footer from './components/layout/Footer';
import PrivateRoute from './components/auth/PrivateRoute';
import OfflineStatus from './components/OfflineStatus';

// Pages
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import FeedbackFormPage from './pages/FeedbackFormPage';
import DashboardPage from './pages/DashboardPage';
import FeedbackDetailPage from './pages/FeedbackDetailPage';
import StatsPage from './pages/StatsPage';
import NotFoundPage from './pages/NotFoundPage';

function App() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  useEffect(() => {
    // Gestionnaires d'événements pour la détection de la connectivité
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return (
    <AuthProvider>
      <OfflineProvider>
        <Router>
          <div className="app-container d-flex flex-column min-vh-100">
            <Header />
            <main className="flex-grow-1 container py-4">
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/submit" element={<FeedbackFormPage />} />
                <Route 
                  path="/dashboard" 
                  element={
                    <PrivateRoute>
                      <DashboardPage />
                    </PrivateRoute>
                  } 
                />
                <Route 
                  path="/feedback/:id" 
                  element={
                    <PrivateRoute>
                      <FeedbackDetailPage />
                    </PrivateRoute>
                  } 
                />
                <Route 
                  path="/stats" 
                  element={
                    <PrivateRoute>
                      <StatsPage />
                    </PrivateRoute>
                  } 
                />
                <Route path="/404" element={<NotFoundPage />} />
                <Route path="*" element={<Navigate to="/404" replace />} />
              </Routes>
            </main>
            <Footer />
            <OfflineStatus />
          </div>
        </Router>
      </OfflineProvider>
    </AuthProvider>
  );
}

export default App;
