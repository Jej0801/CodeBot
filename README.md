# CodeBot / ReviewBuddy

AI-Powered Code Review Assistant for Developers

## Overview

CodeBot is a production-quality software engineering project that helps software engineers improve code quality through AI-powered pull request reviews. When a GitHub Pull Request is opened, CodeBot analyzes the code and provides intelligent feedback.

## Tech Stack

**Backend:**
- Python 3.11
- FastAPI (async web framework)
- SQLAlchemy 2.0 (async ORM)
- PostgreSQL (database)
- Alembic (database migrations)

**Infrastructure:**
- Docker & Docker Compose
- Future: AWS ECS/EKS, RDS, SQS

## Project Structure

```
CodeBot-backend/
├── app/
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py          # Configuration management
│   ├── routes/
│   │   ├── __init__.py
│   │   └── health.py          # Health check endpoints
│   ├── __init__.py
│   ├── database.py            # Async SQLAlchemy setup
│   └── main.py                # FastAPI application
├── alembic/
│   ├── versions/              # Database migrations
│   ├── env.py                 # Alembic environment
│   └── script.py.mako         # Migration template
├── alembic.ini                # Alembic configuration
├── docker-compose.yaml        # Local development setup
├── Dockerfile                 # Container image
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (not in git)
├── .env.example               # Environment template
└── README.md
```

## Getting Started

### Prerequisites

- Docker Desktop installed and running
- Git

### Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd CodeBot/CodeBot-backend
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

3. **Start the services:**
   ```bash
   docker compose up --build
   ```

   This will:
   - Start PostgreSQL container
   - Run database migrations
   - Start FastAPI application on http://localhost:8000

### Testing the Installation

Once the services are running, test the endpoints:

1. **Basic health check:**
   ```bash
   curl http://localhost:8000/api/health
   ```
   Expected: `{"status":"healthy","service":"CodeBot API"}`

2. **Readiness check (includes database):**
   ```bash
   curl http://localhost:8000/api/health/ready
   ```
   Expected: `{"status":"ready","checks":{"database":"healthy"},...}`

3. **API documentation:**
   Visit http://localhost:8000/docs for interactive Swagger UI

### Database Migrations

**Create a new migration:**
```bash
docker compose exec api alembic revision --autogenerate -m "description"
```

**Apply migrations:**
```bash
docker compose exec api alembic upgrade head
```

**Rollback migration:**
```bash
docker compose exec api alembic downgrade -1
```

## Development

### Running Locally Without Docker

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Update .env for local development:**
   ```bash
   POSTGRES_HOST=localhost
   DATABASE_URL=postgresql+asyncpg://codebot:codebotpassword801@localhost:5432/codebot_dev
   ```

4. **Start PostgreSQL:**
   ```bash
   docker compose up db
   ```

5. **Run migrations:**
   ```bash
   alembic upgrade head
   ```

6. **Start the API:**
   ```bash
   uvicorn app.main:app --reload
   ```

## Phase 1: Infrastructure Foundation ✅

**Completed:**
- [x] FastAPI setup with async support
- [x] Docker and Docker Compose configuration
- [x] PostgreSQL database setup
- [x] Async SQLAlchemy with connection pooling
- [x] Alembic migrations setup
- [x] Health check endpoints (basic, readiness, liveness)
- [x] Configuration management with Pydantic Settings
- [x] Environment variable management

**Next: Phase 2 - Database Layer**
- Create database models (Users, Repositories, PullRequests, Reviews, Comments)
- Implement repository pattern
- Add CRUD operations

## Architecture Decisions

### Why Async?

We use async SQLAlchemy and FastAPI for:
- **Concurrency:** Handle multiple requests without blocking
- **Scalability:** Better resource utilization under load
- **Modern Python:** Leverages Python 3.11+ performance improvements

### Health Checks

Three types for Kubernetes/ECS:
- `/api/health` - Basic availability (load balancer)
- `/api/health/ready` - Database connectivity (readiness probe)
- `/api/health/live` - Process liveness (liveness probe)

### Configuration

Using Pydantic Settings for:
- Type validation
- Environment variable parsing
- 12-Factor App compliance
- Easy testing with dependency injection

## Common Issues

**Issue: "Cannot connect to Docker daemon"**
- Solution: Start Docker Desktop

**Issue: "Port 5432 already in use"**
- Solution: Stop existing PostgreSQL: `docker compose down`

**Issue: "Database connection failed"**
- Solution: Ensure database is healthy: `docker compose ps`

## Contributing

Follow these principles:
- SOLID principles
- Clean Architecture
- Service Layer Pattern
- Repository Pattern
- Dependency Injection
