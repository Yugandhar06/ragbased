
CREATE TABLE IF NOT EXISTS compliance_alerts (
    alert_id VARCHAR(255) PRIMARY KEY,
    severity VARCHAR(20) NOT NULL,
    alert_type VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    triggered_by JSON,
    affected_assets JSON,
    recommended_actions JSON,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(255),
    acknowledged_at TIMESTAMP NULL,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_by VARCHAR(255),
    resolved_at TIMESTAMP NULL,
    notes TEXT,
    INDEX idx_alerts_severity (severity),
    INDEX idx_alerts_timestamp (timestamp DESC),
    INDEX idx_alerts_type (alert_type),
    INDEX idx_alerts_resolved (resolved)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS compliance_rules (
    rule_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    severity VARCHAR(20) NOT NULL,
    category VARCHAR(100),
    threshold DECIMAL(10, 4),
    applies_to JSON,
    regulatory_reference VARCHAR(255),
    action_required TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    snapshot_id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_value DECIMAL(20, 2),
    positions JSON,
    risk_metrics JSON,
    compliance_status VARCHAR(50),
    violations JSON,
    INDEX idx_portfolio_timestamp (timestamp DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS document_processing_log (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    document_id VARCHAR(255),
    filename VARCHAR(255),
    doc_type VARCHAR(100),
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    risk_rating VARCHAR(10),
    mentioned_securities JSON,
    compliance_keywords JSON,
    processing_status VARCHAR(50),
    error_message TEXT,
    INDEX idx_doc_log_timestamp (processed_at DESC),
    INDEX idx_doc_log_type (doc_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS audit_trail (
    audit_id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(255),
    action VARCHAR(100),
    entity_type VARCHAR(100),
    entity_id VARCHAR(255),
    details JSON,
    ip_address VARCHAR(45),
    INDEX idx_audit_timestamp (timestamp DESC),
    INDEX idx_audit_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS market_data_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    price DECIMAL(20, 4),
    change_pct DECIMAL(10, 4),
    volume BIGINT,
    market_cap BIGINT,
    sector VARCHAR(100),
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_market_symbol (symbol),
    INDEX idx_market_timestamp (timestamp DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO compliance_rules (rule_id, name, description, severity, category, threshold, applies_to, regulatory_reference, action_required)
VALUES 
    ('CONC_001', 'Single Position Concentration Limit', 
     'No single equity position should exceed 10% of total portfolio value', 
     'HIGH', 'CONCENTRATION_RISK', 0.10, 
     JSON_ARRAY('PORTFOLIO', 'EQUITY'), 'SEC Rule 15c3-1', 
     'Rebalance portfolio or obtain compliance waiver'),
    
    ('RISK_001', 'High Risk Asset Limit', 
     'Assets with risk rating D or E cannot exceed 20% of portfolio', 
     'CRITICAL', 'RISK_MANAGEMENT', 0.20, 
     JSON_ARRAY('RISK_ASSESSMENT', 'PORTFOLIO'), 'FINRA Rule 2111', 
     'Reduce high-risk positions immediately'),
    
    ('VOL_001', 'Intraday Volatility Alert', 
     'Alert if any holding shows >15% intraday price change', 
     'MEDIUM', 'MARKET_VOLATILITY', 0.15, 
     JSON_ARRAY('MARKET_DATA', 'PRICE_MOVEMENT'), 'Internal Monitoring Protocol', 
     'Review position and consider protective measures')
ON DUPLICATE KEY UPDATE 
    name = VALUES(name),
    description = VALUES(description),
    updated_at = CURRENT_TIMESTAMP;