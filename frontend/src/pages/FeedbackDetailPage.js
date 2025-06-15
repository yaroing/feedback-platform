import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, Form, Button, Alert, Badge, ListGroup } from 'react-bootstrap';
import { useParams, useNavigate } from 'react-router-dom';
import { Formik } from 'formik';
import * as Yup from 'yup';
import { feedbackAPI, categoryAPI, attachmentAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import AttachmentManager from '../components/AttachmentManager';
import { isOnline } from '../services/offlineStorage';

// Schéma de validation pour le formulaire de réponse
const ResponseSchema = Yup.object().shape({
  content: Yup.string()
    .required('Le contenu de la réponse est requis')
    .min(10, 'La réponse doit contenir au moins 10 caractères')
});

// Schéma de validation pour le formulaire de mise à jour
const UpdateSchema = Yup.object().shape({
  status: Yup.string().required('Le statut est requis'),
  category: Yup.string(),
  priority: Yup.string().required('La priorité est requise')
});

const FeedbackDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { isModerator } = useAuth();
  
  const [feedback, setFeedback] = useState(null);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [updateStatus, setUpdateStatus] = useState({ type: '', message: '' });
  const [responseStatus, setResponseStatus] = useState({ type: '', message: '' });
  
  const isUserModerator = isModerator();

  // Charger les données du feedback et les catégories
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Récupérer le feedback
        let feedbackResponse;
        try {
          feedbackResponse = await feedbackAPI.getById(id);
        } catch (err) {
          // Essayer avec l'ancienne route si la nouvelle échoue
          console.log('Tentative avec l\'ancienne route API...');
          feedbackResponse = await feedbackAPI.getByIdLegacy(id);
        }
        setFeedback(feedbackResponse.data);
        
        // Récupérer les catégories avec la nouvelle méthode getAllFlat
        try {
          console.log('Récupération des catégories avec getAllFlat...');
          // Cette fonction retourne directement le tableau de catégories
          const categoriesData = await categoryAPI.getAllFlat();
          console.log('Catégories reçues:', categoriesData);
          
          if (Array.isArray(categoriesData) && categoriesData.length > 0) {
            console.log(`${categoriesData.length} catégories récupérées avec succès`);
            setCategories(categoriesData);
          } else {
            console.warn('Aucune catégorie reçue ou format invalide');
            setCategories([]);
          }
        } catch (catErr) {
          console.error('Erreur lors de la récupération des catégories:', catErr);
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
  }, [id]);

  // Gérer la mise à jour du feedback
  const handleUpdate = async (values, { setSubmitting }) => {
    try {
      setUpdateStatus({ type: '', message: '' });
      
      // Préparer les données pour la mise à jour
      // Utiliser uniquement les champs nécessaires pour éviter les erreurs de validation
      const updateData = {};
      
      // Ajouter le statut s'il est défini
      if (values.status) {
        updateData.status = values.status;
      }
      
      // Ajouter la priorité si elle est définie
      if (values.priority) {
        updateData.priority = values.priority;
      }
      
      // Ajouter la catégorie uniquement si elle est sélectionnée
      if (values.category && values.category !== '') {
        updateData.category = parseInt(values.category, 10);
        console.log('Catégorie sélectionnée pour mise à jour:', updateData.category);
      } else {
        // Envoyer explicitement null pour supprimer la catégorie
        updateData.category = null;
        console.log('Catégorie non sélectionnée, envoi de null');
      }
      
      console.log('Données de mise à jour:', updateData);
      
      // Essayer d'abord avec l'API principale
      try {
        const response = await feedbackAPI.update(id, updateData);
        console.log('Réponse de mise à jour:', response.data);
        
        // Mise à jour réussie
        setUpdateStatus({
          type: 'success',
          message: 'Le feedback a été mis à jour avec succès.'
        });
        
        // Recharger les données pour s'assurer que tout est à jour
        const refreshedFeedback = await feedbackAPI.getById(id);
        setFeedback(refreshedFeedback.data);
      } catch (mainApiError) {
        console.error('Erreur avec l\'API principale:', mainApiError);
        
        // Essayer avec l'API alternative
        try {
          console.log('Tentative avec l\'API alternative...');
          // Utiliser l'ancienne route API comme fallback
          const alternativeResponse = await feedbackAPI.update(id, updateData);
          console.log('Réponse alternative:', alternativeResponse.data);
          
          // Mise à jour réussie avec l'API alternative
          setUpdateStatus({
            type: 'success',
            message: 'Le feedback a été mis à jour avec succès.'
          });
          
          // Recharger les données
          const refreshedFeedback = await feedbackAPI.getByIdLegacy(id);
          setFeedback(refreshedFeedback.data);
        } catch (alternativeError) {
          console.error('Détails de l\'erreur alternative:', alternativeError.response?.data);
          throw alternativeError;
        }
      }
      
    } catch (err) {
      console.error('Erreur lors de la mise à jour du feedback:', err);
      setUpdateStatus({
        type: 'danger',
        message: 'Erreur lors de la mise à jour du feedback. Veuillez réessayer.'
      });
    } finally {
      setSubmitting(false);
    }
  };

  // Gérer l'envoi d'une réponse
  const handleRespond = async (values, { setSubmitting, resetForm }) => {
    try {
      setResponseStatus({ type: '', message: '' });
      
      // Nettoyage du contenu pour supprimer tout texte indésirable
      let cleanContent = values.content || '';
      
      // Supprimer le texte dupliqué s'il est présent
      if (cleanContent.includes('Sélectionnez le canal par lequel vous souhaitez simuler')) {
        cleanContent = cleanContent.replace('Sélectionnez le canal par lequel vous souhaitez simuler l\'envoi du feedback', '');
        cleanContent = cleanContent.replace('Sélectionnez le canal par lequel vous souhaitez simuler l\'envoi du feedback Sélectionnez le canal par lequel vous souhaitez simuler l\'envoi du feedback', '');
      }
      
      // Nettoyer les espaces inutiles
      cleanContent = cleanContent.trim();
      
      console.log('Début de l\'envoi de la réponse avec contenu nettoyé:', cleanContent);
      
      // Validation du contenu nettoyé
      if (!cleanContent) {
        setResponseStatus({
          type: 'danger',
          message: 'Le contenu de la réponse ne peut pas être vide'
        });
        return;
      }
      
      // Envoyer la réponse avec le contenu nettoyé
      const response = await feedbackAPI.respond(id, cleanContent);
      console.log('Réponse reçue du serveur:', response);
      
      // Mettre à jour l'état local
      if (response && response.data) {
        setFeedback(prev => ({
          ...prev,
          responses: [...(prev.responses || []), response.data]
        }));
        
        setResponseStatus({
          type: 'success',
          message: 'Votre réponse a été envoyée avec succès.'
        });
        
        resetForm();
      } else {
        throw new Error('Format de réponse invalide');
      }
    } catch (err) {
      console.error('Erreur lors de l\'envoi de la réponse:', err);
      console.error('Détails de l\'erreur:', err.response?.data || err.message);
      
      // Extraction des messages d'erreur du backend
      let errorMessage = 'Erreur lors de l\'envoi de la réponse. Veuillez réessayer.';
      
      if (err.response) {
        // Erreur de l'API avec réponse
        if (err.response.status === 400) {
          // Erreur de validation
          const responseData = err.response.data;
          if (responseData.content) {
            errorMessage = `Erreur de validation: ${responseData.content}`;
          } else if (responseData.detail) {
            errorMessage = responseData.detail;
          } else if (typeof responseData === 'string') {
            errorMessage = responseData;
          }
        }
      } else if (err.message) {
        // Erreur JavaScript standard
        errorMessage = err.message;
      }
      
      setResponseStatus({
        type: 'danger',
        message: errorMessage
      });
    } finally {
      setSubmitting(false);
    }
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

  if (loading) {
    return (
      <Container>
        <div className="text-center py-5">
          <div className="loading-spinner"></div>
          <p className="mt-3">Chargement du feedback...</p>
        </div>
      </Container>
    );
  }

  if (error) {
    return (
      <Container>
        <Alert variant="danger">
          {error}
          <div className="mt-3">
            <Button variant="primary" onClick={() => navigate('/dashboard')}>
              Retour au tableau de bord
            </Button>
          </div>
        </Alert>
      </Container>
    );
  }

  if (!feedback) {
    return (
      <Container>
        <Alert variant="warning">
          Feedback non trouvé.
          <div className="mt-3">
            <Button variant="primary" onClick={() => navigate('/dashboard')}>
              Retour au tableau de bord
            </Button>
          </div>
        </Alert>
      </Container>
    );
  }

  return (
    <Container>
      <div className="mb-4">
        <Button variant="outline-secondary" onClick={() => navigate('/dashboard')}>
          &larr; Retour au tableau de bord
        </Button>
      </div>
      
      <Card className="feedback-detail mb-4">
        <Card.Body>
          <h1 className="mb-4">Feedback #{feedback.id}</h1>
          
          <div className="feedback-meta">
            <div>
              <strong>Canal:</strong> {renderChannelBadge(feedback.channel)}
            </div>
            <div>
              <strong>Statut:</strong> {renderStatusBadge(feedback.status)}
            </div>
            <div>
              <strong>Priorité:</strong> {renderPriorityBadge(feedback.priority)}
            </div>
            <div>
              <strong>Catégorie:</strong> {feedback.category_name || 'Non classé'}
            </div>
            <div>
              <strong>Date:</strong> {new Date(feedback.created_at).toLocaleString()}
            </div>
            {feedback.contact_email && (
              <div>
                <strong>Email:</strong> {feedback.contact_email}
              </div>
            )}
            {feedback.contact_phone && (
              <div>
                <strong>Téléphone:</strong> {feedback.contact_phone}
              </div>
            )}
          </div>
          
          <h5>Contenu</h5>
          <div className="feedback-content">
            {feedback.content}
          </div>
          
          {/* Formulaire de mise à jour (modérateurs uniquement) */}
          {isUserModerator && (
            <div className="mt-4">
              <h5>Traiter ce feedback</h5>
              
              {updateStatus.message && (
                <Alert 
                  variant={updateStatus.type} 
                  onClose={() => setUpdateStatus({ type: '', message: '' })} 
                  dismissible
                >
                  {updateStatus.message}
                </Alert>
              )}
              
              <Formik
                initialValues={{
                  status: feedback.status || 'new',
                  category: feedback.category ? feedback.category.toString() : '',
                  priority: feedback.priority || 'medium'
                }}
                validationSchema={UpdateSchema}
                onSubmit={handleUpdate}
              >
                {({
                  values,
                  errors,
                  touched,
                  handleChange,
                  handleBlur,
                  handleSubmit,
                  isSubmitting
                }) => (
                  <Form onSubmit={handleSubmit}>
                    <Row>
                      <Col md={4}>
                        <Form.Group className="mb-3">
                          <Form.Label>Statut</Form.Label>
                          <Form.Select
                            name="status"
                            value={values.status}
                            onChange={handleChange}
                            onBlur={handleBlur}
                            isInvalid={touched.status && errors.status}
                          >
                            <option value="new">Nouveau</option>
                            <option value="in_progress">En cours</option>
                            <option value="resolved">Résolu</option>
                            <option value="rejected">Rejeté</option>
                          </Form.Select>
                          <Form.Control.Feedback type="invalid">
                            {errors.status}
                          </Form.Control.Feedback>
                        </Form.Group>
                      </Col>
                      <Col md={4}>
                        <Form.Group className="mb-3">
                          <Form.Label>Catégorie</Form.Label>
                          <Form.Select
                            name="category"
                            value={values.category}
                            onChange={handleChange}
                            onBlur={handleBlur}
                            isInvalid={touched.category && errors.category}
                          >
                            <option value="">Non classé</option>
                            {Array.isArray(categories) && categories.length > 0 ? (
                              categories.map(category => (
                                <option key={category.id} value={category.id}>
                                  {category.name}
                                </option>
                              ))
                            ) : (
                              <option value="" disabled>Chargement des catégories...</option>
                            )}
                          </Form.Select>
                          <Form.Control.Feedback type="invalid">
                            {errors.category}
                          </Form.Control.Feedback>
                        </Form.Group>
                      </Col>
                      <Col md={4}>
                        <Form.Group className="mb-3">
                          <Form.Label>Priorité</Form.Label>
                          <Form.Select
                            name="priority"
                            value={values.priority}
                            onChange={handleChange}
                            onBlur={handleBlur}
                            isInvalid={touched.priority && errors.priority}
                          >
                            <option value="low">Basse</option>
                            <option value="medium">Moyenne</option>
                            <option value="high">Haute</option>
                            <option value="urgent">Urgente</option>
                          </Form.Select>
                          <Form.Control.Feedback type="invalid">
                            {errors.priority}
                          </Form.Control.Feedback>
                        </Form.Group>
                      </Col>
                    </Row>
                    
                    <div className="d-flex justify-content-end">
                      <Button
                        variant="primary"
                        type="submit"
                        disabled={isSubmitting}
                      >
                        {isSubmitting ? (
                          <>
                            <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                            Mise à jour...
                          </>
                        ) : (
                          'Mettre à jour'
                        )}
                      </Button>
                    </div>
                  </Form>
                )}
              </Formik>
            </div>
          )}
        </Card.Body>
      </Card>
      
      {/* Pièces jointes */}
      <Card className="mb-4">
        <Card.Header>
          <h5 className="mb-0">Pièces jointes</h5>
        </Card.Header>
        <Card.Body>
          {feedback && (
            <AttachmentManager 
              feedbackId={id} 
              readOnly={!isUserModerator} 
              onAttachmentsChange={(attachments) => {
                console.log('Pièces jointes mises à jour:', attachments);
              }}
            />
          )}
        </Card.Body>
      </Card>
      
      {/* Réponses */}
      <Card className="mb-4">
        <Card.Header>
          <h5 className="mb-0">Réponses ({feedback.responses?.length || 0})</h5>
        </Card.Header>
        <Card.Body>
          {feedback.responses && feedback.responses.length > 0 ? (
            <ListGroup variant="flush" className="response-list">
              {feedback.responses.map(response => (
                <ListGroup.Item key={response.id} className="response-item">
                  <div className="d-flex justify-content-between mb-2">
                    <div>
                      <strong>{response.responder?.username || 'Modérateur'}</strong>
                    </div>
                    <div className="text-muted">
                      {new Date(response.created_at).toLocaleString()}
                    </div>
                  </div>
                  <div>{response.content}</div>
                  {response.sent && (
                    <div className="mt-2">
                      <Badge bg="success">Envoyé</Badge>
                    </div>
                  )}
                </ListGroup.Item>
              ))}
            </ListGroup>
          ) : (
            <p className="text-center py-3">Aucune réponse pour ce feedback.</p>
          )}
          
          {/* Formulaire de réponse (modérateurs uniquement) */}
          {isUserModerator && (
            <div className="mt-4">
              <h5>Répondre</h5>
              
              {responseStatus.message && (
                <Alert 
                  variant={responseStatus.type} 
                  onClose={() => setResponseStatus({ type: '', message: '' })} 
                  dismissible
                >
                  {responseStatus.message}
                </Alert>
              )}
              
              <Formik
                initialValues={{
                  content: ''
                }}
                enableReinitialize={true}
                validateOnChange={true}
                validateOnBlur={true}
                validationSchema={ResponseSchema}
                onSubmit={handleRespond}
              >
                {({
                  values,
                  errors,
                  touched,
                  handleChange,
                  handleBlur,
                  handleSubmit,
                  isSubmitting
                }) => (
                  <Form onSubmit={handleSubmit}>
                    <Form.Group className="mb-3">
                      <Form.Control
                        as="textarea"
                        rows={4}
                        name="content"
                        value={values.content || ''}
                        onChange={(e) => {
                          // Supprimer le texte dupliqué si présent
                          const value = e.target.value;
                          if (value.includes('Sélectionnez le canal par lequel vous souhaitez simuler')) {
                            e.target.value = value.replace('Sélectionnez le canal par lequel vous souhaitez simuler l\'envoi du feedback', '');
                          }
                          handleChange(e);
                        }}
                        onBlur={handleBlur}
                        isInvalid={touched.content && errors.content}
                        placeholder="Écrivez votre réponse ici..."
                      />
                      <Form.Control.Feedback type="invalid">
                        {errors.content}
                      </Form.Control.Feedback>
                      {feedback.channel !== 'web' && (
                        <Form.Text className="text-muted">
                          Cette réponse sera envoyée via {feedback.channel === 'sms' ? 'SMS' : 'WhatsApp'} au numéro {feedback.contact_phone || 'non spécifié'}.
                        </Form.Text>
                      )}
                    </Form.Group>
                    
                    <div className="d-flex justify-content-end">
                      <Button
                        variant="primary"
                        type="submit"
                        disabled={isSubmitting}
                      >
                        {isSubmitting ? (
                          <>
                            <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                            Envoi en cours...
                          </>
                        ) : (
                          'Envoyer la réponse'
                        )}
                      </Button>
                    </div>
                  </Form>
                )}
              </Formik>
            </div>
          )}
        </Card.Body>
      </Card>
    </Container>
  );
};

export default FeedbackDetailPage;
