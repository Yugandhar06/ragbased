"""
LangGraph Compliance Agent with Multi-Step Reasoning
Analyzes violations, checks portfolio impact, drafts alerts
"""

import os
from typing import TypedDict, Annotated, Sequence, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END
import operator
import logging
import json
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


class ComplianceAgentState(TypedDict):
    """State for compliance reasoning agent"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    alert_data: Dict[str, Any]
    portfolio_data: Dict[str, Any]
    violation_analysis: str
    impact_assessment: str
    recommended_actions: List[str]
    email_draft: str
    should_escalate: bool
    reasoning_steps: List[str]


class ComplianceAgent:
    """LangGraph agent for compliance analysis and alerting"""
    
    def __init__(
        self,
        model_name: str = "gpt-4-turbo-preview",
        temperature: float = 0.0,
    ):
        self.model_name = model_name
        self.temperature = temperature
        self.llm = self._initialize_llm()
        self.graph = self._build_graph()
        
        # Email configuration - avoid storing sensitive data directly
        self._smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self._smtp_port = int(os.getenv("SMTP_PORT", 587))
        self._smtp_user = os.getenv("SMTP_USER")
        # Password retrieved at send time, not stored in memory
        self.alert_email = os.getenv("ALERT_EMAIL")
        
        logger.info(f"Compliance Agent initialized with {model_name}")
    
    def _initialize_llm(self):
        """Initialize language model"""
        if "gpt" in self.model_name.lower():
            return ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                openai_api_key=os.getenv("OPENAI_API_KEY"),
            )
        elif "claude" in self.model_name.lower():
            return ChatAnthropic(
                model=self.model_name,
                temperature=self.temperature,
                anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            )
        else:
            raise ValueError(f"Unsupported model: {self.model_name}")
    
    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow for compliance analysis"""
        
        workflow = StateGraph(ComplianceAgentState)
        
        # Add nodes
        workflow.add_node("analyze_violation", self._analyze_violation)
        workflow.add_node("assess_portfolio_impact", self._assess_portfolio_impact)
        workflow.add_node("generate_recommendations", self._generate_recommendations)
        workflow.add_node("draft_alert_email", self._draft_alert_email)
        workflow.add_node("send_alert", self._send_alert)
        
        # Define workflow
        workflow.set_entry_point("analyze_violation")
        workflow.add_edge("analyze_violation", "assess_portfolio_impact")
        workflow.add_edge("assess_portfolio_impact", "generate_recommendations")
        workflow.add_edge("generate_recommendations", "draft_alert_email")
        
        workflow.add_conditional_edges(
            "draft_alert_email",
            self._should_send_alert,
            {
                True: "send_alert",
                False: END,
            }
        )
        
        workflow.add_edge("send_alert", END)
        
        return workflow.compile()
    
    def _analyze_violation(self, state: ComplianceAgentState) -> ComplianceAgentState:
        """Analyze the compliance violation in detail"""
        
        alert_data = state["alert_data"]
        
        analysis_prompt = f"""You are a compliance officer analyzing a potential violation.

Alert Data:
- Type: {alert_data.get('alert_type')}
- Severity: {alert_data.get('severity')}
- Message: {alert_data.get('message')}
- Affected Assets: {', '.join(alert_data.get('affected_assets', []))}
- Triggered By: {json.dumps(alert_data.get('triggered_by', {}), indent=2)}

Provide a detailed analysis:
1. What is the nature of this violation?
2. What regulation or policy does it potentially breach?
3. What are the immediate concerns?
4. What additional information is needed?

Analysis:"""
        
        response = self.llm.invoke([HumanMessage(content=analysis_prompt)])
        analysis = response.content
        
        state["violation_analysis"] = analysis
        state["reasoning_steps"] = [f"Violation Analysis: {analysis[:200]}..."]
        
        logger.info("Violation analysis completed")
        return state
    
    def _assess_portfolio_impact(self, state: ComplianceAgentState) -> ComplianceAgentState:
        """Assess impact on the portfolio"""
        
        alert_data = state["alert_data"]
        portfolio_data = state.get("portfolio_data", {})
        violation_analysis = state["violation_analysis"]
        
        # Calculate portfolio exposure
        affected_symbols = alert_data.get("affected_assets", [])
        total_exposure = 0
        position_details = []
        
        for symbol in affected_symbols:
            position = portfolio_data.get("positions", {}).get(symbol, {})
            if position:
                exposure = position.get("market_value", 0) / portfolio_data.get("total_value", 1)
                total_exposure += exposure
                position_details.append({
                    "symbol": symbol,
                    "shares": position.get("shares", 0),
                    "market_value": position.get("market_value", 0),
                    "exposure": f"{exposure * 100:.2f}%"
                })
        
        impact_prompt = f"""You are assessing the portfolio impact of a compliance violation.

Violation Analysis:
{violation_analysis}

Portfolio Data:
- Total Portfolio Value: ${portfolio_data.get('total_value', 0):,.2f}
- Affected Positions: {len(position_details)}
- Total Exposure to Affected Assets: {total_exposure * 100:.2f}%

Position Details:
{json.dumps(position_details, indent=2)}

Assess the impact:
1. How material is this violation to the portfolio?
2. What is the risk exposure?
3. Could this trigger additional regulatory concerns?
4. What is the potential financial impact?

Impact Assessment:"""
        
        response = self.llm.invoke([HumanMessage(content=impact_prompt)])
        impact_assessment = response.content
        
        state["impact_assessment"] = impact_assessment
        state["reasoning_steps"].append(f"Impact: {total_exposure * 100:.2f}% portfolio exposure")
        
        logger.info(f"Impact assessment completed: {total_exposure * 100:.2f}% exposure")
        return state
    
    def _generate_recommendations(self, state: ComplianceAgentState) -> ComplianceAgentState:
        """Generate actionable recommendations"""
        
        violation_analysis = state["violation_analysis"]
        impact_assessment = state["impact_assessment"]
        alert_data = state["alert_data"]
        
        recommendation_prompt = f"""Based on the violation analysis and impact assessment, generate specific, actionable recommendations.

Violation: {alert_data.get('alert_type')}
Severity: {alert_data.get('severity')}

Analysis:
{violation_analysis}

Impact:
{impact_assessment}

Generate 3-5 specific recommendations with:
1. Immediate actions (within 24 hours)
2. Short-term actions (within 1 week)
3. Long-term preventive measures

Format as a numbered list.

Recommendations:"""
        
        response = self.llm.invoke([HumanMessage(content=recommendation_prompt)])
        recommendations_text = response.content
        
        # Parse recommendations into list
        recommendations = [
            line.strip() 
            for line in recommendations_text.split('\n') 
            if line.strip() and any(line.strip().startswith(f"{i}.") for i in range(1, 20))
        ]
        
        state["recommended_actions"] = recommendations
        state["reasoning_steps"].append(f"Generated {len(recommendations)} recommendations")
        
        # Determine if escalation needed
        severity = alert_data.get("severity", "LOW")
        state["should_escalate"] = severity in ["CRITICAL", "HIGH"]
        
        logger.info(f"Generated {len(recommendations)} recommendations")
        return state
    
    def _draft_alert_email(self, state: ComplianceAgentState) -> ComplianceAgentState:
        """Draft professional alert email"""
        
        alert_data = state["alert_data"]
        violation_analysis = state["violation_analysis"]
        impact_assessment = state["impact_assessment"]
        recommendations = state["recommended_actions"]
        
        email_prompt = f"""Draft a professional compliance alert email.

Alert Type: {alert_data.get('alert_type')}
Severity: {alert_data.get('severity')}
Affected Assets: {', '.join(alert_data.get('affected_assets', []))}

Violation Analysis:
{violation_analysis}

Impact Assessment:
{impact_assessment}

Recommended Actions:
{chr(10).join(recommendations)}

Draft an email with:
- Subject line (marked URGENT if severity is CRITICAL/HIGH)
- Professional greeting
- Clear summary of the issue
- Key findings
- Recommended actions
- Call to action
- Professional closing

Email:"""
        
        response = self.llm.invoke([HumanMessage(content=email_prompt)])
        email_draft = response.content
        
        state["email_draft"] = email_draft
        state["reasoning_steps"].append("Email draft completed")
        
        logger.info("Alert email drafted")
        return state
    
    def _send_alert(self, state: ComplianceAgentState) -> ComplianceAgentState:
        """Send alert email if configured"""
        
        if not self.alert_email or not self.smtp_config.get("user"):
            logger.warning("Email not configured, skipping send")
            state["reasoning_steps"].append("Email sending skipped (not configured)")
            return state
        
        try:
            alert_data = state["alert_data"]
            email_draft = state["email_draft"]
            
            # Extract subject from email draft
            lines = email_draft.split('\n')
            subject = lines[0].replace("Subject:", "").strip() if lines else "Compliance Alert"
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config["user"]
            msg['To'] = self.alert_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(email_draft, 'plain'))
            
            # Send email - retrieve password only at send time
            smtp_password = os.getenv("SMTP_PASSWORD")
            with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
                server.starttls()
                server.login(self._smtp_user, smtp_password)
                server.send_message(msg)
            
            logger.info(f"Alert email sent to {self.alert_email}")
            state["reasoning_steps"].append(f"Alert email sent successfully")
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            state["reasoning_steps"].append(f"Email sending failed: {str(e)}")
        
        return state
    
    def _should_send_alert(self, state: ComplianceAgentState) -> bool:
        """Determine if alert should be sent"""
        return state.get("should_escalate", False)
    
    def process_alert(
        self,
        alert_data: Dict[str, Any],
        portfolio_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process compliance alert through reasoning workflow"""
        
        initial_state = {
            "messages": [],
            "alert_data": alert_data,
            "portfolio_data": portfolio_data or {},
            "violation_analysis": "",
            "impact_assessment": "",
            "recommended_actions": [],
            "email_draft": "",
            "should_escalate": False,
            "reasoning_steps": [],
        }
        
        try:
            final_state = self.graph.invoke(initial_state)
            
            return {
                "violation_analysis": final_state.get("violation_analysis", ""),
                "impact_assessment": final_state.get("impact_assessment", ""),
                "recommended_actions": final_state.get("recommended_actions", []),
                "email_draft": final_state.get("email_draft", ""),
                "should_escalate": final_state.get("should_escalate", False),
                "reasoning_steps": final_state.get("reasoning_steps", []),
                "success": True,
            }
            
        except Exception as e:
            logger.error(f"Error processing alert: {e}", exc_info=True)
            return {
                "error": str(e),
                "success": False,
            }