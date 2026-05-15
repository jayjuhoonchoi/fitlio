# How to verify Fitlio changes after pulling `main`

Use this after `git pull` (or `git fetch && git merge origin/main`) so you can trust what landed without reading every file.

## 1. See what commits you just received

```bash
cd ~/fitlio   # or your clone path
git fetch origin
git log --oneline HEAD~15..HEAD
git log --oneline origin/main~15..origin/main   # if you track remote explicitly
```

Optional: list files touched in those commits:

```bash
git diff --name-only HEAD~20..HEAD
```

## 2. Static + automated checks (recommended every pull)

From the repo root, with Python 3 and the project venv:

```bash
./venv/bin/python -m compileall app tests
./venv/bin/python -m pytest -q tests/test_main.py
```

If `pytest` is missing: `./venv/bin/pip install -r requirements.txt` then re-run.

## 3. Smoke against a running API

Start the stack (Docker or local uvicorn per your usual workflow), then:

```bash
./scripts/preflight_env.sh http://127.0.0.1:8000
./scripts/smoke_core.sh http://127.0.0.1:8000
```

For production/staging, pass that base URL instead of localhost.

**Smoke now covers:** health, member/admin auth gates, tablet 404/contract, quick-reserve reachability, weekly report gate, center discover gate, **member `/member/checkin-qr` gate**, **tablet `/centers/tablet/check-in-qr` invalid-token 401**, **admin roster gate**, **premium overview gate**.

## 4. Quick UI smoke (manual)

With API running and DNS/port as you use in prod:

| Surface | URL | What to check |
|--------|-----|----------------|
| Member app | `/app/member` | Summary, **Front desk QR** card, renew flow |
| Admin app | `/app/admin` | Classes → **Roster** → **Mark present** |
| Tablet | `/app/tablet/{center_slug}` | PIN vs **QR** mode |
| Public landing | `/center/{slug}` | Published CMS page |
| Health | `/health` | `{"status":"healthy",...}` |

## 5. Optional: timing / cache sanity

```bash
./scripts/bench_pages.sh http://127.0.0.1:8000
```

Run twice; second run should show similar or better `time_starttransfer` for cached static routes.

## 6. If something fails

1. Note the **first** failing command and exact output.
2. Open `docs/today-qa-checklist.md` for flow-level checks.
3. Ops HTTPS issues: `docs` in README + `./scripts/fix_https.sh` (server path).
