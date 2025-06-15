import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Navbar, Nav, Container, Button } from 'react-bootstrap';
import { useAuth } from '../../context/AuthContext';

const Header = () => {
  const { currentUser, logout, isModerator } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <Navbar bg="primary" variant="dark" expand="lg" className="mb-3">
      <Container>
        <Navbar.Brand as={Link} to="/">
          Feedback Platform
        </Navbar.Brand>
        <Navbar.Toggle aria-controls="basic-navbar-nav" />
        <Navbar.Collapse id="basic-navbar-nav">
          <Nav className="me-auto">
            <Nav.Link as={Link} to="/">Accueil</Nav.Link>
            <Nav.Link as={Link} to="/submit">Soumettre un feedback</Nav.Link>
            
            {currentUser && (
              <>
                <Nav.Link as={Link} to="/dashboard">Tableau de bord</Nav.Link>
                {isModerator() && (
                  <Nav.Link as={Link} to="/stats">Statistiques</Nav.Link>
                )}
              </>
            )}
          </Nav>
          
          <Nav>
            {currentUser ? (
              <div className="d-flex align-items-center">
                <span className="text-light me-3">
                  Bonjour, {currentUser.username}
                </span>
                <Button 
                  variant="outline-light" 
                  size="sm" 
                  onClick={handleLogout}
                >
                  Déconnexion
                </Button>
              </div>
            ) : (
              <Nav.Link as={Link} to="/login">Connexion</Nav.Link>
            )}
          </Nav>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
};

export default Header;
