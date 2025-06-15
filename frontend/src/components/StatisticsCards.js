import React, { useState, useEffect } from 'react';
import { Row, Col } from 'react-bootstrap';
import { feedbackAPI } from '../services/api';
import StatisticsCard from './StatisticsCard';
import '../styles/statistics.css';

const StatisticsCards = ({ providedStats = null, showTitle = true }) => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (providedStats) {
      setStats(providedStats);
      setLoading(false);
      return;
    }

    const fetchStats = async () => {
      try {
        setLoading(true);
        const response = await feedbackAPI.getStats();
        console.log('Statistiques reçues:', response.data);
        setStats(response.data);
      } catch (err) {
        console.error('Erreur lors du chargement des statistiques:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, [providedStats]);

  if (loading || !stats) {
    return (
      <div className="statistics-section mb-4">
        {showTitle && <h2 className="mb-3">Statistiques des feedbacks</h2>}
        <div className="text-center py-3">
          <p>Chargement des statistiques...</p>
        </div>
      </div>
    );
  }

  // Récupérer le nombre de feedbacks résolus
  const getResolvedCount = () => {
    if (!stats.by_status || !Array.isArray(stats.by_status)) {
      return 0;
    }
    const resolvedItem = stats.by_status.find(item => item.status === 'resolved');
    return resolvedItem ? resolvedItem.count : 0;
  };

  // Formater le temps moyen de résolution
  const formatResolutionTime = () => {
    if (stats.avg_resolution_time_hours === null || stats.avg_resolution_time_hours === undefined) {
      return 'N/A';
    }
    return Math.round(stats.avg_resolution_time_hours) + 'h';
  };

  return (
    <div className="statistics-section mb-4">
      {showTitle && <h2 className="mb-3">Statistiques des feedbacks</h2>}
      <Row>
        <Col md={3} sm={6} className="mb-3">
          <StatisticsCard 
            value={stats.total || 0} 
            label="Total des feedbacks" 
          />
        </Col>
        <Col md={3} sm={6} className="mb-3">
          <StatisticsCard 
            value={stats.today || 0} 
            label="Aujourd'hui" 
          />
        </Col>
        <Col md={3} sm={6} className="mb-3">
          <StatisticsCard 
            value={getResolvedCount()} 
            label="Feedbacks résolus" 
          />
        </Col>
        <Col md={3} sm={6} className="mb-3">
          <StatisticsCard 
            value={formatResolutionTime()} 
            label="Temps moyen de résolution" 
          />
        </Col>
      </Row>
    </div>
  );
};

export default StatisticsCards;
