# Azure Team - CommercePulse Backend

This directory contains the production-ready backend and infrastructure for Azure deployment.

## Components
- **app/**: Core business logic, FastAPI routes, and SQLAlchemy models.
- **workers/**: Celery application factory and background task configuration.
- **infrastructure/**: Future-proofing for Azure-specific configurations (App Service, ACR, etc.).
- **Brainstorming/**: Restored visual assets and logic diagrams.

## How to Deploy (Local)
1. Copy `.env.example` to `.env`.
2. Run `docker-compose up -d`.
3. API available at `http://localhost:8000/docs`.

## Azure Readiness
- Docker-ready
- Environment variable-based configuration
- Clean module structure for CI/CD
