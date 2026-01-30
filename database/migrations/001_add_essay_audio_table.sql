-- ============================================
-- Migration 001: Add EssayAudio Table
-- Purpose: Create table for storing essay audio files and metadata
-- Description: EssayAudio table was missing from the schema but referenced
--              by audio_repository.py and generate-audio endpoint
-- ============================================

USE AURA_Research;
GO

-- Check if table already exists (idempotent)
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[EssayAudio]') AND type in (N'U'))
BEGIN
    CREATE TABLE EssayAudio (
        audio_id INT IDENTITY(1,1) PRIMARY KEY,
        session_id INT NOT NULL UNIQUE,
        audio_filename NVARCHAR(255) NOT NULL,
        file_size_bytes BIGINT,
        voice_id NVARCHAR(100) DEFAULT '21m00Tcm4TlvDq8ikWAM',
        generated_at DATETIME2 DEFAULT GETDATE(),
        last_accessed_at DATETIME2 DEFAULT GETDATE(),

        CONSTRAINT FK_EssayAudio_Sessions
            FOREIGN KEY (session_id) REFERENCES ResearchSessions(session_id)
            ON DELETE CASCADE
    );

    CREATE INDEX IX_EssayAudio_SessionId ON EssayAudio(session_id);

    PRINT 'Migration 001: EssayAudio table created successfully';
END
ELSE
BEGIN
    PRINT 'Migration 001: EssayAudio table already exists - skipping creation';
END
GO
