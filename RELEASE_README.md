# Abacus Backup Chat Export Manager

> Self-hosted backup and export manager for Abacus.AI chat conversations (unofficial tool, not affiliated with Abacus.AI).

**Status:** 🚧 In development · **Version:** 1.0.0 · **Platform:** Docker (FastAPI + React web UI)

## 🔎 Overview

Abacus.AI offers no chat export in its web UI, so this tool makes backups repeatable through the `abacusai` SDK. A FastAPI backend runs backup jobs against the API, stores metadata in SQLite and writes the chats to disk; a React dashboard starts jobs, shows progress and exports the results. It is intended for local, single-operator use.

- Backup jobs with live progress, crash recovery and a completeness check per chat in `manifest.json`
- Exports per chat: JSON (raw data), Markdown, print-friendly HTML, optional Open WebUI import format
- Per-backup `index.html` overview, `manifest.json`, `errors.log` and ZIP download
- 120-second timeout per SDK call; timed-out items are listed and can be retried
- API key via environment, a local `0600` file or the UI; secrets redacted from all outputs
- Optional Basic Auth; `/api/health` with an active database ping

## 🧰 Tech Stack

| Area | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, uvicorn, pydantic, `abacusai` SDK |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Data | SQLite plus files under `APP_DATA_DIR` (`/data`) |
| Runtime | Multi-stage Docker image (non-root), Docker Compose bound to `127.0.0.1:8080` |

## ⚡ Setup

### Requirements

- Docker Desktop, or Python 3.11+ and Node.js 20+ for local development
- An Abacus.AI API key with access to the conversations to back up

### Installation

```bash
cp .env.example .env
docker compose -f compose.yaml up --build
```

Local development:

```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

```bash
cd frontend
npm install
npm run dev
```

### Configuration

| Variable | Purpose |
|---|---|
| `ABACUS_API_KEY` | Abacus.AI API key (can also be entered in the UI) |
| `ABACUS_DEPLOYMENT_IDS`, `ABACUS_EXTERNAL_APPLICATION_IDS`, `ABACUS_CONVERSATION_TYPES` | Optional scope narrowing |
| `APP_ALLOW_UI_API_KEY`, `APP_ALLOW_PERSISTENT_API_KEY` | Allow entering / persisting the key from the UI |
| `APP_BASIC_AUTH_USER`, `APP_BASIC_AUTH_PASSWORD` | Basic Auth; both required, setting only one aborts the start |
| `APP_DATA_DIR` | Root for database, backups and settings |
| `APP_STATIC_DIR`, `APP_COMMIT`, `APP_VERSION` | Static bundle path, build metadata, Docker label version |

## 🚀 Usage

1. Open the web UI at `http://127.0.0.1:8080`.
2. Enter or verify the Abacus.AI API key under Settings.
3. Load the available conversation scopes.
4. Start a backup job and follow its progress; retry timed-out items if listed.
5. Review the chats in the table and export them (all or a selection) in the chosen formats.

## 🗂️ Project Structure

```
backend/app/     FastAPI app, Abacus client, backup engine, exporters, security
frontend/src/    React dashboard
docs/            documentation set 01–12, openapi.yaml, bug review
compose.yaml     single-container deployment
Dockerfile       multi-stage build (frontend bundle + backend)
```

## 📍 Status & Roadmap

**Status: In development.** Core backup and export work, and the security hardening (loopback binding, non-root container, Basic Auth guard) is in place. However, `PROJEKTSTAND.md` states the tool is not yet a reliable backup: listings can be silently truncated and listing errors can end a job as "completed" with missing chats.

Open (see `PROJEKTSTAND.md`, `todo2026.md`, `docs/BUGS-NAECHSTER-LAUF.md`):
- Fix silent pagination truncation and swallowed listing errors (P1)
- Retry/backoff and 429 handling against the Abacus API
- Retention/encryption for exported chats, version pinning for `abacusai`
- Tests and CI (none yet)

## 🐛 Troubleshooting

- **Not reachable from the LAN:** Compose binds to `127.0.0.1` on purpose; set both Basic Auth variables before publishing the port.
- **Start aborts:** only one of `APP_BASIC_AUTH_USER` / `APP_BASIC_AUTH_PASSWORD` is set – set both or neither.
- **A job seems stuck:** check `docker compose logs -f`; SDK calls are skipped after 120 s and listed as timed-out items.
- **Exports are empty:** select scopes and run a backup before exporting.

## 📄 License

MIT – see [LICENSE](LICENSE).

## 📚 Documentation

- [README.md](README.md)
- [CHANGELOG.md](CHANGELOG.md)
- [SECURITY.md](SECURITY.md)
- [PROJEKTSTAND.md](PROJEKTSTAND.md)
- [todo2026.md](todo2026.md)
- [docs/](docs/README.md)

## 👨‍💻 Developer

Developed by [mrhymes26](https://github.com/mrhymes26)

## ☕ Support the Project

If you find this project useful, consider supporting its development:

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/mrhymes)
