# AURA Research Agent - Production Hardening Checkpoint
**Date**: 2026-02-15
**Status**: Week 1, Task 1.1 Complete
**Production Readiness**: 45/100 → Target 75+/100

---

## What We're Doing

Implementing a comprehensive 3-week production hardening sprint to make the AURA Research Agent deployment-ready for 100+ concurrent users.

**Time Commitment**: 10 hours/week
**Timeline**: 3 weeks for Week 1 (Feb 15 - Mar 7), then Weeks 2-3 (optional, based on beta feedback)

---

## Current Status: Task 1.1 Rate Limiting ✅ COMPLETE

### What Was Implemented

**Goal**: Protect expensive research endpoint from abuse/cost explosion

**Solution**: Slowapi rate limiting middleware
- Research endpoint: `10 requests/hour` (prevents $1,000+ API cost abuse)
- Chat endpoint: `50 messages/hour`
- Login endpoint: `5 attempts/15 minutes` (brute force protection)
- Export endpoint: `20 exports/hour`
- Shared limiter instance for all routes

**Files Modified**:
1. `requirements.txt` - Added `slowapi>=0.1.9`
2. `aura_research/main.py` - Registered limiter, added 429 error handler
3. `aura_research/utils/rate_limiter.py` - NEW shared limiter module
4. `aura_research/routes/research.py` - 3 endpoints with @limiter decorators
5. `aura_research/routes/auth.py` - Login with 5/15min limit
6. `aura_research/routes/chat.py` - Chat with 50/hour limit

**Key Technical Decisions**:
- Used shared limiter instance (slowapi best practice)
- Parameter naming: HTTP request → `request`, body → `body` (avoid slowapi conflicts)
- IP-based limiting via `get_remote_address()`
- Custom 429 handler returns JSON error response

**Verification**:
```bash
python -c "from aura_research.main import app; print('App imported successfully')"
# Output: App imported successfully ✓
```

---

## What's Next: Remaining Week 1 Tasks

### Priority Order (Highest Risk First)

#### Task 1.3: Password Hashing (4 hours)
**Current Risk**: SHA-256 hashing vulnerable to brute force (1B hashes/second)
**Solution**: Upgrade to bcrypt (200-500ms per verify)
- Files: `auth_service.py`, `requirements.txt`
- Add `passlib[bcrypt]>=1.7.4`
- Replace SHA-256 with bcrypt in password hashing

#### Task 1.2: Connection Pooling (5 hours)
**Current Risk**: Single DB connection bottlenecks at 50+ concurrent users
**Solution**: Implement pyodbc connection pooling (20-50 connections)
- Files: `database/connection.py`, repository files
- Add connection health checks
- Implement checkout/return mechanism

#### Task 1.5: Docker Secrets (2 hours) - QUICK WIN
**Current Risk**: SQL_SA password hardcoded in docker-compose.yml
**Solution**: Move to `.env` file
- Files: `docker-compose.yml`, `.env.example`
- Add SQL_SA_PASSWORD environment variable
- Update README with setup instructions

#### Task 1.4: Input Validation (5 hours)
**Current Risk**: No query length limits, no format validation
**Solution**: Add Pydantic validators
- Files: `research.py`, `auth.py`, `chat.py`
- Query max: 500 chars, Message max: 2000 chars
- Email validation with MX record check
- Username blacklist (admin, root, system)

#### Task 1.6: Health Checks (3 hours)
**Current Risk**: Blind to OpenAI API, disk space, memory failures
**Solution**: Enhanced `/health` and `/readiness` endpoints
- Files: `main.py`, new `health_service.py`
- Check DB, OpenAI, disk space, memory usage
- Return detailed status JSON

#### Task 1.7: CORS Hardening (2 hours)
**Current Risk**: CORS allows all origins (permissive default)
**Solution**: Environment-based origin whitelist
- Files: `main.py`, `config.py`, `.env.example`
- Default to `localhost:3000` for dev
- Require explicit config for production

**Total Remaining Week 1**: 21 hours (should take ~2 weeks at 10 hrs/week)

---

## How to Get Context Next Session

### Option 1: Use `/remember` Command
If available in your Claude Code setup, you can ask Claude to remember:
```
/remember Save the current production hardening context:
- Task 1.1 (Rate Limiting) is COMPLETE
- Next task is 1.3 (Password Hashing with bcrypt)
- 21 hours remaining in Week 1
- Full checkpoint at PRODUCTION_HARDENING_CHECKPOINT.md
```

### Option 2: Reference This File
Simply tell Claude: "Please review PRODUCTION_HARDENING_CHECKPOINT.md for context"

### Option 3: Check Task List
```bash
# See all pending tasks
TaskList  # Shows 7 tasks, #1 completed, #2-7 pending
```

---

## Testing / Validation

### Rate Limiting (Already Verified)
✅ App imports successfully
✅ Limiter registered with FastAPI
✅ All 5 decorated endpoints ready
✅ No syntax errors

### Next Validations
- [ ] Rate limiting actually blocks requests after limit (integration test)
- [ ] Error response returns 429 with proper headers
- [ ] Bcrypt password hashing working with existing SHA-256 passwords
- [ ] Connection pool shows 20-50 connections under load
- [ ] `/health` returns status of all dependencies
- [ ] CORS blocks unauthorized origins

---

## Key Metrics to Track

**Production Readiness Score**: Currently 45/100
- Testing: 5% (→ 50% by end of Week 2)
- Security: 60% (→ 90% by end of Week 1)
- Monitoring: 20% (→ 70% by end of Week 2)
- Resilience: 10% (→ 80% by end of Week 3)

**Target After Week 1**: 60/100
**Target After Weeks 1-3**: 75+/100

---

## Important Project Context

**AURA Research Agent** is a multi-agent research platform that:
- Fetches academic papers via Serper/Tavily APIs
- Analyzes papers with subordinate agents
- Generates essays with quality scoring
- Exports to PDF with citations (APA/MLA/Chicago)
- Provides RAG chatbot for Q&A
- Requires JWT authentication

**Current Deployment**: Docker Compose with FastAPI + SQL Server
**Target Deployment**: Production cloud (AWS/Azure/GCP) with 100+ users

**Critical External APIs**:
- OpenAI (GPT-4o for analysis) - 🔑 KEY
- Serper (Google Scholar papers)
- Tavily (Web search fallback)
- ElevenLabs (Text-to-speech audio)

---

## Quick Command Reference

```bash
# Test app loads
cd C:\Users\91838\Downloads\AURA_Research_Agent
python -c "from aura_research.main import app; print('OK')"

# Check current tasks
TaskList

# Get specific task details
TaskGet taskId=2  # Task 1.3 Password Hashing

# Update task status when done
TaskUpdate taskId=2 status=completed
```

---

## Contact Points

If you need to:
- **Continue production hardening**: Review tasks #2-7 above
- **Test rate limiting**: Start Docker, make 11 research requests to `/research/start`
- **Launch beta**: Complete Week 1, then deploy to staging
- **Get full plan details**: See end of initial plan message for complete 85-hour breakdown

---

**Last Updated**: 2026-02-15 20:00 UTC
**Next Checkpoint**: After Task 1.3 (Password Hashing)
