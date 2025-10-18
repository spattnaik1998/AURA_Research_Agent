"""
FAISS Vector Store Manager for AURA RAG System
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from ..utils.config import OPENAI_API_KEY, EMBEDDING_MODEL, VECTOR_STORE_DIR, ANALYSIS_DIR
import os


class VectorStoreManager:
    """
    Manages FAISS vector store for RAG chatbot
    Handles document indexing and retrieval
    """

    def __init__(self, session_id: Optional[str] = None):
        """
        Initialize vector store manager

        Args:
            session_id: Research session ID to load specific results
        """
        self.session_id = session_id
        self.embeddings = OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            api_key=OPENAI_API_KEY
        )
        self.vector_store: Optional[FAISS] = None

    def initialize_from_session(self, session_id: str) -> bool:
        """
        Initialize vector store from a research session

        Args:
            session_id: Research session ID

        Returns:
            True if successful, False otherwise
        """
        try:
            # Load research results
            analysis_file = Path(ANALYSIS_DIR) / f"research_{session_id}.json"

            if not analysis_file.exists():
                print(f"[VectorStore] Session file not found: {analysis_file}")
                return False

            with open(analysis_file, 'r', encoding='utf-8') as f:
                research_data = json.load(f)

            # Extract documents from analyses
            documents = self._create_documents_from_analyses(
                research_data.get('analyses', []),
                research_data.get('essay', ''),
                research_data.get('query', '')
            )

            if not documents:
                print("[VectorStore] No documents to index")
                return False

            # Create vector store
            self.vector_store = FAISS.from_documents(
                documents,
                self.embeddings
            )

            # Save vector store
            self._save_vector_store(session_id)

            print(f"[VectorStore] Initialized with {len(documents)} documents")
            return True

        except Exception as e:
            print(f"[VectorStore] Initialization error: {str(e)}")
            return False

    def _create_documents_from_analyses(
        self,
        analyses: List[Dict[str, Any]],
        essay: str,
        query: str
    ) -> List[Document]:
        """
        Create LangChain documents from research analyses

        Args:
            analyses: List of paper analyses
            essay: Generated essay text
            query: Research query

        Returns:
            List of Document objects
        """
        documents = []

        # Add essay as primary document
        if essay:
            # Split essay into sections
            sections = self._split_essay(essay)
            for i, section in enumerate(sections):
                documents.append(Document(
                    page_content=section,
                    metadata={
                        "type": "essay_section",
                        "section_index": i,
                        "query": query
                    }
                ))

        # Add individual paper analyses
        for i, analysis in enumerate(analyses):
            # Create document from summary and key points
            content = self._format_analysis_content(analysis)

            documents.append(Document(
                page_content=content,
                metadata={
                    "type": "paper_analysis",
                    "paper_index": i,
                    "title": analysis.get("metadata", {}).get("core_ideas", [""])[0] if analysis.get("metadata") else "",
                    "relevance_score": analysis.get("metadata", {}).get("relevance_score", 0),
                    "query": query
                }
            ))

        print(f"[VectorStore] Created {len(documents)} documents from analyses")
        return documents

    def _split_essay(self, essay: str) -> List[str]:
        """Split essay into sections for better retrieval"""
        # Split by markdown headers
        sections = []
        current_section = []

        for line in essay.split('\n'):
            if line.startswith('##') and current_section:
                sections.append('\n'.join(current_section))
                current_section = [line]
            else:
                current_section.append(line)

        if current_section:
            sections.append('\n'.join(current_section))

        return [s for s in sections if len(s.strip()) > 100]  # Filter short sections

    def _format_analysis_content(self, analysis: Dict[str, Any]) -> str:
        """
        Format analysis into searchable text

        Args:
            analysis: Analysis dictionary

        Returns:
            Formatted text content
        """
        parts = []

        # Add summary
        if "summary" in analysis:
            parts.append(f"Summary: {analysis['summary']}")

        # Add key points
        if "key_points" in analysis:
            parts.append("Key Points:")
            for point in analysis['key_points']:
                parts.append(f"- {point}")

        # Add metadata insights
        metadata = analysis.get("metadata", {})
        if metadata.get("core_ideas"):
            parts.append(f"\nCore Ideas: {', '.join(metadata['core_ideas'])}")

        if metadata.get("key_findings"):
            parts.append(f"Key Findings: {', '.join(metadata['key_findings'])}")

        if metadata.get("methodology"):
            parts.append(f"Methodology: {metadata['methodology']}")

        return '\n'.join(parts)

    def search(self, query: str, k: int = 4) -> List[Document]:
        """
        Search vector store for relevant documents

        Args:
            query: Search query
            k: Number of results to return

        Returns:
            List of relevant documents
        """
        if not self.vector_store:
            return []

        try:
            results = self.vector_store.similarity_search(query, k=k)
            return results
        except Exception as e:
            print(f"[VectorStore] Search error: {str(e)}")
            return []

    def search_with_score(self, query: str, k: int = 4) -> List[tuple]:
        """
        Search with relevance scores

        Args:
            query: Search query
            k: Number of results

        Returns:
            List of (document, score) tuples
        """
        if not self.vector_store:
            return []

        try:
            results = self.vector_store.similarity_search_with_score(query, k=k)
            return results
        except Exception as e:
            print(f"[VectorStore] Search error: {str(e)}")
            return []

    def _save_vector_store(self, session_id: str):
        """Save vector store to disk"""
        try:
            vector_store_path = Path(VECTOR_STORE_DIR) / f"faiss_{session_id}"
            self.vector_store.save_local(str(vector_store_path))
            print(f"[VectorStore] Saved to: {vector_store_path}")
        except Exception as e:
            print(f"[VectorStore] Save error: {str(e)}")

    def load_vector_store(self, session_id: str) -> bool:
        """
        Load existing vector store from disk

        Args:
            session_id: Research session ID

        Returns:
            True if successful
        """
        try:
            vector_store_path = Path(VECTOR_STORE_DIR) / f"faiss_{session_id}"

            if not vector_store_path.exists():
                return False

            self.vector_store = FAISS.load_local(
                str(vector_store_path),
                self.embeddings,
                allow_dangerous_deserialization=True  # Required for FAISS
            )
            self.session_id = session_id
            print(f"[VectorStore] Loaded from: {vector_store_path}")
            return True

        except Exception as e:
            print(f"[VectorStore] Load error: {str(e)}")
            return False
