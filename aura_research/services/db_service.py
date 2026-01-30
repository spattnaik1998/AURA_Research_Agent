"""
Database Service
Unified service layer for database operations across all features
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from ..database.repositories import (
    ResearchSessionRepository,
    PaperRepository,
    PaperAnalysisRepository,
    EssayRepository,
    ChatRepository,
    GraphRepository,
    IdeationRepository,
    AuditLogRepository,
    UserRepository,
    AudioRepository
)


class DatabaseService:
    """
    Unified database service that provides high-level operations
    for all AURA features with automatic database persistence.
    """

    _instance = None

    def __new__(cls):
        """Singleton pattern for database service."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Initialize all repositories
        self.sessions = ResearchSessionRepository()
        self.papers = PaperRepository()
        self.analyses = PaperAnalysisRepository()
        self.essays = EssayRepository()
        self.chat = ChatRepository()
        self.graph = GraphRepository()
        self.ideation = IdeationRepository()
        self.audit = AuditLogRepository()
        self.users = UserRepository()
        self.audio = AudioRepository()

        # Cache for session_code to session_id mapping
        self._session_cache: Dict[str, int] = {}

        self._initialized = True
        print("[DBService] Database service initialized")

    # ==================== Research Session Methods ====================

    def create_research_session(
        self,
        session_code: str,
        query: str,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        source_type: str = "text",
        source_metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Create a new research session in the database.

        Args:
            session_code: Unique session identifier (e.g., '20251024_205342')
            query: Research query
            user_id: Optional user ID
            ip_address: Optional IP address for audit
            source_type: Source of the research query ('text' or 'image')
            source_metadata: Optional JSON metadata for source (e.g., image filename)

        Returns:
            session_id from database
        """
        try:
            # Convert source_metadata dict to JSON string if provided
            import json
            source_metadata_json = None
            if source_metadata:
                source_metadata_json = json.dumps(source_metadata)

            # Create session in database
            session_id = self.sessions.create(
                session_code=session_code,
                query=query,
                user_id=user_id,
                source_type=source_type,
                source_metadata=source_metadata_json
            )

            # Validate session_id was created successfully
            if not session_id or session_id <= 0:
                print(f"[DBService] Warning: Invalid session_id returned: {session_id}")
                # Try to retrieve it from database
                session = self.sessions.get_by_session_code(session_code)
                if session:
                    session_id = session['session_id']
                else:
                    raise Exception(f"Failed to create or retrieve session: {session_code}")

            # Cache the mapping
            self._session_cache[session_code] = session_id

            # Log the action (non-fatal if it fails)
            try:
                self.audit.log_research_started(
                    session_id=session_id,
                    user_id=user_id,
                    query=query,
                    ip_address=ip_address
                )
            except Exception as audit_error:
                print(f"[DBService] Warning: Audit logging failed: {audit_error}")
                # Continue without audit log - not critical for research

            print(f"[DBService] Research session created: {session_code} -> ID {session_id}")
            return session_id

        except Exception as e:
            print(f"[DBService] Error creating session: {e}")
            raise

    def get_session_id(self, session_code: str) -> Optional[int]:
        """Get database session_id from session_code."""
        # Check cache first
        if session_code in self._session_cache:
            return self._session_cache[session_code]

        # Query database
        session = self.sessions.get_by_session_code(session_code)
        if session:
            self._session_cache[session_code] = session['session_id']
            return session['session_id']

        return None

    def update_session_status(
        self,
        session_code: str,
        status: str,
        progress: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update research session status."""
        session_id = self.get_session_id(session_code)
        if not session_id:
            return False

        return self.sessions.update_status(
            session_id=session_id,
            status=status,
            progress=progress,
            error_message=error_message
        )

    def complete_research_session(
        self,
        session_code: str,
        total_papers: int,
        total_analyzed: int,
        user_id: Optional[int] = None
    ) -> bool:
        """Mark research session as completed."""
        session_id = self.get_session_id(session_code)
        if not session_id:
            return False

        success = self.sessions.mark_completed(
            session_id=session_id,
            total_papers_found=total_papers,
            total_papers_analyzed=total_analyzed
        )

        if success:
            try:
                self.audit.log_research_completed(
                    session_id=session_id,
                    user_id=user_id,
                    papers_count=total_papers,
                    analyses_count=total_analyzed
                )
            except Exception as e:
                print(f"[DBService] Warning: Audit logging failed: {e}")

        return success

    def fail_research_session(
        self,
        session_code: str,
        error_message: str,
        user_id: Optional[int] = None
    ) -> bool:
        """Mark research session as failed."""
        session_id = self.get_session_id(session_code)
        if not session_id:
            return False

        success = self.sessions.mark_failed(session_id, error_message)

        if success:
            try:
                self.audit.log_research_failed(
                    session_id=session_id,
                    error_message=error_message,
                    user_id=user_id
                )
            except Exception as e:
                print(f"[DBService] Warning: Audit logging failed: {e}")

        return success

    def get_session_details(self, session_code: str) -> Optional[Dict[str, Any]]:
        """Get full session details with related data."""
        session_id = self.get_session_id(session_code)
        if not session_id:
            return None

        return self.sessions.get_session_with_details(session_id)

    def get_recent_sessions(
        self,
        user_id: Optional[int] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent research sessions."""
        if user_id:
            return self.sessions.get_user_sessions(user_id, limit)
        return self.sessions.get_recent_sessions(limit)

    def get_completed_sessions(
        self,
        limit: int = 20,
        user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get completed sessions for chat/ideation.

        Args:
            limit: Maximum number of sessions to return
            user_id: If provided, only return sessions for this user

        Returns:
            List of completed sessions
        """
        return self.sessions.get_completed_sessions(limit=limit, user_id=user_id)

    # ==================== Paper Methods ====================

    def save_papers(
        self,
        session_code: str,
        papers: List[Dict[str, Any]]
    ) -> int:
        """
        Save fetched papers to database.

        Args:
            session_code: Session identifier
            papers: List of paper metadata from Serper API

        Returns:
            Number of papers saved
        """
        session_id = self.get_session_id(session_code)
        if not session_id:
            print(f"[DBService] Session not found: {session_code}")
            return 0

        try:
            # Transform paper format for database
            db_papers = []
            for p in papers:
                db_papers.append({
                    'title': p.get('title', 'Untitled'),
                    'authors': p.get('publication_info', {}).get('authors'),
                    'abstract': p.get('snippet', ''),
                    'publication_year': p.get('publication_info', {}).get('year'),
                    'source': p.get('publication_info', {}).get('journal'),
                    'url': p.get('link', ''),
                    'citation_count': p.get('cited_by', {}).get('total', 0),
                    'category': p.get('category')
                })

            count = self.papers.create_many(session_id, db_papers)
            print(f"[DBService] Saved {count} papers for session {session_code}")
            return count

        except Exception as e:
            print(f"[DBService] Error saving papers: {e}")
            return 0

    def get_session_papers(self, session_code: str) -> List[Dict[str, Any]]:
        """Get all papers for a session."""
        session_id = self.get_session_id(session_code)
        if not session_id:
            return []

        return self.papers.get_by_session(session_id)

    # ==================== Paper Analysis Methods ====================

    def save_paper_analyses(
        self,
        session_code: str,
        analyses: List[Dict[str, Any]],
        agent_id: Optional[str] = None
    ) -> int:
        """
        Save paper analyses to database.

        Args:
            session_code: Session identifier
            analyses: List of analysis results from subordinate agents
            agent_id: Optional agent identifier

        Returns:
            Number of analyses saved
        """
        session_id = self.get_session_id(session_code)
        if not session_id:
            return 0

        try:
            saved_count = 0
            papers = self.papers.get_by_session(session_id)

            # Create a mapping of title to paper_id
            title_to_paper_id = {p['title']: p['paper_id'] for p in papers}

            for analysis in analyses:
                # Try to match analysis to paper
                title = analysis.get('title', '')
                paper_id = title_to_paper_id.get(title)

                if not paper_id:
                    # If no match, create a paper record first
                    paper_id = self.papers.create(
                        session_id=session_id,
                        title=title or 'Unknown Paper',
                        url=analysis.get('source_url')
                    )

                # Save analysis
                self.analyses.create_from_analysis_result(
                    paper_id=paper_id,
                    session_id=session_id,
                    analysis=analysis,
                    agent_id=agent_id
                )
                saved_count += 1

            print(f"[DBService] Saved {saved_count} analyses for session {session_code}")
            return saved_count

        except Exception as e:
            print(f"[DBService] Error saving analyses: {e}")
            return 0

    def get_session_analyses(self, session_code: str) -> List[Dict[str, Any]]:
        """Get all analyses for a session."""
        session_id = self.get_session_id(session_code)
        if not session_id:
            return []

        return self.analyses.get_by_session(session_id)

    # ==================== Essay Methods ====================

    def save_essay(
        self,
        session_code: str,
        essay_data: Dict[str, Any],
        user_id: Optional[int] = None
    ) -> Optional[int]:
        """
        Save generated essay to database.

        Args:
            session_code: Session identifier
            essay_data: Essay data from summarizer agent

        Returns:
            essay_id or None if failed
        """
        session_id = self.get_session_id(session_code)
        if not session_id:
            return None

        try:
            essay_id = self.essays.create_from_essay_result(session_id, essay_data)

            # Log the action (non-fatal)
            try:
                self.audit.log_essay_generated(
                    session_id=session_id,
                    essay_id=essay_id,
                    word_count=essay_data.get('word_count', 0),
                    user_id=user_id
                )
            except Exception as audit_error:
                print(f"[DBService] Warning: Audit logging failed: {audit_error}")

            print(f"[DBService] Essay saved for session {session_code}, ID: {essay_id}")
            return essay_id

        except Exception as e:
            print(f"[DBService] Error saving essay: {e}")
            return None

    def get_session_essay(self, session_code: str) -> Optional[Dict[str, Any]]:
        """Get essay for a session."""
        session_id = self.get_session_id(session_code)
        if not session_id:
            return None

        return self.essays.get_by_session(session_id)

    # ==================== Audio Methods ====================

    def create_audio_record(
        self,
        session_code: str,
        audio_filename: str,
        file_size_bytes: int,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        user_id: Optional[int] = None
    ) -> Optional[int]:
        """
        Create an audio record in the database.

        Args:
            session_code: Session identifier
            audio_filename: Name of the audio file
            file_size_bytes: Size of the audio file in bytes
            voice_id: ElevenLabs voice ID
            user_id: Optional user ID for audit logging

        Returns:
            audio_id or None if failed
        """
        session_id = self.get_session_id(session_code)
        if not session_id:
            return None

        try:
            audio_id = self.audio.create(
                session_id=session_id,
                audio_filename=audio_filename,
                file_size_bytes=file_size_bytes,
                voice_id=voice_id
            )

            print(f"[DBService] Audio record created for session {session_code}, ID: {audio_id}")
            return audio_id

        except Exception as e:
            print(f"[DBService] Error creating audio record: {e}")
            return None

    def get_session_audio(self, session_code: str) -> Optional[Dict[str, Any]]:
        """Get audio metadata for a session."""
        session_id = self.get_session_id(session_code)
        if not session_id:
            return None

        return self.audio.get_by_session(session_id)

    def audio_exists(self, session_code: str) -> bool:
        """Check if audio exists for a session."""
        session_id = self.get_session_id(session_code)
        if not session_id:
            return False

        return self.audio.audio_exists(session_id)

    def update_audio_access_time(self, session_code: str) -> bool:
        """Update the last_accessed_at timestamp for audio."""
        session_id = self.get_session_id(session_code)
        if not session_id:
            return False

        return self.audio.update_last_accessed(session_id)

    def delete_audio_record(self, session_code: str) -> bool:
        """Delete audio record for a session."""
        session_id = self.get_session_id(session_code)
        if not session_id:
            return False

        return self.audio.delete_by_session(session_id)

    # ==================== Chat Methods ====================

    def create_conversation(
        self,
        session_code: str,
        user_id: Optional[int] = None,
        title: Optional[str] = None,
        language: str = "en"
    ) -> Optional[Dict[str, Any]]:
        """Create a new chat conversation."""
        session_id = self.get_session_id(session_code)
        if not session_id:
            return None

        return self.chat.create_conversation(
            session_id=session_id,
            user_id=user_id,
            title=title,
            language=language
        )

    def get_or_create_conversation(
        self,
        session_code: str,
        conversation_code: Optional[str] = None,
        user_id: Optional[int] = None,
        language: str = "en"
    ) -> Optional[Dict[str, Any]]:
        """Get existing conversation or create new one."""
        session_id = self.get_session_id(session_code)
        if not session_id:
            return None

        if conversation_code:
            conv = self.chat.get_conversation_by_code(conversation_code)
            if conv:
                return conv

        # Create new conversation
        return self.create_conversation(
            session_code=session_code,
            user_id=user_id,
            language=language
        )

    def save_chat_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        context_used: Optional[List[Dict]] = None,
        context_scores: Optional[List[float]] = None,
        user_id: Optional[int] = None
    ) -> int:
        """Save a chat message."""
        message_id = self.chat.add_message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            context_used=context_used,
            context_scores=context_scores
        )

        # Get conversation to find session_id for audit (non-fatal)
        try:
            conv = self.chat.get_by_id(conversation_id)
            if conv:
                self.audit.log_chat_message(
                    session_id=conv.get('session_id'),
                    conversation_id=conversation_id,
                    message_role=role,
                    user_id=user_id
                )
        except Exception as e:
            print(f"[DBService] Warning: Audit logging failed: {e}")

        return message_id

    def get_conversation_history(
        self,
        conversation_id: int,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get conversation messages."""
        return self.chat.get_conversation_messages(conversation_id, limit)

    def get_session_conversations(self, session_code: str) -> List[Dict[str, Any]]:
        """Get all conversations for a session."""
        session_id = self.get_session_id(session_code)
        if not session_id:
            return []

        return self.chat.get_session_conversations(session_id)

    # ==================== Graph Methods ====================

    def save_graph(
        self,
        session_code: str,
        graph_data: Dict[str, Any],
        user_id: Optional[int] = None
    ) -> bool:
        """
        Save knowledge graph to database.

        Args:
            session_code: Session identifier
            graph_data: Graph data with nodes and edges

        Returns:
            True if successful
        """
        session_id = self.get_session_id(session_code)
        if not session_id:
            return False

        try:
            # Delete existing graph data for this session
            self.graph.delete_graph_by_session(session_id)

            nodes = graph_data.get('nodes', [])
            edges = graph_data.get('edges', [])

            # Save nodes and get ID mapping
            node_id_map = {}
            for node in nodes:
                node_db_id = self.graph.create_node(
                    session_id=session_id,
                    node_type=node.get('type', 'unknown'),
                    node_key=node.get('id', ''),
                    label=node.get('label', ''),
                    properties=node.get('properties')
                )
                node_id_map[node.get('id')] = node_db_id

            # Save edges with mapped node IDs
            for edge in edges:
                source_db_id = node_id_map.get(edge.get('source'))
                target_db_id = node_id_map.get(edge.get('target'))

                if source_db_id and target_db_id:
                    self.graph.create_edge(
                        session_id=session_id,
                        source_node_id=source_db_id,
                        target_node_id=target_db_id,
                        edge_type=edge.get('type', 'related_to'),
                        weight=edge.get('weight', 1.0),
                        properties=edge.get('properties')
                    )

            # Log the action (non-fatal)
            try:
                self.audit.log_graph_built(
                    session_id=session_id,
                    nodes_count=len(nodes),
                    edges_count=len(edges),
                    user_id=user_id
                )
            except Exception as audit_error:
                print(f"[DBService] Warning: Audit logging failed: {audit_error}")

            print(f"[DBService] Graph saved: {len(nodes)} nodes, {len(edges)} edges")
            return True

        except Exception as e:
            print(f"[DBService] Error saving graph: {e}")
            return False

    def get_session_graph(self, session_code: str) -> Optional[Dict[str, Any]]:
        """Get graph data for a session."""
        session_id = self.get_session_id(session_code)
        if not session_id:
            return None

        if not self.graph.graph_exists(session_id):
            return None

        return self.graph.get_full_graph(session_id)

    def update_graph_centrality(
        self,
        session_code: str,
        centrality_data: Dict[str, Dict[str, float]]
    ) -> bool:
        """Update node centrality metrics."""
        session_id = self.get_session_id(session_code)
        if not session_id:
            return False

        try:
            for node_key, metrics in centrality_data.items():
                node = self.graph.get_node_by_key(session_id, 'any', node_key)
                if node:
                    self.graph.update_node_centrality(
                        node_id=node['node_id'],
                        degree=metrics.get('degree'),
                        pagerank=metrics.get('pagerank'),
                        betweenness=metrics.get('betweenness')
                    )
            return True
        except Exception as e:
            print(f"[DBService] Error updating centrality: {e}")
            return False

    # ==================== Ideation Methods ====================

    def save_ideation_results(
        self,
        session_code: str,
        result: Dict[str, Any],
        user_id: Optional[int] = None
    ) -> bool:
        """
        Save ideation results (gaps and questions) to database.

        Args:
            session_code: Session identifier
            result: Ideation result with gaps and questions

        Returns:
            True if successful
        """
        session_id = self.get_session_id(session_code)
        if not session_id:
            return False

        try:
            # Delete existing ideation data
            self.ideation.delete_ideation_by_session(session_id)

            gaps = result.get('gaps_identified', [])
            questions = result.get('questions', [])

            # Save gaps and get ID mapping
            gap_id_map = {}
            for gap in gaps:
                gap_db_id = self.ideation.create_gap(
                    session_id=session_id,
                    gap_type=gap.get('type', 'general'),
                    title=gap.get('title', ''),
                    description=gap.get('description'),
                    evidence=gap.get('evidence'),
                    priority_score=gap.get('priority_score')
                )
                gap_id_map[gap.get('title', '')] = gap_db_id

            # Save questions
            self.ideation.create_questions_bulk(session_id, questions)

            # Log the action (non-fatal)
            try:
                self.audit.log_questions_generated(
                    session_id=session_id,
                    questions_count=len(questions),
                    gaps_count=len(gaps),
                    user_id=user_id
                )
            except Exception as audit_error:
                print(f"[DBService] Warning: Audit logging failed: {audit_error}")

            print(f"[DBService] Ideation saved: {len(gaps)} gaps, {len(questions)} questions")
            return True

        except Exception as e:
            print(f"[DBService] Error saving ideation: {e}")
            return False

    def get_session_questions(self, session_code: str) -> List[Dict[str, Any]]:
        """Get questions for a session."""
        session_id = self.get_session_id(session_code)
        if not session_id:
            return []

        return self.ideation.get_questions_by_session(session_id)

    def get_session_gaps(self, session_code: str) -> List[Dict[str, Any]]:
        """Get research gaps for a session."""
        session_id = self.get_session_id(session_code)
        if not session_id:
            return []

        return self.ideation.get_gaps_by_session(session_id)

    # ==================== User Methods ====================

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        return self.users.get_by_id(user_id)

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        return self.users.get_by_email(email)

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        return self.users.get_by_username(username)

    # ==================== Session Ownership Methods ====================

    def get_session_owner(self, session_code: str) -> Optional[int]:
        """
        Get the owner (user_id) of a session.

        Args:
            session_code: The session code

        Returns:
            user_id if session exists, None otherwise
        """
        return self.sessions.get_session_owner(session_code)

    def verify_session_ownership(
        self,
        session_code: str,
        user_id: int
    ) -> bool:
        """
        Verify that a user owns a specific session.

        Args:
            session_code: The session code to check
            user_id: The user ID to verify ownership for

        Returns:
            True if the user owns the session, False otherwise
        """
        return self.sessions.verify_session_ownership(session_code, user_id)


# Global database service instance
_db_service: Optional[DatabaseService] = None


def get_db_service() -> DatabaseService:
    """Get the global database service instance."""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service
