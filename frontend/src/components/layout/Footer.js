import React from 'react';
import { Container } from 'react-bootstrap';

const Footer = () => {
  const currentYear = new Date().getFullYear();
  
  return (
    <footer className="bg-light py-3 mt-auto">
      <Container className="text-center">
        <p className="mb-0 text-muted">
          &copy; {currentYear} Feedback Platform - Tous droits réservés
        </p>
        <small className="text-muted">
          Une plateforme de feedback communautaire multicanal
        </small>
      </Container>
    </footer>
  );
};

export default Footer;
