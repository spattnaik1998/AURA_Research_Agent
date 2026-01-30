-- ============================================
-- Migration 002: Add Session Source Tracking (Optional)
-- Purpose: Track whether research session came from text or image input
-- Description: Adds source_type and source_metadata columns to ResearchSessions
--              to support analytics and image-based research workflows
-- ============================================

USE AURA_Research;
GO

-- Check if source_type column exists (idempotent)
IF NOT EXISTS (
    SELECT 1
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'ResearchSessions'
    AND COLUMN_NAME = 'source_type'
)
BEGIN
    ALTER TABLE ResearchSessions
    ADD source_type NVARCHAR(50) DEFAULT 'text',  -- 'text', 'image'
        source_metadata NVARCHAR(MAX);  -- JSON for image-specific data

    CREATE INDEX IX_ResearchSessions_SourceType ON ResearchSessions(source_type);

    PRINT 'Migration 002: source_type and source_metadata columns added to ResearchSessions';
END
ELSE
BEGIN
    PRINT 'Migration 002: source_type column already exists - skipping';
END
GO
