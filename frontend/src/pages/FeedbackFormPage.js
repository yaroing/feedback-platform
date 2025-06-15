import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Form, Button, Alert, Card, Badge } from 'react-bootstrap';
import { Formik } from 'formik';
import * as Yup from 'yup';
import { useNavigate } from 'react-router-dom';
import { feedbackAPI } from '../services/api';
import { useOffline } from '../context/OfflineContext';
import { isOnline as checkIsOnline } from '../services/offlineStorage';

// Schéma de validation pour le formulaire
const FeedbackSchema = Yup.object().shape({
  content: Yup.string()
    .required('Le contenu du feedback est requis')
    .min(10, 'Le feedback doit contenir au moins 10 caractères'),
  channel: Yup.string()
    .required('Le canal est requis'),
  contact_email: Yup.string()
    .email('Adresse email invalide'),
  contact_phone: Yup.string()
    .matches(/^[0-9+\s()-]{6,20}$/, 'Numéro de téléphone invalide')
});

const FeedbackFormPage = () => {
  const [submitStatus, setSubmitStatus] = useState({ type: '', message: '' });
  const [connectionStatus, setConnectionStatus] = useState(checkIsOnline());
  const navigate = useNavigate();
  const { isOnline } = useOffline();
  
  // Mettre à jour le statut de connexion lorsqu'il change
  useEffect(() => {
    setConnectionStatus(isOnline);
  }, [isOnline]);

  const handleSubmit = async (values, { setSubmitting, resetForm }) => {
    try {
      // Utiliser l'API améliorée qui gère automatiquement le mode hors-ligne
      const response = await feedbackAPI.create(values);
      
      // Vérifier si le feedback a été sauvegardé en mode hors-ligne
      if (response.data && response.data._offline) {
        setSubmitStatus({
          type: 'warning',
          message: 'Vous êtes hors ligne. Votre feedback a été enregistré et sera envoyé automatiquement lorsque vous serez de nouveau en ligne.'
        });
      } else {
        setSubmitStatus({
          type: 'success',
          message: 'Votre feedback a été soumis avec succès. Merci pour votre contribution!'
        });
      }
      
      resetForm();
    } catch (error) {
      console.error('Erreur lors de la soumission du feedback:', error);
      setSubmitStatus({
        type: 'danger',
        message: 'Une erreur est survenue lors de la soumission de votre feedback. Veuillez réessayer.'
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Container>
      <Row className="justify-content-center">
        <Col md={8}>
          <Card className="feedback-form">
            <Card.Body>
              <h1 className="text-center mb-4">Soumettre un Feedback</h1>
              
              {/* Indicateur de statut de connexion */}
              <div className="d-flex justify-content-center mb-3">
                <Badge 
                  bg={connectionStatus ? "success" : "warning"}
                  className="py-2 px-3"
                >
                  <i className={`bi bi-${connectionStatus ? "wifi" : "wifi-off"} me-2`}></i>
                  {connectionStatus ? "En ligne" : "Hors ligne"}
                </Badge>
              </div>
              
              {submitStatus.message && (
                <Alert 
                  variant={submitStatus.type} 
                  onClose={() => setSubmitStatus({ type: '', message: '' })} 
                  dismissible
                >
                  {submitStatus.message}
                </Alert>
              )}
              
              <Formik
                initialValues={{
                  content: '',
                  channel: 'web',
                  contact_email: '',
                  contact_phone: ''
                }}
                validationSchema={FeedbackSchema}
                onSubmit={handleSubmit}
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
                    <Form.Group className="mb-4">
                      <Form.Label>Canal</Form.Label>
                      <Form.Select
                        name="channel"
                        value={values.channel}
                        onChange={handleChange}
                        onBlur={handleBlur}
                        isInvalid={touched.channel && errors.channel}
                      >
                        <option value="web">Site Web</option>
                        <option value="sms">SMS (simulation)</option>
                        <option value="whatsapp">WhatsApp (simulation)</option>
                      </Form.Select>
                      <Form.Control.Feedback type="invalid">
                        {errors.channel}
                      </Form.Control.Feedback>
                      <Form.Text className="text-muted">
                        Sélectionnez le canal par lequel vous souhaitez simuler l'envoi du feedback
                      </Form.Text>
                    </Form.Group>

                    <Form.Group className="mb-4">
                      <Form.Label>Votre Feedback</Form.Label>
                      <Form.Control
                        as="textarea"
                        rows={5}
                        name="content"
                        value={values.content}
                        onChange={handleChange}
                        onBlur={handleBlur}
                        isInvalid={touched.content && errors.content}
                        placeholder="Partagez vos idées, suggestions ou préoccupations..."
                      />
                      <Form.Control.Feedback type="invalid">
                        {errors.content}
                      </Form.Control.Feedback>
                    </Form.Group>

                    <Form.Group className="mb-4">
                      <Form.Label>Email de contact (optionnel)</Form.Label>
                      <Form.Control
                        type="email"
                        name="contact_email"
                        value={values.contact_email}
                        onChange={handleChange}
                        onBlur={handleBlur}
                        isInvalid={touched.contact_email && errors.contact_email}
                        placeholder="votre@email.com"
                      />
                      <Form.Control.Feedback type="invalid">
                        {errors.contact_email}
                      </Form.Control.Feedback>
                    </Form.Group>

                    <Form.Group className="mb-4">
                      <Form.Label>Téléphone de contact (optionnel)</Form.Label>
                      <Form.Control
                        type="tel"
                        name="contact_phone"
                        value={values.contact_phone}
                        onChange={handleChange}
                        onBlur={handleBlur}
                        isInvalid={touched.contact_phone && errors.contact_phone}
                        placeholder="+33612345678"
                      />
                      <Form.Control.Feedback type="invalid">
                        {errors.contact_phone}
                      </Form.Control.Feedback>
                    </Form.Group>

                    <div className="d-grid gap-2">
                      <Button
                        variant="primary"
                        type="submit"
                        size="lg"
                        disabled={isSubmitting}
                      >
                        {isSubmitting ? (
                          <>
                            <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                            Envoi en cours...
                          </>
                        ) : (
                          'Envoyer le feedback'
                        )}
                      </Button>
                    </div>
                  </Form>
                )}
              </Formik>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default FeedbackFormPage;
