-- ============================================
-- AURA Research Agent - Database Schema
-- SQL Server (SSMS) with Windows Authentication
-- Server: LAPTOP-FO95TROJ
-- ============================================

-- Create Database
USE master;
GO

IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'AURA_Research')
BEGIN
    CREATE DATABASE AURA_Research;
END
GO

USE AURA_Research;
GO

-- ============================================
-- 1. USERS TABLE
-- For authentication and user management
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Users]') AND type in (N'U'))
BEGIN
    CREATE TABLE Users (
        user_id INT IDENTITY(1,1) PRIMARY KEY,
        username NVARCHAR(100) NOT NULL UNIQUE,
        email NVARCHAR(255) NOT NULL UNIQUE,
        password_hash NVARCHAR(255) NOT NULL,
        full_name NVARCHAR(200),
        role NVARCHAR(50) DEFAULT 'user',  -- 'user', 'admin', 'researcher'
        is_active BIT DEFAULT 1,
        created_at DATETIME2 DEFAULT GETDATE(),
        updated_at DATETIME2 DEFAULT GETDATE(),
        last_login DATETIME2
    );

    CREATE INDEX IX_Users_Email ON Users(email);
    CREATE INDEX IX_Users_Username ON Users(username);
END
GO

-- ============================================
-- 2. RESEARCH SESSIONS TABLE
-- Main table for research queries/sessions
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ResearchSessions]') AND type in (N'U'))
BEGIN
    CREATE TABLE ResearchSessions (
        session_id INT IDENTITY(1,1) PRIMARY KEY,
        session_code NVARCHAR(50) NOT NULL UNIQUE,  -- e.g., '20251024_205342'
        user_id INT NULL,
        query NVARCHAR(500) NOT NULL,
        status NVARCHAR(50) DEFAULT 'pending',  -- 'pending', 'fetching', 'analyzing', 'synthesizing', 'completed', 'failed'
        progress INT DEFAULT 0,  -- 0-100
        total_papers_found INT DEFAULT 0,
        total_papers_analyzed INT DEFAULT 0,
        started_at DATETIME2 DEFAULT GETDATE(),
        completed_at DATETIME2,
        error_message NVARCHAR(MAX),
        metadata NVARCHAR(MAX),  -- JSON for additional data

        CONSTRAINT FK_ResearchSessions_Users
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
            ON DELETE SET NULL
    );

    CREATE INDEX IX_ResearchSessions_SessionCode ON ResearchSessions(session_code);
    CREATE INDEX IX_ResearchSessions_UserId ON ResearchSessions(user_id);
    CREATE INDEX IX_ResearchSessions_Status ON ResearchSessions(status);
    CREATE INDEX IX_ResearchSessions_CreatedAt ON ResearchSessions(started_at DESC);
END
GO

-- ============================================
-- 3. PAPERS TABLE
-- Stores fetched research papers
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Papers]') AND type in (N'U'))
BEGIN
    CREATE TABLE Papers (
        paper_id INT IDENTITY(1,1) PRIMARY KEY,
        session_id INT NOT NULL,
        title NVARCHAR(500) NOT NULL,
        authors NVARCHAR(MAX),  -- JSON array of authors
        abstract NVARCHAR(MAX),
        publication_year INT,
        source NVARCHAR(255),  -- Journal/Conference name
        url NVARCHAR(1000),
        citation_count INT DEFAULT 0,
        category NVARCHAR(50),  -- 'high_impact', 'medium_impact', 'recent'
        fetched_at DATETIME2 DEFAULT GETDATE(),

        CONSTRAINT FK_Papers_ResearchSessions
            FOREIGN KEY (session_id) REFERENCES ResearchSessions(session_id)
            ON DELETE CASCADE
    );

    CREATE INDEX IX_Papers_SessionId ON Papers(session_id);
    CREATE INDEX IX_Papers_CitationCount ON Papers(citation_count DESC);
END
GO

-- ============================================
-- 4. PAPER ANALYSES TABLE
-- Stores subordinate agent analysis results
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[PaperAnalyses]') AND type in (N'U'))
BEGIN
    CREATE TABLE PaperAnalyses (
        analysis_id INT IDENTITY(1,1) PRIMARY KEY,
        paper_id INT NOT NULL,
        session_id INT NOT NULL,
        agent_id NVARCHAR(50),  -- Which subordinate agent processed this
        summary NVARCHAR(MAX),
        key_points NVARCHAR(MAX),  -- JSON array
        methodology NVARCHAR(MAX),
        key_findings NVARCHAR(MAX),  -- JSON array
        novelty NVARCHAR(MAX),
        limitations NVARCHAR(MAX),  -- JSON array
        relevance_score DECIMAL(3,1),  -- 1.0 - 10.0
        technical_depth NVARCHAR(50),  -- 'theoretical', 'applied', 'empirical', 'survey'
        research_domain NVARCHAR(200),
        core_ideas NVARCHAR(MAX),  -- JSON array
        reasoning NVARCHAR(MAX),  -- ReAct reasoning trace
        citations NVARCHAR(MAX),  -- JSON array of extracted citations
        analyzed_at DATETIME2 DEFAULT GETDATE(),

        CONSTRAINT FK_PaperAnalyses_Papers
            FOREIGN KEY (paper_id) REFERENCES Papers(paper_id)
            ON DELETE CASCADE,
        CONSTRAINT FK_PaperAnalyses_Sessions
            FOREIGN KEY (session_id) REFERENCES ResearchSessions(session_id)
    );

    CREATE INDEX IX_PaperAnalyses_PaperId ON PaperAnalyses(paper_id);
    CREATE INDEX IX_PaperAnalyses_SessionId ON PaperAnalyses(session_id);
    CREATE INDEX IX_PaperAnalyses_RelevanceScore ON PaperAnalyses(relevance_score DESC);
END
GO

-- ============================================
-- 5. ESSAYS TABLE
-- Stores generated research essays
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Essays]') AND type in (N'U'))
BEGIN
    CREATE TABLE Essays (
        essay_id INT IDENTITY(1,1) PRIMARY KEY,
        session_id INT NOT NULL UNIQUE,
        title NVARCHAR(500),
        introduction NVARCHAR(MAX),
        body NVARCHAR(MAX),
        conclusion NVARCHAR(MAX),
        full_content NVARCHAR(MAX),  -- Complete essay text
        full_content_markdown NVARCHAR(MAX),  -- Markdown version
        references_list NVARCHAR(MAX),  -- JSON array of references
        word_count INT,
        citation_count INT,
        synthesis_themes NVARCHAR(MAX),  -- JSON array of themes
        generated_at DATETIME2 DEFAULT GETDATE(),

        CONSTRAINT FK_Essays_ResearchSessions
            FOREIGN KEY (session_id) REFERENCES ResearchSessions(session_id)
            ON DELETE CASCADE
    );

    CREATE INDEX IX_Essays_SessionId ON Essays(session_id);
END
GO

-- ============================================
-- 6. CHAT CONVERSATIONS TABLE
-- Stores RAG chatbot conversation threads
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ChatConversations]') AND type in (N'U'))
BEGIN
    CREATE TABLE ChatConversations (
        conversation_id INT IDENTITY(1,1) PRIMARY KEY,
        conversation_code NVARCHAR(100) NOT NULL UNIQUE,  -- UUID or similar
        session_id INT NOT NULL,
        user_id INT NULL,
        title NVARCHAR(255),
        language NVARCHAR(20) DEFAULT 'en',  -- 'en', 'fr', 'zh', 'ru'
        created_at DATETIME2 DEFAULT GETDATE(),
        updated_at DATETIME2 DEFAULT GETDATE(),
        is_active BIT DEFAULT 1,

        CONSTRAINT FK_ChatConversations_Sessions
            FOREIGN KEY (session_id) REFERENCES ResearchSessions(session_id)
            ON DELETE CASCADE,
        CONSTRAINT FK_ChatConversations_Users
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
            ON DELETE SET NULL
    );

    CREATE INDEX IX_ChatConversations_SessionId ON ChatConversations(session_id);
    CREATE INDEX IX_ChatConversations_UserId ON ChatConversations(user_id);
    CREATE INDEX IX_ChatConversations_Code ON ChatConversations(conversation_code);
END
GO

-- ============================================
-- 7. CHAT MESSAGES TABLE
-- Stores individual chat messages
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ChatMessages]') AND type in (N'U'))
BEGIN
    CREATE TABLE ChatMessages (
        message_id INT IDENTITY(1,1) PRIMARY KEY,
        conversation_id INT NOT NULL,
        role NVARCHAR(20) NOT NULL,  -- 'user', 'assistant', 'system'
        content NVARCHAR(MAX) NOT NULL,
        context_used NVARCHAR(MAX),  -- JSON array of context chunks used
        context_scores NVARCHAR(MAX),  -- JSON array of relevance scores
        tokens_used INT,
        created_at DATETIME2 DEFAULT GETDATE(),

        CONSTRAINT FK_ChatMessages_Conversations
            FOREIGN KEY (conversation_id) REFERENCES ChatConversations(conversation_id)
            ON DELETE CASCADE
    );

    CREATE INDEX IX_ChatMessages_ConversationId ON ChatMessages(conversation_id);
    CREATE INDEX IX_ChatMessages_CreatedAt ON ChatMessages(created_at);
END
GO

-- ============================================
-- 8. KNOWLEDGE GRAPH NODES TABLE
-- Stores graph nodes (papers, concepts, authors, methods)
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[GraphNodes]') AND type in (N'U'))
BEGIN
    CREATE TABLE GraphNodes (
        node_id INT IDENTITY(1,1) PRIMARY KEY,
        session_id INT NOT NULL,
        node_type NVARCHAR(50) NOT NULL,  -- 'paper', 'concept', 'author', 'method'
        node_key NVARCHAR(255) NOT NULL,  -- Unique identifier within session
        label NVARCHAR(500) NOT NULL,
        properties NVARCHAR(MAX),  -- JSON for type-specific properties
        centrality_degree DECIMAL(10,6),
        centrality_pagerank DECIMAL(10,6),
        centrality_betweenness DECIMAL(10,6),
        community_id INT,
        created_at DATETIME2 DEFAULT GETDATE(),

        CONSTRAINT FK_GraphNodes_Sessions
            FOREIGN KEY (session_id) REFERENCES ResearchSessions(session_id)
            ON DELETE CASCADE,
        CONSTRAINT UQ_GraphNodes_SessionKey
            UNIQUE (session_id, node_type, node_key)
    );

    CREATE INDEX IX_GraphNodes_SessionId ON GraphNodes(session_id);
    CREATE INDEX IX_GraphNodes_NodeType ON GraphNodes(node_type);
    CREATE INDEX IX_GraphNodes_CommunityId ON GraphNodes(community_id);
END
GO

-- ============================================
-- 9. KNOWLEDGE GRAPH EDGES TABLE
-- Stores relationships between nodes
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[GraphEdges]') AND type in (N'U'))
BEGIN
    CREATE TABLE GraphEdges (
        edge_id INT IDENTITY(1,1) PRIMARY KEY,
        session_id INT NOT NULL,
        source_node_id INT NOT NULL,
        target_node_id INT NOT NULL,
        edge_type NVARCHAR(50) NOT NULL,  -- 'discusses', 'authored', 'uses_method', 'related_to'
        weight DECIMAL(5,2) DEFAULT 1.0,
        properties NVARCHAR(MAX),  -- JSON for additional properties
        created_at DATETIME2 DEFAULT GETDATE(),

        CONSTRAINT FK_GraphEdges_Sessions
            FOREIGN KEY (session_id) REFERENCES ResearchSessions(session_id)
            ON DELETE CASCADE,
        CONSTRAINT FK_GraphEdges_SourceNode
            FOREIGN KEY (source_node_id) REFERENCES GraphNodes(node_id),
        CONSTRAINT FK_GraphEdges_TargetNode
            FOREIGN KEY (target_node_id) REFERENCES GraphNodes(node_id)
    );

    CREATE INDEX IX_GraphEdges_SessionId ON GraphEdges(session_id);
    CREATE INDEX IX_GraphEdges_SourceNode ON GraphEdges(source_node_id);
    CREATE INDEX IX_GraphEdges_TargetNode ON GraphEdges(target_node_id);
    CREATE INDEX IX_GraphEdges_EdgeType ON GraphEdges(edge_type);
END
GO

-- ============================================
-- 10. RESEARCH GAPS TABLE
-- Stores identified research gaps
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ResearchGaps]') AND type in (N'U'))
BEGIN
    CREATE TABLE ResearchGaps (
        gap_id INT IDENTITY(1,1) PRIMARY KEY,
        session_id INT NOT NULL,
        gap_type NVARCHAR(50) NOT NULL,  -- 'methodological', 'theoretical', 'empirical', 'practical', 'integration'
        title NVARCHAR(500) NOT NULL,
        description NVARCHAR(MAX),
        evidence NVARCHAR(MAX),  -- JSON array of supporting evidence
        priority_score DECIMAL(3,1),  -- 1.0 - 10.0
        created_at DATETIME2 DEFAULT GETDATE(),

        CONSTRAINT FK_ResearchGaps_Sessions
            FOREIGN KEY (session_id) REFERENCES ResearchSessions(session_id)
            ON DELETE CASCADE
    );

    CREATE INDEX IX_ResearchGaps_SessionId ON ResearchGaps(session_id);
    CREATE INDEX IX_ResearchGaps_GapType ON ResearchGaps(gap_type);
END
GO

-- ============================================
-- 11. RESEARCH QUESTIONS TABLE
-- Stores generated research questions
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ResearchQuestions]') AND type in (N'U'))
BEGIN
    CREATE TABLE ResearchQuestions (
        question_id INT IDENTITY(1,1) PRIMARY KEY,
        session_id INT NOT NULL,
        gap_id INT NULL,  -- Optional link to specific gap
        question_type NVARCHAR(50) NOT NULL,  -- 'exploratory', 'explanatory', 'comparative', 'predictive', 'evaluative', 'design', 'causal', 'integrative'
        question_text NVARCHAR(MAX) NOT NULL,
        rationale NVARCHAR(MAX),

        -- Scoring dimensions (1-10)
        score_novelty DECIMAL(3,1),
        score_feasibility DECIMAL(3,1),
        score_clarity DECIMAL(3,1),
        score_impact DECIMAL(3,1),
        score_specificity DECIMAL(3,1),
        score_overall DECIMAL(3,1),  -- Computed average

        suggested_methods NVARCHAR(MAX),  -- JSON array
        related_concepts NVARCHAR(MAX),  -- JSON array
        created_at DATETIME2 DEFAULT GETDATE(),

        CONSTRAINT FK_ResearchQuestions_Sessions
            FOREIGN KEY (session_id) REFERENCES ResearchSessions(session_id)
            ON DELETE CASCADE,
        CONSTRAINT FK_ResearchQuestions_Gaps
            FOREIGN KEY (gap_id) REFERENCES ResearchGaps(gap_id)
    );

    CREATE INDEX IX_ResearchQuestions_SessionId ON ResearchQuestions(session_id);
    CREATE INDEX IX_ResearchQuestions_GapId ON ResearchQuestions(gap_id);
    CREATE INDEX IX_ResearchQuestions_QuestionType ON ResearchQuestions(question_type);
    CREATE INDEX IX_ResearchQuestions_OverallScore ON ResearchQuestions(score_overall DESC);
END
GO

-- ============================================
-- 12. VECTOR EMBEDDINGS TABLE
-- Stores document embeddings for RAG
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[VectorEmbeddings]') AND type in (N'U'))
BEGIN
    CREATE TABLE VectorEmbeddings (
        embedding_id INT IDENTITY(1,1) PRIMARY KEY,
        session_id INT NOT NULL,
        document_type NVARCHAR(50) NOT NULL,  -- 'essay_section', 'paper_analysis'
        document_id INT,  -- Reference to source document (essay_id or analysis_id)
        chunk_index INT,
        content NVARCHAR(MAX) NOT NULL,
        embedding VARBINARY(MAX),  -- Serialized embedding vector
        metadata NVARCHAR(MAX),  -- JSON for additional metadata
        created_at DATETIME2 DEFAULT GETDATE(),

        CONSTRAINT FK_VectorEmbeddings_Sessions
            FOREIGN KEY (session_id) REFERENCES ResearchSessions(session_id)
            ON DELETE CASCADE
    );

    CREATE INDEX IX_VectorEmbeddings_SessionId ON VectorEmbeddings(session_id);
    CREATE INDEX IX_VectorEmbeddings_DocumentType ON VectorEmbeddings(document_type);
END
GO

-- ============================================
-- 13. AUDIT LOG TABLE
-- Tracks important actions for debugging/analytics
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[AuditLog]') AND type in (N'U'))
BEGIN
    CREATE TABLE AuditLog (
        log_id INT IDENTITY(1,1) PRIMARY KEY,
        user_id INT NULL,
        session_id INT NULL,
        action NVARCHAR(100) NOT NULL,  -- 'research_started', 'paper_analyzed', 'essay_generated', etc.
        entity_type NVARCHAR(50),
        entity_id INT,
        details NVARCHAR(MAX),  -- JSON for action-specific details
        ip_address NVARCHAR(50),
        user_agent NVARCHAR(500),
        created_at DATETIME2 DEFAULT GETDATE(),

        CONSTRAINT FK_AuditLog_Users
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
            ON DELETE SET NULL,
        CONSTRAINT FK_AuditLog_Sessions
            FOREIGN KEY (session_id) REFERENCES ResearchSessions(session_id)
            ON DELETE SET NULL
    );

    CREATE INDEX IX_AuditLog_UserId ON AuditLog(user_id);
    CREATE INDEX IX_AuditLog_SessionId ON AuditLog(session_id);
    CREATE INDEX IX_AuditLog_Action ON AuditLog(action);
    CREATE INDEX IX_AuditLog_CreatedAt ON AuditLog(created_at DESC);
END
GO

-- ============================================
-- PRINT SUCCESS MESSAGE
-- ============================================
PRINT 'AURA Research Database Schema Created Successfully!';
PRINT '';
PRINT 'Tables Created:';
PRINT '  1. Users - User authentication and management';
PRINT '  2. ResearchSessions - Main research queries';
PRINT '  3. Papers - Fetched research papers';
PRINT '  4. PaperAnalyses - Agent analysis results';
PRINT '  5. Essays - Generated research essays';
PRINT '  6. ChatConversations - Chat threads';
PRINT '  7. ChatMessages - Individual messages';
PRINT '  8. GraphNodes - Knowledge graph nodes';
PRINT '  9. GraphEdges - Knowledge graph relationships';
PRINT '  10. ResearchGaps - Identified research gaps';
PRINT '  11. ResearchQuestions - Generated questions';
PRINT '  12. VectorEmbeddings - RAG embeddings';
PRINT '  13. AuditLog - Action tracking';
GO
