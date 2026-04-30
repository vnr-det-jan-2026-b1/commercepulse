# Gemini AI Integration Guide

This document defines how AI assistants (like Gemini/Antigravity) should interact with the **CommercePulse** project.

## 🚀 Core Directives

1.  **Strict Adherence**: Always follow the instructions in [AGENTS.md](./AGENTS.md).
2.  **Skill-Based Execution**: Use the specialized workflows in the `skills/` directory for data analysis and codebase exploration.
3.  **Privacy First**: Adhere to the E-commerce Integrity Rules in `AGENTS.md`. Never expose customer PII.

## 🛠️ AI Skill Map

| Skill | Path | Use Case |
| :--- | :--- | :--- |
| **Analyze Data** | `skills/analyze-data/SKILL.md` | Schema verification, revenue logic, and inventory audits. |
| **Explore Codebase** | `skills/explore-codebase/SKILL.md` | Mapping cloud modules (Azure/AWS/Google) and identifying entry points. |

## 🔄 Development Workflow

### 1. Planning & Issue Tracking
*   Always check available work using `bd ready`.
*   Claim issues using `bd update <id> --claim` before starting.
*   If `bd` is unavailable due to shell restrictions, use `cmd /c bd` as a fallback.

### 2. Implementation
*   **Aesthetics**: Prioritize "Rich Aesthetics" for frontend components (use `lucide-react`, glassmorphism, and premium color palettes).
*   **Infrastructure**: Focus on the `AZURE/` directory for production-ready code.

### 3. Session Completion
*   Follow the **MANDATORY WORKFLOW** in `AGENTS.md`:
    1. File issues for remaining work.
    2. Quality check ingestion logic.
    3. Push to remote (`git pull --rebase`, `bd dolt push`, `git push`).

## 📁 Directory Context

- `AZURE/backend`: FastAPI, SQLAlchemy, pgvector (AI layer).
- `AZURE/frontend`: React, Vite, TailwindCSS (for UI/UX).
- `AZURE/ai_agents`: LangGraph agents for "The Why" analytics.
