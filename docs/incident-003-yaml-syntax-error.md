# Incident 003 — docker-compose.yml YAML Syntax Error

## Date
2026-05-20

## Symptoms
- GitHub Actions deploy job failing
- Error: `services.api.environment.db must be a boolean, null, number or string`
- EC2 containers not starting after deployment

## Root Cause
`depends_on` block was accidentally placed inside `environment` block during editing:

```yaml
# Wrong
environment:
  DATABASE_URL: ...
  depends_on:        ← indented one level too deep
    db:
      condition: service_healthy

# Correct
environment:
  DATABASE_URL: ...
depends_on:          ← same level as environment
  db:
    condition: service_healthy
```

## Diagnosis Steps
1. Checked Actions log → found YAML validation error
2. Opened docker-compose.yml → found depends_on inside environment

## Resolution
Moved `depends_on` block out of `environment` block to correct indentation level.

## Prevention
- Always run `docker compose config` to validate YAML before pushing
- Use a YAML linter in Cursor

## Lessons Learned
- YAML indentation errors are silent until runtime
- `docker compose config` catches syntax errors locally before pushing