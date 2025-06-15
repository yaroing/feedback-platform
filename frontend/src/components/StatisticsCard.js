import React from 'react';
import { Card } from 'react-bootstrap';
import '../styles/statistics.css';

const StatisticsCard = ({ value, label, className = '' }) => {
  return (
    <Card className={`text-center h-100 ${className}`}>
      <Card.Body>
        <h1 className="stats-number text-primary">{value}</h1>
        <p className="stats-label text-muted">{label}</p>
      </Card.Body>
    </Card>
  );
};

export default StatisticsCard;
