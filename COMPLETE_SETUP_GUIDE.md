🚀 Complete Setup Guide - Live Wealth & Compliance Sentinel
This guide walks you through every single step to build this project from absolute scratch, including where to put API keys, passwords, and all configuration details.

📋 Table of Contents
Prerequisites & Account Setup
Project Structure Creation
File-by-File Setup
API Keys & Credentials Configuration
Google Drive Setup
Building & Running
Verification & Testing
Troubleshooting
1. Prerequisites & Account Setup
Required Accounts & API Keys
Service	Purpose	Free Tier?	Sign Up Link
OpenAI	LLM & Embeddings	No (pay-as-go)	https://platform.openai.com/signup
Google Cloud	Drive API	Yes (generous)	https://console.cloud.google.com
Anthropic (Optional)	Claude models	No (pay-as-go)	https://console.anthropic.com
Alpha Vantage (Optional)	Market data	Yes (500 calls/day)	https://www.alphavantage.co/support/#api-key
Finnhub (Optional)	Market data	Yes (60 calls/min)	https://finnhub.io/register
System Requirements
bash
# Operating System: Linux, macOS, or Windows with WSL2
# Required Software:
- Docker Desktop (20.10+)
- Docker Compose (2.0+)
- Git
- Text editor (VS Code recommended)
- 8GB RAM minimum (16GB recommended)
- 20GB free disk space
Install Docker & Docker Compose
bash
# macOS (using Homebrew)
brew install --cask docker

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install docker.io docker-compose-plugin

# Windows
# Download Docker Desktop from: https://www.docker.com/products/docker-desktop/

# Verify installation
docker --version
docker-compose --version
2. Project Structure Creation
Step 1: Create Project Directory
bash
# Create main project folder
mkdir compliance-sentinel
cd compliance-sentinel

# Create complete directory structure
mkdir -p {src,credentials,data,rules,logs}
mkdir -p data/pathway_storage

# Create placeholder files
touch .env
touch .env.example
touch .gitignore
touch docker-compose.yml
touch pipeline.py
touch init-db.sql
touch README.md
touch COMPLETE_SETUP_GUIDE.md
Step 2: Your Directory Should Look Like This
compliance-sentinel/
├── .env                          # ⚠️  SECRET - Your actual credentials (DO NOT COMMIT)
├── .env.example                  # Template for .env file
├── .gitignore                    # Git ignore rules
├── docker-compose.yml            # Docker orchestration
├── pipeline.py                   # Main Pathway pipeline
├── init-db.sql                   # MySQL schema initialization
├── README.md                     # Project documentation
├── COMPLETE_SETUP_GUIDE.md       # This file
├── Dockerfile.pipeline           # Pipeline container
├── Dockerfile.streamlit          # Dashboard container
├── Dockerfile.streamer           # Market data container
├── requirements-pipeline.txt     # Python deps for pipeline
├── requirements-streamlit.txt    # Python deps for UI
├── src/
│   ├── dashboard.py              # Streamlit UI
│   ├── compliance_agent.py       # LangGraph agent
│   ├── vector_search.py          # Qdrant interface
│   └── market_streamer.py        # Market data feed
├── credentials/
│   └── google-credentials.json   # ⚠️  SECRET - Google service account key
├── rules/
│   └── compliance_rules.json     # Compliance rule definitions
├── data/
│   └── pathway_storage/          # Persistent Pathway data
└── logs/                         # Application logs
3. File-by-File Setup
Step 3.1: Create .gitignore
bash
cat > .gitignore << 'EOF'
# Secrets - NEVER COMMIT THESE
.env
credentials/
*.json
*.pem
*.key

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/

# Data & Logs
data/
logs/
*.log
*.db
*.sqlite

# Docker
.dockerignore

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
EOF
Step 3.2: Create Dockerfile.pipeline
bash
cat > Dockerfile.pipeline << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements-pipeline.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-pipeline.txt

# Create necessary directories
RUN mkdir -p /app/data /app/credentials /app/src /app/gdrive_cache /app/rules

# Copy source code
COPY src/ /app/src/
COPY pipeline.py /app/
COPY rules/ /app/rules/

# Set Python path
ENV PYTHONPATH=/app

# Expose API port
EXPOSE 8000

CMD ["python", "pipeline.py"]
EOF
Step 3.3: Create Dockerfile.streamlit
bash
cat > Dockerfile.streamlit << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements-streamlit.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-streamlit.txt

# Create necessary directories
RUN mkdir -p /app/src /app/data /app/rules

# Copy source code
COPY src/ /app/src/
COPY rules/ /app/rules/

# Set Python path
ENV PYTHONPATH=/app

# Expose Streamlit port
EXPOSE 8501

CMD ["streamlit", "run", "src/dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
EOF
Step 3.4: Create Dockerfile.streamer
bash
cat > Dockerfile.streamer << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    redis==5.0.1 \
    requests==2.31.0 \
    python-dotenv==1.0.1

# Copy market streamer script
COPY src/market_streamer.py /app/src/

ENV PYTHONPATH=/app

CMD ["python", "src/market_streamer.py"]
EOF
Step 3.5: Create requirements-pipeline.txt
bash
cat > requirements-pipeline.txt << 'EOF'
# Pathway Framework
pathway[all]==0.13.0

# Vector Database
qdrant-client==1.7.3

# Document Processing
unstructured[all]==0.11.8
python-magic==0.4.27
pypdf==3.17.4
python-docx==1.1.0
python-pptx==0.6.23

# OpenAI
openai==1.12.0
tiktoken==0.5.2

# Google Drive Integration
google-auth==2.27.0
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0
google-api-python-client==2.116.0

# Redis for streaming
redis==5.0.1

# MySQL
pymysql==1.1.0
mysql-connector-python==8.2.0

# Utilities
python-dotenv==1.0.1
requests==2.31.0
aiohttp==3.9.1
EOF
Step 3.6: Create requirements-streamlit.txt
bash
cat > requirements-streamlit.txt << 'EOF'
# Streamlit
streamlit==1.31.1

# LangChain & LangGraph
langgraph==0.2.28
langchain==0.2.16
langchain-openai==0.1.25
langchain-anthropic==0.1.23
langchain-community==0.2.16
langchain-core==0.2.38

# Vector Database
qdrant-client==1.7.3

# OpenAI & Anthropic
openai==1.12.0
anthropic==0.25.1

# Redis
redis==5.0.1

# MySQL
pymysql==1.1.0
mysql-connector-python==8.2.0

# Data visualization
pandas==2.1.4
plotly==5.18.0

# Utilities
python-dotenv==1.0.1
requests==2.31.0
pydantic==2.6.1
EOF
Step 3.7: Copy All Artifact Files
You need to copy these files from the artifacts I created:

docker-compose.yml - Full orchestration
pipeline.py - Main Pathway pipeline
init-db.sql - MySQL schema
src/dashboard.py - Streamlit dashboard
src/compliance_agent.py - LangGraph agent
src/vector_search.py - Vector search interface
src/market_streamer.py - Market data streamer
rules/compliance_rules.json - Compliance rules
README.md - Documentation
Copy these into your project directory exactly as shown in the structure above.

4. API Keys & Credentials Configuration
Step 4.1: Create .env File
bash
cat > .env << 'EOF'
# =============================================================================
# API KEYS - REPLACE WITH YOUR ACTUAL KEYS
# =============================================================================

# OpenAI API Key (REQUIRED)
# Get from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-proj-XXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# Anthropic API Key (OPTIONAL - for Claude models)
# Get from: https://console.anthropic.com/settings/keys
ANTHROPIC_API_KEY=sk-ant-XXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# =============================================================================
# MARKET DATA APIs (OPTIONAL - will simulate if not provided)
# =============================================================================

# Alpha Vantage API Key
# Get from: https://www.alphavantage.co/support/#api-key
ALPHA_VANTAGE_API_KEY=YOUR_ALPHA_VANTAGE_KEY_HERE

# Finnhub API Key
# Get from: https://finnhub.io/dashboard
FINNHUB_API_KEY=YOUR_FINNHUB_KEY_HERE

# =============================================================================
# GOOGLE DRIVE CONFIGURATION (REQUIRED)
# =============================================================================

# Google Drive Folder ID
# How to get: Open your folder in Google Drive, copy ID from URL
# URL format: https://drive.google.com/drive/folders/FOLDER_ID_HERE
GDRIVE_FOLDER_ID=1a2b3c4d5e6f7g8h9i0j

# Path to Google Service Account Credentials
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/google-credentials.json

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# MySQL Configuration
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_DB=compliance_db
MYSQL_USER=compliance_user
MYSQL_PASSWORD=SecurePassword123!  # ⚠️ CHANGE THIS
MYSQL_ROOT_PASSWORD=RootPassword456!  # ⚠️ CHANGE THIS

# Qdrant Vector Database
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# Redis Cache
REDIS_HOST=redis
REDIS_PORT=6379

# =============================================================================
# EMAIL ALERT CONFIGURATION (OPTIONAL)
# =============================================================================

# SMTP Configuration for Email Alerts
# Gmail Example (requires App Password, not regular password)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password

# Email address to receive alerts
ALERT_EMAIL=compliance-team@yourcompany.com

# =============================================================================
# SYSTEM CONFIGURATION
# =============================================================================

# Pathway persistent storage
PATHWAY_PERSISTENT_STORAGE=/app/data/pathway_storage

# Pathway API URL (internal)
PATHWAY_API_URL=http://pathway-sentinel:8000

# Market data stream interval (seconds)
STREAM_INTERVAL=10
EOF
Step 4.2: Update .env with YOUR Credentials
🔴 CRITICAL: Replace these values in .env:

Variable	Where to Find	Example
OPENAI_API_KEY	https://platform.openai.com/api-keys	sk-proj-abc123...
GDRIVE_FOLDER_ID	Google Drive folder URL	1a2b3c4d5e6f7g8h9i0j
MYSQL_PASSWORD	Create a strong password	MySecure123!
MYSQL_ROOT_PASSWORD	Create a strong password	RootPass456!
SMTP_USER	Your Gmail address	you@gmail.com
SMTP_PASSWORD	Gmail App Password	abcd efgh ijkl mnop
ALERT_EMAIL	Where to send alerts	team@company.com
5. Google Drive Setup
Step 5.1: Create Google Cloud Project
Go to https://console.cloud.google.com
Click "Select a project" → "New Project"
Name it: Compliance Sentinel
Click "Create"
Step 5.2: Enable Google Drive API
In Google Cloud Console, go to "APIs & Services" → "Library"
Search for "Google Drive API"
Click on it and press "Enable"
Step 5.3: Create Service Account
Go to "APIs & Services" → "Credentials"
Click "Create Credentials" → "Service Account"
Fill in:
Name: compliance-sentinel-service
ID: (auto-generated)
Description: Service account for Compliance Sentinel
Click "Create and Continue"
Skip optional steps, click "Done"
Step 5.4: Create Service Account Key
Click on the service account you just created
Go to "Keys" tab
Click "Add Key" → "Create new key"
Choose "JSON" format
Click "Create"
Save the downloaded JSON file as: credentials/google-credentials.json
bash
# Move the downloaded JSON file
mv ~/Downloads/compliance-sentinel-service-*.json credentials/google-credentials.json

# Verify the file
cat credentials/google-credentials.json | jq .
Step 5.5: Setup Google Drive Folder
Create a folder in Google Drive named Compliance Documents
Get the folder ID from URL:
   https://drive.google.com/drive/folders/1a2b3c4d5e6f7g8h9i0j
                                           ^^^^^^^^^^^^^^^^^^^^
                                           This is your FOLDER_ID
Share the folder with your service account:
Right-click folder → "Share"
Paste the service account email (from JSON file):
     compliance-sentinel-service@your-project.iam.gserviceaccount.com
Set permission: "Editor"
Click "Send"
Update .env with your folder ID:
bash
   GDRIVE_FOLDER_ID=1a2b3c4d5e6f7g8h9i0j  # Your actual ID
Step 5.6: Add Test Documents
Upload sample documents to test:

bash
# Create sample documents
echo "Risk Assessment Report - AAPL has been upgraded to risk rating D due to market volatility." > test-risk-report.txt
echo "Portfolio Holdings: AAPL 25%, TSLA 15%, GOOGL 20%, MSFT 20%, NVDA 20%" > test-portfolio.txt

# Upload to Google Drive manually or via CLI
6. Building & Running
Step 6.1: Verify All Files Are in Place
bash
# Check structure
tree -L 2

# Expected output:
# .
# ├── docker-compose.yml
# ├── pipeline.py
# ├── init-db.sql
# ├── Dockerfile.pipeline
# ├── Dockerfile.streamlit
# ├── Dockerfile.streamer
# ├── requirements-pipeline.txt
# ├── requirements-streamlit.txt
# ├── .env
# ├── src/
# │   ├── dashboard.py
# │   ├── compliance_agent.py
# │   ├── vector_search.py
# │   └── market_streamer.py
# ├── credentials/
# │   └── google-credentials.json
# └── rules/
#     └── compliance_rules.json
Step 6.2: Build Docker Images
bash
# Build all containers (this takes 5-10 minutes first time)
docker-compose build

# Expected output:
# [+] Building 234.5s (47/47) FINISHED
# => [pathway-sentinel 1/8] FROM docker.io/library/python:3.11-slim
# => [streamlit-dashboard 1/7] FROM docker.io/library/python:3.11-slim
# ...
Step 6.3: Start All Services
bash
# Start in detached mode
docker-compose up -d

# Expected output:
# [+] Running 6/6
#  ✔ Network sentinel-network         Created
#  ✔ Container qdrant-vectordb        Started
#  ✔ Container redis-cache            Started
#  ✔ Container mysql-compliance       Started
#  ✔ Container market-data-streamer   Started
#  ✔ Container compliance-sentinel    Started
#  ✔ Container compliance-dashboard   Started
Step 6.4: Monitor Logs
bash
# Watch all logs
docker-compose logs -f

# Watch specific service
docker-compose logs -f compliance-sentinel
docker-compose logs -f compliance-dashboard

# Check if services are healthy
docker-compose ps

# Expected output:
# NAME                    STATUS              PORTS
# compliance-dashboard    Up (healthy)        0.0.0.0:8501->8501/tcp
# compliance-sentinel     Up (healthy)        0.0.0.0:8000->8000/tcp
# market-data-streamer    Up                  
# mysql-compliance        Up (healthy)        0.0.0.0:3306->3306/tcp
# qdrant-vectordb         Up                  0.0.0.0:6333->6333/tcp
# redis-cache             Up (healthy)        0.0.0.0:6379->6379/tcp
7. Verification & Testing
Step 7.1: Access Services
Open your browser and verify:

Service	URL	Expected
Dashboard	http://localhost:8501	Streamlit UI loads
Qdrant	http://localhost:6333/dashboard	Vector DB dashboard
MySQL	localhost:3306	Can connect via client
Step 7.2: Test MySQL Connection
bash
# Connect to MySQL
docker-compose exec mysql mysql -u compliance_user -p

# Enter password from .env: SecurePassword123!

# Run test queries
mysql> SHOW DATABASES;
mysql> USE compliance_db;
mysql> SHOW TABLES;
mysql> SELECT * FROM compliance_rules;
mysql> exit;
Step 7.3: Test Pathway Pipeline
bash
# Check pipeline logs
docker-compose logs compliance-sentinel | tail -50

# Should see:
# INFO - Starting Live Wealth & Compliance Sentinel...
# INFO - Setting up Google Drive monitoring...
# INFO - Google Drive source configured successfully
# INFO - Market data stream configured
# INFO - Compliance Sentinel initialized successfully
Step 7.4: Test Document Processing
bash
# Upload a document to Google Drive folder
# Within 10 seconds, check logs:
docker-compose logs -f compliance-sentinel

# Should see:
# INFO - New document detected: test-risk-report.txt
# INFO - Document type: RISK_ASSESSMENT
# INFO - Extracted metadata: {'risk_rating': 'D', ...}
# INFO - Document indexed successfully
Step 7.5: Test Market Data Stream
bash
# Check market streamer logs
docker-compose logs market-streamer | tail -20

# Should see:
# INFO - Starting market data stream...
# INFO - Published: AAPL @ $180.23 (+0.45%)
# INFO - Published: TSLA @ $245.67 (-1.23%)
# ...
Step 7.6: Test Dashboard
Open http://localhost:8501
Check "System Status" in sidebar:
All should show 🟢 Active
Click on "Market Data" tab
Should show live prices
Try semantic search:
Type: "What are the risk ratings?"
Should return relevant documents
8. Troubleshooting
Issue: Containers Won't Start
bash
# Check Docker is running
docker info

# Check disk space
df -h

# View container logs
docker-compose logs --tail=100

# Restart services
docker-compose down
docker-compose up -d
Issue: Google Drive Not Connecting
bash
# Verify credentials file exists
ls -la credentials/google-credentials.json

# Check service account email in file
cat credentials/google-credentials.json | jq -r .client_email

# Verify folder is shared with this email
# Go to Google Drive → Right-click folder → "Share" → Check email is listed

# Check pipeline logs
docker-compose logs compliance-sentinel | grep -i "google"
Issue: MySQL Connection Failed
bash
# Check MySQL is running
docker-compose ps mysql

# Try connecting
docker-compose exec mysql mysql -u root -p
# Enter MYSQL_ROOT_PASSWORD from .env

# If connection fails, check credentials in .env
grep MYSQL .env

# Reset MySQL
docker-compose stop mysql
docker volume rm compliance-sentinel_mysql-data
docker-compose up -d mysql
Issue: API Rate Limits
bash
# OpenAI rate limit
# Solution: Wait or upgrade to higher tier

# Market data rate limit
# Solution: System will fall back to simulation mode
# Check logs: docker-compose logs market-streamer
Issue: Port Already in Use
bash
# Check what's using the port
sudo lsof -i :8501  # Streamlit
sudo lsof -i :3306  # MySQL
sudo lsof -i :6333  # Qdrant

# Kill the process or change port in docker-compose.yml
# Example: Change "8501:8501" to "8502:8501"
Issue: Out of Memory
bash
# Check Docker memory
docker stats

# Increase Docker Desktop memory:
# Settings → Resources → Memory → Increase to 8GB

# Or reduce services:
docker-compose up -d mysql qdrant redis compliance-sentinel
🎯 Quick Reference: Where Everything Is
API Keys & Passwords
Item	File	Line/Section
OpenAI API Key	.env	Line 7
MySQL Password	.env	Lines 34-35
Gmail App Password	.env	Line 49
Google Folder ID	.env	Line 24
Configuration Files
What to Change	File	Purpose
Database credentials	.env	MySQL user/password
Google Drive folder	.env	Folder ID to monitor
Email alerts	.env	SMTP settings
Compliance rules	rules/compliance_rules.json	Rule thresholds
Alert severity	src/compliance_agent.py	Escalation logic
Document types	pipeline.py	Document classification
Service Ports
Service	Port	Access
Dashboard	8501	http://localhost:8501
Pathway API	8000	http://localhost:8000
Qdrant	6333	http://localhost:6333
MySQL	3306	mysql -h localhost -P 3306
Redis	6379	redis-cli -h localhost -p 6379
🚀 Next Steps After Setup
1. Customize Compliance Rules
Edit rules/compliance_rules.json:

json
{
  "rule_id": "CUSTOM_001",
  "name": "Your Custom Rule",
  "threshold": 0.25,
  "severity": "HIGH"
}
2. Add More Document Types
Edit pipeline.py, function _classify_document_type():

python
if "your_keyword" in filename_lower:
    return "YOUR_DOC_TYPE"
3. Configure Email Templates
Edit src/compliance_agent.py, function _draft_alert_email():

python
email_prompt = f"""Your custom email template..."""
4. Add Custom Market Data Sources
Edit src/market_streamer.py, add new API:

python
def fetch_custom_api(self, symbol):
    # Your API integration
5. Monitor Production
bash
# Set up monitoring
docker-compose logs -f > logs/system.log

# Set up alerts
crontab -e
# Add: */5 * * * * docker-compose ps | grep -v "Up" && mail -s "Service Down" admin@company.com
📞 Support Checklist
Before asking for help, verify:

 All files are in correct directories
 .env file has YOUR actual API keys (not placeholders)
 credentials/google-credentials.json exists
 Google Drive folder is shared with service account
 Docker has enough memory (8GB+)
 All ports are free (8501, 3306, 6333, 6379)
 Internet connection is working
 Checked logs: docker-compose logs
🎉 Success Indicators
You know it's working when:

✅ Dashboard loads at http://localhost:8501 ✅ "System Status" shows all green (🟢 Active) ✅ Documents from Google Drive appear in search ✅ Market data updates every 10 seconds ✅ Alerts appear when violations detected ✅ MySQL shows data in tables ✅ No error messages in logs

Congratulations! Your Live Wealth & Compliance Sentinel is operational! 🛡️

