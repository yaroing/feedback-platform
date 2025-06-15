import React from 'react';
import { Container, Row, Col, Card, Button } from 'react-bootstrap';
import { Link } from 'react-router-dom';

const HomePage = () => {
  return (
    <Container>
      <Row className="mb-4">
        <Col>
          <div className="text-center py-5">
            <h1 className="display-4 mb-4">Plateforme de Feedback Communautaire</h1>
            <p className="lead mb-4">
              Partagez vos idées, suggestions et préoccupations à travers différents canaux.
              Notre équipe est à votre écoute pour améliorer continuellement nos services.
            </p>
            <Button 
              as={Link} 
              to="/submit" 
              variant="primary" 
              size="lg" 
              className="px-4 py-2"
            >
              Soumettre un feedback
            </Button>
          </div>
        </Col>
      </Row>

      <Row className="mb-5">
        <Col md={4} className="mb-4">
          <Card className="h-100 shadow-sm">
            <Card.Body className="text-center">
              <div className="mb-3">
                <i className="bi bi-globe fs-1 text-primary"></i>
              </div>
              <Card.Title>Web</Card.Title>
              <Card.Text>
                Soumettez vos feedbacks directement depuis notre plateforme web,
                accessible sur tous vos appareils.
              </Card.Text>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4} className="mb-4">
          <Card className="h-100 shadow-sm">
            <Card.Body className="text-center">
              <div className="mb-3">
                <i className="bi bi-chat-dots fs-1 text-success"></i>
              </div>
              <Card.Title>SMS</Card.Title>
              <Card.Text>
                Envoyez vos feedbacks par SMS, même sans connexion internet.
                Simple, rapide et accessible à tous.
              </Card.Text>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4} className="mb-4">
          <Card className="h-100 shadow-sm">
            <Card.Body className="text-center">
              <div className="mb-3">
                <i className="bi bi-whatsapp fs-1 text-success"></i>
              </div>
              <Card.Title>WhatsApp</Card.Title>
              <Card.Text>
                Utilisez WhatsApp pour nous envoyer vos feedbacks avec la possibilité
                d'inclure des photos et des messages vocaux.
              </Card.Text>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Row className="py-4">
        <Col lg={6} className="mb-4">
          <h2 className="mb-3">Comment ça marche ?</h2>
          <ol className="fs-5">
            <li className="mb-2">Soumettez votre feedback via le canal de votre choix</li>
            <li className="mb-2">Notre équipe analyse et catégorise votre message</li>
            <li className="mb-2">Vous recevez une réponse personnalisée</li>
            <li className="mb-2">Vos suggestions sont intégrées dans nos améliorations</li>
          </ol>
        </Col>
        <Col lg={6} className="mb-4">
          <h2 className="mb-3">Pourquoi participer ?</h2>
          <ul className="fs-5">
            <li className="mb-2">Contribuez à l'amélioration des services</li>
            <li className="mb-2">Faites entendre votre voix</li>
            <li className="mb-2">Recevez des réponses personnalisées</li>
            <li className="mb-2">Suivez l'évolution de vos suggestions</li>
          </ul>
        </Col>
      </Row>
    </Container>
  );
};

export default HomePage;
