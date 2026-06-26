# CodeBot Technical Documentation

**Last Updated:** 2026-06-22
**Project:** AI-Powered Code Review Assistant
**Status:** Phase 1 Complete (Infrastructure Foundation)

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Technology Stack Integration](#technology-stack-integration)
3. [Module Documentation](#module-documentation)
4. [Data Flow](#data-flow)
5. [Change Log](#change-log)

---

## Architecture Overview

CodeBot follows a **Clean Architecture** pattern with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Application                   │
│                      (app/main.py)                       │
└───────────────────┬─────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌───────────────┐      ┌───────────────┐
│    Routes     │      │  Health Check │
│  (app/routes) │      │  (monitoring) │
└───────┬───────┘      └───────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│       Database Dependency Layer       │
│         (app/database.py)             │
│   - Session Management                │
│   - Connection Pooling                │
└───────┬───────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│      PostgreSQL Database              │
│   - Async Connection (asyncpg)        │
│   - Managed by Docker Compose         │
└───────────────────────────────────────┘
```

---

## Technology Stack Integration

### 1. FastAPI → SQLAlchemy → PostgreSQL Pipeline

**Flow:** HTTP Request → FastAPI Router → Dependency Injection → Async SQLAlchemy → PostgreSQL

```python
# How technologies work together:
# 1. FastAPI receives HTTP request
# 2. Calls route handler with injected dependencies
# 3. get_db() provides async database session
# 4. SQLAlchemy translates Python to SQL
# 5. asyncpg executes queries against PostgreSQL
# 6. Results flow back through the stack
```

### 2. Configuration Management Chain

**Flow:** .env file → Pydantic Settings → Application Configuration

- **Environment Variables (.env)** → Loaded at startup
- **Pydantic Settings** → Validates and parses configuration
- **lru_cache** → Creates singleton Settings instance
- **Dependency Injection** → Makes settings available throughout app

### 3. Docker Orchestration

**Services Communication:**
```
┌──────────────┐         Network: codebot-network
│  API Service │ ←──────→ Container Name: api
│  (FastAPI)   │         Port: 8000 → host:8000
└──────┬───────┘
       │ Connects to
       ▼
┌──────────────┐
│  DB Service  │         Container Name: db
│ (PostgreSQL) │         Port: 5432 (internal only)
└──────────────┘
```

---

## Module Documentation

### **app/main.py**

**Purpose:** Application entry point and FastAPI instance configuration

**Functions:**

#### `app = FastAPI(title="CodeBot API", version="1.0")`
- **Type:** FastAPI Application Instance
- **Configuration:**
  - `title`: API documentation title
  - `version`: API version for OpenAPI docs
- **Integrations:**
  - Registers health check router from `app/routes/health.py`
  - Mounts all endpoints under `/api` prefix
  - Auto-generates OpenAPI/Swagger documentation at `/docs`

#### `root()`
- **Route:** `GET /`
- **Purpose:** Basic root endpoint to verify API is running
- **Returns:** `{"message": "🚀 CodeBot API is running successfully!"}`
- **Use Case:** Quick check that server started successfully
- **Integration:** Standalone endpoint, no database dependency

---

### **app/core/config.py**

**Purpose:** Centralized configuration management using Pydantic Settings

**Classes:**

#### `Settings(BaseSettings)`
- **Inherits:** `pydantic_settings.BaseSettings`
- **Purpose:** Type-safe application configuration with validation
- **Technology Integration:**
  - Uses **Pydantic** for automatic type validation
  - Reads from `.env` file automatically
  - Follows **12-Factor App** methodology (config via environment)

**Attributes:**

| Attribute | Type | Default | Purpose | Required |
|-----------|------|---------|---------|----------|
| `app_name` | str | "CodeBot API" | Application name | No |
| `debug_mode` | bool | True | Enable debug logging | No |
| `app_host` | str | "0.0.0.0" | Server bind address | No |
| `app_port` | int | 8000 | Server port | No |
| `secret_key` | str | - | Security key for JWT/sessions | **Yes** |
| `postgres_user` | str | - | Database username | **Yes** |
| `postgres_password` | str | - | Database password | **Yes** |
| `postgres_db` | str | - | Database name | **Yes** |
| `postgres_host` | str | "db" | Database host (container name) | No |
| `postgres_port` | int | 5432 | Database port | No |
| `database_url` | str | - | Full database connection URL | **Yes** |

**Properties:**

#### `async_database_url` (property)
- **Returns:** str
- **Purpose:** Provides async-compatible database URL
- **Current Implementation:** Returns `database_url` directly (already in asyncpg format)
- **Format:** `postgresql+asyncpg://user:password@host:port/database`
- **Used By:** `app/database.py` for creating async engine

**Functions:**

#### `get_settings()`
- **Decorator:** `@lru_cache()`
- **Returns:** `Settings` instance
- **Purpose:** Singleton pattern for configuration
- **Why Cached:**
  - Prevents re-reading `.env` file on every request
  - Ensures single source of truth
  - Improves performance (cached after first call)
- **Integration:** Imported by `app/database.py` and other modules

**Configuration Flow:**
```
.env file → Pydantic Settings → get_settings() [cached] → Used across app
```

---

### **app/database.py**

**Purpose:** Async database layer with SQLAlchemy 2.0 and connection management

**Imports & Dependencies:**
```python
sqlalchemy.ext.asyncio → Async engine and sessions
asyncpg → PostgreSQL async driver (used by SQLAlchemy under the hood)
app.core.config → Configuration settings
```

**Module-Level Objects:**

#### `engine` (AsyncEngine)
- **Created By:** `create_async_engine()`
- **Configuration:**
  ```python
  settings.async_database_url  # Connection string
  echo=settings.debug_mode     # SQL logging (True in dev, False in prod)
  future=True                  # Use SQLAlchemy 2.0 style
  pool_pre_ping=True           # Validate connections before use
  pool_size=10                 # Maintain 10 persistent connections
  max_overflow=20              # Allow 20 additional connections when needed
  ```
- **Purpose:** Database connection factory
- **Integration:**
  - Uses **asyncpg** driver for PostgreSQL
  - Connects to PostgreSQL container via Docker network
  - Manages connection pool for performance

**Connection Pool Behavior:**
```
Normal Load: Uses pool_size (10 connections)
High Load: Can create up to 30 connections (10 + 20 overflow)
Idle Connections: Maintained in pool for reuse
Stale Connections: pool_pre_ping validates before use
```

#### `AsyncSessionLocal` (async_sessionmaker)
- **Created By:** `async_sessionmaker()`
- **Configuration:**
  ```python
  engine=engine                 # Uses the async engine
  class_=AsyncSession          # Session type
  expire_on_commit=False       # Don't invalidate objects after commit
  autocommit=False             # Manual transaction control
  autoflush=False              # Manual flush control
  ```
- **Purpose:** Factory for creating database sessions
- **Why expire_on_commit=False:**
  - In async contexts, we may access objects after commit
  - Prevents lazy-loading errors in async code
  - Objects remain accessible without additional queries

#### `Base` (DeclarativeMeta)
- **Created By:** `declarative_base()`
- **Purpose:** Base class for all ORM models
- **Usage:**
  ```python
  # Future models will inherit from this
  class User(Base):
      __tablename__ = "users"
      id = Column(Integer, primary_key=True)
  ```
- **Integration:** Will be used by models in `app/models.py` (Phase 2)

**Functions:**

#### `get_db()` (async generator)
- **Returns:** `AsyncGenerator[AsyncSession, None]`
- **Purpose:** FastAPI dependency for database access
- **Pattern:** Dependency Injection + Context Manager
- **Lifecycle:**
  ```
  1. Request arrives → FastAPI calls get_db()
  2. Opens async session → yields session to route
  3. Route executes → session is available
  4. Route completes → commits transaction
  5. Error occurs → rolls back transaction
  6. Finally → closes session (always happens)
  ```

**Usage Example:**
```python
@router.get("/users")
async def get_users(db: AsyncSession = Depends(get_db)):
    # db is automatically injected
    result = await db.execute(select(User))
    return result.scalars().all()
    # Session auto-commits and closes after return
```

**Error Handling:**
```python
try:
    yield session          # Provide session to route
    await session.commit() # Commit if successful
except Exception:
    await session.rollback()  # Rollback on error
    raise                     # Re-raise exception
finally:
    await session.close()     # Always close session
```

#### `init_db()` (async)
- **Purpose:** Initialize database tables
- **Current Use:** Development/testing
- **Future:** Will be replaced by Alembic migrations in production
- **How It Works:**
  ```python
  1. Opens connection via engine.begin()
  2. Runs Base.metadata.create_all() synchronously within async context
  3. Creates all tables defined in models that inherit from Base
  ```
- **Integration:** Uses `Base.metadata` (contains all model definitions)

#### `check_db_connection()` (async)
- **Returns:** `bool`
- **Purpose:** Verify database connectivity for health checks
- **How It Works:**
  ```python
  1. Creates temporary session
  2. Executes simple query: SELECT 1
  3. Returns True if successful
  4. Returns False if exception occurs
  ```
- **Used By:** `app/routes/health.py` readiness endpoint
- **Why Simple Query:** Minimal overhead, just tests connectivity

**Technology Integration Map:**
```
FastAPI Route
    ↓ (Depends injection)
get_db()
    ↓ (creates)
AsyncSession
    ↓ (uses)
AsyncEngine
    ↓ (connects via)
asyncpg driver
    ↓ (communicates with)
PostgreSQL Container
```

---

### **app/routes/health.py**

**Purpose:** Health monitoring endpoints for Kubernetes/ECS deployment

**Router Setup:**
```python
router = APIRouter()
# Included in main.py with prefix="/api"
# All routes become /api/health, /api/health/ready, etc.
```

**Endpoints:**

#### `GET /api/health` - Basic Health Check
```python
@router.get("/health")
async def health_check()
```

**Purpose:** Verify API process is running
- **Response:** `{"status": "healthy", "service": "CodeBot API"}`
- **Status Code:** Always `200 OK` (if reachable)
- **No Dependencies:** Doesn't check database or external services
- **Use Case:** Load balancer health check (AWS ALB, Nginx)
- **Latency:** < 1ms (instant response)

**When to Use:**
- Load balancer target health checks
- Simple "is the server up?" checks
- Initial smoke tests

---

#### `GET /api/health/ready` - Readiness Check
```python
@router.get("/health/ready")
async def readiness_check()
```

**Purpose:** Verify service is ready to handle traffic
- **Checks Performed:**
  1. Database connectivity via `check_db_connection()`
- **Response (Healthy):**
  ```json
  {
    "status": "ready",
    "checks": {
      "database": "healthy"
    },
    "response_time_ms": 12.34
  }
  ```
- **Response (Unhealthy):**
  ```json
  {
    "status": "not_ready",
    "checks": {
      "database": "unhealthy"
    },
    "response_time_ms": 45.67
  }
  ```
- **Status Codes:**
  - `200 OK` - Service is ready
  - `503 Service Unavailable` - Service not ready (DB down)

**Kubernetes Integration:**
```yaml
readinessProbe:
  httpGet:
    path: /api/health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

**What Happens When Failing:**
- Kubernetes removes pod from service load balancer
- No new requests routed to this pod
- Existing connections may complete
- Pod stays running (not restarted)

**Timing Measurement:**
```python
start_time = time.time()
db_healthy = await check_db_connection()
response_time = time.time() - start_time
# Returns time in milliseconds for monitoring
```

---

#### `GET /api/health/live` - Liveness Check
```python
@router.get("/health/live")
async def liveness_check()
```

**Purpose:** Verify process is alive and not deadlocked
- **Response:** `{"status": "alive", "service": "CodeBot API"}`
- **Status Code:** Always `200 OK` (if process responsive)
- **No Dependencies:** Similar to basic health check
- **Difference from `/health`:**
  - Semantic purpose for Kubernetes liveness probes
  - May include internal process health checks in future

**Kubernetes Integration:**
```yaml
livenessProbe:
  httpGet:
    path: /api/health/live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 30
```

**What Happens When Failing:**
- Kubernetes kills the pod
- Pod is restarted
- Used to recover from deadlocks or hung processes

---

### Health Check Strategy Summary

| Endpoint | Purpose | Checks | Failure Action | Update Frequency |
|----------|---------|--------|----------------|------------------|
| `/api/health` | Basic availability | None | None (informational) | Every 5s |
| `/api/health/ready` | Ready for traffic | Database | Remove from LB | Every 10s |
| `/api/health/live` | Process alive | None (may expand) | Restart pod | Every 30s |

**Integration with Monitoring:**
```
CloudWatch/Prometheus
    ↓ (scrapes)
/api/health/ready
    ↓ (calls)
check_db_connection()
    ↓ (queries)
PostgreSQL
    ↓ (reports)
Metrics Dashboard
```

---

## Data Flow

### Example: Processing a Request with Database Access

```
1. HTTP Request arrives
   ↓
2. FastAPI Router matches route
   ↓
3. Dependency Injection calls get_db()
   ↓
4. AsyncSessionLocal creates new session from pool
   ↓
5. Session yielded to route handler
   ↓
6. Route executes SQLAlchemy queries
   ↓
7. asyncpg translates to PostgreSQL wire protocol
   ↓
8. PostgreSQL processes query
   ↓
9. Results return through stack
   ↓
10. Session commits transaction
   ↓
11. Session returns to pool
   ↓
12. FastAPI serializes response (Pydantic models)
   ↓
13. HTTP Response sent to client
```

### Docker Startup Sequence

```
1. docker-compose.yaml read
   ↓
2. PostgreSQL container starts
   ↓
3. Database initialization (if first run)
   ↓
4. API container starts
   ↓
5. FastAPI app initializes
   ↓
6. Settings loaded from .env
   ↓
7. Async engine created
   ↓
8. Connection pool established
   ↓
9. Alembic migrations run (if configured)
   ↓
10. FastAPI starts listening on port 8000
```

---

## Change Log

### Phase 1: Infrastructure Foundation ✅ (Completed: June 2026)

#### Commit: dff0af2 - "initial commit + docker setup"
**Date:** October 2025
**Author:** Niccolo Protacio Duina

**Changes:**
- Created Docker infrastructure
- Configured docker-compose.yaml with API and DB services
- Set up Dockerfile for FastAPI application
- Established development environment

**Files Modified:**
- `/Dockerfile` - Created
- `/docker-compose.yaml` - Created
- `/requirements.txt` - Initial dependencies

**Technology Integration:**
- Docker → Containerizes FastAPI application
- Docker Compose → Orchestrates multi-container setup
- Docker Network → Allows API container to communicate with DB container

**Impact:**
- Enables consistent development environment across machines
- Simplifies onboarding (just `docker compose up`)
- Prepares for production deployment (ECS/EKS)

---

#### Commit: ee2589c - "database setup and backend file creation"
**Date:** October 2025
**Author:** Niccolo Protacio Duina
**Pull Request:** #1 (DB-Setup branch)

**Changes:**
- Implemented async SQLAlchemy 2.0 database layer
- Created Pydantic Settings configuration system
- Set up Alembic for database migrations
- Configured environment variable management
- Implemented connection pooling

**Files Created:**
- `/app/database.py` - Async database configuration
- `/app/core/config.py` - Pydantic Settings
- `/app/settings.py` - Legacy settings (backward compatibility)
- `/.env` - Environment variables (not in git)
- `/.env.example` - Environment template
- `/alembic.ini` - Alembic configuration
- `/alembic/env.py` - Alembic environment setup

**Database Configuration:**
```python
Engine: AsyncEngine with asyncpg driver
Pool Size: 10 connections
Max Overflow: 20 additional connections
Pre-ping: Enabled (validates connections)
```

**Technology Integration:**
- SQLAlchemy 2.0 → ORM for database operations
- asyncpg → PostgreSQL async driver
- Pydantic → Configuration validation
- Alembic → Database version control

**Impact:**
- Production-ready async database layer
- Type-safe configuration with validation
- Scalable connection management (up to 30 concurrent connections)
- Database migrations under version control

---

#### Commit: eef916a - "Merge pull request #1 from Jej0801/DB-Setup"
**Date:** October 2025

**Changes:**
- Merged database setup into main branch
- Finalized Phase 1 infrastructure

---

### Current Status (as of June 22, 2026)

**Completed Features:**
- ✅ Async FastAPI application with production-grade configuration
- ✅ PostgreSQL database with async SQLAlchemy 2.0
- ✅ Docker containerization with docker-compose
- ✅ Health check endpoints for Kubernetes deployment
- ✅ Configuration management with Pydantic Settings
- ✅ Database connection pooling (10 base + 20 overflow)
- ✅ Alembic migration system

**Next Phase (Phase 2 - Database Layer):**
- ⏳ Database models (User, Repository, PullRequest, Review, Comment)
- ⏳ Repository pattern implementation
- ⏳ CRUD operations
- ⏳ Pydantic schemas for request/response validation

---

## Future Documentation Protocol

**When making changes, update this document with:**

### For New Functions:
```markdown
#### function_name()
- **Location:** file_path:line_number
- **Purpose:** What does this function do?
- **Parameters:** List with types and descriptions
- **Returns:** Return type and description
- **Technology Integration:** How does it interact with other components?
- **Use Case:** When/why to use this function
- **Example:** Code snippet showing usage
```

### For New Features:
```markdown
### Feature Name
**Date Added:** YYYY-MM-DD
**Commit:** hash
**Phase:** Phase number

**Description:** What problem does this solve?

**Files Modified:**
- file_path - What changed

**Technology Integration:**
- Technology → How it's used → Result

**Impact:**
- Performance impact
- Scalability considerations
- Breaking changes (if any)
```

### For Configuration Changes:
```markdown
**Environment Variable:** VAR_NAME
- **Type:** string/int/bool
- **Required:** Yes/No
- **Default:** Default value
- **Purpose:** Why this config exists
- **Used By:** Which modules use it
- **Example:** `.env` example
```

---

## Quick Reference

### Key File Locations
- **Main Application:** `/app/main.py`
- **Database Layer:** `/app/database.py`
- **Configuration:** `/app/core/config.py`
- **Health Checks:** `/app/routes/health.py`
- **Models (Future):** `/app/models.py`
- **Schemas (Future):** `/app/schemas.py`
- **CRUD (Future):** `/app/crud.py`

### Key Technologies
- **Web Framework:** FastAPI 0.104.1
- **Database:** PostgreSQL (via Docker)
- **ORM:** SQLAlchemy 2.0.23 (async)
- **DB Driver:** asyncpg 0.29.0
- **Migrations:** Alembic 1.12.1
- **Config:** Pydantic Settings 2.1.0
- **Server:** Uvicorn 0.24.0

### Important Commands
```bash
# Start services
docker compose up --build

# Run migrations
docker compose exec api alembic upgrade head

# Create new migration
docker compose exec api alembic revision --autogenerate -m "description"

# Check logs
docker compose logs -f api

# Access database
docker compose exec db psql -U codebot -d codebot_dev
```

---

**Documentation Maintained By:** Development Team
**Review Frequency:** After each significant change
**Last Review:** 2026-06-22
