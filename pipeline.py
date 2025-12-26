"""
Live Wealth & Compliance Sentinel - Real-Time RAG Pipeline
Monitors financial documents, joins live market data, detects compliance violations
"""

import os
import pathway as pw
from pathway.xpacks.llm import embedders, parsers
from pathway.stdlib.ml.classifiers import knn_classifier
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import asyncio
import aiohttp
from dataclasses import dataclass
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ComplianceAlert:
    """Compliance alert data structure"""
    alert_id: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    alert_type: str
    message: str
    triggered_by: Dict[str, Any]
    affected_assets: List[str]
    recommended_actions: List[str]
    timestamp: str


class ComplianceSentinel:
    """Real-time compliance monitoring with active alerting"""
    
    def __init__(
        self,
        gdrive_credentials_path: str,
        gdrive_folder_id: str,
        qdrant_host: str = "qdrant",
        qdrant_port: int = 6333,
        redis_host: str = "redis",
        redis_port: int = 6379,
        postgres_config: Optional[Dict] = None,
    ):
        self.gdrive_credentials_path = gdrive_credentials_path
        self.gdrive_folder_id = gdrive_folder_id
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.mysql_config = postgres_config or self._default_mysql_config()
        
        # Initialize components
        self.embedder = None
        self.compliance_rules = {}
        self.portfolio_state = {}
        self.alert_callbacks = []
        
    def _default_mysql_config(self) -> Dict:
        return {
            "host": os.getenv("MYSQL_HOST", "mysql"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "database": os.getenv("MYSQL_DB", "compliance_db"),
            "user": os.getenv("MYSQL_USER", "compliance_user"),
            "password": os.getenv("MYSQL_PASSWORD", "password"),
        }
    
    def setup_gdrive_source(self) -> pw.Table:
        """Configure Google Drive as streaming source for compliance docs"""
        logger.info(f"Setting up Google Drive monitoring for folder: {self.gdrive_folder_id}")
        
        try:
            documents = pw.io.gdrive.read(
                object_id=self.gdrive_folder_id,
                service_user_credentials_file=self.gdrive_credentials_path,
                mode="streaming",
                refresh_interval=10,  # Check every 10 seconds for critical compliance updates
                with_metadata=True,
            )
            
            logger.info("Google Drive source configured for real-time monitoring")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to setup Google Drive source: {e}")
            raise
    
    def setup_market_data_stream(self) -> pw.Table:
        """Setup live market data stream from Redis"""
        logger.info("Setting up live market data stream")
        
        try:
            # Connect to Redis stream where market-streamer publishes data
            market_stream = pw.io.redis.read(
                host=self.redis_host,
                port=self.redis_port,
                channel="market_data",
                format="json",
                mode="streaming",
            )
            
            # Parse market data
            market_data = market_stream.select(
                symbol=pw.this.data["symbol"],
                price=pw.this.data["price"],
                change_pct=pw.this.data["change_pct"],
                volume=pw.this.data["volume"],
                timestamp=pw.this.data["timestamp"],
                market_cap=pw.this.data.get("market_cap"),
                sector=pw.this.data.get("sector"),
            )
            
            logger.info("Market data stream configured")
            return market_data
            
        except Exception as e:
            logger.error(f"Failed to setup market data stream: {e}")
            raise
    
    def extract_document_metadata(self, documents: pw.Table) -> pw.Table:
        """Extract critical metadata from financial documents"""
        logger.info("Setting up document metadata extraction")
        
        # Use LLM to extract structured metadata from documents
        def extract_metadata(text: str, filename: str) -> Dict[str, Any]:
            """Extract financial document metadata using pattern matching and LLM"""
            metadata = {
                "filename": filename,
                "doc_type": self._classify_document_type(text, filename),
                "risk_rating": self._extract_risk_rating(text),
                "mentioned_securities": self._extract_securities(text),
                "compliance_keywords": self._extract_compliance_keywords(text),
                "effective_date": self._extract_date(text, "effective"),
                "filing_date": self._extract_date(text, "filing"),
                "parsed_at": datetime.utcnow().isoformat(),
            }
            return metadata
        
        enriched_docs = documents.select(
            data=pw.this.data,
            raw_metadata=pw.this._metadata,
            extracted_metadata=pw.apply(
                lambda text, meta: extract_metadata(text, meta.get("path", "unknown")),
                pw.this.data,
                pw.this._metadata
            )
        )
        
        return enriched_docs
    
    def _classify_document_type(self, text: str, filename: str) -> str:
        """Classify financial document type"""
        filename_lower = filename.lower()
        text_lower = text[:1000].lower()
        
        if "portfolio" in filename_lower or "holdings" in filename_lower:
            return "PORTFOLIO"
        elif "10-k" in filename_lower or "10-q" in filename_lower:
            return "SEC_FILING"
        elif "compliance" in filename_lower or "policy" in filename_lower:
            return "COMPLIANCE_POLICY"
        elif "risk" in filename_lower or "risk assessment" in text_lower:
            return "RISK_ASSESSMENT"
        elif "market" in filename_lower and "report" in filename_lower:
            return "MARKET_REPORT"
        else:
            return "OTHER"
    
    def _extract_risk_rating(self, text: str) -> Optional[str]:
        """Extract risk rating from document text"""
        patterns = [
            r"risk rating[:\s]+([A-E]|low|medium|high|critical)",
            r"risk level[:\s]+([A-E]|low|medium|high|critical)",
            r"risk score[:\s]+(\d+)",
        ]
        
        text_lower = text.lower()
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                return match.group(1).upper()
        
        return None
    
    def _extract_securities(self, text: str) -> List[str]:
        """Extract mentioned securities/tickers from text"""
        # Pattern for stock tickers (simplified)
        ticker_pattern = r'\b[A-Z]{1,5}\b'
        
        # Common words to exclude
        exclude = {'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 
                   'CAN', 'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'GET'}
        
        tickers = re.findall(ticker_pattern, text)
        return [t for t in set(tickers) if t not in exclude][:20]  # Limit to 20
    
    def _extract_compliance_keywords(self, text: str) -> List[str]:
        """Extract compliance-related keywords"""
        keywords = [
            "regulation", "compliance", "violation", "sec", "finra",
            "audit", "disclosure", "fiduciary", "suitability",
            "risk limit", "exposure limit", "concentration limit"
        ]
        
        text_lower = text.lower()
        found = [kw for kw in keywords if kw in text_lower]
        return found
    
    def _extract_date(self, text: str, date_type: str) -> Optional[str]:
        """Extract dates from text"""
        patterns = [
            rf"{date_type} date[:\s]+(\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}})",
            rf"{date_type}[:\s]+(\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}})",
        ]
        
        text_lower = text.lower()
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                return match.group(1)
        
        return None
    
    def join_market_and_documents(
        self, 
        documents: pw.Table, 
        market_data: pw.Table
    ) -> pw.Table:
        """Join document mentions with live market data"""
        logger.info("Setting up document-market data join")
        
        # Flatten securities mentioned in documents
        docs_with_securities = documents.flatten(
            pw.this.extracted_metadata["mentioned_securities"]
        ).select(
            doc_id=pw.this.id,
            symbol=pw.this.mentioned_securities,
            doc_type=pw.this.extracted_metadata["doc_type"],
            risk_rating=pw.this.extracted_metadata["risk_rating"],
            data=pw.this.data,
        )
        
        # Join with market data on symbol
        joined = docs_with_securities.join(
            market_data,
            docs_with_securities.symbol == market_data.symbol,
            how="left"
        ).select(
            doc_id=docs_with_securities.doc_id,
            symbol=docs_with_securities.symbol,
            doc_type=docs_with_securities.doc_type,
            risk_rating=docs_with_securities.risk_rating,
            current_price=market_data.price,
            price_change=market_data.change_pct,
            volume=market_data.volume,
            sector=market_data.sector,
            last_updated=market_data.timestamp,
        )
        
        logger.info("Document-market join configured")
        return joined
    
    def load_compliance_rules(self) -> List[Dict[str, Any]]:
        """Load compliance rules from configuration"""
        rules_path = "/app/rules/compliance_rules.json"
        
        if os.path.exists(rules_path):
            try:
                with open(rules_path, 'r') as f:
                    rules = json.load(f)
                logger.info(f"Loaded {len(rules)} compliance rules")
                return rules
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in rules file: {e}")
                logger.warning("Using default rules instead")
        else:
            # Default rules
            default_rules = [
                {
                    "rule_id": "CONC_001",
                    "name": "Portfolio Concentration Limit",
                    "description": "No single position should exceed 10% of portfolio",
                    "severity": "HIGH",
                    "threshold": 0.10,
                    "applies_to": "PORTFOLIO"
                },
                {
                    "rule_id": "RISK_001",
                    "name": "High Risk Asset Limit",
                    "description": "Assets with risk rating D or E cannot exceed 20% of portfolio",
                    "severity": "CRITICAL",
                    "threshold": 0.20,
                    "applies_to": "RISK_ASSESSMENT"
                },
                {
                    "rule_id": "VOL_001",
                    "name": "Volatility Threshold",
                    "description": "Alert if any holding shows >15% daily price change",
                    "severity": "MEDIUM",
                    "threshold": 0.15,
                    "applies_to": "MARKET_DATA"
                }
            ]
            logger.info(f"Using {len(default_rules)} default compliance rules")
            return default_rules
    
    def detect_compliance_violations(
        self, 
        joined_data: pw.Table,
        portfolio_docs: pw.Table
    ) -> pw.Table:
        """Detect compliance violations using LangGraph agent"""
        logger.info("Setting up compliance violation detection")
        
        # Load compliance rules
        rules = self.load_compliance_rules()
        
        # Check for violations
        def check_violations(row: Dict) -> Optional[ComplianceAlert]:
            """Check if current data violates any compliance rules"""
            alerts = []
            
            # Rule: Excessive price volatility
            if row.get("price_change") and abs(float(row["price_change"])) > 15.0:
                alert = ComplianceAlert(
                    alert_id=f"VOL_{row['symbol']}_{datetime.utcnow().timestamp()}",
                    severity="MEDIUM",
                    alert_type="VOLATILITY_BREACH",
                    message=f"{row['symbol']} shows {row['price_change']}% change (>15% threshold)",
                    triggered_by={"rule_id": "VOL_001", "data": row},
                    affected_assets=[row['symbol']],
                    recommended_actions=[
                        "Review position sizing",
                        "Consider hedging strategies",
                        "Monitor for continued volatility"
                    ],
                    timestamp=datetime.utcnow().isoformat()
                )
                alerts.append(alert)
            
            # Rule: High risk rating changes
            if row.get("risk_rating") in ["D", "E"]:
                alert = ComplianceAlert(
                    alert_id=f"RISK_{row['doc_id']}_{datetime.utcnow().timestamp()}",
                    severity="HIGH",
                    alert_type="RISK_RATING_CHANGE",
                    message=f"Document indicates risk rating {row['risk_rating']} for {row['symbol']}",
                    triggered_by={"rule_id": "RISK_001", "data": row},
                    affected_assets=[row['symbol']],
                    recommended_actions=[
                        "Review portfolio exposure",
                        "Assess rebalancing needs",
                        "Consult risk management team"
                    ],
                    timestamp=datetime.utcnow().isoformat()
                )
                alerts.append(alert)
            
            return alerts
        
        violations = joined_data.select(
            alerts=pw.apply(lambda row: check_violations(row), pw.this)
        ).flatten(pw.this.alerts).select(
            alert=pw.this.alerts
        ).filter(pw.this.alert.is_not_none())
        
        return violations
    
    def setup_alert_system(self, violations: pw.Table):
        """Setup real-time alerting system"""
        logger.info("Setting up alert system")
        
        # Write alerts to MySQL for audit trail
        pw.io.sql.write(
            violations,
            uri=f"mysql+pymysql://{self.mysql_config['user']}:{self.mysql_config['password']}@{self.mysql_config['host']}:{self.mysql_config['port']}/{self.mysql_config['database']}",
            table_name="compliance_alerts",
        )
        
        # Publish to Redis for real-time dashboard updates
        pw.io.redis.write(
            violations.select(
                alert_json=pw.apply(lambda a: json.dumps(a.__dict__), pw.this.alert)
            ),
            redis_settings=pw.io.redis.RedisSettings(
                host=self.redis_host,
                port=self.redis_port,
            ),
            channel="compliance_alerts",
        )
        
        logger.info("Alert system configured")
    
    def setup_embeddings(self, documents: pw.Table) -> pw.Table:
        """Generate embeddings for semantic search"""
        logger.info("Setting up document embeddings")
        
        self.embedder = embedders.OpenAIEmbedder(
            model="text-embedding-3-small",
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        
        # Chunk documents
        chunked = documents.select(
            chunks=pw.apply(
                lambda text: self._chunk_text(text, 800, 150),
                pw.this.data
            ),
            metadata=pw.this.extracted_metadata,
        ).flatten(pw.this.chunks).select(
            text=pw.this.chunks,
            metadata=pw.this.metadata,
        )
        
        # Generate embeddings
        embedded = chunked + chunked.select(
            embedding=self.embedder.apply(text=pw.this.text, max_retries=3)
        )
        
        return embedded
    
    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Chunk text with overlap"""
        if not text:
            return []
        
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = start + chunk_size
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk)
            start = end - overlap
            if start + chunk_size >= text_len:
                break
        
        return chunks if chunks else [text]
    
    def setup_vector_store(self, embedded_chunks: pw.Table):
        """Configure Qdrant vector store"""
        logger.info(f"Setting up vector store at {self.qdrant_host}:{self.qdrant_port}")
        
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
            
            qdrant_client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
            
            collection_name = "compliance_documents"
            collections = qdrant_client.get_collections().collections
            
            if collection_name not in [c.name for c in collections]:
                qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
                )
                logger.info(f"Created collection: {collection_name}")
            
            pw.io.qdrant.write(
                embedded_chunks,
                qdrant_client=qdrant_client,
                collection_name=collection_name,
                vector_field="embedding",
                payload_fields=["text", "metadata"],
            )
            
            logger.info("Vector store configured")
            
        except Exception as e:
            logger.error(f"Failed to setup vector store: {e}")
            raise
    
    def run(self):
        """Run the complete compliance sentinel pipeline"""
        logger.info("Starting Live Wealth & Compliance Sentinel...")
        
        try:
            # 1. Setup data sources
            documents = self.setup_gdrive_source()
            market_data = self.setup_market_data_stream()
            
            # 2. Extract document metadata
            enriched_docs = self.extract_document_metadata(documents)
            
            # 3. Join documents with live market data
            joined_data = self.join_market_and_documents(enriched_docs, market_data)
            
            # 4. Detect compliance violations
            violations = self.detect_compliance_violations(joined_data, enriched_docs)
            
            # 5. Setup alerting system
            self.setup_alert_system(violations)
            
            # 6. Setup semantic search (embeddings + vector store)
            embedded_chunks = self.setup_embeddings(enriched_docs)
            self.setup_vector_store(embedded_chunks)
            
            logger.info("Compliance Sentinel initialized successfully")
            
            # Run Pathway computation
            pw.run(
                monitoring_level=pw.MonitoringLevel.ALL,
                persistence_backend=pw.persistence.Backend.filesystem(
                    os.getenv("PATHWAY_PERSISTENT_STORAGE", "./pathway_storage")
                ),
            )
            
        except KeyboardInterrupt:
            logger.info("Sentinel stopped by user")
        except Exception as e:
            logger.error(f"Sentinel error: {e}", exc_info=True)
            raise


def main():
    """Main entry point"""
    
    gdrive_credentials = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS",
        "/app/credentials/google-credentials.json"
    )
    gdrive_folder_id = os.getenv("GDRIVE_FOLDER_ID")
    
    if not gdrive_folder_id:
        raise ValueError("GDRIVE_FOLDER_ID environment variable required")
    
    if not os.path.exists(gdrive_credentials):
        raise FileNotFoundError(f"Google credentials not found at {gdrive_credentials}")
    
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY required")
    
    sentinel = ComplianceSentinel(
        gdrive_credentials_path=gdrive_credentials,
        gdrive_folder_id=gdrive_folder_id,
    )
    
    sentinel.run()


if __name__ == "__main__":
    main()