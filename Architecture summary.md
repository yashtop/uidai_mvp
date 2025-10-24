# 🏗️ Technical Architecture

## System Overview

Full-stack testing platform combining AI test generation with manual recording.

## High-Level Architecture

```
Frontend (React + Chakra UI)
    ↓ REST API / WebSocket
Backend (FastAPI + Python)
    ↓
Services (Playwright, AI, Storage)
    ↓
Data (PostgreSQL, MinIO, File System)
```

## Pipeline Flow

### AI Mode
```
Discovery → Generation → Execution → Healing
```

### Recorder Mode  
```
Recording → Execution (skip discovery & generation)
```

## Key Components

### 1. Frontend
- React 18 with Chakra UI
- Real-time WebSocket updates
- Responsive dashboard
- Progress tracking

### 2. Backend
- FastAPI for REST API
- SQLAlchemy + PostgreSQL
- WebSocket for real-time
- Async task execution

### 3. Services
- **Recorder**: Playwright Codegen
- **Discovery**: Page crawler
- **Generator**: AI (Claude/Ollama)
- **Runner**: Pytest execution
- **Healer**: Auto-fix failures
- **Storage**: MinIO artifacts

## Data Flow

```
User → API → Pipeline → Database
               ↓
          WebSocket → UI (real-time)
               ↓
         Artifacts → MinIO
```

## Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Frontend | React, Chakra UI |
| Backend | FastAPI, Python 3.10+ |
| Database | PostgreSQL 14+ |
| Storage | MinIO (S3-compatible) |
| Browser | Playwright |
| AI | Claude API, Ollama |
| Testing | Pytest |

## Scalability

- Horizontal scaling ready
- Task queue support (future)
- Microservices ready (future)

*See full ARCHITECTURE.md for details*