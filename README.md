# 🧪 UIDAI Automated Testing Platform

> **AI-Powered End-to-End Testing Suite with Visual Test Recorder**

A comprehensive automated testing platform that combines AI-driven test generation with manual test recording capabilities. Built for testing complex web applications like UIDAI (Aadhaar) portals with intelligent discovery, generation, execution, and self-healing.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![React](https://img.shields.io/badge/react-18.0+-61DAFB)
![Playwright](https://img.shields.io/badge/playwright-1.40+-2EAD33)

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Testing Modes](#-testing-modes)
- [API Documentation](#-api-documentation)
- [Project Structure](#-project-structure)
- [Troubleshooting](#-troubleshooting)

---

## ✨ Features

### 🤖 AI-Powered Test Generation
- Automatic test case generation using Claude AI or local Ollama models
- Context-aware test creation based on discovered UI elements
- Multiple scenario support (smoke, regression, accessibility, etc.)
- Intelligent selector generation with fallback strategies

### 🎥 Visual Test Recorder
- Interactive browser-based test recording using Playwright Codegen
- Manual test creation with real-time action capture
- Automatic conversion to pytest format
- Skip AI generation when using recorder mode

### 🔍 Intelligent Discovery
- Multi-level page crawling (quick, balanced, deep)
- Smart element extraction (buttons, links, inputs, forms)
- Accessibility metadata capture
- Duplicate prevention with URL normalization

### 🧪 Test Execution
- Headed (visible) and headless browser modes
- Parallel test execution support
- Real-time progress tracking via WebSocket
- Screenshot and video recording on failures
- Artifact storage in MinIO/S3

### 🔧 Self-Healing
- Automatic test failure analysis
- AI-powered test repair
- Multiple healing attempts with retry logic
- Intelligent selector updates

### 📊 Comprehensive Reporting
- Real-time test execution dashboard
- Detailed phase-wise reports (Discovery, Generation, Execution)
- Pass/fail statistics with visual charts
- Downloadable test artifacts
- Print-friendly report views

---

## 🏗️ Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│  ┌─────────────┬─────────────┬──────────────┬─────────────┐ │
│  │  Dashboard  │   Progress  │  Test Config │   Reports   │ │
│  └─────────────┴─────────────┴──────────────┴─────────────┘ │
└───────────────────────┬─────────────────────────────────────┘
                        │ REST API / WebSocket
┌───────────────────────▼─────────────────────────────────────┐
│                   Backend (FastAPI)                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Pipeline Orchestrator                    │   │
│  │  ┌──────────┬──────────┬──────────┬─────────────┐   │   │
│  │  │ Recorder │Discovery │Generation│  Execution  │   │   │
│  │  └──────────┴──────────┴──────────┴─────────────┘   │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌─────▼─────┐ ┌──────▼──────┐
│  PostgreSQL  │ │   MinIO   │ │  Playwright │
└──────────────┘ └───────────┘ └─────────────┘
```

### Pipeline Flow

```
MODE: NORMAL (AI-Driven)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Discovery (10-30%)
   ├─ Launch browser
   ├─ Crawl pages (depth-based)
   ├─ Extract interactive elements
   └─ Save selectors + metadata
        ▼
2. Generation (40-60%)
   ├─ Analyze discovered elements
   ├─ Call AI (Claude/Ollama)
   ├─ Generate test cases
   └─ Save .py test files
        ▼
3. Execution (70-85%)
   ├─ Run pytest
   ├─ Capture screenshots/videos
   ├─ Upload artifacts to MinIO
   └─ Generate report
        ▼
4. Healing (90-100%) [if failures]
   ├─ Analyze failed tests
   ├─ AI suggests fixes
   ├─ Update test code
   └─ Re-run tests

MODE: RECORDER (Manual)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Recording (10-60%)
   ├─ Launch Playwright Codegen
   ├─ User performs actions
   ├─ Auto-capture as Python code
   └─ Save recorded test
        ▼
2. ⏭️  Skip Discovery
        ▼
3. ⏭️  Skip Generation
        ▼
4. Execution (70-100%)
   ├─ Run recorded test (headed mode)
   ├─ Capture artifacts
   └─ Generate report
```

---

## 🛠️ Tech Stack

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.10+ | Core backend language |
| **FastAPI** | 0.104+ | REST API framework |
| **Playwright** | 1.40+ | Browser automation |
| **Anthropic Claude** | Latest | AI test generation |
| **Ollama** | Latest | Local AI models |
| **SQLAlchemy** | 2.0+ | ORM for database |
| **PostgreSQL** | 14+ | Primary database |
| **MinIO** | Latest | Object storage |
| **Pytest** | 7.4+ | Test execution |
| **WebSocket** | - | Real-time updates |

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| **React** | 18.0+ | UI framework |
| **Chakra UI** | 2.8+ | Component library |
| **React Router** | 6.0+ | Routing |
| **Axios** | 1.6+ | HTTP client |
| **WebSocket** | - | Real-time updates |

---

## 🚀 Installation

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Git

### Quick Start

#### 1. Clone Repository
```bash
git clone https://github.com/your-org/uidai-testing-platform.git
cd uidai-testing-platform
```

#### 2. Setup Backend
```bash
cd server

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
playwright install-deps
```

#### 3. Setup Frontend
```bash
cd ../ui
npm install
```

#### 4. Setup Database (PostgreSQL)

**Option A: Docker**
```bash
docker run -d \
  --name uidai-postgres \
  -e POSTGRES_DB=uidai_testing \
  -e POSTGRES_USER=uidai_user \
  -e POSTGRES_PASSWORD=your_password \
  -p 5432:5432 \
  postgres:14
```

**Option B: Local**
```bash
# macOS
brew install postgresql@14
brew services start postgresql@14

# Create database
psql postgres
CREATE DATABASE uidai_testing;
CREATE USER uidai_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE uidai_testing TO uidai_user;
```

#### 5. Setup MinIO (Object Storage)
```bash
docker run -d \
  --name uidai-minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"
```

#### 6. Configure Environment

**Backend (.env)**
```bash
# server/.env
DATABASE_URL=postgresql://uidai_user:your_password@localhost:5432/uidai_testing

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=uidai-artifacts

# AI
ANTHROPIC_API_KEY=sk-ant-xxx
USE_OLLAMA=false

# Server
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:3000
```

**Frontend (.env)**
```bash
# ui/.env
REACT_APP_API_BASE=http://localhost:8000
```

#### 7. Initialize Database
```bash
cd server
source .venv/bin/activate
python -c "from src.database import init_db; init_db()"
```

#### 8. Start Services

**Terminal 1: Backend**
```bash
cd server
source .venv/bin/activate
python main.py
```

**Terminal 2: Frontend**
```bash
cd ui
npm start
```

**Access:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- MinIO Console: http://localhost:9001

---

## ⚙️ Configuration

### Test Presets

```python
# server/src/config.py
PRESETS = {
    "quick": {
        "level": 0,      # Homepage only
        "max_pages": 1,
        "timeout": 30
    },
    "balanced": {
        "level": 1,      # 1 level deep
        "max_pages": 5,
        "timeout": 60
    },
    "comprehensive": {
        "level": 2,      # 2 levels deep
        "max_pages": 20,
        "timeout": 120
    }
}
```

### AI Models

**Claude AI (Default)**
```bash
ANTHROPIC_API_KEY=sk-ant-xxx
USE_OLLAMA=false
```

**Local Ollama**
```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull model
ollama pull qwen2.5-coder:14b

# Configure
USE_OLLAMA=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:14b
```

---

## 📖 Usage

### 1. Create Test Run (UI)

1. Open http://localhost:3000
2. Click "New Test Run"
3. Configure:
   - **URL**: Target website
   - **Preset**: Quick/Balanced/Comprehensive
   - **Mode**: Headed/Headless
   - **Recorder**: Enable for manual recording
   - **Auto-Heal**: Enable self-healing
4. Click "Start Test"

### 2. Create Test Run (API)

```bash
curl -X POST http://localhost:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://uidai.gov.in/en/",
    "preset": "balanced",
    "mode": "headless",
    "useRecorder": false,
    "autoHeal": true,
    "scenario": "auto"
  }'
```

### 3. Monitor Progress

- Real-time progress bar
- WebSocket updates
- Phase indicators

### 4. View Results

- **Discovery**: Pages and elements found
- **Tests**: Generated test code
- **Results**: Pass/fail statistics
- **Report**: Comprehensive overview

---

## 🎯 Testing Modes

### Mode 1: AI-Driven (Normal)

**Use when:**
- Need comprehensive coverage
- Don't know exact scenarios
- Regression testing

**Flow:**
```
Discovery → Generation → Execution → Healing
```

**Config:**
```json
{
  "useRecorder": false,
  "preset": "comprehensive",
  "mode": "headless"
}
```

---

### Mode 2: Visual Recorder (Manual)

**Use when:**
- Testing specific user flows
- Complex interactions
- Want to see execution

**Flow:**
```
Recording → Execution (visible browser)
```

**Config:**
```json
{
  "useRecorder": true,
  "preset": "quick",
  "mode": "headed"
}
```

**Steps:**
1. Enable recorder toggle
2. Click "Start Test"
3. Browser opens with toolbar
4. Perform actions
5. Close browser
6. Test saved and executed

---

## 🔌 API Documentation

### Key Endpoints

#### Create Run
```http
POST /api/run
{
  "url": "https://example.com",
  "preset": "balanced",
  "useRecorder": false
}
```

#### Get Status
```http
GET /api/run/{runId}
```

#### Progress (WebSocket)
```javascript
ws://localhost:8000/api/ws/progress/{runId}
```

#### Get Results
```http
GET /api/run/{runId}/results
```

**Full docs:** http://localhost:8000/docs

---

## 📁 Project Structure

```
uidai-testing-platform/
├── server/                    # Backend
│   ├── main.py               # Entry point
│   ├── src/
│   │   ├── database.py       # Models
│   │   ├── config.py         # Config
│   │   ├── api/
│   │   │   └── routes.py     # Endpoints
│   │   └── tools/
│   │       ├── recorder.py   # Recorder
│   │       ├── discovery_enhanced.py
│   │       ├── generator.py  # AI generation
│   │       ├── runner.py     # Execution
│   │       └── healer.py     # Self-healing
│   └── requirements.txt
│
└── ui/                        # Frontend
    ├── src/
    │   ├── App.js
    │   └── views/
    │       └── agentic/
    │           ├── AgenticHome.jsx
    │           ├── ProgressView.jsx
    │           ├── ReportView.jsx
    │           ├── DiscoveryView.jsx
    │           ├── TestsView.jsx
    │           └── ResultsView.jsx
    └── package.json
```

---

## 🐛 Troubleshooting

### Playwright Issues
```bash
playwright install chromium
playwright install-deps
```

### Database Issues
```bash
# Check PostgreSQL
psql -U uidai_user -d uidai_testing

# Restart
brew services restart postgresql@14
```

### MinIO Issues
```bash
# Check container
docker ps | grep minio

# Restart
docker restart uidai-minio
```

### WebSocket Issues
```bash
# Check CORS in server/.env
CORS_ORIGINS=http://localhost:3000
```

### Common Errors

| Error | Solution |
|-------|----------|
| Browser not connected | `playwright install chromium` |
| Database error | Check credentials in `.env` |
| MinIO error | Check Docker container running |
| Import error | `pip install -r requirements.txt` |

---

## 📊 Performance

| Metric | Quick | Balanced | Comprehensive |
|--------|-------|----------|---------------|
| Pages | 1 | 5 | 20 |
| Tests | 2-3 | 5-8 | 15-25 |
| Time | 1-2 min | 3-5 min | 10-15 min |
| Coverage | ~20% | ~50% | ~80% |

---

## 🚀 Roadmap

### v1.1 (Q1 2025)
- User authentication
- Test scheduling
- Email notifications

### v1.2 (Q2 2025)
- Multi-browser support
- Mobile testing
- API testing

### v1.3 (Q3 2025)
- CI/CD integration
- Cloud deployment
- Team collaboration

---

## 📝 Key Features Summary

✅ AI-powered test generation (Claude/Ollama)
✅ Visual test recorder (Playwright Codegen)
✅ Intelligent page discovery
✅ Self-healing capabilities
✅ Real-time progress tracking
✅ Headed/headless browser modes
✅ Comprehensive reporting
✅ MinIO artifact storage
✅ WebSocket real-time updates
✅ Docker support

---

## 🙏 Acknowledgments

- Anthropic (Claude AI)
- Playwright Team
- FastAPI Framework
- React & Chakra UI
- Ollama Project

---

## 📞 Support

- **Documentation**: http://localhost:8000/docs
- **Issues**: GitHub Issues
- **Email**: yashtop@gmail.com

---

## 📄 License

MIT License - See LICENSE file

---

