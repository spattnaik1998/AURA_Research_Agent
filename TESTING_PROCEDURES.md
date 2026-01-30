# Testing Procedures - Audio & Image Integration

## Pre-Testing Setup

### Prerequisites
- [ ] Database migrations applied (001 and 002)
- [ ] Backend running on localhost:8000
- [ ] Frontend running on localhost:3000 (or configured port)
- [ ] ElevenLabs API key configured in .env
- [ ] User account created and authenticated
- [ ] Storage directories exist:
  - [ ] `aura_research/storage/audio/`
  - [ ] `aura_research/storage/uploads/` (for images)

### Database Verification
```sql
-- Verify EssayAudio table exists
SELECT * FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_NAME = 'EssayAudio';

-- Verify ResearchSessions has source_type column
SELECT TOP 1 source_type FROM ResearchSessions;
```

---

## Test 1: EssayAudio Table Existence

### Purpose
Verify the EssayAudio table exists and has correct structure

### Steps
1. Open SQL Server Management Studio
2. Navigate to AURA_Research database
3. Expand Tables
4. Look for EssayAudio table

### Expected Result
```
✅ EssayAudio table visible in table list
✅ Contains columns:
   - audio_id (primary key)
   - session_id (unique foreign key)
   - audio_filename
   - file_size_bytes
   - voice_id
   - generated_at
   - last_accessed_at
```

### Verification Query
```sql
EXEC sp_help 'EssayAudio';
```

---

## Test 2: Audio Generation - Text-Based Research

### Purpose
Verify audio generation works for standard text-based research

### Steps

#### 2.1: Start Text-Based Research
```bash
# Via Frontend:
1. Login to AURA app
2. Switch to "Text Query" mode
3. Enter query: "machine learning applications in healthcare"
4. Click "Start Research"

# Via API (alternative):
curl -X POST http://localhost:8000/research/start \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning in healthcare", "source_type": "text"}'
```

#### 2.2: Wait for Research Completion
```bash
# Check status:
curl http://localhost:8000/research/status/<session_id> \
  -H "Authorization: Bearer <your_token>"

# Poll until status = "completed"
```

#### 2.3: Generate Audio
```bash
# Via Frontend:
1. Wait for essay to complete
2. Click "Generate Audio" button
3. Wait for audio to generate

# Via API:
curl -X POST http://localhost:8000/research/session/<session_id>/generate-audio \
  -H "Authorization: Bearer <your_token>"
```

### Expected Results
```
✅ Audio generation completes without errors
✅ Response includes:
   {
     "status": "success",
     "message": "Audio generated successfully",
     "audio_path": "aura_research/storage/audio/...",
     "file_size": 12345
   }
✅ Audio file exists at specified path
✅ File size > 0 bytes
```

### Database Verification
```sql
-- Check audio record was created
SELECT * FROM EssayAudio
WHERE session_id = (SELECT session_id FROM ResearchSessions WHERE session_code = '<session_id>');

-- Expected result:
-- | audio_id | session_id | audio_filename | file_size_bytes | voice_id | generated_at | last_accessed_at |
-- | 1 | 1 | audio_*.mp3 | [size] | 21m00Tcm4TlvDq8ikWAM | 2025-01-29... | 2025-01-29... |
```

---

## Test 3: Audio Generation - Image-Based Research

### Purpose
Verify audio generation works for image-based research

### Steps

#### 3.1: Upload and Analyze Image
```bash
# Via Frontend:
1. Login to AURA app
2. Switch to "Image Upload" mode
3. Select an image of a research paper or academic diagram
4. Click "Upload and Extract"
5. Wait for image analysis to complete
6. Verify extracted query appears in input field
```

#### 3.2: Start Image-Based Research
```bash
# Via Frontend:
1. Once image is analyzed
2. Click "Start Research" with extracted query
3. Frontend automatically sets source_type='image'
```

#### 3.3: Wait for Completion and Generate Audio
```bash
# Same as Test 2, steps 2.2-2.3
```

### Expected Results
```
✅ Image analysis succeeds (extracted query is meaningful)
✅ Research starts with source_type='image'
✅ Audio generation completes without errors
✅ Audio file created successfully
```

### Database Verification
```sql
-- Check source_type was recorded as 'image'
SELECT session_code, query, source_type, source_metadata
FROM ResearchSessions
WHERE source_type = 'image'
ORDER BY started_at DESC
LIMIT 1;

-- Expected result:
-- | session_code | query | source_type | source_metadata |
-- | 20250129_... | AI ethics | image | NULL or JSON |

-- Check audio record for image-based session
SELECT r.session_code, r.source_type, a.audio_filename
FROM EssayAudio a
JOIN ResearchSessions r ON a.session_id = r.session_id
WHERE r.source_type = 'image'
ORDER BY a.generated_at DESC
LIMIT 1;
```

---

## Test 4: Source Type Tracking

### Purpose
Verify source_type is correctly recorded for both text and image research

### Steps

#### 4.1: Perform Mixed Research Sessions
```bash
# Create at least 3 research sessions:
# 1. Text-based research
# 2. Image-based research
# 3. Another text-based research
```

#### 4.2: Query Database for Source Types
```sql
SELECT
    session_code,
    query,
    source_type,
    status,
    started_at
FROM ResearchSessions
ORDER BY started_at DESC
LIMIT 10;
```

### Expected Results
```
✅ source_type column exists (no error "column doesn't exist")
✅ Values are either 'text' or 'image'
✅ Text-based research has source_type='text'
✅ Image-based research has source_type='image'
✅ Default value is 'text' for any sessions created before implementation
```

### Sample Output
```
| session_code | query | source_type | started_at |
|---|---|---|---|
| 20250129_235959 | "AI ethics" | image | 2025-01-29 23:59:59 |
| 20250129_235930 | "Blockchain security" | text | 2025-01-29 23:59:30 |
| 20250129_235900 | "Quantum computing" | image | 2025-01-29 23:59:00 |
```

---

## Test 5: End-to-End User Workflow

### Purpose
Verify complete workflow from image upload to audio playback

### Steps

1. **Login**
   - [ ] User authenticates successfully

2. **Upload Image**
   - [ ] User switches to "Image Upload" tab
   - [ ] Selects research paper screenshot
   - [ ] Sees "Analyzing image..." message
   - [ ] Gets extracted research query

3. **Start Research**
   - [ ] Clicks "Start Research"
   - [ ] Sees status tracker begin
   - [ ] Observes progress through steps

4. **Monitor Progress**
   - [ ] Fetching step shows papers found
   - [ ] Analyzing step shows progress
   - [ ] Synthesizing step creates essay
   - [ ] Completion displays essay preview

5. **Generate Audio**
   - [ ] Clicks "Generate Audio" button
   - [ ] Sees "Generating..." message
   - [ ] Audio completes without errors
   - [ ] Audio file ready to download/play

### Expected Results
```
✅ Image analysis provides meaningful query
✅ Research completes successfully
✅ Essay is generated and displayed
✅ Audio generation succeeds
✅ Audio file is playable
✅ All data properly saved to database
```

### Database Verification
```sql
-- Verify complete record
SELECT
    r.session_code,
    r.query,
    r.source_type,
    r.status,
    e.full_content IS NOT NULL as has_essay,
    a.audio_filename IS NOT NULL as has_audio,
    r.started_at
FROM ResearchSessions r
LEFT JOIN Essays e ON r.session_id = e.session_id
LEFT JOIN EssayAudio a ON r.session_id = a.session_id
WHERE r.source_type = 'image'
ORDER BY r.started_at DESC
LIMIT 1;

-- Expected result:
-- | session_code | source_type | status | has_essay | has_audio |
-- | 20250129_... | image | completed | 1 | 1 |
```

---

## Test 6: Error Handling

### Purpose
Verify graceful error handling for edge cases

### Test 6.1: Audio Generation on Non-Existent Session
```bash
curl -X POST http://localhost:8000/research/session/invalid_id/generate-audio \
  -H "Authorization: Bearer <your_token>"
```

**Expected:** 404 error with descriptive message

### Test 6.2: Audio Generation Before Essay Complete
```bash
# Start research but call audio endpoint while still analyzing
curl -X POST http://localhost:8000/research/session/<session_id>/generate-audio \
  -H "Authorization: Bearer <your_token>"
```

**Expected:** 404 error "No essay found for this session"

### Test 6.3: Missing Authorization
```bash
curl -X POST http://localhost:8000/research/session/<session_id>/generate-audio
```

**Expected:** 401 Unauthorized error

### Test 6.4: Permission Check (Wrong User)
```bash
# User A creates research, User B tries to access
curl -X POST http://localhost:8000/research/session/<user_a_session>/generate-audio \
  -H "Authorization: Bearer <user_b_token>"
```

**Expected:** 403 Forbidden error

---

## Test 7: Performance Testing

### Purpose
Verify no performance degradation from new fields

### Steps

#### 7.1: Query Performance
```sql
-- Time the query (should be fast)
SET STATISTICS TIME ON
SELECT * FROM ResearchSessions WHERE source_type = 'image'
SET STATISTICS TIME OFF

-- Check index statistics
SELECT OBJECT_NAME(ps.object_id) as TableName,
       i.name as IndexName,
       ps.user_seeks,
       ps.user_scans,
       ps.user_lookups
FROM sys.dm_db_index_usage_stats ps
INNER JOIN sys.indexes i ON ps.object_id = i.object_id
WHERE OBJECT_NAME(ps.object_id) = 'ResearchSessions'
```

**Expected:**
- Queries using source_type index are fast
- Index is being used (user_seeks/scans > 0)

#### 7.2: Audio Table Performance
```sql
-- Verify audio operations are fast
SET STATISTICS TIME ON
SELECT COUNT(*) FROM EssayAudio
SET STATISTICS TIME OFF

-- Should complete in < 100ms
```

---

## Test 8: Data Integrity

### Purpose
Verify referential integrity and cascade deletes work correctly

### Steps

#### 8.1: Create Audio Record and Delete Session
```sql
-- Find a session with audio
DECLARE @session_id INT = (
    SELECT TOP 1 session_id FROM EssayAudio
    ORDER BY generated_at DESC
);

-- Verify audio exists
SELECT COUNT(*) FROM EssayAudio WHERE session_id = @session_id;
-- Expected: 1

-- Note: DO NOT actually delete, just verify the constraint exists
-- Verify foreign key
SELECT * FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS
WHERE CONSTRAINT_NAME = 'FK_EssayAudio_Sessions';

-- Expected: Should show "CASCADE" for DELETE_RULE
```

#### 8.2: Verify Unique Constraint
```sql
-- Try to insert duplicate audio for same session
-- This should fail
DECLARE @session_id INT = (SELECT TOP 1 session_id FROM EssayAudio)

INSERT INTO EssayAudio (session_id, audio_filename)
VALUES (@session_id, 'test.mp3')

-- Expected: Error about unique constraint
```

---

## Test 9: Migration Rollback Testing (Optional)

### Purpose
Verify migrations can be safely rolled back if needed

### Prerequisites
- [ ] Current database backup taken
- [ ] All tests passing

### Steps

```sql
-- 1. Verify tables exist
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_NAME IN ('EssayAudio', 'ResearchSessions');

-- 2. Check column exists
SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'ResearchSessions'
AND COLUMN_NAME = 'source_type';

-- 3. Run rollback scripts (from DATABASE_MIGRATION_GUIDE.md)
DROP TABLE IF EXISTS EssayAudio;

-- 4. Verify removal
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_NAME = 'EssayAudio';
-- Expected: No results

-- 5. Restore from backup to get back to working state
```

**Note:** Only do this if testing rollback procedures. Keep working database intact.

---

## Test 10: Backward Compatibility

### Purpose
Verify old code continues to work

### Steps

#### 10.1: Research Without Source Type
```bash
# Call /research/start without specifying source_type
curl -X POST http://localhost:8000/research/start \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'
```

**Expected:**
- ✅ Request succeeds (source_type is optional)
- ✅ Database defaults to source_type='text'

#### 10.2: Database Queries Without Filter
```sql
-- Old code that doesn't use source_type should still work
SELECT * FROM ResearchSessions
WHERE query LIKE '%machine%';

-- Should return results without error
```

---

## Final Verification Checklist

### Core Functionality
- [ ] Audio generation works for text research
- [ ] Audio generation works for image research
- [ ] Audio files are created and saved
- [ ] Audio records saved to EssayAudio table
- [ ] Source type tracking works correctly
- [ ] Backward compatibility maintained

### Database
- [ ] EssayAudio table exists
- [ ] ResearchSessions has source_type column
- [ ] ResearchSessions has source_metadata column
- [ ] All indexes created
- [ ] Foreign keys set up correctly
- [ ] Cascade deletes work

### API
- [ ] /research/start accepts source_type
- [ ] /research/session/{id}/generate-audio works
- [ ] Error handling proper
- [ ] Permission checks work

### Frontend
- [ ] Image upload sets source_type='image'
- [ ] Text query sets source_type='text'
- [ ] Audio generation UI responsive

---

## Testing Complete! ✅

If all tests pass with expected results:

✅ Implementation is working correctly
✅ Ready for production deployment
✅ All features functioning as designed
✅ No data integrity issues
✅ Performance is acceptable
✅ Error handling is robust

---

## Support

If any test fails:
1. Check error messages in logs
2. Review DATABASE_MIGRATION_GUIDE.md
3. Verify all migrations were run
4. Check API keys and configuration
5. See VALIDATION_CHECKLIST.md for detailed review
