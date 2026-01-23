"""
RAG Chatbot with LangGraph Memory for AURA
Uses GPT-4o with ReAct reasoning pattern
"""

from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict
from .vector_store import VectorStoreManager
from ..utils.config import OPENAI_API_KEY, GPT_MODEL


class ChatState(TypedDict):
    """State for chat conversation"""
    messages: List[BaseMessage]
    context: str
    query: str
    response: str
    language: str


class RAGChatbot:
    """
    RAG-enabled chatbot with LangGraph memory
    Uses ReAct pattern for reasoning
    """

    def __init__(self, session_id: str):
        """
        Initialize RAG chatbot

        Args:
            session_id: Research session ID for vector store
        """
        self.session_id = session_id
        self.vector_store_manager = VectorStoreManager()

        # Initialize vector store with detailed error messages
        print(f"[RAGChatbot] Attempting to initialize for session: {session_id}")

        # Try to load existing vector store
        if self.vector_store_manager.load_vector_store(session_id):
            print(f"[RAGChatbot] ✅ Loaded existing vector store for session {session_id}")
        else:
            # Try to create new vector store from session data
            print(f"[RAGChatbot] No existing vector store found. Attempting to create new one...")

            if self.vector_store_manager.initialize_from_session(session_id):
                print(f"[RAGChatbot] ✅ Created new vector store for session {session_id}")
            else:
                error_msg = (
                    f"Could not initialize RAG chatbot for session '{session_id}'.\n"
                    f"Possible causes:\n"
                    f"1. Research session data not found (check aura_research/storage/analysis/)\n"
                    f"2. No analyses in session data\n"
                    f"3. Vector store creation failed\n"
                    f"Please ensure the research session completed successfully."
                )
                print(f"[RAGChatbot] ❌ {error_msg}")
                raise ValueError(error_msg)

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=GPT_MODEL,
            api_key=OPENAI_API_KEY,
            temperature=0.7  # Slightly higher for conversational responses
        )

        # Initialize memory
        self.memory = MemorySaver()

        # Build LangGraph workflow
        self.graph = self._build_graph()

        print(f"[RAGChatbot] ✅ Fully initialized for session: {session_id}")

    def _build_graph(self) -> StateGraph:
        """
        Build LangGraph workflow with memory

        Returns:
            Compiled state graph
        """
        workflow = StateGraph(ChatState)

        # Add nodes
        workflow.add_node("retrieve_context", self._retrieve_context_node)
        workflow.add_node("generate_response", self._generate_response_node)

        # Define flow
        workflow.set_entry_point("retrieve_context")
        workflow.add_edge("retrieve_context", "generate_response")
        workflow.add_edge("generate_response", END)

        # Compile with memory
        return workflow.compile(checkpointer=self.memory)

    async def _retrieve_context_node(self, state: ChatState) -> ChatState:
        """
        Retrieve relevant context from vector store

        Args:
            state: Current chat state

        Returns:
            Updated state with context
        """
        query = state["query"]

        # Search vector store
        results = self.vector_store_manager.search_with_score(query, k=4)

        # Format context
        context_parts = []
        for doc, score in results:
            context_parts.append(f"[Relevance: {1-score:.2f}]\n{doc.page_content}\n")

        state["context"] = "\n---\n".join(context_parts) if context_parts else "No relevant context found."

        return state

    async def _generate_response_node(self, state: ChatState) -> ChatState:
        """
        Generate response using GPT-4o with ReAct pattern and structured template

        Args:
            state: Current chat state with context

        Returns:
            Updated state with response
        """
        # Get language from state (default to English)
        language = state.get("language", "English")

        # Language-specific instructions
        language_instructions = {
            "English": "",
            "French": "\n\nIMPORTANT: Respond ENTIRELY in French. All sections, headings, and content must be in French.",
            "Chinese": "\n\nIMPORTANT: Respond ENTIRELY in Simplified Chinese (简体中文). All sections, headings, and content must be in Chinese.",
            "Russian": "\n\nIMPORTANT: Respond ENTIRELY in Russian (Русский). All sections, headings, and content must be in Russian."
        }

        language_instruction = language_instructions.get(language, "")

        # Create ReAct-style prompt with comprehensive structured template
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are AURA, an AI research assistant. You help users understand research findings through comprehensive, structured responses.

Use the ReAct (Reasoning + Acting) framework internally:
1. THOUGHT: Analyze what the user is asking
2. ACTION: Retrieve relevant information from the research context
3. OBSERVATION: Identify key insights from the context
4. RESPONSE: Provide a structured, comprehensive answer

RESPONSE FORMAT - Use this exact structure for EVERY response:

## 📌 Direct Answer
[Provide a concise, direct answer to the user's question in 1-3 sentences. This should immediately address what they're asking.]

## 🔍 Key Insights
[Present the main findings as clear bullet points. Each point should be specific and actionable. Include 3-5 key insights from the research.]
• [Key insight 1]
• [Key insight 2]
• [Key insight 3]

## 📚 Supporting Evidence
[Provide specific details, data, methodologies, or findings from the research papers. Include citations when possible (author names, years, or paper titles from the context).]

## 💡 Context & Connections
[Explain relevant background, how different findings relate to each other, themes across papers, or broader implications. Help the user understand the "big picture".]

## ⚠️ Important Notes
[Include any limitations, caveats, conflicting findings, or nuances the user should be aware of. If information is missing, state it clearly.]

## 🎯 Suggested Follow-ups
[Suggest 2-3 related questions the user might want to explore based on the research. Make these specific and valuable.]

GUIDELINES:
✓ Always follow the structure above - use all sections
✓ Be specific and cite details from the research context
✓ Use clear, accessible language
✓ Make responses comprehensive but concise
✓ If context is insufficient for a section, say so honestly (e.g., "The research provided doesn't contain information about...")
✓ Use markdown formatting for readability
✗ Don't skip sections - include all parts of the template
✗ Don't be vague - use specific findings and data
✗ Don't make up information not in the context{language_instruction}

Context from research:
{{context}}"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{query}")
        ])

        # Get chat history
        chat_history = state.get("messages", [])

        # Generate response
        chain = prompt | self.llm
        response = await chain.ainvoke({
            "context": state["context"],
            "chat_history": chat_history[:-1] if chat_history else [],  # Exclude current message
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
            conversation_id: Optional conversation ID for memory
            language: Response language (English, French, Chinese, Russian)

        Returns:
            Response dictionary
        """
        # Create initial state
        initial_state: ChatState = {
            "messages": [HumanMessage(content=message)],
            "context": "",
            "query": message,
            "response": "",
            "language": language
        }

        # Configure for conversation tracking
        config = {
            "configurable": {
                "thread_id": conversation_id or "default"
            }
        }

        # Execute graph
        final_state = await self.graph.ainvoke(initial_state, config)

        # Prepare response
        return {
            "response": final_state["response"],
            "context_used": final_state["context"],
            "conversation_id": conversation_id or "default",
            "session_id": self.session_id
        }

    def get_conversation_history(self, conversation_id: str = "default") -> List[Dict[str, str]]:
        """
        Get conversation history

        Args:
            conversation_id: Conversation ID

        Returns:
            List of message dictionaries
        """
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
            print(f"[RAGChatbot] History error: {str(e)}")
            return []


# Singleton pattern for chatbot instances
_chatbot_instances: Dict[str, RAGChatbot] = {}


def get_chatbot(session_id: str) -> RAGChatbot:
    """
    Get or create chatbot instance for session

    Args:
        session_id: Research session ID

    Returns:
        RAGChatbot instance
    """
    if session_id not in _chatbot_instances:
        _chatbot_instances[session_id] = RAGChatbot(session_id)

    return _chatbot_instances[session_id]


def clear_chatbot(session_id: str):
    """
    Clear chatbot instance

    Args:
        session_id: Research session ID
    """
    if session_id in _chatbot_instances:
        del _chatbot_instances[session_id]
