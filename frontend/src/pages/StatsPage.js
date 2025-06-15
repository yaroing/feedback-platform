import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, Alert } from 'react-bootstrap';
import { Bar, Pie, Line } from 'react-chartjs-2';
import { Chart, registerables } from 'chart.js';
import { feedbackAPI } from '../services/api';
import StatisticsCards from '../components/StatisticsCards';

// Enregistrer les composants Chart.js
Chart.register(...registerables);

const StatsPage = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Charger les statistiques
  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await feedbackAPI.getStats();
        setStats(response.data);
      } catch (err) {
        console.error('Erreur lors du chargement des statistiques:', err);
        setError('Erreur lors du chargement des statistiques. Veuillez réessayer.');
      } finally {
        setLoading(false);
      }
    };
    
    fetchStats();
  }, []);

  // Préparer les données pour le graphique par canal
  const prepareChannelData = () => {
    if (!stats || !stats.by_channel) return null;
    
    const labels = stats.by_channel.map(item => {
      const channelMap = {
        'web': 'Web',
        'sms': 'SMS',
        'whatsapp': 'WhatsApp'
      };
      return channelMap[item.channel] || item.channel;
    });
    
    const data = stats.by_channel.map(item => item.count);
    
    const backgroundColor = [
      'rgba(54, 162, 235, 0.6)', // Web - bleu
      'rgba(75, 192, 192, 0.6)', // SMS - turquoise
      'rgba(40, 167, 69, 0.6)'   // WhatsApp - vert
    ];
    
    return {
      labels,
      datasets: [
        {
          label: 'Nombre de feedbacks',
          data,
          backgroundColor,
          borderColor: backgroundColor.map(color => color.replace('0.6', '1')),
          borderWidth: 1
        }
      ]
    };
  };

  // Préparer les données pour le graphique par catégorie
  const prepareCategoryData = () => {
    if (!stats || !stats.by_category) return null;
    
    const labels = stats.by_category.map(item => item.category__name || 'Non classé');
    const data = stats.by_category.map(item => item.count);
    
    // Générer des couleurs aléatoires pour les catégories
    const backgroundColor = stats.by_category.map(() => {
      const r = Math.floor(Math.random() * 200);
      const g = Math.floor(Math.random() * 200);
      const b = Math.floor(Math.random() * 200);
      return `rgba(${r}, ${g}, ${b}, 0.6)`;
    });
    
    return {
      labels,
      datasets: [
        {
          label: 'Nombre de feedbacks',
          data,
          backgroundColor,
          borderColor: backgroundColor.map(color => color.replace('0.6', '1')),
          borderWidth: 1
        }
      ]
    };
  };

  // Préparer les données pour le graphique par statut
  const prepareStatusData = () => {
    if (!stats || !stats.by_status) return null;
    
    const statusMap = {
      'new': 'Nouveau',
      'in_progress': 'En cours',
      'resolved': 'Résolu',
      'rejected': 'Rejeté'
    };
    
    const labels = stats.by_status.map(item => statusMap[item.status] || item.status);
    const data = stats.by_status.map(item => item.count);
    
    const backgroundColor = [
      'rgba(23, 162, 184, 0.6)', // Nouveau - info
      'rgba(255, 193, 7, 0.6)',  // En cours - warning
      'rgba(40, 167, 69, 0.6)',  // Résolu - success
      'rgba(220, 53, 69, 0.6)'   // Rejeté - danger
    ];
    
    return {
      labels,
      datasets: [
        {
          label: 'Nombre de feedbacks',
          data,
          backgroundColor,
          borderColor: backgroundColor.map(color => color.replace('0.6', '1')),
          borderWidth: 1
        }
      ]
    };
  };

  // Préparer les données pour le graphique par période
  const preparePeriodData = () => {
    if (!stats) return null;
    
    const labels = ['Aujourd\'hui', '7 derniers jours', '30 derniers jours'];
    const data = [stats.today, stats.this_week, stats.this_month];
    
    return {
      labels,
      datasets: [
        {
          label: 'Nombre de feedbacks',
          data,
          backgroundColor: 'rgba(54, 162, 235, 0.6)',
          borderColor: 'rgba(54, 162, 235, 1)',
          borderWidth: 1
        }
      ]
    };
  };

  // Options communes pour les graphiques
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom'
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            const label = context.label || '';
            const value = context.raw || 0;
            const total = context.dataset.data.reduce((a, b) => a + b, 0);
            const percentage = Math.round((value / total) * 100);
            return `${label}: ${value} (${percentage}%)`;
          }
        }
      }
    }
  };

  if (loading) {
    return (
      <Container>
        <div className="text-center py-5">
          <div className="loading-spinner"></div>
          <p className="mt-3">Chargement des statistiques...</p>
        </div>
      </Container>
    );
  }

  if (error) {
    return (
      <Container>
        <Alert variant="danger">{error}</Alert>
      </Container>
    );
  }

  return (
    <Container>
      <h1 className="mb-4">Statistiques des feedbacks</h1>
      
      {/* KPI principaux */}
      <StatisticsCards providedStats={stats} showTitle={false} />
      
      {/* Graphiques */}
      <div className="stats-container">
        {/* Graphique par canal */}
        <Card className="chart-container mb-4">
          <Card.Header>
            <h5 className="mb-0">Répartition par canal</h5>
          </Card.Header>
          <Card.Body>
            <div style={{ height: '300px' }}>
              {prepareChannelData() && (
                <Bar data={prepareChannelData()} options={chartOptions} />
              )}
            </div>
          </Card.Body>
        </Card>
        
        {/* Graphique par catégorie */}
        <Card className="chart-container mb-4">
          <Card.Header>
            <h5 className="mb-0">Répartition par catégorie</h5>
          </Card.Header>
          <Card.Body>
            <div style={{ height: '300px' }}>
              {prepareCategoryData() && (
                <Pie data={prepareCategoryData()} options={chartOptions} />
              )}
            </div>
          </Card.Body>
        </Card>
        
        {/* Graphique par statut */}
        <Card className="chart-container mb-4">
          <Card.Header>
            <h5 className="mb-0">Répartition par statut</h5>
          </Card.Header>
          <Card.Body>
            <div style={{ height: '300px' }}>
              {prepareStatusData() && (
                <Pie data={prepareStatusData()} options={chartOptions} />
              )}
            </div>
          </Card.Body>
        </Card>
        
        {/* Graphique par période */}
        <Card className="chart-container mb-4">
          <Card.Header>
            <h5 className="mb-0">Volume par période</h5>
          </Card.Header>
          <Card.Body>
            <div style={{ height: '300px' }}>
              {preparePeriodData() && (
                <Bar data={preparePeriodData()} options={chartOptions} />
              )}
            </div>
          </Card.Body>
        </Card>
      </div>
    </Container>
  );
};

export default StatsPage;
