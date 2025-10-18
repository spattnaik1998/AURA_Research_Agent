# AURA - Complete Setup & Usage Guide

## 🎯 Overview

AURA (Autonomous Unified Research Assistant) is a full-stack AI research application featuring:

- **Multi-Agent Research System**: 3 subordinate agents + 1 supervisor orchestrating parallel paper analysis
- **RAG Chatbot**: Interactive Q&A with persistent memory using LangGraph
- **Modern Web Interface**: React-style frontend with real-time status updates
- **Automated Workflow**: From query to synthesized essay with automatic tab switching

---

## 📋 Prerequisites

### Required Software:
- **Python 3.8+**
- **Node.js 16+** and npm
- **Git** (for version control)

### API Keys Required:
1. **OpenAI API Key** - For GPT-4o and embeddings
2. **Serper API Key** - For academic paper searches

---

## 🚀 Installation & Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/spattnaik1998/AURA_Research_Agent.git
cd AURA_Research_Agent
```

### Step 2: Set Up Environment Variables

Create a `.env` file in the project root:

```bash
# .env file
OPENAI_API_KEY=your_openai_api_key_here
SERPER_API_KEY=your_serper_api_key_here
```

### Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

---

## 🏃 Running the Application

### Method 1: Quick Start (Recommended)

Open **two terminal windows**:

#### Terminal 1 - Backend:
```bash
uvicorn aura_research.main:app --host 0.0.0.0 --port 8000
```

#### Terminal 2 - Frontend:
```bash
cd frontend
npm start
```

### Method 2: Development Mode (with auto-reload)

#### Terminal 1 - Backend with reload:
```bash
uvicorn aura_research.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Terminal 2 - Frontend with nodemon:
```bash
cd frontend
npm run dev
```

### Access the Application:
- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

---

## 💡 Using AURA

### Research Panel Tab

#### 1. Start a Research Session

1. Enter a research query (e.g., "quantum computing in cryptography")
2. Click **"Start Research"** button
3. Watch the real-time progress:
   - ⏳ **Fetching Papers** - Searching academic databases
   - 🔍 **Analyzing Papers** - Multi-agent parallel analysis
   - ✍️ **Synthesizing Essay** - GPT-4o generates comprehensive report

#### 2. Monitor Progress

The status tracker shows:
- **Papers Analyzed**: Real-time count
- **Agents Complete**: 0/3 → 1/3 → 2/3 → 3/3
- **Essay Word Count**: Updates as synthesis progresses

#### 3. Automatic Completion

When research completes:
- ✅ All progress steps turn green
- 🎉 Success notification appears
- ⏱️ After 2 seconds, **automatically switches to RAG Chatbot tab**
- 📥 Download button becomes available

---

### RAG Chatbot Tab

#### 1. Select a Research Session

- Dropdown menu lists all completed research sessions
- Format: `Session YYYYMMDD_HHMMSS`
- Select the session you want to query

#### 2. Ask Questions

**Example Questions:**
```
What are the main findings in this research?
```
```
Can you explain the methodology used?
```
```
What are the ethical considerations mentioned?
```
```
Compare the different approaches discussed
```

#### 3. Interactive Conversation

- Chat maintains context across messages
- Uses ReAct reasoning pattern (THOUGHT → ACTION → OBSERVATION → RESPONSE)
- Retrieves relevant context from FAISS vector store
- Conversation history persists per session

---

## 🔧 API Endpoints

### Research Endpoints

#### Start Research
```http
POST /research/start
Content-Type: application/json

{
  "query": "machine learning in healthcare"
}
```

**Response:**
```json
{
  "session_id": "20251018_133827",
  "status": "started",
  "message": "Research started for query: machine learning in healthcare"
}
```

#### Get Research Status
```http
GET /research/status/{session_id}
```

**Response:**
```json
{
  "session_id": "20251018_133827",
  "query": "machine learning in healthcare",
  "status": "running",
  "current_step": "analyzing",
  "progress": {
    "papers_analyzed": 15,
    "agents_completed": 2,
    "word_count": 0
  }
}
```

#### List Research Sessions
```http
GET /research/sessions
```

### Chat Endpoints

#### Send Message
```http
POST /chat/
Content-Type: application/json

{
  "message": "What are the main findings?",
  "session_id": "20251018_133827",
  "conversation_id": "user123"
}
```

#### Get Chat History
```http
GET /chat/history/{session_id}/{conversation_id}
```

#### List Chat Sessions
```http
GET /chat/sessions
```

---

## 📁 Project Structure

```
AURA_Research_Agent/
├── aura_research/                 # Backend (FastAPI)
│   ├── agents/                    # Multi-agent system
│   │   ├── base_agent.py         # Abstract base agent
│   │   ├── subordinate_agent.py  # Analysis agents (3x)
│   │   ├── supervisor_agent.py   # Orchestrator agent
│   │   ├── summarizer_agent.py   # Essay synthesis agent
│   │   ├── workflow.py           # LangGraph state machine
│   │   └── orchestrator.py       # Main entry point
│   │
│   ├── rag/                       # RAG chatbot system
│   │   ├── vector_store.py       # FAISS vector store
│   │   └── chatbot.py            # LangGraph memory chatbot
│   │
│   ├── routes/                    # API endpoints
│   │   ├── research.py           # Research orchestration
│   │   └── chat.py               # Chat endpoints
│   │
│   ├── utils/                     # Utilities
│   │   └── config.py             # Configuration
│   │
│   ├── storage/                   # Data storage
│   │   ├── essays/               # Generated essays (.txt)
│   │   ├── analysis/             # Research results (.json)
│   │   └── vector_store/         # FAISS indices
│   │
│   └── main.py                    # FastAPI app
│
├── frontend/                      # Frontend (Node.js)
│   ├── public/                    # Static files
│   │   ├── index.html            # Main UI
│   │   ├── app.js                # JavaScript logic
│   │   └── output.css            # Tailwind CSS
│   │
│   ├── src/
│   │   ├── server.js             # Express server
│   │   └── input.css             # Tailwind source
│   │
│   ├── package.json
│   └── tailwind.config.js
│
├── test_agents.py                 # Test multi-agent system
├── test_chatbot.py                # Test RAG chatbot
├── requirements.txt               # Python dependencies
├── .env                           # Environment variables
└── SETUP_AND_USAGE.md            # This file
```

---

## 🧪 Testing

### Test Multi-Agent Research
```bash
python test_agents.py
```

This will:
- Fetch 20 papers on "machine learning in healthcare"
- Analyze papers with 3 parallel agents
- Synthesize a comprehensive essay
- Initialize FAISS vector store

### Test RAG Chatbot
```bash
python test_chatbot.py
```

This will:
- List available research sessions
- Send test questions
- Display AI responses
- Show conversation history

### Test API Directly

Using curl:
```bash
# Start research
curl -X POST http://localhost:8000/research/start \
  -H "Content-Type: application/json" \
  -d '{"query":"quantum computing"}'

# Check status
curl http://localhost:8000/research/status/20251018_133827

# Send chat message
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message":"What are the key findings?",
    "session_id":"20251018_133827",
    "conversation_id":"test1"
  }'
```

---

## ⚙️ Configuration

### Backend Configuration

Edit `aura_research/utils/config.py`:

```python
# Model configuration
GPT_MODEL = "gpt-4o"              # GPT model for analysis
EMBEDDING_MODEL = "text-embedding-3-small"  # Embedding model

# Research parameters
MAX_PAPERS = 20                    # Papers to fetch per query
BATCH_SIZE = 7                     # Papers per subordinate agent
```

### Frontend Configuration

Edit `frontend/public/app.js`:

```javascript
// API endpoint
const API_BASE_URL = 'http://localhost:8000';

// Polling interval (milliseconds)
const POLLING_INTERVAL = 2000;  // 2 seconds
```

---

## 🐛 Troubleshooting

### Backend Issues

**Port 8000 already in use:**
```bash
# Windows
netstat -ano | findstr :8000
taskkill /F /PID <PID>

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

**Missing dependencies:**
```bash
pip install -r requirements.txt --upgrade
```

**API key errors:**
```bash
# Verify .env file exists
cat .env

# Check environment variables are loaded
python -c "from aura_research.utils.config import OPENAI_API_KEY; print(OPENAI_API_KEY[:10])"
```

### Frontend Issues

**Port 3000 already in use:**
```bash
# Change port in src/server.js
const PORT = process.env.PORT || 3001;
```

**npm install fails:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

**CORS errors:**
- Verify backend is running on port 8000
- Check browser console for specific errors
- Backend already allows all origins in `main.py`

### Research Workflow Issues

**Papers not fetching:**
- Check Serper API key is valid
- Verify internet connection
- Check Serper API quota

**Agent analysis errors:**
- Check OpenAI API key is valid
- Verify GPT-4o access
- Check OpenAI API quota

**Vector store initialization fails:**
- Ensure research completed successfully
- Check `storage/analysis/` directory has .json files
- Verify FAISS is installed: `pip install faiss-cpu`

---

## 📊 Performance Tips

### Backend Optimization

1. **Use async/await** properly for concurrent operations
2. **Increase worker count** for production:
   ```bash
   uvicorn aura_research.main:app --workers 4
   ```
3. **Enable caching** for frequent queries
4. **Use Redis** for session storage instead of in-memory

### Frontend Optimization

1. **Reduce polling frequency** for completed sessions
2. **Implement WebSocket** for real-time updates
3. **Add request debouncing** for chat input
4. **Cache session list** to reduce API calls

---

## 🔐 Security Considerations

### Production Deployment

1. **Environment Variables**: Never commit `.env` file
2. **CORS Configuration**: Restrict allowed origins in `main.py`
3. **API Rate Limiting**: Implement rate limiting middleware
4. **Input Validation**: Sanitize all user inputs
5. **HTTPS**: Use SSL certificates in production
6. **Authentication**: Add user authentication for multi-user deployment

---

## 📈 Monitoring & Logging

### Backend Logs

```bash
# View real-time logs
uvicorn aura_research.main:app --log-level debug

# Save logs to file
uvicorn aura_research.main:app 2>&1 | tee backend.log
```

### Frontend Logs

Check browser console:
- F12 → Console tab
- Look for error messages
- Monitor API requests in Network tab

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -m "Add feature"`
4. Push to branch: `git push origin feature-name`
5. Open pull request

---

## 📝 License

MIT License - See LICENSE file for details

---

## 🆘 Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review API documentation at `/docs`

---

## 🎉 Quick Reference

### Essential Commands

```bash
# Start backend
uvicorn aura_research.main:app --host 0.0.0.0 --port 8000

# Start frontend
cd frontend && npm start

# Run tests
python test_agents.py
python test_chatbot.py

# Check backend health
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs
```

### Key URLs

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

---

**Built with ❤️ using Claude Code**
