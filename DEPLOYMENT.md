# AURA Research Agent - Deployment Guide

## Overview

This guide covers deploying the AURA Research Agent using Docker. The application uses environment variables to manage all secrets, ensuring security and enabling safe GitHub publication.

---

## Prerequisites

- Docker and Docker Compose installed
- Git installed
- Terminal/Command Prompt access
- (Optional) OpenSSL for JWT secret generation

---

## 1. Initial Setup

### 1.1 Clone the Repository

```bash
git clone https://github.com/your-org/AURA_Research_Agent.git
cd AURA_Research_Agent
```

### 1.2 Create Environment File

Copy the environment template and configure your secrets:

```bash
# Copy example to .env
cp .env.example .env

# Edit .env with your actual values
# On Windows: notepad .env
# On macOS/Linux: nano .env
```

### 1.3 Configure Environment Variables

Edit `.env` and set the following values:

#### API Keys (Required)
```
OPENAI_API_KEY=sk-your-actual-openai-key
SERPER_API_KEY=your-serper-api-key
TAVILY_API_KEY=your-tavily-api-key
ELEVENLABS_API_KEY=your-elevenlabs-api-key
```

#### JWT Secret (Generate New)

Generate a secure JWT secret using OpenSSL:

```bash
# On macOS/Linux/WSL:
openssl rand -base64 32

# On Windows (PowerShell):
[Convert]::ToBase64String((1..32 | ForEach-Object { [byte](Get-Random -Maximum 256) }))
```

Then set in `.env`:
```
JWT_SECRET_KEY=<your-generated-secret>
```

#### Database Password (Create Secure Password)

Set a strong database password (minimum 8 characters with uppercase, lowercase, number, special char):

```
DB_PASSWORD=YourSecurePassword123!
```

**Important**: The password must meet SQL Server requirements:
- At least 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character (!@#$%^&*)

### 1.4 Verify Environment File

Ensure `.env` is in the root directory and NOT committed to git:

```bash
# Verify .env exists
ls -la .env

# Verify git will NOT track .env
git status | grep ".env"  # Should NOT appear
```

---

## 2. Docker Startup

### 2.1 Build and Start Containers

```bash
# Start all containers in detached mode
docker-compose up -d

# Or, to see logs while starting:
docker-compose up
```

### 2.2 Monitor Initialization

Check the database initialization:

```bash
# Watch SQL Server logs
docker logs aura-sqlserver -f

# Expected output:
# "Waiting for SQL Server..."
# "SQL Server started"
# "Running schema.sql..."
# "Running migration: 001_..."
# "Database initialization complete!"
```

### 2.3 Verify All Services Are Running

```bash
# Check container status
docker ps

# Expected output:
# aura-sqlserver    - healthy (after ~40s)
# aura-backend      - Up and running
# aura-frontend     - Up and running
# aura-nginx        - Up and running
```

### 2.4 Test API Health

```bash
# Test main API
curl http://localhost:8000/

# Test health endpoint
curl http://localhost:8000/health

# Test readiness endpoint
curl http://localhost:8000/readiness
```

Expected response for `/health`:
```json
{
  "status": "healthy",
  "services": {
    "api": "running",
    "agents": "ready",
    "rag": "ready",
    "database": "connected",
    "auth": "ready",
    "api_keys": "configured",
    "disk_space": "available",
    "memory": "available"
  },
  "timestamp": "2026-02-15T10:30:00Z"
}
```

---

## 3. Verification Checklist

### Security
- [ ] `.env` file exists in root directory
- [ ] `.env` is NOT tracked by git (`git status` shows no `.env`)
- [ ] No hardcoded passwords in `docker-compose.yml`
- [ ] `DB_PASSWORD` in `.env` is strong (8+ chars, mixed case, number, special)
- [ ] `JWT_SECRET_KEY` is unique (generated with openssl)

### Database
- [ ] `docker logs aura-sqlserver` shows "Database initialization complete!"
- [ ] Database contains 14 tables (Users, ResearchSessions, Papers, etc.)
- [ ] All 4 migrations applied successfully

### API
- [ ] `curl http://localhost:8000/` returns 200 OK
- [ ] `curl http://localhost:8000/health` returns healthy status
- [ ] `curl http://localhost:8000/readiness` returns ready status
- [ ] Frontend accessible at http://localhost:3000

### Docker
- [ ] All 4 containers running: `docker ps`
- [ ] Backend container shows "healthy" status
- [ ] No container restart errors: `docker ps --no-trunc | grep aura`

---

## 4. Common Operations

### 4.1 Stop All Containers

```bash
docker-compose down
```

### 4.2 Stop and Remove Volumes (Full Reset)

```bash
# WARNING: This deletes all data!
docker-compose down -v
```

### 4.3 View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker logs aura-backend -f
docker logs aura-sqlserver -f
docker logs aura-frontend -f
```

### 4.4 Rebuild Containers

```bash
# Rebuild all images
docker-compose build

# Rebuild specific service
docker-compose build backend

# Start with fresh build
docker-compose build --no-cache
docker-compose up -d
```

### 4.5 Execute Commands in Containers

```bash
# Database query
docker exec -it aura-sqlserver /opt/mssql-tools18/bin/sqlcmd \
    -S localhost -U sa -P 'YourPassword123!' \
    -Q "SELECT COUNT(*) FROM AURA_Research.sys.tables"

# API logs
docker exec aura-backend tail -f logs/aura.log

# Frontend shell
docker exec -it aura-frontend sh
```

---

## 5. Troubleshooting

### Database Connection Failed

```bash
# Check SQL Server is running
docker logs aura-sqlserver

# Verify connection string
docker exec aura-backend python -c \
    "from aura_research.database.connection import get_db_connection; \
    db = get_db_connection(); print('Connected!' if db.test_connection() else 'Failed')"
```

### API Port Already in Use

```bash
# Change port in docker-compose.yml
# Find: ports: - "8000:8000"
# Change to: ports: - "8001:8000"
docker-compose down
docker-compose up -d
```

### Frontend Can't Connect to Backend

```bash
# Check backend is running
curl http://localhost:8000/health

# Check CORS configuration in docker-compose.yml
# Verify ALLOWED_ORIGINS includes frontend URL
```

### Containers Keep Restarting

```bash
# Check logs for errors
docker logs aura-backend
docker logs aura-frontend

# Try full reset
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

---

## 6. Production Deployment

For production deployment, consider:

1. **Use a secret management service** (AWS Secrets Manager, Azure Key Vault, Vault)
2. **Enable SSL/TLS** with valid certificates (Let's Encrypt)
3. **Configure database backups** (automated snapshots)
4. **Set up monitoring** (Prometheus, DataDog, New Relic)
5. **Enable logging** (ELK stack, CloudWatch)
6. **Use managed services** where possible (RDS, managed Kubernetes)
7. **Implement auto-scaling** based on load
8. **Regular security audits** and penetration testing
9. **Keep Docker images updated** with security patches
10. **Use private container registry** for sensitive images

---

## 7. Security Best Practices

### Environment Variables
- ✅ Use `.env` file for secrets (never commit to git)
- ✅ Keep API keys confidential
- ✅ Rotate JWT_SECRET_KEY regularly
- ✅ Use strong database passwords (16+ chars in production)

### Database
- ✅ Enable database encryption at rest
- ✅ Use parameterized queries (ORM handles this)
- ✅ Implement row-level security for multi-tenant
- ✅ Regular backups with off-site replication

### API
- ✅ Rate limiting enabled (10 req/hour for research endpoint)
- ✅ CORS configured for specific origins
- ✅ JWT validation on protected routes
- ✅ Health checks for monitoring

### Container Security
- ✅ Run containers as non-root user
- ✅ Use read-only filesystems where possible
- ✅ Scan images for vulnerabilities
- ✅ Keep base images updated

---

## 8. Support

For issues or questions:
- Check Docker logs: `docker logs <container-name>`
- Review application logs in `./logs/`
- Check `.env` file configuration
- Verify all API keys are set
- Ensure SQL Server is accessible

---

## Next Steps

1. ✅ Configure `.env` with your API keys
2. ✅ Start Docker containers: `docker-compose up -d`
3. ✅ Verify health: `curl http://localhost:8000/health`
4. ✅ Access frontend: http://localhost:3000
5. ✅ Register a user and test authentication
6. ✅ Submit a research query and verify essay generation

---

**Last Updated**: February 2026
**Version**: 2.0.0-production-ready
