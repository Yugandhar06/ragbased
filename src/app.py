"""
Streamlit UI with LangGraph Agentic RAG
"""

import streamlit as st
import os
from typing import List, Dict, Any
import json
from datetime import datetime

# Import agent components
from src.agent import RAGAgent
from src.vector_search import VectorSearch

# Page configuration
st.set_page_config(
    page_title="Real-Time RAG System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .message-user {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .message-assistant {
        background-color: #f5f5f5;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .source-card {
        background-color: #fff3e0;
        padding: 0.8rem;
        border-radius: 5px;
        margin: 0.3rem 0;
        border-left: 3px solid #ff9800;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "agent" not in st.session_state:
        st.session_state.agent = None
    
    if "vector_search" not in st.session_state:
        st.session_state.vector_search = None
    
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")


def initialize_components():
    """Initialize RAG components"""
    if st.session_state.agent is None:
        with st.spinner("Initializing AI Agent..."):
            try:
                # Initialize vector search
                st.session_state.vector_search = VectorSearch(
                    qdrant_host=os.getenv("QDRANT_HOST", "qdrant"),
                    qdrant_port=int(os.getenv("QDRANT_PORT", "6333")),
                    collection_name="rag_documents",
                )
                
                # Initialize LangGraph agent
                st.session_state.agent = RAGAgent(
                    vector_search=st.session_state.vector_search,
                    model_name=st.session_state.get("model_name", "gpt-4-turbo-preview"),
                )
                
                st.success("✅ System initialized successfully!")
                
            except Exception as e:
                st.error(f"Failed to initialize system: {str(e)}")
                st.stop()


def render_sidebar():
    """Render sidebar with settings"""
    with st.sidebar:
        st.markdown("## ⚙️ Configuration")
        
        # Model selection
        model_options = {
            "GPT-4 Turbo": "gpt-4-turbo-preview",
            "GPT-4": "gpt-4",
            "Claude 3 Opus": "claude-3-opus-20240229",
            "Claude 3 Sonnet": "claude-3-sonnet-20240229",
        }
        
        selected_model = st.selectbox(
            "AI Model",
            options=list(model_options.keys()),
            index=0,
        )
        st.session_state.model_name = model_options[selected_model]
        
        st.markdown("---")
        
        # RAG settings
        st.markdown("### 🔍 Search Settings")
        
        st.session_state.top_k = st.slider(
            "Number of sources",
            min_value=1,
            max_value=10,
            value=5,
            help="Number of document chunks to retrieve"
        )
        
        st.session_state.score_threshold = st.slider(
            "Relevance threshold",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.05,
            help="Minimum similarity score for retrieved documents"
        )
        
        st.markdown("---")
        
        # Agent settings
        st.markdown("### 🤖 Agent Settings")
        
        st.session_state.use_reasoning = st.checkbox(
            "Enable multi-step reasoning",
            value=True,
            help="Allow agent to break down complex queries"
        )
        
        st.session_state.show_reasoning = st.checkbox(
            "Show agent reasoning",
            value=True,
            help="Display agent's thought process"
        )
        
        st.markdown("---")
        
        # System status
        st.markdown("### 📊 System Status")
        
        if st.session_state.agent:
            st.success("🟢 Agent: Ready")
        else:
            st.warning("🟡 Agent: Initializing...")
        
        if st.session_state.vector_search:
            try:
                count = st.session_state.vector_search.get_collection_size()
                st.info(f"📚 Documents indexed: {count}")
            except:
                st.error("🔴 Vector DB: Disconnected")
        
        st.markdown("---")
        
        # Clear conversation
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.rerun()


def render_message(role: str, content: str, sources: List[Dict] = None, reasoning: List[str] = None):
    """Render a chat message"""
    
    if role == "user":
        st.markdown(f"""
        <div class="message-user">
            <strong>You:</strong><br>{content}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="message-assistant">
            <strong>Assistant:</strong><br>{content}
        </div>
        """, unsafe_allow_html=True)
        
        # Show reasoning steps if available
        if reasoning and st.session_state.get("show_reasoning", True):
            with st.expander("🧠 Agent Reasoning", expanded=False):
                for i, step in enumerate(reasoning, 1):
                    st.markdown(f"**Step {i}:** {step}")
        
        # Show sources if available
        if sources:
            with st.expander(f"📚 Sources ({len(sources)})", expanded=False):
                for i, source in enumerate(sources, 1):
                    st.markdown(f"""
                    <div class="source-card">
                        <strong>Source {i}</strong> (Score: {source.get('score', 0):.3f})<br>
                        <small><em>{source.get('metadata', {}).get('source', 'Unknown')}</em></small><br>
                        {source.get('text', '')[:300]}...
                    </div>
                    """, unsafe_allow_html=True)


def main():
    """Main application"""
    
    # Initialize
    initialize_session_state()
    
    # Header
    st.markdown('<div class="main-header">🤖 Real-Time RAG System</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Powered by Pathway + LangGraph</div>', unsafe_allow_html=True)
    
    # Sidebar
    render_sidebar()
    
    # Initialize components
    initialize_components()
    
    # Main chat interface
    chat_container = st.container()
    
    with chat_container:
        # Display chat history
        for message in st.session_state.messages:
            render_message(
                role=message["role"],
                content=message["content"],
                sources=message.get("sources"),
                reasoning=message.get("reasoning")
            )
    
    # Chat input
    user_input = st.chat_input("Ask a question about your documents...")
    
    if user_input:
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat()
        })
        
        # Get agent response
        with st.spinner("🤔 Thinking..."):
            try:
                response = st.session_state.agent.query(
                    question=user_input,
                    top_k=st.session_state.get("top_k", 5),
                    score_threshold=st.session_state.get("score_threshold", 0.7),
                    use_reasoning=st.session_state.get("use_reasoning", True),
                )
                
                # Add assistant message
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response["answer"],
                    "sources": response.get("sources", []),
                    "reasoning": response.get("reasoning_steps", []),
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                st.error(f"Error processing query: {str(e)}")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"I apologize, but I encountered an error: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                })
        
        if user_input:
            st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "Real-Time RAG System | Monitoring Google Drive for updates"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()