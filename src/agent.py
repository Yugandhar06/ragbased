"""
LangGraph Agent for Agentic RAG with multi-step reasoning
"""

import os
from typing import TypedDict, Annotated, Sequence, List, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
import operator
import logging

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State for the RAG agent"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    question: str
    retrieved_docs: List[Dict[str, Any]]
    reasoning_steps: List[str]
    answer: str
    should_retrieve: bool
    should_reason: bool


class RAGAgent:
    """LangGraph-based RAG Agent with multi-step reasoning"""
    
    def __init__(
        self,
        vector_search,
        model_name: str = "gpt-4-turbo-preview",
        temperature: float = 0.0,
    ):
        self.vector_search = vector_search
        self.model_name = model_name
        self.temperature = temperature
        
        # Initialize LLM
        self.llm = self._initialize_llm()
        
        # Build agent graph
        self.graph = self._build_graph()
        
        logger.info(f"RAG Agent initialized with model: {model_name}")
    
    def _initialize_llm(self):
        """Initialize the language model"""
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
        """Build the LangGraph agent workflow"""
        
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("analyze_query", self._analyze_query)
        workflow.add_node("retrieve_documents", self._retrieve_documents)
        workflow.add_node("reason_and_plan", self._reason_and_plan)
        workflow.add_node("generate_answer", self._generate_answer)
        
        # Define edges
        workflow.set_entry_point("analyze_query")
        
        workflow.add_conditional_edges(
            "analyze_query",
            self._should_retrieve,
            {
                True: "retrieve_documents",
                False: "generate_answer",
            }
        )
        
        workflow.add_conditional_edges(
            "retrieve_documents",
            self._should_reason,
            {
                True: "reason_and_plan",
                False: "generate_answer",
            }
        )
        
        workflow.add_edge("reason_and_plan", "generate_answer")
        workflow.add_edge("generate_answer", END)
        
        return workflow.compile()
    
    def _analyze_query(self, state: AgentState) -> AgentState:
        """Analyze the user query to determine approach"""
        
        question = state["question"]
        
        # Use LLM to analyze query complexity
        analysis_prompt = f"""Analyze this question and determine:
1. Does it require retrieving information from documents? (yes/no)
2. Is it a complex question requiring multi-step reasoning? (yes/no)

Question: {question}

Respond in this format:
RETRIEVE: yes/no
REASON: yes/no
"""
        
        response = self.llm.invoke([HumanMessage(content=analysis_prompt)])
        analysis_text = response.content.lower()
        
        should_retrieve = "retrieve: yes" in analysis_text
        should_reason = "reason: yes" in analysis_text
        
        state["should_retrieve"] = should_retrieve
        state["should_reason"] = should_reason
        state["reasoning_steps"] = [
            f"Query Analysis: Retrieve={should_retrieve}, Complex Reasoning={should_reason}"
        ]
        
        logger.info(f"Query analyzed: retrieve={should_retrieve}, reason={should_reason}")
        
        return state
    
    def _retrieve_documents(self, state: AgentState) -> AgentState:
        """Retrieve relevant documents from vector store"""
        
        question = state["question"]
        
        try:
            # Perform vector search
            results = self.vector_search.search(
                query=question,
                top_k=5,
                score_threshold=0.7,
            )
            
            state["retrieved_docs"] = results
            state["reasoning_steps"].append(
                f"Retrieved {len(results)} relevant documents from knowledge base"
            )
            
            logger.info(f"Retrieved {len(results)} documents")
            
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            state["retrieved_docs"] = []
            state["reasoning_steps"].append(
                f"Document retrieval failed: {str(e)}"
            )
        
        return state
    
    def _reason_and_plan(self, state: AgentState) -> AgentState:
        """Perform multi-step reasoning on retrieved documents"""
        
        question = state["question"]
        docs = state["retrieved_docs"]
        
        # Create context from retrieved documents
        context = "\n\n".join([
            f"Document {i+1} (Score: {doc['score']:.3f}):\n{doc['text']}"
            for i, doc in enumerate(docs)
        ])
        
        reasoning_prompt = f"""You are analyzing documents to answer a question.
Break down your reasoning into clear steps.

Context from documents:
{context}

Question: {question}

Provide a step-by-step reasoning process:
1. What are the key points from the documents?
2. How do they relate to the question?
3. What conclusion can be drawn?
"""
        
        response = self.llm.invoke([HumanMessage(content=reasoning_prompt)])
        reasoning_text = response.content
        
        # Extract reasoning steps
        steps = [
            line.strip() 
            for line in reasoning_text.split('\n') 
            if line.strip() and any(line.strip().startswith(f"{i}.") for i in range(1, 10))
        ]
        
        state["reasoning_steps"].extend(steps if steps else [reasoning_text])
        
        logger.info("Multi-step reasoning completed")
        
        return state
    
    def _generate_answer(self, state: AgentState) -> AgentState:
        """Generate final answer based on analysis"""
        
        question = state["question"]
        docs = state.get("retrieved_docs", [])
        reasoning = state.get("reasoning_steps", [])
        
        if docs:
            # Answer based on retrieved documents
            context = "\n\n".join([
                f"Source {i+1}:\n{doc['text']}"
                for i, doc in enumerate(docs)
            ])
            
            prompt = f"""Answer the question based on the provided context.
Be specific and cite the sources when relevant.
If the context doesn't contain enough information, say so.

Context:
{context}

Question: {question}

Answer:"""
        else:
            # Answer without retrieval
            prompt = f"""Answer the following question to the best of your knowledge.
If you're not certain about the answer, say so.

Question: {question}

Answer:"""
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        answer = response.content
        
        state["answer"] = answer
        state["reasoning_steps"].append("Generated final answer based on analysis")
        
        logger.info("Answer generated")
        
        return state
    
    def _should_retrieve(self, state: AgentState) -> bool:
        """Determine if document retrieval is needed"""
        return state.get("should_retrieve", True)
    
    def _should_reason(self, state: AgentState) -> bool:
        """Determine if complex reasoning is needed"""
        # Allow reasoning even without docs if user explicitly requested it
        return state.get("should_reason", True)
    
    def query(
        self,
        question: str,
        top_k: int = 5,
        score_threshold: float = 0.7,
        use_reasoning: bool = True,
    ) -> Dict[str, Any]:
        """
        Process a query through the agent
        
        Args:
            question: User question
            top_k: Number of documents to retrieve
            score_threshold: Minimum relevance score
            use_reasoning: Whether to use multi-step reasoning
        
        Returns:
            Dictionary with answer, sources, and reasoning steps
        """
        
        # Initialize state
        initial_state = {
            "messages": [HumanMessage(content=question)],
            "question": question,
            "retrieved_docs": [],
            "reasoning_steps": [],
            "answer": "",
            "should_retrieve": True,
            "should_reason": use_reasoning,
        }
        
        # Run the graph
        try:
            final_state = self.graph.invoke(initial_state)
            
            return {
                "answer": final_state.get("answer", "Unable to generate answer"),
                "sources": final_state.get("retrieved_docs", []),
                "reasoning_steps": final_state.get("reasoning_steps", []),
                "success": True,
            }
            
        except Exception as e:
            logger.error(f"Error in agent query: {e}", exc_info=True)
            return {
                "answer": f"I apologize, but I encountered an error: {str(e)}",
                "sources": [],
                "reasoning_steps": [f"Error: {str(e)}"],
                "success": False,
            }