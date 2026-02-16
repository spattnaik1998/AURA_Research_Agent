# AURA - Autonomous Unified Research Assistant

<div align="center">

**An AI-powered multi-agent research system that automates academic paper discovery, analysis, and synthesis**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![LangChain](https://img.shields.io/badge/LangChain-0.1.20-orange.svg)](https://langchain.com)
[![Production Readiness](https://img.shields.io/badge/Production_Readiness-75%25-yellow.svg)](#production-readiness)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## Overview

AURA (Autonomous Unified Research Assistant) is a sophisticated multi-agent system designed to streamline academic research workflows. It leverages GPT-4o and LangGraph to orchestrate multiple AI agents that collaboratively fetch, analyze, and synthesize research papers into comprehensive literature reviews.

### Key Capabilities

- **Automated Paper Discovery** - Fetches relevant papers from Google Scholar, Semantic Scholar, and arXiv
- **Multi-Agent Analysis** - Parallel processing of papers using supervisor-subordinate agent architecture
- **RAG-Powered Chatbot** - Ask questions about your research with context-aware responses
- **Knowledge Graph Visualization** - Interactive graph showing relationships between papers, concepts, and authors
- **Research Gap Identification** - AI-generated research questions and gap analysis
- **Multi-Language Support** - Chat responses in English, French, Chinese, and Russian

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Express.js)                    │
│                    Tailwind CSS + Vanilla JS                     │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend (Python)                    │
├─────────────────────────────────────────────────────────────────┤
│  /research    │  /chat    │  /graph    │  /ideation   │  /auth  │
└───────┬───────┴─────┬─────┴─────┬──────┴──────┬───────┴────┬────┘
        │             │           │             │            │
        ▼             ▼           ▼             ▼            ▼
┌───────────────────────────────────────────────────────────────┐
│                     Multi-Agent System (LangGraph)             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│  │ Supervisor  │──│ Subordinate │──│ Summarizer Agent    │   │
│  │   Agent     │  │  Agents(5)  │  │ (Essay Generation)  │   │
│  └─────────────┘  └─────────────┘  └─────────────────────┘   │
└───────────────────────────────────────────────────────────────┘
        │             │           │             │
        ▼             ▼           ▼             ▼
┌───────────────────────────────────────────────────────────────┐
│                    SQL Server Database                         │
│  Sessions │ Papers │ Analyses │ Essays │ Chat │ Graphs │ Users │
└───────────────────────────────────────────────────────────────┘
```

### Agent Workflow

1. **Orchestrator** - Coordinates the entire research pipeline
2. **Supervisor Agent** - Manages task distribution and monitors subordinate progress
3. **Subordinate Agents** (up to 5) - Analyze papers in parallel with ReAct reasoning
4. **Summarizer Agent** - Synthesizes all analyses into a cohesive literature review

---

## Features

### 1. Research Pipeline
- Enter a research query and let AURA fetch and analyze relevant papers
- Real-time progress tracking with WebSocket updates
- Automated essay generation with proper citations

### 2. RAG Chatbot
- Chat about your research using vector similarity search (FAISS)
- Context-aware responses grounded in your analyzed papers
- Conversation history persistence

### 3. Knowledge Graph
- Interactive visualization of research concepts
- Node types: Papers, Concepts, Authors, Methods
- Community detection and centrality analysis
- Path finding between concepts

### 4. Research Ideation
- Automatic identification of research gaps
- AI-generated research questions scored by:
  - Novelty, Feasibility, Clarity, Impact, Specificity

### 5. User Authentication
- JWT-based authentication
- Role-based access (user, researcher, admin)
- Session tracking and audit logging

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Express.js, Tailwind CSS, Vanilla JavaScript |
| **Backend** | FastAPI, Python 3.10+ |
| **AI/ML** | OpenAI GPT-4o, LangChain, LangGraph |
| **Vector Store** | FAISS (faiss-cpu) |
| **Database** | SQL Server with Windows Authentication |
| **Authentication** | PyJWT |

---

## Installation

### Prerequisites

- Python 3.10 or higher
- Node.js 18+ and npm
- SQL Server (with ODBC Driver 17)
- OpenAI API key
- Serper API key (for Google Scholar search)

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/AURA_Research_Agent.git
cd AURA_Research_Agent
```

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

### 4. Environment Configuration

Create a `.env` file in the root directory:

```env
# API Keys
OPENAI_API_KEY=your_openai_api_key_here
SERPER_API_KEY=your_serper_api_key_here

# Database Configuration
DB_SERVER=your_server_name
DB_DATABASE=AURA_Research

# Optional: Debug Mode
AURA_DEBUG_MODE=false
```

### 5. Database Setup

Run the SQL schema in SQL Server Management Studio:

```bash
# Execute Table_Creation.sql or database/schema.sql
```

---

## Usage

### Starting the Application

**Terminal 1 - Backend:**
```bash
python -m aura_research.main
# Server runs on http://localhost:8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
# Server runs on http://localhost:3000
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/research/start` | POST | Start a new research session |
| `/research/status/{session_id}` | GET | Get research progress |
| `/chat/` | POST | Send message to RAG chatbot |
| `/chat/sessions` | GET | List available sessions |
| `/graph/build/{session_id}` | POST | Build knowledge graph |
| `/graph/data/{session_id}` | GET | Get graph data |
| `/ideation/generate/{session_id}` | POST | Generate research questions |
| `/auth/register` | POST | Register new user |
| `/auth/login` | POST | User login |
| `/health` | GET | Health check |

---

## Project Structure

```
AURA_Research_Agent/
├── aura_research/
│   ├── agents/                 # Multi-agent system
│   │   ├── orchestrator.py     # Main coordinator
│   │   ├── supervisor_agent.py # Task manager
│   │   ├── subordinate_agent.py# Paper analyzers
│   │   ├── summarizer_agent.py # Essay generator
│   │   └── workflow.py         # LangGraph workflow
│   ├── database/
│   │   ├── connection.py       # SQL Server connection
│   │   └── repositories/       # Data access layer
│   ├── graph/
│   │   ├── graph_builder.py    # Knowledge graph construction
│   │   └── graph_analyzer.py   # Graph metrics
│   ├── rag/
│   │   ├── chatbot.py          # RAG chatbot
│   │   └── vector_store.py     # FAISS vector store
│   ├── routes/                 # API endpoints
│   │   ├── research.py
│   │   ├── chat.py
│   │   ├── graph.py
│   │   ├── ideation.py
│   │   └── auth.py
│   ├── services/               # Business logic
│   │   ├── db_service.py
│   │   └── auth_service.py
│   ├── storage/                # Generated files
│   └── main.py                 # FastAPI app
├── frontend/
│   ├── public/
│   │   ├── index.html          # Main application
│   │   ├── landing.html        # Landing page
│   │   ├── app.js              # Frontend logic
│   │   └── output.css          # Tailwind CSS
│   └── src/
│       └── server.js           # Express server
├── database/
│   └── schema.sql              # Database schema
├── Table_Creation.sql          # SQL Server tables
├── requirements.txt            # Python dependencies
└── README.md
```

---

## Database Schema

The application uses 13 interconnected tables:

- **Users** - User accounts and authentication
- **ResearchSessions** - Research queries and status
- **Papers** - Fetched paper metadata
- **PaperAnalyses** - AI-generated paper analyses
- **Essays** - Synthesized literature reviews
- **ChatConversations** - Chat session metadata
- **ChatMessages** - Individual chat messages
- **GraphNodes** - Knowledge graph nodes
- **GraphEdges** - Knowledge graph relationships
- **ResearchGaps** - Identified research gaps
- **ResearchQuestions** - Generated research questions
- **VectorEmbeddings** - Stored embeddings (optional)
- **AuditLog** - Activity tracking

---

## Configuration

### Agent Configuration (`config.py`)

```python
MAX_SUBORDINATE_AGENTS = 5  # Parallel analysis agents
BATCH_SIZE = 10             # Papers per agent
GPT_MODEL = "gpt-4o"        # LLM model
EMBEDDING_MODEL = "text-embedding-3-small"
CHUNK_SIZE = 1000           # RAG chunk size
CHUNK_OVERLAP = 200         # Chunk overlap
```

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## Production Readiness

**Current Status**: 75% (Week 2 Complete)

### Completed (Week 1-2)
✅ Security hardening (rate limiting, password hashing, Docker secrets)
✅ Health checks and auto-initialization
✅ Structured JSON logging with automatic error tracking
✅ Prometheus metrics for operational monitoring
✅ 22+ unit and integration tests
✅ 5-minute timeout implementation with graceful degradation
✅ Tavily API fallback for resilience
✅ Validation guardrails relaxation (3-phase)

### In Progress (Week 3)
⏳ Redis caching layer (40-60% cost reduction)
⏳ Circuit breaker pattern (prevent cascade failures)
⏳ Alembic database migrations (zero-downtime schema updates)
⏳ Celery background task queue (non-blocking research API)

**Target**: 85%+ for beta launch

See [PRODUCTION_HARDENING_CHECKPOINT.md](PRODUCTION_HARDENING_CHECKPOINT.md) for detailed status.

---

## Documentation

- **[CHANGELOG.md](CHANGELOG.md)** - All notable changes and bugfixes
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment instructions and Docker setup
- **[TESTING_QUICK_REFERENCE.md](TESTING_QUICK_REFERENCE.md)** - Testing guide and test execution
- **[PRODUCTION_HARDENING_CHECKPOINT.md](PRODUCTION_HARDENING_CHECKPOINT.md)** - Production readiness tracker

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [LangChain](https://langchain.com) - LLM application framework
- [LangGraph](https://github.com/langchain-ai/langgraph) - Multi-agent orchestration
- [FastAPI](https://fastapi.tiangolo.com) - Modern Python web framework
- [FAISS](https://github.com/facebookresearch/faiss) - Vector similarity search
- [Tailwind CSS](https://tailwindcss.com) - Utility-first CSS framework

---

<div align="center">

**Built with AI, for Researchers**

</div>
