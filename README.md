🛡️ Live Wealth & Compliance Sentinel
A sophisticated real-time compliance monitoring system that goes beyond traditional RAG search. This system actively monitors financial documents, joins live market data streams, and uses agentic reasoning to detect violations, assess portfolio impact, and trigger automated alerts.

🚀 What Makes This Advanced
Unlike basic RAG systems that just search documents, the Compliance Sentinel:

🔄 Real-Time Stream Processing: Joins live Google Drive documents with streaming market data using Pathway
🤖 Agentic Compliance Logic: LangGraph agent performs multi-step reasoning to analyze violations and their portfolio impact
⚡ Active Monitoring & Alerting: Automatically detects compliance breaches and drafts executive alerts
📊 Financial Intelligence: Extracts risk ratings, securities mentions, and compliance keywords from documents
💼 Portfolio Analysis: Checks if new regulations or risk changes violate current holdings
Architecture Overview
┌─────────────────────┐         ┌─────────────────────┐
│   Google Drive      │         │  Market Data APIs   │
│ (Compliance Docs)   │         │   (Live Prices)     │
└──────────┬──────────┘         └──────────┬──────────┘
           │                               │
           │ 10s refresh                   │ Real-time
           ▼                               ▼
    ┌──────────────────────────────────────────┐
    │      Pathway Stream Processing           │
    │  • Document parsing & metadata extract   │
    │  • Join docs with market data on symbols │
    │  • Detect compliance rule violations     │
    └──────────┬──────────────────────┬────────┘
               │                      │
               ▼                      ▼
    ┌──────────────────┐   ┌──────────────────┐
    │  Qdrant Vector   │   │     MySQL        │
    │  (Semantic Search)│   │  (Audit Trail)   │
    └──────────────────┘   └──────────────────┘
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │  LangGraph Agent     │
                          │  • Analyze violation │
                          │  • Assess portfolio  │
                          │  • Draft alert email │
                          │  • Recommend actions │
                          └──────────┬───────────┘
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │  Streamlit Dashboard │
                          │  + Email Alerts      │
                          └──────────────────────┘
🎯 Key Features
1. Live Document-Market Data Join
Pathway continuously monitors your Google Drive folder and joins document content with live market data streams. If a document mentions "AAPL" and its risk rating changes, the system immediately correlates it with Apple's current stock price and volatility.

2. Multi-Step Agentic Reasoning
When a violation is detected, the LangGraph agent:

Step 1: Analyzes the violation nature and severity
Step 2: Assesses portfolio exposure to affected securities
Step 3: Generates specific, actionable recommendations
Step 4: Drafts a professional alert email
Step 5: Sends alert if severity warrants escalation
3. Smart Compliance Rules
Pre-configured rules monitor:

Concentration Risk: Single position or sector limits
Risk Management: High-risk asset exposure limits
Market Volatility: Extreme price movement alerts
Liquidity: Minimum liquid asset requirements
Regulatory: SEC/FINRA disclosure requirements
4. Active Alerting
Unlike passive search systems, this actively triggers alerts when:

A new compliance policy document is uploaded
Risk ratings change in market reports
Portfolio positions violate newly detected rules
Extreme market volatility affects holdings
5. MySQL-Powered Data Management
Audit Trail: Full logging of all violations and actions
Compliance Rules: Configurable thresholds stored in MySQL
Portfolio Snapshots: Historical tracking of positions
Document Processing: Complete processing history
📋 Prerequisites
Docker & Docker Compose
Google Cloud Project with Drive API enabled
OpenAI API key (for LLM and embeddings)
Anthropic API key (optional, for Claude models)
SMTP credentials (optional, for email alerts)
Market data API keys (optional, will simulate if not provided):
Alpha Vantage API key
Finnhub API key
🚀 Quick Start
1. Clone and Setup
bash
mkdir compliance-sentinel && cd compliance-sentinel

# Create directory structure
mkdir -p data credentials src rules

# Copy environment template
cp .env.example .env
2. Configure Google Drive
Go to Google Cloud Console
Enable Google Drive API
Create Service Account credentials
Download JSON key to credentials/google-credentials.json
Share your Google Drive folder with the service account email
Copy the folder ID to .env
3. Configure Environment
Edit .env:

bash
OPENAI_API_KEY=sk-...
GDRIVE_FOLDER_ID=your_folder_id
MYSQL_USER=compliance_user
MYSQL_PASSWORD=secure_password
MYSQL_ROOT_PASSWORD=root_password

# Optional: Email alerts
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
ALERT_EMAIL=compliance-team@company.com
4. Launch System
bash
# Build all containers
docker-compose build

# Start services
docker-compose up -d

# Watch logs
docker-compose logs -f pathway-sentinel
5. Access Dashboard
Open http://localhost:8501 in your browser

📁 Project Structure
compliance-sentinel/
├── docker-compose.yml           # Orchestrates all services
├── Dockerfile.pipeline          # Pathway pipeline container
├── Dockerfile.streamlit         # Dashboard container
├── Dockerfile.streamer          # Market data streamer
├── pipeline.py                  # Main Pathway pipeline
├── init-db.sql                  # PostgreSQL schema
├── .env                         # Configuration
├── src/
│   ├── dashboard.py             # Streamlit compliance dashboard
│   ├── compliance_agent.py      # LangGraph reasoning agent
│   ├── vector_search.py         # Qdrant search interface
│   └── market_streamer.py       # Live market data feed
├── rules/
│   └── compliance_rules.json    # Compliance rule definitions
├── credentials/
│   └── google-credentials.json  # Google service account
└── data/                        # Persistent storage
🎯 Usage Examples
Example 1: New Risk Assessment Document
Scenario: You upload a risk assessment report to Google Drive that mentions "TSLA" with a risk rating of "D" (high risk).

What Happens:

Pathway detects the new document within 10 seconds
Extracts metadata: risk_rating: D, mentioned_securities: [TSLA]
Joins with live TSLA market data from the stream
Detects violation: "High risk assets exceed 20% threshold"
LangGraph agent:
Analyzes your portfolio exposure to TSLA
Calculates that TSLA is 25% of your holdings
Generates recommendation: "Reduce TSLA position to <20%"
Drafts alert email to compliance team
Alert appears in dashboard and email is sent
Example 2: Extreme Volatility
Scenario: NVDA drops 18% intraday due to earnings miss.

What Happens:

Market streamer publishes real-time NVDA price data
Pathway detects 18% change exceeds 15% threshold
Triggers "Extreme Volatility" alert
Agent checks your NVDA holdings
Recommends protective actions (stop-loss, hedging)
Critical alert displayed in dashboard
Example 3: SEC Filing Update
Scenario: New 10-K filing uploaded mentioning revised concentration limits.

What Happens:

Document classified as "SEC_FILING"
Compliance keywords extracted
Agent cross-references with current portfolio
Identifies positions violating new limits
Generates rebalancing recommendations
🛠️ Customization
Add Custom Compliance Rules
Edit rules/compliance_rules.json:

json
{
  "rule_id": "CUSTOM_001",
  "name": "Your Custom Rule",
  "description": "Description here",
  "severity": "HIGH",
  "threshold": 0.15,
  "applies_to": ["PORTFOLIO"],
  "action_required": "Your action"
}
Modify Agent Reasoning
Edit src/compliance_agent.py:

python
def _analyze_violation(self, state):
    # Add your custom analysis logic
    # Access alert data: state["alert_data"]
    # Return updated state
Add Document Types
Edit pipeline.py:

python
def _classify_document_type(self, text, filename):
    if "your_keyword" in filename.lower():
        return "YOUR_DOC_TYPE"
    # ...
📊 Monitoring & Maintenance
View Pipeline Status
bash
# Check all services
docker-compose ps

# View pipeline logs
docker-compose logs -f pathway-sentinel

# Check database
docker-compose exec postgres psql -U compliance_user -d compliance_db
Query Alerts
sql
-- Recent critical alerts
SELECT * FROM compliance_alerts 
WHERE severity = 'CRITICAL' 
ORDER BY timestamp DESC 
LIMIT 10;

-- Unresolved alerts
SELECT * FROM compliance_alerts 
WHERE resolved = FALSE 
ORDER BY severity, timestamp DESC;
Monitor Market Data
bash
# Check Redis stream
docker-compose exec redis redis-cli
> SUBSCRIBE market_data
Database Backups
bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U compliance_user compliance_db > backup.sql

# Backup Qdrant
docker-compose exec qdrant tar -czf /qdrant/backup.tar.gz /qdrant/storage
🔧 Troubleshooting
Pipeline not processing documents:

Check Google Drive credentials: docker-compose logs pathway-sentinel
Verify folder permissions
Ensure folder ID is correct
No market data appearing:

Market streamer runs every 10 seconds
Check Redis: docker-compose logs market-streamer
Verify API keys if using real data
Alerts not triggering:

Check compliance rules are loaded: Query compliance_rules table
Review violation detection logic in pipeline.py
Verify thresholds are set correctly
Email alerts not sending:

Check SMTP configuration in .env
For Gmail, use App Password, not regular password
Verify should_escalate logic in agent
🚀 Advanced Features
Add More Data Sources
Connect additional streams:

python
# In pipeline.py
sec_filings = pw.io.http.read(
    url="https://sec.gov/api/filings",
    format="json",
    mode="streaming"
)
Custom Alert Channels
Add Slack notifications:

python
# In compliance_agent.py
def _send_slack_alert(self, state):
    webhook_url = os.getenv("SLACK_WEBHOOK")
    # Send to Slack
Machine Learning Integration
Add ML-based anomaly detection:

python
from pathway.stdlib.ml.classifiers import knn_classifier

anomalies = violations.select(
    is_anomaly=knn_classifier(pw.this.features)
)
🔒 Security Considerations
Never commit .env or credentials to git
Use environment-specific credentials
Implement role-based access for production
Enable audit logging for all actions
Use encrypted connections for external APIs
Rotate API keys regularly
Implement rate limiting on dashboard
📈 Performance Optimization
Batch document processing for large uploads
Cache frequently accessed market data in Redis
Partition MySQL tables by date for large datasets
Tune Qdrant collection parameters for your dataset size
Adjust Pathway refresh interval based on criticality
Use connection pooling for database access
🤝 Contributing
This is a reference architecture. Customize for your use case:

Fork the repository
Add your custom rules and logic
Test thoroughly with your data
Deploy to your infrastructure
📄 License
MIT License - Use freely for your compliance monitoring needs

🆘 Support
For issues:

Check the logs: docker-compose logs
Review the troubleshooting section
Verify all API keys and credentials
Test with sample documents first
🎓 Learn More
Pathway Documentation
LangGraph Guide
Qdrant Vector DB
SEC EDGAR Filings
FINRA Rules
Built with: Pathway • LangGraph • Streamlit • Qdrant • MySQL • Redis

Status: 🟢 Production-Ready Architecture

