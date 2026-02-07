"""
Fallback Chatbot for AURA - Used when Vector Store Initialization Fails

This chatbot provides a graceful degradation path when:
- Vector store creation fails
- No analysis data is available
- RAG initialization encounters errors

Instead of failing completely, it generates responses directly from papers
using domain knowledge and LLM reasoning.
"""

from typing import Dict, Any, List, Optional
import json
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict
from ..utils.config import OPENAI_API_KEY, GPT_MODEL, ANALYSIS_DIR
import logging

logger = logging.getLogger('aura.rag')


class FallbackChatState(TypedDict):
    """State for fallback chat conversation"""
    messages: List
    context: str
    query: str
    response: str
    language: str
    papers_summary: str


class FallbackChatbot:
    """
    Fallback chatbot that operates WITHOUT vector store.

    When vector store fails, this bot:
    1. Reads papers directly from session data
    2. Creates a text-based summary of papers
    3. Uses LLM to answer questions based on this summary
    4. Maintains conversation history

    This ensures the user always gets SOMETHING instead of complete failure.
    """

    def __init__(self, session_id: str, papers: List[Dict[str, Any]] = None):
        """
        Initialize fallback chatbot

        Args:
            session_id: Research session ID
            papers: List of papers to use for context (optional)
        """
        self.session_id = session_id
        self.papers = papers or []
        self.papers_summary = self._create_papers_summary()

        logger.warning(
            f"[FallbackChatbot] Initialized for session {session_id}. "
            f"Vector store unavailable. Using {len(self.papers)} papers for context."
        )

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=GPT_MODEL,
            api_key=OPENAI_API_KEY,
            temperature=0.7
        )

        # Initialize memory
        self.memory = MemorySaver()

        # Build workflow
        self.graph = self._build_graph()

    def _create_papers_summary(self) -> str:
        """
        Create a text summary of all papers for context.

        Returns:
            Formatted summary of papers
        """
        if not self.papers:
            return "No papers available for context."

        summary_parts = []
        for i, paper in enumerate(self.papers, 1):
            title = paper.get("title", "Unknown Title")
            snippet = paper.get("snippet", "No abstract available")
            pub_info = paper.get("publication_info", {})
            publication = pub_info.get("publication", "Unknown")
            citation_count = paper.get("cited_by", {}).get("total", 0)

            paper_text = (
                f"[Paper {i}] {title}\n"
                f"Published in: {publication}\n"
                f"Summary: {snippet[:500]}...\n"
                f"Citations: {citation_count}\n"
            )
            summary_parts.append(paper_text)

        return "\n---\n".join(summary_parts)

    def _build_graph(self) -> StateGraph:
        """
        Build LangGraph workflow

        Returns:
            Compiled state graph
        """
        workflow = StateGraph(FallbackChatState)

        # Add single node (no retrieval needed)
        workflow.add_node("generate_response", self._generate_response_node)

        # Simple workflow
        workflow.set_entry_point("generate_response")
        workflow.add_edge("generate_response", END)

        # Compile with memory
        return workflow.compile(checkpointer=self.memory)

    async def _generate_response_node(self, state: FallbackChatState) -> FallbackChatState:
        """
        Generate response using LLM with paper summaries.

        Args:
            state: Current chat state

        Returns:
            Updated state with response
        """
        language = state.get("language", "English")

        language_instructions = {
            "English": "",
            "French": "\n\nIMPORTANT: Respond ENTIRELY in French.",
            "Chinese": "\n\nIMPORTANT: Respond ENTIRELY in Simplified Chinese.",
            "Russian": "\n\nIMPORTANT: Respond ENTIRELY in Russian."
        }

        language_instruction = language_instructions.get(language, "")

        # Create prompt with paper summaries instead of RAG context
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are AURA, an AI research assistant specializing in academic research.

IMPORTANT: The vector store is currently unavailable, so you are using direct paper summaries.
Despite this limitation, provide comprehensive, accurate responses based on the available papers.

Use this exact response structure for EVERY response:

## 📌 Direct Answer
[Provide a concise answer to the user's question in 1-3 sentences.]

## 🔍 Key Insights
• [Key insight 1 from the papers]
• [Key insight 2 from the papers]
• [Key insight 3 from the papers]

## 📚 Supporting Evidence
[Provide specific details, data, or findings from the papers listed below.]

## 💡 Context & Connections
[Explain how findings relate and broader implications.]

## ⚠️ Important Notes
[Include limitations or caveats from the research.]

## 🎯 Suggested Follow-ups
[Suggest 2-3 related questions the user might explore.]

AVAILABLE RESEARCH MATERIALS:
{self.papers_summary}

GUIDELINES:
✓ Use the paper summaries above as your context
✓ Be specific - cite actual findings, data, or claims from papers
✓ Follow the structure exactly
✓ Be honest about limitations
✗ Don't make up information not in the papers
✗ Don't skip response sections{language_instruction}

Remember: Even though vector store is unavailable, these papers represent
the full research material available. Answer thoroughly based on them."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{query}")
        ])

        chat_history = state.get("messages", [])
        chain = prompt | self.llm

        response = await chain.ainvoke({
            "chat_history": chat_history[:-1] if chat_history else [],
            "query": state["query"]
        })

        state["response"] = response.content
        return state

    async def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        language: str = "English"
    ) -> Dict[str, Any]:
        """
        Process chat message and return response

        Args:
            message: User message
            conversation_id: Optional conversation ID
            language: Response language

        Returns:
            Response dictionary
        """
        initial_state: FallbackChatState = {
            "messages": [HumanMessage(content=message)],
            "context": "Using paper summaries (vector store unavailable)",
            "query": message,
            "response": "",
            "language": language,
            "papers_summary": self.papers_summary
        }

        config = {
            "configurable": {
                "thread_id": conversation_id or "default"
            }
        }

        final_state = await self.graph.ainvoke(initial_state, config)

        return {
            "response": final_state["response"],
            "context_used": "Paper summaries (fallback mode)",
            "conversation_id": conversation_id or "default",
            "session_id": self.session_id,
            "fallback_mode": True,
            "papers_count": len(self.papers)
        }

    def get_conversation_history(self, conversation_id: str = "default") -> List[Dict[str, str]]:
        """Get conversation history"""
        try:
            config = {"configurable": {"thread_id": conversation_id}}
            state = self.memory.get(config)

            if not state or "messages" not in state:
                return []

            history = []
            for msg in state["messages"]:
                if isinstance(msg, HumanMessage):
                    history.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    history.append({"role": "assistant", "content": msg.content})

            return history
        except Exception as e:
            logger.warning(f"[FallbackChatbot] History error: {str(e)}")
            return []
