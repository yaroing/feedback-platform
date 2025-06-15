import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, Table, Badge, Form, Button, Pagination, Alert } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { feedbackAPI, categoryAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import StatisticsCards from '../components/StatisticsCards';

const DashboardPage = () => {
  const [feedbacks, setFeedbacks] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    status: '',
    category: '',
    channel: '',
    priority: ''
  });
  const [pagination, setPagination] = useState({
    page: 1,
    pageSize: 10,
    count: 0
  });
  
  const { isModerator } = useAuth();
  const isUserModerator = isModerator();

  // Charger les feedbacks et les catégories au chargement de la page
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Construire les paramètres de requête
        const params = {
          page: pagination.page,
          ...Object.fromEntries(
            Object.entries(filters).filter(([_, value]) => value !== '')
          )
        };
        
        // Récupérer les feedbacks
        const feedbackResponse = await feedbackAPI.getAll(params);
        setFeedbacks(feedbackResponse.data.results);
        setPagination(prev => ({
          ...prev,
          count: feedbackResponse.data.count
        }));
        
        // Récupérer les catégories
        const categoryResponse = await categoryAPI.getAll();
        
        // Vérifier si les données sont paginées ou non
        if (categoryResponse.data && categoryResponse.data.results) {
          // Format paginé
          setCategories(categoryResponse.data.results);
          console.log('Catégories chargées (format paginé):', categoryResponse.data.results);
        } else if (Array.isArray(categoryResponse.data)) {
          // Format tableau
          setCategories(categoryResponse.data);
          console.log('Catégories chargées (format tableau):', categoryResponse.data);
        } else {
          // Format inconnu
          console.error('Format de réponse catégories inconnu:', categoryResponse.data);
          setCategories([]);
        }
      } catch (err) {
        console.error('Erreur lors du chargement des données:', err);
        setError('Erreur lors du chargement des données. Veuillez réessayer.');
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [filters, pagination.page]);

  // Gérer le changement de filtre
  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    
    // Traitement spécial pour la catégorie (convertir en nombre si nécessaire)
    let processedValue = value;
    if (name === 'category' && value !== '') {
      processedValue = parseInt(value, 10);
      // Si la conversion échoue, utiliser la valeur d'origine
      if (isNaN(processedValue)) {
        processedValue = value;
      }
    }
    
    setFilters(prev => ({
      ...prev,
      [name]: processedValue
    }));
    
    // Réinitialiser la pagination lors du changement de filtre
    setPagination(prev => ({
      ...prev,
      page: 1
    }));
  };

  // Gérer le changement de page
  const handlePageChange = (page) => {
    setPagination(prev => ({
      ...prev,
      page
    }));
  };

  // Rendu des badges de statut
  const renderStatusBadge = (status) => {
    const statusMap = {
      'new': { variant: 'info', label: 'Nouveau' },
      'in_progress': { variant: 'warning', label: 'En cours' },
      'resolved': { variant: 'success', label: 'Résolu' },
      'rejected': { variant: 'danger', label: 'Rejeté' }
    };
    
    const { variant, label } = statusMap[status] || { variant: 'secondary', label: status };
    
    return (
      <Badge bg={variant} className="status-badge">
        {label}
      </Badge>
    );
  };

  // Rendu des badges de canal
  const renderChannelBadge = (channel) => {
    const channelMap = {
      'web': { variant: 'primary', label: 'Web' },
      'sms': { variant: 'success', label: 'SMS' },
      'whatsapp': { variant: 'success', label: 'WhatsApp' }
    };
    
    const { variant, label } = channelMap[channel] || { variant: 'secondary', label: channel };
    
    return (
      <Badge bg={variant} className={`channel-badge channel-${channel}`}>
        {label}
      </Badge>
    );
  };

  // Rendu des badges de priorité
  const renderPriorityBadge = (priority) => {
    const priorityMap = {
      'low': { variant: 'success', label: 'Basse' },
      'medium': { variant: 'info', label: 'Moyenne' },
      'high': { variant: 'warning', label: 'Haute' },
      'urgent': { variant: 'danger', label: 'Urgente' }
    };
    
    const { variant, label } = priorityMap[priority] || { variant: 'secondary', label: priority };
    
    return (
      <Badge bg={variant} className="priority-badge">
        {label}
      </Badge>
    );
  };

  // Générer la pagination
  const renderPagination = () => {
    const totalPages = Math.ceil(pagination.count / pagination.pageSize);
    const items = [];
    
    // Bouton précédent
    items.push(
      <Pagination.Prev 
        key="prev"
        disabled={pagination.page === 1}
        onClick={() => handlePageChange(pagination.page - 1)}
      />
    );
    
    // Pages
    for (let page = 1; page <= totalPages; page++) {
      if (
        page === 1 || 
        page === totalPages || 
        (page >= pagination.page - 1 && page <= pagination.page + 1)
      ) {
        items.push(
          <Pagination.Item
            key={page}
            active={page === pagination.page}
            onClick={() => handlePageChange(page)}
          >
            {page}
          </Pagination.Item>
        );
      } else if (
        (page === pagination.page - 2 && pagination.page > 3) ||
        (page === pagination.page + 2 && pagination.page < totalPages - 2)
      ) {
        items.push(<Pagination.Ellipsis key={`ellipsis-${page}`} />);
      }
    }
    
    // Bouton suivant
    items.push(
      <Pagination.Next
        key="next"
        disabled={pagination.page === totalPages}
        onClick={() => handlePageChange(pagination.page + 1)}
      />
    );
    
    return <Pagination>{items}</Pagination>;
  };

  return (
    <Container fluid>
      <h1 className="mb-4">Tableau de bord</h1>
      
      {/* Statistiques */}
      <StatisticsCards />
      
      {/* Filtres */}
      <Card className="mb-4 dashboard-filters">
        <Card.Body>
          <Row>
            <Col md={3} className="mb-3 mb-md-0">
              <Form.Group>
                <Form.Label>Statut</Form.Label>
                <Form.Select
                  name="status"
                  value={filters.status}
                  onChange={handleFilterChange}
                >
                  <option value="">Tous les statuts</option>
                  <option value="new">Nouveau</option>
                  <option value="in_progress">En cours</option>
                  <option value="resolved">Résolu</option>
                  <option value="rejected">Rejeté</option>
                </Form.Select>
              </Form.Group>
            </Col>
            <Col md={3} className="mb-3 mb-md-0">
              <Form.Group>
                <Form.Label>Catégorie</Form.Label>
                <Form.Select
                  name="category"
                  value={filters.category}
                  onChange={handleFilterChange}
                >
                  <option value="">Toutes les catégories</option>
                  {Array.isArray(categories) && categories.map(category => (
                    <option key={category.id} value={category.id}>
                      {category.name}
                    </option>
                  ))}
                </Form.Select>
              </Form.Group>
            </Col>
            <Col md={3} className="mb-3 mb-md-0">
              <Form.Group>
                <Form.Label>Canal</Form.Label>
                <Form.Select
                  name="channel"
                  value={filters.channel}
                  onChange={handleFilterChange}
                >
                  <option value="">Tous les canaux</option>
                  <option value="web">Web</option>
                  <option value="sms">SMS</option>
                  <option value="whatsapp">WhatsApp</option>
                </Form.Select>
              </Form.Group>
            </Col>
            <Col md={3}>
              <Form.Group>
                <Form.Label>Priorité</Form.Label>
                <Form.Select
                  name="priority"
                  value={filters.priority}
                  onChange={handleFilterChange}
                >
                  <option value="">Toutes les priorités</option>
                  <option value="low">Basse</option>
                  <option value="medium">Moyenne</option>
                  <option value="high">Haute</option>
                  <option value="urgent">Urgente</option>
                </Form.Select>
              </Form.Group>
            </Col>
          </Row>
        </Card.Body>
      </Card>
      
      {/* Tableau des feedbacks */}
      <Card>
        <Card.Body>
          {loading ? (
            <div className="text-center py-5">
              <div className="loading-spinner"></div>
              <p className="mt-3">Chargement des feedbacks...</p>
            </div>
          ) : error ? (
            <Alert variant="danger">{error}</Alert>
          ) : feedbacks.length === 0 ? (
            <div className="text-center py-5">
              <p className="mb-3">Aucun feedback trouvé avec les filtres actuels.</p>
              <Button 
                variant="outline-primary"
                onClick={() => setFilters({
                  status: '',
                  category: '',
                  channel: '',
                  priority: ''
                })}
              >
                Réinitialiser les filtres
              </Button>
            </div>
          ) : (
            <>
              <Table responsive hover>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Canal</th>
                    <th>Contenu</th>
                    <th>Catégorie</th>
                    <th>Priorité</th>
                    <th>Statut</th>
                    <th>Date</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {feedbacks.map(feedback => (
                    <tr 
                      key={feedback.id} 
                      className={`priority-${feedback.priority}`}
                    >
                      <td>{feedback.id}</td>
                      <td>{renderChannelBadge(feedback.channel)}</td>
                      <td>
                        <div className="text-truncate" style={{ maxWidth: '250px' }}>
                          {feedback.content}
                        </div>
                      </td>
                      <td>{feedback.category_name || '-'}</td>
                      <td>{renderPriorityBadge(feedback.priority)}</td>
                      <td>{renderStatusBadge(feedback.status)}</td>
                      <td>{new Date(feedback.created_at).toLocaleDateString()}</td>
                      <td>
                        <Button
                          as={Link}
                          to={`/feedback/${feedback.id}`}
                          variant="outline-primary"
                          size="sm"
                        >
                          {isUserModerator ? 'Traiter' : 'Voir'}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
              
              {/* Pagination */}
              <div className="d-flex justify-content-center mt-4">
                {renderPagination()}
              </div>
            </>
          )}
        </Card.Body>
      </Card>
    </Container>
  );
};

export default DashboardPage;
