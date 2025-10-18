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

        # Initialize vector store
        if not self.vector_store_manager.load_vector_store(session_id):
            if not self.vector_store_manager.initialize_from_session(session_id):
                raise ValueError(f"Could not initialize vector store for session {session_id}")

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

        print(f"[RAGChatbot] Initialized for session: {session_id}")

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
        Generate response using GPT-4o with ReAct pattern

        Args:
            state: Current chat state with context

        Returns:
            Updated state with response
        """
        # Create ReAct-style prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are AURA, an AI research assistant. You help users understand research findings through conversational interaction.

Use the ReAct (Reasoning + Acting) framework:
1. THOUGHT: Analyze what the user is asking
2. ACTION: Retrieve relevant information from the research context
3. OBSERVATION: Identify key insights from the context
4. RESPONSE: Provide a clear, helpful answer

Guidelines:
- Be conversational and friendly
- Cite specific findings from the research when relevant
- If the context doesn't contain the answer, say so honestly
- Ask clarifying questions if needed
- Support follow-up and comparative questions

Context from research:
{context}"""),
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
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process chat message and return response

        Args:
            message: User message
            conversation_id: Optional conversation ID for memory

        Returns:
            Response dictionary
        """
        # Create initial state
        initial_state: ChatState = {
            "messages": [HumanMessage(content=message)],
            "context": "",
            "query": message,
            "response": ""
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
