# Agent Instructions

This project is an AI-powered e-commerce analytics platform. Use **bd** (beads) for issue tracking.

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work atomically
bd close <id>         # Complete work
```

## Non-Interactive Shell Commands

**ALWAYS use non-interactive flags** for file operations:
- `cp -f`
- `mv -f`
- `rm -rf`

## E-commerce Integrity Rules

- **Data Privacy**: Never hardcode or leak real customer data if present in test datasets.
- **Service Verification**: When modifying cloud-specific logic (AWS/Azure/Google), verify the impacts on service configuration.

## Session Completion

**MANDATORY WORKFLOW:**
1. **File issues** for remaining work.
2. **Quality Check**: Verify data ingestion and analytics logic if modified.
3. **PUSH TO REMOTE**:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   ```
