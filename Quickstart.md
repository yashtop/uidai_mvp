# 🚀 Quick Start Guide

## 5-Minute Setup

### 1. Prerequisites
```bash
# Check versions
python --version  # Need 3.10+
node --version    # Need 18+
```

### 2. Clone & Install
```bash
# Clone repo
git clone <repo-url>
cd uidai-testing-platform

# Backend
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Frontend
cd ../ui
npm install
```

### 3. Setup Services
```bash
# PostgreSQL (Docker)
docker run -d \
  --name uidai-postgres \
  -e POSTGRES_DB=uidai_testing \
  -e POSTGRES_USER=uidai_user \
  -e POSTGRES_PASSWORD=password123 \
  -p 5432:5432 \
  postgres:14

# MinIO (Docker)
docker run -d \
  --name uidai-minio \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"
```

### 4. Configure
```bash
# Backend .env (server/.env)
cat > server/.env << EOF
DATABASE_URL=postgresql://uidai_user:password123@localhost:5432/uidai_testing
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
ANTHROPIC_API_KEY=sk-ant-your-key-here
USE_OLLAMA=false
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:3000
EOF

# Frontend .env (ui/.env)
cat > ui/.env << EOF
REACT_APP_API_BASE=http://localhost:8000
EOF
```

### 5. Initialize Database
```bash
cd server
source .venv/bin/activate
python -c "from src.database import init_db; init_db()"
```

### 6. Start!
```bash
# Terminal 1: Backend
cd server
source .venv/bin/activate
python main.py

# Terminal 2: Frontend
cd ui
npm start
```

### 7. Access
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## First Test Run

### Option 1: AI Mode (Auto)
1. Open http://localhost:3000
2. Click "New Test Run"
3. Enter URL: `https://uidai.gov.in/en/`
4. Select: Balanced, Headless
5. Click "Start Test"
6. Watch progress!

### Option 2: Recorder Mode (Manual)
1. Open http://localhost:3000
2. Click "New Test Run"
3. Enter URL: `https://uidai.gov.in/en/`
4. Toggle "Visual Test Recorder" ON
5. Click "Start Test"
6. Browser opens → Perform actions
7. Close browser → Test runs!

---

## Common Commands

### Backend
```bash
# Start server
cd server
source .venv/bin/activate
python main.py

# Run tests
pytest tests/ -v

# Check logs
tail -f logs/app.log
```

### Frontend
```bash
# Start dev server
npm start

# Build for production
npm run build

# Run tests
npm test
```

### Database
```bash
# Connect to DB
psql -U uidai_user -d uidai_testing

# Reset database
python -c "from src.database import reset_db; reset_db()"
```

### Docker
```bash
# Check services
docker ps

# View logs
docker logs uidai-postgres
docker logs uidai-minio

# Restart
docker restart uidai-postgres
docker restart uidai-minio

# Stop all
docker stop uidai-postgres uidai-minio
```

---

## Troubleshooting

### Playwright not found
```bash
cd server
source .venv/bin/activate
playwright install chromium
playwright install-deps
```

### Database connection failed
```bash
# Check container
docker ps | grep postgres

# Restart
docker restart uidai-postgres

# Check credentials in .env
```

### Frontend won't start
```bash
cd ui
rm -rf node_modules package-lock.json
npm install
npm start
```

### MinIO connection failed
```bash
docker restart uidai-minio
# Access console: http://localhost:9001
# Login: minioadmin / minioadmin
```

---

## Project Structure (Simplified)

```
project/
├── server/
│   ├── main.py              ← Start backend
│   ├── .env                 ← Config
│   ├── requirements.txt     ← Dependencies
│   └── src/
│       ├── tools/
│       │   ├── recorder.py      ← Visual recorder
│       │   ├── discovery_enhanced.py
│       │   ├── generator.py     ← AI generation
│       │   └── runner.py        ← Test execution
│       └── api/
│           └── routes.py        ← API endpoints
│
└── ui/
    ├── src/
    │   └── views/
    │       └── agentic/
    │           ├── AgenticHome.jsx    ← Main page
    │           ├── ProgressView.jsx   ← Progress
    │           └── ReportView.jsx     ← Results
    ├── .env                 ← Config
    └── package.json         ← Dependencies
```

---

## Environment Variables Reference

### Backend (.env)
```bash
# Required
DATABASE_URL=postgresql://user:pass@host:5432/db
ANTHROPIC_API_KEY=sk-ant-xxx

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Optional
USE_OLLAMA=false
HOST=0.0.0.0
PORT=8000
DEBUG=true
```

### Frontend (.env)
```bash
REACT_APP_API_BASE=http://localhost:8000
```

---

## Testing Checklist

### Before First Run
- [ ] PostgreSQL running
- [ ] MinIO running
- [ ] Database initialized
- [ ] Playwright installed
- [ ] .env files configured
- [ ] API key set (if using Claude)

### Test AI Mode
- [ ] URL entered
- [ ] Preset selected
- [ ] Start test clicked
- [ ] Progress shows phases
- [ ] Results display
- [ ] Report accessible

### Test Recorder Mode
- [ ] Recorder toggle ON
- [ ] Browser opens
- [ ] Actions recorded
- [ ] Browser closed
- [ ] Test executes
- [ ] Results show

---

## Next Steps

1. ✅ Complete setup
2. ✅ Run first test
3. ✅ Check results
4. 📚 Read full README.md
5. 🛠️ Customize configuration
6. 🚀 Deploy to production

---

**Need help?**
- Full docs: README.md
- API docs: http://localhost:8000/docs
- Issues: GitHub Issues

---
