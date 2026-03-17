CREATE DATABASE IF NOT EXISTS predictor_partidos;
USE predictor_partidos;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    competition VARCHAR(120) NOT NULL,
    match_date DATETIME NOT NULL,
    home_team VARCHAR(120) NOT NULL,
    away_team VARCHAR(120) NOT NULL,
    predicted_result VARCHAR(50) NOT NULL,
    predicted_home_score INT DEFAULT NULL,
    predicted_away_score INT DEFAULT NULL,
    confidence_level VARCHAR(30) DEFAULT 'Media',
    analysis TEXT,
    status VARCHAR(30) DEFAULT 'Pendiente',
    actual_home_score INT DEFAULT NULL,
    actual_away_score INT DEFAULT NULL,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);