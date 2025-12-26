"""
Live Wealth & Compliance Sentinel Dashboard
Real-time monitoring, alert management, portfolio analysis
"""

import streamlit as st
import os
import json
import redis
import psycopg2
import mysql.connector
from mysql.connector import Error as MySQLError
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import List, Dict, Any
import time

# Import agent components
from src.compliance_agent import ComplianceAgent
from src.vector_search import VectorSearch

# Page configuration
st.set_page_config(
    page_title="Compliance Sentinel",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .alert-critical {
        background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 5px solid #a71d2a;
    }
    .alert-high {
        background: linear-gradient(135deg, #fd7e14 0%, #e8590c 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 5px solid #d64301;
    }
    .alert-medium {
        background: linear-gradient(135deg, #ffc107 0%, #ff9800 100%);
        color: #333;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 5px solid #ff6f00;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #dee2e6;
        text-align: center;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #666;
        margin-top: 0.5rem;
    }
    .status-active {
        color: #28a745;
        font-weight: bold;
    }
    .status-warning {
        color: #ffc107;
        font-weight: bold;
    }
    .status-critical {
        color: #dc3545;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state"""
    if "compliance_agent" not in st.session_state:
        st.session_state.compliance_agent = None
    
    if "vector_search" not in st.session_state:
        st.session_state.vector_search = None
    
    if "redis_client" not in st.session_state:
        st.session_state.redis_client = None
    
    if "db_conn" not in st.session_state:
        st.session_state.db_conn = None
    
    if "active_alerts" not in st.session_state:
        st.session_state.active_alerts = []
    
    if "market_data" not in st.session_state:
        st.session_state.market_data = {}


def initialize_connections():
    """Initialize all database and service connections"""
    
    if st.session_state.redis_client is None:
        try:
            st.session_state.redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "redis"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                decode_responses=True
            )
            st.session_state.redis_client.ping()
        except Exception as e:
            st.error(f"Redis connection failed: {e}")
    
    if st.session_state.db_conn is None:
        try:
            st.session_state.db_conn = mysql.connector.connect(
                host=os.getenv("MYSQL_HOST", "mysql"),
                port=int(os.getenv("MYSQL_PORT", 3306)),
                database=os.getenv("MYSQL_DB", "compliance_db"),
                user=os.getenv("MYSQL_USER", "compliance_user"),
                password=os.getenv("MYSQL_PASSWORD", "password"),
            )
            # Ensure connection is closed on app termination
            import atexit
            atexit.register(lambda: st.session_state.db_conn.close() if st.session_state.db_conn else None)
        except MySQLError as e:
            st.error(f"MySQL connection failed: {e}")
    
    if st.session_state.vector_search is None:
        try:
            st.session_state.vector_search = VectorSearch(
                qdrant_host=os.getenv("QDRANT_HOST", "qdrant"),
                qdrant_port=int(os.getenv("QDRANT_PORT", 6333)),
                collection_name="compliance_documents",
            )
        except Exception as e:
            st.warning(f"Vector search initialization: {e}")
    
    if st.session_state.compliance_agent is None:
        try:
            st.session_state.compliance_agent = ComplianceAgent(
                model_name=st.session_state.get("model_name", "gpt-4-turbo-preview"),
            )
        except Exception as e:
            st.error(f"Agent initialization failed: {e}")


def fetch_recent_alerts() -> List[Dict]:
    """Fetch recent compliance alerts from MySQL"""
    if not st.session_state.db_conn:
        return []
    
    try:
        cursor = st.session_state.db_conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT alert_id, severity, alert_type, message, 
                   affected_assets, timestamp
            FROM compliance_alerts
            ORDER BY timestamp DESC
            LIMIT 50
        """)
        
        alerts = cursor.fetchall()
        cursor.close()
        
        # Parse JSON fields
        for alert in alerts:
            if isinstance(alert.get('affected_assets'), str):
                try:
                    alert['affected_assets'] = json.loads(alert['affected_assets'])
                except:
                    alert['affected_assets'] = []
        
        return alerts
        
    except MySQLError as e:
        st.error(f"Error fetching alerts: {e}")
        return []


def fetch_market_data() -> Dict:
    """Fetch latest market data from Redis"""
    if not st.session_state.redis_client:
        return {}
    
    try:
        # Get latest market data (simulated - in production would query Redis stream)
        market_data = {}
        
        symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
        for symbol in symbols:
            key = f"market:{symbol}:latest"
            data = st.session_state.redis_client.get(key)
            if data:
                market_data[symbol] = json.loads(data)
        
        return market_data
        
    except Exception as e:
        st.warning(f"Error fetching market data: {e}")
        return {}


def render_sidebar():
    """Render sidebar with system status and controls"""
    
    with st.sidebar:
        st.markdown("## 🛡️ Sentinel Control")
        
        # System status
        st.markdown("### System Status")
        
        status_items = [
            ("Pathway Pipeline", st.session_state.redis_client is not None),
            ("Vector Database", st.session_state.vector_search is not None),
            ("MySQL", st.session_state.db_conn is not None),
            ("Compliance Agent", st.session_state.compliance_agent is not None),
        ]
        
        for name, active in status_items:
            status_class = "status-active" if active else "status-critical"
            status_text = "🟢 Active" if active else "🔴 Offline"
            st.markdown(f"{name}: <span class='{status_class}'>{status_text}</span>", 
                       unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Alert filters
        st.markdown("### 🔍 Alert Filters")
        
        severity_filter = st.multiselect(
            "Severity",
            options=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
            default=["CRITICAL", "HIGH"]
        )
        
        alert_type_filter = st.multiselect(
            "Alert Type",
            options=["VOLATILITY_BREACH", "RISK_RATING_CHANGE", 
                    "CONCENTRATION_LIMIT", "COMPLIANCE_VIOLATION"],
            default=[]
        )
        
        st.session_state.severity_filter = severity_filter
        st.session_state.alert_type_filter = alert_type_filter
        
        st.markdown("---")
        
        # Model selection
        st.markdown("### 🤖 AI Model")
        
        model_options = {
            "GPT-4 Turbo": "gpt-4-turbo-preview",
            "GPT-4": "gpt-4",
            "Claude 3 Opus": "claude-3-opus-20240229",
        }
        
        selected_model = st.selectbox(
            "Model",
            options=list(model_options.keys()),
            index=0,
        )
        st.session_state.model_name = model_options[selected_model]
        
        st.markdown("---")
        
        # Refresh button
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()


def render_overview_metrics():
    """Render key metrics overview"""
    
    st.markdown("### 📊 System Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Total alerts
    alerts = fetch_recent_alerts()
    total_alerts = len(alerts)
    
    # Critical alerts
    critical_alerts = sum(1 for a in alerts if a["severity"] == "CRITICAL")
    
    # Documents indexed
    doc_count = 0
    if st.session_state.vector_search:
        try:
            doc_count = st.session_state.vector_search.get_collection_size()
        except:
            pass
    
    # Active monitoring
    monitoring_status = "Active" if st.session_state.redis_client else "Inactive"
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_alerts}</div>
            <div class="metric-label">Total Alerts (24h)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #dc3545;">{critical_alerts}</div>
            <div class="metric-label">Critical Alerts</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{doc_count}</div>
            <div class="metric-label">Documents Indexed</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #28a745;">{monitoring_status}</div>
            <div class="metric-label">Monitoring Status</div>
        </div>
        """, unsafe_allow_html=True)


def render_active_alerts():
    """Render active compliance alerts"""
    
    st.markdown("### 🚨 Active Compliance Alerts")
    
    alerts = fetch_recent_alerts()
    
    # Apply filters
    severity_filter = st.session_state.get("severity_filter", [])
    alert_type_filter = st.session_state.get("alert_type_filter", [])
    
    if severity_filter:
        alerts = [a for a in alerts if a["severity"] in severity_filter]
    
    if alert_type_filter:
        alerts = [a for a in alerts if a["alert_type"] in alert_type_filter]
    
    if not alerts:
        st.info("No active alerts matching current filters")
        return
    
    for alert in alerts[:10]:  # Show top 10
        severity = alert["severity"]
        alert_class = f"alert-{severity.lower()}"
        
        st.markdown(f"""
        <div class="{alert_class}">
            <strong>{severity}</strong> | {alert["alert_type"]}<br>
            {alert["message"]}<br>
            <small>Affected: {', '.join(alert.get("affected_assets", []))}</small><br>
            <small>{alert["timestamp"]}</small>
        </div>
        """, unsafe_allow_html=True)
        
        # Action buttons
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("Analyze", key=f"analyze_{alert['alert_id']}"):
                analyze_alert(alert)
        with col2:
            if st.button("Dismiss", key=f"dismiss_{alert['alert_id']}"):
                st.success(f"Alert {alert['alert_id']} dismissed")


def analyze_alert(alert: Dict):
    """Analyze alert using compliance agent"""
    
    with st.expander(f"🔍 Analysis: {alert['alert_id']}", expanded=True):
        with st.spinner("Analyzing with AI agent..."):
            
            if not st.session_state.compliance_agent:
                st.error("Compliance agent not initialized")
                return
            
            # Mock portfolio data (in production, fetch from Drive/DB)
            portfolio_data = {
                "total_value": 1000000,
                "positions": {
                    symbol: {
                        "shares": 100,
                        "market_value": 50000,
                    }
                    for symbol in alert.get("affected_assets", [])
                }
            }
            
            result = st.session_state.compliance_agent.process_alert(
                alert_data=alert,
                portfolio_data=portfolio_data,
            )
            
            if result.get("success"):
                st.markdown("#### Violation Analysis")
                st.write(result["violation_analysis"])
                
                st.markdown("#### Impact Assessment")
                st.write(result["impact_assessment"])
                
                st.markdown("#### Recommended Actions")
                for action in result["recommended_actions"]:
                    st.markdown(f"- {action}")
                
                st.markdown("#### Email Draft")
                st.code(result["email_draft"], language="text")
                
                if result["should_escalate"]:
                    st.error("⚠️ ESCALATION RECOMMENDED")
            else:
                st.error(f"Analysis failed: {result.get('error')}")


def render_market_overview():
    """Render live market data overview"""
    
    st.markdown("### 📈 Live Market Data")
    
    market_data = st.session_state.get("market_data", {})
    
    if not market_data:
        market_data = fetch_market_data()
        st.session_state.market_data = market_data
    
    if not market_data:
        st.info("No market data available")
        return
    
    # Create DataFrame
    df = pd.DataFrame([
        {
            "Symbol": symbol,
            "Price": f"${data.get('price', 0):.2f}",
            "Change": f"{data.get('change_pct', 0):+.2f}%",
            "Volume": f"{data.get('volume', 0):,}",
        }
        for symbol, data in market_data.items()
    ])
    
    st.dataframe(df, use_container_width=True)


def main():
    """Main dashboard"""
    
    # Header
    st.markdown('<div class="main-header">🛡️ Live Wealth & Compliance Sentinel</div>', 
               unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Real-Time Monitoring | Powered by Pathway + LangGraph</div>', 
               unsafe_allow_html=True)
    
    # Initialize
    initialize_session_state()
    initialize_connections()
    
    # Sidebar
    render_sidebar()
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏠 Dashboard", 
        "🚨 Alerts", 
        "📈 Market Data",
        "🔍 Document Search"
    ])
    
    with tab1:
        render_overview_metrics()
        st.markdown("---")
        render_active_alerts()
    
    with tab2:
        render_active_alerts()
    
    with tab3:
        render_market_overview()
    
    with tab4:
        st.markdown("### 🔍 Semantic Document Search")
        query = st.text_input("Search compliance documents...")
        
        if query and st.session_state.vector_search:
            with st.spinner("Searching..."):
                results = st.session_state.vector_search.search(
                    query=query,
                    top_k=5,
                    score_threshold=0.7,
                )
                
                for i, result in enumerate(results, 1):
                    with st.expander(f"Result {i} (Score: {result['score']:.3f})"):
                        st.write(result["text"])
                        st.json(result.get("metadata", {}))
    
    # Note: Auto-refresh removed to prevent infinite loops
    # Users can manually refresh with the 🔄 Refresh Data button


if __name__ == "__main__":
    main()