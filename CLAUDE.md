# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

This is the **Discovery Chat Microservice** - a FastAPI-based AI-powered chat system that guides users through a structured discovery process to generate technical documentation and task lists for software projects.

## Key Commands

### Development
```bash
# Run the server locally
python main.py

# Run with Docker (includes Redis)
docker-compose up

# Install dependencies
pip install -r requirements.txt
```

### Testing
```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=app

# Run specific test file
pytest test_wizard.py
pytest test_message.py
pytest test_upload.py

# Run tests in watch mode
pytest --watch
```

### Linting and Type Checking
```bash
# Format code with black
black app/

# Check with flake8
flake8 app/

# Type checking with mypy
mypy app/
```

### Access Points
- Main API: `http://localhost:8001`
- Test Interface: `http://localhost:8001/test`
- Wizard Form: `http://localhost:8001/wizard`

## Architecture Overview

### Core Flow: 9-Stage Discovery Process
The system guides users through 9 sequential stages, each with specific validation criteria:

1. **business_context** → 2. **users_and_journeys** → 3. **functional_scope** → 4. **constraints_policies** → 5. **non_functional** → 6. **tech_preferences** → 7. **delivery_budget** → 8. **review_gaps** → 9. **finalize_docs**

### Key Components

#### State Management
- **DiscoveryStateMachine** (`app/core/state_machine.py`): Controls stage transitions and maintains discovery state
- **ValidationEngine** (`app/core/validation_engine.py`): Validates completeness of each stage using checklists

#### AI Processing
- **AIProcessingEngine** (`app/services/ai_processing.py`): OpenAI GPT-4 integration with context-aware prompts
- **TokenOptimizer** (`app/utils/token_optimizer.py`): Optimizes token usage for cost efficiency

#### Document Generation
- **DocumentGenerator** (`app/services/document_generator.py`): Generates 6 technical documents (3 docs + 3 task lists)
- Output files: `backend_v1.md`, `frontend_v1.md`, `bancodedados_v1.md`, `tarefas_*.md`

#### Data Flow
- **SessionManager** (`app/services/session_manager.py`): Handles session persistence (Firestore/Local fallback)
- **StorageService** (`app/services/storage_service.py`): File storage (GCS/Local fallback)
- **WizardEngine** (`app/services/wizard_engine.py`): Conditional logic for wizard form flow

### API Structure
- `/v1/sessions` - Session management
- `/v1/messages:stream` - Real-time chat streaming (SSE)
- `/v1/sessions/{id}/documents` - Document operations
- `/api/wizard/*` - Wizard form endpoints

### Data Models
All models use Pydantic v2 with strict validation:
- Discovery stages: `app/models/discovery.py`
- Session management: `app/models/session.py`
- Wizard forms: `app/models/wizard_form.py`

## Important Patterns

### Real-time Streaming
Uses Server-Sent Events (SSE) for chat streaming. Client connects to `/v1/messages:stream` and receives events:
- `message`: AI response chunks
- `stage_transition`: Stage changes
- `validation_status`: Validation results
- `document_generated`: Document completion

### Error Handling
- All endpoints return structured error responses
- PII-safe logging (no sensitive data in logs)
- Graceful fallbacks (Redis → Memory, GCS → Local)

### Session Management
- Sessions stored in Firestore (production) or local JSON files (development)
- Each session tracks: current stage, message history, validation status, generated documents

### Wizard to Discovery Conversion
The wizard form data is converted to discovery session format via `WizardConverter` (`app/utils/wizard_converter.py`)

## Environment Configuration

Required environment variables (see `.env.example`):
- `OPENAI_API_KEY` - OpenAI API key for GPT-4
- `GCS_BUCKET_NAME` - Google Cloud Storage bucket
- `FIRESTORE_PROJECT_ID` - Firestore project ID
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to GCP credentials JSON

## Development Notes

### Local Development Mode
When `ENVIRONMENT=development`:
- Uses local file storage instead of GCS
- Sessions saved as JSON files in `/storage/sessions/`
- Documents saved in `/storage/documents/`
- In-memory cache instead of Redis

### Testing Strategy
- Unit tests for individual components
- Integration tests for API endpoints
- E2E tests for complete discovery flow
- Test files in root: `test_*.py`

### Code Style
- Python 3.11+ with type hints
- Async/await patterns throughout
- Pydantic for data validation
- FastAPI dependency injection

### Common Debugging
- Check logs for detailed error traces
- Session data in `/storage/sessions/{session_id}.json`
- Redis connection warnings are normal in local dev (uses fallback)
- For wizard issues, check browser console for `wizardState`