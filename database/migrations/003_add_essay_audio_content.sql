-- ============================================
-- Migration 003: Add audio_content Column to Essays
-- Purpose: Store audio-optimized essay version without metadata/headers
-- ============================================

USE AURA_Research;
GO

IF NOT EXISTS (
    SELECT 1
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'Essays'
    AND COLUMN_NAME = 'audio_content'
)
BEGIN
    ALTER TABLE Essays
    ADD audio_content NVARCHAR(MAX);  -- Clean prose for audio generation

    PRINT 'Migration 003: audio_content column added to Essays table';
END
ELSE
BEGIN
    PRINT 'Migration 003: audio_content column already exists - skipping';
END
GO
