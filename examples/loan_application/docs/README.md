# Workflow Manager Application

A FastAPI application for managing workflows using the Riparius domain system.

## Features

- **Workflow Management**: Create, update, start, cancel, and abort workflows
- **Step Operations**: Manage workflow steps and their transitions
- **Participant Management**: Add and remove workflow participants with roles
- **Activity Processing**: Process workflow activities and events
- **Query APIs**: Search and filter workflows, steps, participants, and stages
- **REST API**: Full REST API with OpenAPI documentation

## Quick Start

### Installation

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup application with uv
just install

# Or manually with uv
uv venv
uv pip install -r requirements.txt
```

### Running the Application

```bash
# Development server with just
just run

# Development server with auto-reload
just dev

# Or using uv directly
uv run python -m workflow_manager.main

# Or using uvicorn with uv
uv run uvicorn workflow_manager.main:app --reload --host 0.0.0.0 --port 8000
```

### Running Tests

```bash
# Run all tests with just
just test

# Run with coverage
just test-cov

# Run basic tests
just test-basic

# Verify setup
just verify

# Or using uv directly
uv run pytest tests/
```

## API Documentation

Once the application is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Workflow Commands
- `POST /api/v1/workflow/create-workflow` - Create a new workflow
- `POST /api/v1/workflow/update-workflow` - Update workflow properties
- `POST /api/v1/workflow/start-workflow` - Start workflow execution
- `POST /api/v1/workflow/cancel-workflow` - Cancel a workflow
- `POST /api/v1/workflow/abort-workflow` - Abort a workflow
- `POST /api/v1/workflow/process-activity` - Process workflow activity
- `POST /api/v1/workflow/add-participant` - Add participant to workflow
- `POST /api/v1/workflow/remove-participant` - Remove participant from workflow
- `POST /api/v1/workflow/add-role` - Add role to workflow
- `POST /api/v1/workflow/remove-role` - Remove role from workflow
- `POST /api/v1/workflow/ignore-step` - Ignore a workflow step
- `POST /api/v1/workflow/cancel-step` - Cancel a workflow step

### Workflow Queries
- `GET /api/v1/workflow/workflow` - List and search workflows
- `GET /api/v1/workflow/workflow/{id}` - Get specific workflow
- `GET /api/v1/workflow/workflow-step` - List and search workflow steps
- `GET /api/v1/workflow/workflow-participant` - List workflow participants
- `GET /api/v1/workflow/workflow-stage` - List workflow stages

## Configuration

Configure the application using environment variables:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname

# Authentication
AUTH_ENABLED=true
SECRET_KEY=your-secret-key

# Debug mode
DEBUG=true
```

## Architecture

The application is built using:
- **FastAPI**: Modern Python web framework
- **Riparius Domain**: Workflow management domain logic
- **Fluvius Framework**: Domain-driven architecture framework
- **PostgreSQL**: Database for persistence
- **SQLAlchemy**: ORM for database operations 