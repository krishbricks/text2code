# Technical Design Document: Text2Code Generator

## High-Level Design

### System Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                    Frontend (React + TypeScript)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│  │ CSV Uploader │  │ Pattern      │  │ Monaco Code Editor       │ │
│  │ Component    │  │ Selector     │  │ (Syntax Highlighting)    │ │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ History & Diff Viewer (React Query + TanStack Table)         │ │
│  └──────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
                              ↕ REST API (FastAPI routes)
┌────────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI + Python)                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ API Routers:                                                  │ │
│  │  - /api/generate (POST) - Generate code from mapping CSV     │ │
│  │  - /api/patterns (GET) - List available ETL patterns         │ │
│  │  - /api/history (GET/POST) - Version history CRUD            │ │
│  │  - /api/deploy (POST) - Deploy to Databricks                 │ │
│  │  - /api/validate (POST) - Validate CSV schema                │ │
│  └──────────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ Business Logic Services:                                      │ │
│  │  - CodeGenerator: Orchestrates LLM calls                     │ │
│  │  - PatternLibrary: Manages prompt templates                  │ │
│  │  - HistoryManager: Tracks generations                        │ │
│  │  - DeploymentService: Databricks integration                 │ │
│  │  - CacheManager: Pattern caching for offline mode            │ │
│  └──────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
         ↕                    ↕                      ↕
┌─────────────────┐  ┌──────────────────┐  ┌───────────────────────┐
│ Databricks SDK  │  │  OpenAI Client   │  │  SQLite Database      │
│ - Workspace API │  │ (Foundation API) │  │  - Generation history │
│ - Jobs API      │  │ Claude Sonnet 4.5│  │  - Pattern cache      │
│ - Volumes API   │  │                  │  │  - User sessions      │
└─────────────────┘  └──────────────────┘  └───────────────────────┘
```

---

## Technology Stack

### Frontend Stack
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite (fast HMR, optimized builds)
- **State Management**: React Query (TanStack Query v5) for API state
- **UI Components**: shadcn/ui + Tailwind CSS
- **Code Editor**: Monaco Editor (VS Code engine)
- **File Upload**: react-dropzone
- **Diff Viewer**: react-diff-viewer-continued
- **Data Tables**: TanStack Table v8
- **Package Manager**: Bun

### Backend Stack
- **Framework**: FastAPI 0.115+
- **Runtime**: Python 3.11 with uv for dependency management
- **Database**: SQLite (aiosqlite for async operations)
- **ORM**: SQLAlchemy 2.0 with async support
- **LLM Client**: OpenAI Python SDK (Databricks-compatible)
- **Databricks Integration**: Databricks SDK 0.59+
- **CSV Processing**: Pandas 2.2+
- **Code Validation**: ast module (Python standard library)
- **Logging**: structlog for structured logging

### External Services
- **Databricks Foundation Model API**: Claude Sonnet 4.5
- **Databricks Workspace API**: File/notebook operations
- **Databricks Jobs API**: Workflow creation

---

## Libraries and Frameworks

### Frontend Dependencies

```json
{
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "@tanstack/react-query": "^5.59.0",
    "@tanstack/react-table": "^8.20.5",
    "@monaco-editor/react": "^4.6.0",
    "react-dropzone": "^14.3.5",
    "react-diff-viewer-continued": "^3.4.0",
    "lucide-react": "^0.462.0",
    "tailwindcss": "^3.4.17",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "tailwind-merge": "^2.6.0"
  }
}
```

### Backend Dependencies (pyproject.toml)

```toml
[project]
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.6",
    "databricks-sdk>=0.59.0",
    "openai>=2.0.0",
    "pandas>=2.2.0",
    "aiosqlite>=0.20.0",
    "sqlalchemy>=2.0.0",
    "pydantic>=2.12.0",
    "python-multipart>=0.0.20",
    "httpx>=0.28.0",
    "structlog>=25.3.0",
]
```

---

## Data Architecture

### Database Schema (SQLite)

```sql
-- Generation history table
CREATE TABLE generations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_email TEXT NOT NULL,
    pattern_name TEXT NOT NULL,
    model_version TEXT DEFAULT 'databricks-claude-sonnet-4-5',
    mapping_csv_path TEXT,
    mapping_csv_content TEXT,
    generated_code TEXT NOT NULL,
    generation_duration_ms INTEGER,
    status TEXT DEFAULT 'success', -- success, failed, cached
    error_message TEXT,
    metadata JSON -- Additional flexible metadata
);

-- Pattern cache table
CREATE TABLE pattern_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_name TEXT UNIQUE NOT NULL,
    sample_mapping TEXT, -- Example mapping CSV
    cached_code TEXT NOT NULL,
    cache_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    usage_count INTEGER DEFAULT 0,
    last_used DATETIME
);

-- User sessions (optional for future use)
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    user_email TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

-- Indexes for performance
CREATE INDEX idx_generations_timestamp ON generations(timestamp DESC);
CREATE INDEX idx_generations_user ON generations(user_email);
CREATE INDEX idx_generations_pattern ON generations(pattern_name);
CREATE INDEX idx_pattern_cache_name ON pattern_cache(pattern_name);
```

### Data Models (Pydantic)

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict

class MappingRow(BaseModel):
    source_table: str = Field(..., description="Source table/volume path")
    source_column: Optional[str] = Field(None, description="Source column name")
    target_table: str = Field(..., description="Target table/volume path")
    target_column: str = Field(..., description="Target column name")
    transformation: Optional[str] = Field(None, description="Transformation expression")

class GenerateCodeRequest(BaseModel):
    mapping_csv: str = Field(..., description="CSV content as string")
    pattern_name: str = Field(..., description="ETL pattern to use")
    custom_prompt: Optional[str] = Field(None, description="Custom generation prompt")
    generate_tests: bool = Field(False, description="Generate unit tests")

class GeneratedCodeResponse(BaseModel):
    code: str = Field(..., description="Generated PySpark code")
    tests: Optional[str] = Field(None, description="Generated unit tests")
    generation_id: int = Field(..., description="History record ID")
    cached: bool = Field(False, description="Whether response was cached")
    generation_duration_ms: int

class PatternDefinition(BaseModel):
    name: str
    display_name: str
    description: str
    prompt_template: str
    example_mapping: str

class GenerationHistory(BaseModel):
    id: int
    timestamp: datetime
    user_email: str
    pattern_name: str
    generated_code: str
    status: str
    generation_duration_ms: Optional[int]
```

---

## Integration Points

### Databricks Foundation Model API

```python
from openai import OpenAI

class ClaudeClient:
    def __init__(self, workspace_url: str, token: str):
        self.client = OpenAI(
            api_key=token,
            base_url=f"{workspace_url}/serving-endpoints"
        )
        self.model = "databricks-claude-sonnet-4-5"

    async def generate_code(self, prompt: str, max_tokens: int = 4000) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a senior Databricks PySpark engineer."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.05
        )
        return response.choices[0].message.content
```

### Databricks Workspace API

```python
from databricks.sdk import WorkspaceClient

class DatabricksDeployment:
    def __init__(self, host: str, token: str):
        self.client = WorkspaceClient(host=host, token=token)

    async def save_to_workspace(self, code: str, path: str):
        """Save generated code to Databricks workspace as notebook"""
        self.client.workspace.import_(
            path=path,
            format="SOURCE",
            language="PYTHON",
            content=code.encode('utf-8'),
            overwrite=True
        )

    async def save_to_volume(self, code: str, volume_path: str):
        """Write code to Unity Catalog Volume"""
        # Use dbutils in deployed app or Files API
        pass

    async def create_workflow(self, code: str, job_name: str):
        """Create Databricks Job with generated code"""
        pass
```

---

## Implementation Plan

### Phase 1: MVP (Core Generation) - Weeks 1-2

#### Backend Implementation

**Week 1: Core API & Database**

1. **Set up FastAPI project structure** (Day 1)
   - File: `server/app.py` - Main FastAPI app
   - File: `server/routers/generate.py` - Code generation endpoint
   - File: `server/routers/patterns.py` - Pattern library endpoint
   - File: `server/routers/validate.py` - CSV validation endpoint
   - File: `server/models/schemas.py` - Pydantic models
   - File: `server/database/connection.py` - SQLite connection
   - File: `server/database/models.py` - SQLAlchemy models

2. **Implement Pattern Library** (Day 2)
   - File: `server/services/pattern_library.py`
   - Define 5 ETL patterns (Full Load, Incremental, MERGE, SCD2, Custom)
   - Store as JSON in `server/data/patterns.json`
   - Load patterns on app startup

3. **Build Code Generation Service** (Days 3-4)
   - File: `server/services/code_generator.py`
   - Function: `parse_mapping_csv(csv_content: str) -> List[MappingRow]`
   - Function: `build_prompt(mappings: List[MappingRow], pattern: str) -> str`
   - Function: `call_claude_api(prompt: str) -> str`
   - Function: `validate_generated_code(code: str) -> bool` (AST parsing)
   - Add comprehensive error handling

4. **Implement SQLite Database** (Day 5)
   - File: `server/database/init_db.py` - Schema initialization
   - File: `server/services/history_manager.py`
   - Function: `save_generation(...)` - Store generation history
   - Function: `get_history(user_email: str) -> List[GenerationHistory]`
   - Add database migrations with Alembic

**Week 2: API Endpoints & Testing**

5. **Create API Endpoints** (Days 1-2)
   - `POST /api/generate` - Main generation endpoint
     ```python
     @router.post("/generate", response_model=GeneratedCodeResponse)
     async def generate_code(request: GenerateCodeRequest, user: User = Depends(get_current_user)):
         # Parse CSV
         mappings = parse_mapping_csv(request.mapping_csv)
         # Get pattern
         pattern = pattern_library.get_pattern(request.pattern_name)
         # Build prompt
         prompt = build_prompt(mappings, pattern, request.custom_prompt)
         # Call Claude API (with caching fallback)
         code = await code_generator.generate(prompt)
         # Validate code
         validate_generated_code(code)
         # Save to history
         history_id = await history_manager.save_generation(...)
         return GeneratedCodeResponse(code=code, generation_id=history_id, ...)
     ```
   - `GET /api/patterns` - List available patterns
   - `POST /api/validate` - Validate CSV before generation

6. **Add Databricks Authentication** (Day 3)
   - File: `server/auth/databricks_oauth.py`
   - Use Databricks OAuth for user authentication
   - Extract user email from token
   - Dependency: `get_current_user()`

7. **Implement Caching Logic** (Day 4)
   - File: `server/services/cache_manager.py`
   - Function: `get_cached_pattern(pattern_name: str) -> Optional[str]`
   - Function: `cache_pattern(pattern_name: str, code: str)`
   - Fallback to cache if API call fails

8. **Testing & Debugging** (Day 5)
   - Write pytest tests for all endpoints
   - Test CSV parsing edge cases
   - Test code validation logic
   - Manual testing with real Databricks workspace

#### Frontend Implementation

**Week 1: Basic UI Components**

1. **Set up React project** (Day 1)
   - Initialize Vite + React + TypeScript
   - Configure Tailwind CSS
   - Add shadcn/ui components
   - Set up React Query

2. **Build CSV Upload Component** (Days 2-3)
   - File: `client/src/components/CSVUploader.tsx`
   - Use react-dropzone for drag-and-drop
   - Display CSV preview table
   - Validate CSV schema on frontend
   - Show upload progress

3. **Create Pattern Selector** (Day 4)
   - File: `client/src/components/PatternSelector.tsx`
   - Fetch patterns from `/api/patterns`
   - Display as radio buttons with descriptions
   - Show example mapping for each pattern

4. **Build Code Preview** (Day 5)
   - File: `client/src/components/CodePreview.tsx`
   - Display generated code with syntax highlighting (Prism.js or Monaco)
   - Add "Copy to Clipboard" button
   - Add "Download .py" button

**Week 2: Main Page & Integration**

5. **Create Main Generation Page** (Days 1-2)
   - File: `client/src/pages/GeneratePage.tsx`
   - Layout: CSV upload → Pattern selector → Generate button → Code preview
   - Wire up API calls with React Query
   - Show loading state during generation
   - Error handling with toast notifications

6. **Add API Client** (Day 3)
   - File: `client/src/api/client.ts`
   - Use auto-generated TypeScript client from FastAPI OpenAPI spec
   - Configure React Query hooks
   - Add request/response interceptors

7. **Styling & UX Polish** (Day 4)
   - Responsive design for mobile/desktop
   - Add animations and transitions
   - Improve error messages
   - Add helpful tooltips

8. **End-to-End Testing** (Day 5)
   - Test full workflow: upload CSV → select pattern → generate code
   - Verify downloaded code runs in Databricks
   - Fix any integration bugs

---

### Phase 2: Enhanced UX (Preview & Editing) - Weeks 3-4

**Week 3: Monaco Editor Integration**

1. **Add Monaco Editor** (Days 1-2)
   - File: `client/src/components/CodeEditor.tsx`
   - Install @monaco-editor/react
   - Configure Python language support
   - Add IntelliSense for PySpark
   - Implement auto-save

2. **Build Code Editing Workflow** (Day 3)
   - Edit generated code in-place
   - Track changes (dirty state)
   - "Save Changes" button
   - "Reset to Original" button

3. **Add All ETL Patterns** (Days 4-5)
   - Implement MERGE pattern prompt
   - Implement SCD Type 2 pattern prompt
   - Add custom pattern UI (textarea for custom prompt)
   - Test all patterns with sample CSVs

**Week 4: Deployment Features**

4. **Implement Workspace Deployment** (Days 1-2)
   - File: `server/routers/deploy.py`
   - `POST /api/deploy/workspace` endpoint
   - Use Databricks SDK to create notebook
   - Show deployment status in UI
   - Add "Open in Databricks" link

5. **Implement Volume Deployment** (Day 3)
   - `POST /api/deploy/volume` endpoint
   - Write .py file to Unity Catalog Volume
   - Handle authentication with user's PAT
   - Show success message with volume path

6. **Build Deployment UI** (Day 4)
   - File: `client/src/components/DeploymentPanel.tsx`
   - Radio buttons: Workspace / Volume / Workflow
   - Input fields for paths
   - Deploy button with progress indicator

7. **Testing & Refinement** (Day 5)
   - Test all deployment options
   - Verify files appear in Databricks
   - Fix permission issues
   - Add error handling for deployment failures

---

### Phase 3: Quality & Automation (Tests & Deployment) - Weeks 5-6

**Week 5: Unit Test Generation**

1. **Implement Test Generator** (Days 1-3)
   - File: `server/services/test_generator.py`
   - Function: `generate_tests(code: str, mappings: List[MappingRow]) -> str`
   - Build prompt for test generation
   - Call Claude API with test-specific prompt
   - Generate pytest + chispa tests

2. **Add Test Preview UI** (Day 4)
   - File: `client/src/components/TestPreview.tsx`
   - Tabbed interface: "Code" / "Tests"
   - Display tests with syntax highlighting
   - Download tests button

3. **Enhance Generation Endpoint** (Day 5)
   - Support `generate_tests: true` parameter
   - Return both code and tests in response
   - Update frontend to handle test generation

**Week 6: Workflow Automation**

4. **Implement Workflow Creation** (Days 1-2)
   - File: `server/services/workflow_service.py`
   - Function: `create_job(code: str, job_name: str, params: dict) -> str`
   - Use Databricks Jobs API
   - Configure task with generated code
   - Set up schedule (optional)

5. **Build Workflow UI** (Days 3-4)
   - File: `client/src/components/WorkflowCreator.tsx`
   - Form: Job name, cluster config, schedule
   - Parse dbutils.widgets from code
   - Pre-populate job parameters
   - Show job URL after creation

6. **End-to-End Testing** (Day 5)
   - Test test generation for all patterns
   - Test workflow creation
   - Verify jobs run successfully in Databricks
   - Performance testing (generation time)

---

### Phase 4: Version Control (History & Diff) - Weeks 7-8

**Week 7: History Tracking**

1. **Build History API** (Days 1-2)
   - File: `server/routers/history.py`
   - `GET /api/history` - List all generations
   - `GET /api/history/{id}` - Get specific generation
   - `GET /api/history/search` - Search with filters
   - Pagination support

2. **Create History Page** (Days 3-4)
   - File: `client/src/pages/HistoryPage.tsx`
   - Display table with TanStack Table
   - Columns: Timestamp, Pattern, Status, Actions
   - Filter by pattern, date range, status
   - Sort by any column

3. **Implement Generation Detail View** (Day 5)
   - File: `client/src/pages/GenerationDetailPage.tsx`
   - Show full generation metadata
   - Display mapping CSV used
   - Show generated code
   - "Re-generate" button

**Week 8: Diff Viewer & Rollback**

4. **Build Diff Viewer** (Days 1-2)
   - File: `client/src/components/DiffViewer.tsx`
   - Use react-diff-viewer-continued
   - Side-by-side diff display
   - Highlight added/removed/changed lines
   - "Compare with..." dropdown

5. **Implement Rollback** (Day 3)
   - `POST /api/history/{id}/rollback` endpoint
   - Re-generate code using stored CSV and pattern
   - Create new history entry
   - Show rollback success message

6. **Add Audit Logging** (Day 4)
   - Enhance database schema with audit fields
   - Log all user actions (generate, deploy, rollback)
   - Build admin audit log viewer (optional)

7. **Final Testing & Deployment** (Day 5)
   - Comprehensive testing of all features
   - Performance optimization
   - Security audit
   - Deploy to production Databricks Apps

---

## Development Workflow

### Local Development Setup

1. **Backend Development**
   ```bash
   # Start backend with hot reload
   ./watch.sh

   # Backend runs on http://localhost:8000
   # API docs at http://localhost:8000/docs
   ```

2. **Frontend Development**
   ```bash
   # Frontend runs on http://localhost:5173 (started by watch.sh)
   # Hot module replacement enabled
   ```

3. **Database Initialization**
   ```bash
   uv run python -m server.database.init_db
   ```

### Testing Strategy

**Backend Tests** (pytest):
- Unit tests for all business logic
- Integration tests for API endpoints
- Mock Databricks SDK calls
- Test database operations

**Frontend Tests** (Vitest):
- Component unit tests
- API integration tests with MSW
- User interaction tests with Testing Library

**E2E Tests** (Playwright):
- Full user workflows
- Cross-browser testing
- Visual regression testing

### Deployment Process

1. **Build Frontend**
   ```bash
   cd client && bun run build
   ```

2. **Generate requirements.txt**
   ```bash
   uv export --no-hashes > requirements.txt
   ```

3. **Deploy to Databricks Apps**
   ```bash
   ./deploy.sh
   ```

4. **Verify Deployment**
   ```bash
   ./app_status.sh
   ```

---

## Code Quality & Standards

### Python Code Standards
- Follow PEP 8 style guide
- Use ruff for linting and formatting
- Type hints for all functions
- Docstrings in Google format
- Maximum line length: 100 characters

### TypeScript Code Standards
- Use ESLint + Prettier
- Strict TypeScript mode enabled
- No `any` types allowed
- Functional components with hooks
- CSS Modules or Tailwind for styling

### API Standards
- RESTful endpoint design
- OpenAPI 3.1 specification
- Consistent error responses
- Pagination for list endpoints
- Rate limiting on expensive operations

---

## Security Considerations

### Authentication
- Databricks OAuth 2.0 for user authentication
- JWT tokens for session management
- Token refresh handling
- Secure token storage (httpOnly cookies)

### Authorization
- User can only access their own generation history
- Admin role for audit log access (future)
- Validate user permissions before deployment

### Data Security
- No storage of sensitive data (PATs, secrets)
- Sanitize user input (CSV, prompts)
- SQL injection prevention (parameterized queries)
- XSS prevention (React auto-escaping)

### API Security
- Rate limiting on generation endpoint (max 10/minute per user)
- File upload size limits (10MB max)
- Timeout for LLM calls (30 seconds)
- CORS configuration for production

---

## Performance Optimization

### Backend Optimization
- Async I/O for all database operations
- Connection pooling for SQLite
- Caching frequent patterns in memory
- Background tasks for deployment operations

### Frontend Optimization
- Code splitting for large components
- Lazy loading for Monaco Editor
- Virtual scrolling for history table
- Debounce for search inputs

### Database Optimization
- Indexes on frequently queried columns
- Archive old generations (>6 months)
- VACUUM database periodically
- Optimize query patterns

---

## Monitoring & Observability

### Logging
- Structured logging with structlog
- Log levels: DEBUG, INFO, WARNING, ERROR
- Log all API requests/responses
- Log generation duration and status

### Metrics
- Generation success rate
- Average generation time
- API error rate
- Active users count

### Error Tracking
- Exception logging with stack traces
- User-facing error messages (sanitized)
- Admin error dashboard (future)

---

## Deployment Architecture

### Databricks Apps Deployment

```yaml
# app.yaml
name: text2codeapp
python:
  version: "3.11"
resources:
  - name: server
    entrypoint: "uvicorn server.app:app --host 0.0.0.0 --port 8000"
    env:
      - name: DATABRICKS_HOST
        value: "${DATABRICKS_HOST}"
      - name: DATABRICKS_TOKEN
        value: "${DATABRICKS_TOKEN}"
    static:
      - source: client/dist
        target: /
```

### Environment Variables

```bash
# .env.local (for local development)
DATABRICKS_HOST=https://your-workspace.azuredatabricks.net/
DATABRICKS_TOKEN=dapi...
DATABRICKS_APP_NAME=text2codeapp
DBA_SOURCE_CODE_PATH=/Workspace/Users/your-email/text2codeapp

# Database
DATABASE_PATH=./data/text2code.db

# Model Config
MODEL_NAME=databricks-claude-sonnet-4-5
MODEL_MAX_TOKENS=4000
MODEL_TEMPERATURE=0.05

# Cache Config
ENABLE_PATTERN_CACHE=true
CACHE_TTL_HOURS=24
```

---

## Technical Risks & Mitigation

### Risk 1: LLM API Failures
**Mitigation**:
- Implement pattern caching for offline mode
- Retry logic with exponential backoff
- Fallback to cached patterns
- User-friendly error messages

### Risk 2: Slow Code Generation
**Mitigation**:
- Show progress indicator with estimated time
- Stream partial results (if API supports)
- Optimize prompt size
- Use smaller max_tokens for simple patterns

### Risk 3: Database Corruption
**Mitigation**:
- Regular database backups (daily)
- Write-ahead logging (WAL) mode for SQLite
- Transaction management for all writes
- Database health checks on startup

### Risk 4: Security Vulnerabilities
**Mitigation**:
- Regular dependency updates
- Security scanning with Snyk/Dependabot
- Input sanitization
- Rate limiting
- OWASP Top 10 compliance

---

## Future Technical Improvements

### Short-term (Next 6 months)
- Add support for SQL code generation (not just PySpark)
- Implement real-time collaboration (WebSockets)
- Add code linting and suggestions in editor
- Support for uploading Excel files (not just CSV)

### Long-term (Next 12 months)
- Natural language to mapping CSV conversion
- AI-assisted code debugging
- Template marketplace for sharing patterns
- Integration with Git (GitHub/GitLab)
- Multi-language support (Scala, R)

---

## Appendix: Key Files Structure

```
text2code/
├── client/                          # Frontend
│   ├── src/
│   │   ├── components/             # React components
│   │   │   ├── CSVUploader.tsx
│   │   │   ├── PatternSelector.tsx
│   │   │   ├── CodePreview.tsx
│   │   │   ├── CodeEditor.tsx      # Monaco Editor
│   │   │   ├── DiffViewer.tsx
│   │   │   └── ui/                 # shadcn/ui components
│   │   ├── pages/                  # Main pages
│   │   │   ├── GeneratePage.tsx
│   │   │   ├── HistoryPage.tsx
│   │   │   └── GenerationDetailPage.tsx
│   │   ├── api/                    # API client
│   │   │   └── client.ts
│   │   └── App.tsx
│   └── package.json
├── server/                          # Backend
│   ├── routers/                    # API endpoints
│   │   ├── generate.py
│   │   ├── patterns.py
│   │   ├── history.py
│   │   ├── deploy.py
│   │   └── validate.py
│   ├── services/                   # Business logic
│   │   ├── code_generator.py
│   │   ├── pattern_library.py
│   │   ├── history_manager.py
│   │   ├── test_generator.py
│   │   ├── cache_manager.py
│   │   └── workflow_service.py
│   ├── database/                   # Database layer
│   │   ├── connection.py
│   │   ├── models.py              # SQLAlchemy models
│   │   └── init_db.py
│   ├── models/                     # Pydantic models
│   │   └── schemas.py
│   ├── auth/                       # Authentication
│   │   └── databricks_oauth.py
│   ├── data/                       # Static data
│   │   └── patterns.json          # Pattern definitions
│   └── app.py                     # FastAPI app
├── tests/                          # Tests
│   ├── backend/
│   │   ├── test_generate.py
│   │   └── test_patterns.py
│   └── frontend/
│       └── components/
├── docs/                           # Documentation
│   ├── product.md                 # This PRD
│   └── design.md                  # This TDD
├── pyproject.toml                 # Python dependencies
├── watch.sh                       # Dev server script
├── deploy.sh                      # Deployment script
└── app.yaml                       # Databricks Apps config
```

---

## Implementation Checklist

### Phase 1: MVP
- [ ] FastAPI project structure
- [ ] SQLite database schema
- [ ] Pattern library (5 patterns)
- [ ] Code generation service
- [ ] Claude API integration
- [ ] Generation history tracking
- [ ] CSV upload component
- [ ] Pattern selector component
- [ ] Code preview component
- [ ] Main generation page
- [ ] End-to-end workflow testing

### Phase 2: Enhanced UX
- [ ] Monaco Editor integration
- [ ] Code editing workflow
- [ ] All ETL patterns implemented
- [ ] Workspace deployment
- [ ] Volume deployment
- [ ] Deployment UI panel
- [ ] Authentication with Databricks OAuth

### Phase 3: Quality & Automation
- [ ] Unit test generation service
- [ ] Test preview UI
- [ ] Workflow creation service
- [ ] Workflow creator UI
- [ ] Parameterization handling
- [ ] Performance testing

### Phase 4: Version Control
- [ ] History API endpoints
- [ ] History page with table
- [ ] Generation detail page
- [ ] Diff viewer component
- [ ] Rollback functionality
- [ ] Audit logging
- [ ] Production deployment

---

## Success Criteria

### Technical Success Metrics
- **Uptime**: 99.5% availability
- **Performance**: Code generation <30 seconds for 95th percentile
- **Reliability**: <1% error rate on generation endpoint
- **Test Coverage**: >80% backend, >70% frontend

### User Success Metrics
- **Adoption**: 50+ active users within first month
- **Satisfaction**: NPS >50
- **Deployment Rate**: 70% of generated code gets deployed
- **Time Savings**: Average generation to deployment <5 minutes
