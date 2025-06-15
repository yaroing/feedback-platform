import React from 'react';
import { Container, Row, Col, Button } from 'react-bootstrap';
import { Link } from 'react-router-dom';

const NotFoundPage = () => {
  return (
    <Container>
      <Row className="justify-content-center text-center py-5">
        <Col md={8} lg={6}>
          <h1 className="display-1 mb-4">404</h1>
          <h2 className="mb-4">Page non trouvée</h2>
          <p className="lead mb-5">
            La page que vous recherchez n'existe pas ou a été déplacée.
          </p>
          <div className="d-flex justify-content-center gap-3">
            <Button as={Link} to="/" variant="primary">
              Retour à l'accueil
            </Button>
            <Button as={Link} to="/submit" variant="outline-primary">
              Soumettre un feedback
            </Button>
          </div>
        </Col>
      </Row>
    </Container>
  );
};

export default NotFoundPage;
