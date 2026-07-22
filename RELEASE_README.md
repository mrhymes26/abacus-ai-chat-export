# Abacus Backup Chat Export Manager v1.0.0 - Release Notes

## 🎉 Welcome to Abacus Backup Chat Export Manager!

**Abacus Backup Chat Export Manager** makes backing up your Abacus.AI conversations repeatable instead of manual — a FastAPI backend and a lightweight React dashboard let you run backup jobs, watch their progress, and export collected chats to JSON, Markdown, HTML, and Open WebUI formats, all self-hosted.

---

## ⚡ Quick Start

### Docker Compose (recommended)

```bash
docker compose -f compose.yaml up --build
```

Then open the web UI at **http://localhost:8080**.

### Local Development

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

---

## 🚀 First Steps

1. **Start** the backend and frontend (or the single Docker container).
2. **Enter or verify** your Abacus.AI API key in the UI.
3. **Load** the available conversation scopes.
4. **Start a backup job** and follow its progress in the dashboard.
5. **Review** the backed-up chats in the table and **export** them in your chosen formats.

---

## ✨ Features

### 🔌 Connect & Configure
- Connect to Abacus.AI through the backend client (`backend/app/abacus_client.py`)
- Manage the API key and local settings from the dashboard, with automatic SDK scope discovery plus optional manual narrowing

### 💾 Backup Jobs
- Asynchronous backup jobs with live progress information
- Crash recovery for interrupted jobs
- Completeness self-check: history length vs. `total_events` is recorded in the manifest

### 📤 Flexible Export
- Per-chat exports to **JSON** (complete raw data), **Markdown**, and **HTML** (`*_Konversation.html`, print/PDF-friendly)
- Optional **Open WebUI** export (`*_openwebui.json` + root `openwebui_import.json`)
- Every backup writes a navigable `index.html` summary plus `manifest.json` and `errors.log`
- "All" vs. "selection" export modes with a canonical selection key to avoid duplicate exports

### 📋 Review UI
- Inspect conversations in a React table with pagination (**10 / 50 / 100** rows per page)
- Sidebar navigation between Chats, Backups, and Settings
- Connection status, backup progress, export panel, and history in one dashboard

### ⏱️ Resilience
- Each `get_chat_detail` / `export_chat_html` SDK call has a **120-second timeout**; timed-out items are skipped so the job continues
- A prominent amber warning surfaces skipped items immediately
- Timed-out items are recorded (`timed_out_items`) with a **"Retry timed-out items"** button

**How it works:**
1. You provide an Abacus.AI API key (via env, a `0600` local file, or the UI).
2. A backup job iterates the discovered conversation scopes, fetching each chat's detail and HTML through the `abacusai` SDK with per-item timeout isolation.
3. Each chat is written to disk in the selected formats; the assistant's nested `segments` are flattened so transcripts include full turns.
4. A `manifest.json`, an `index.html` overview, and an `errors.log` are written per backup, and everything can be downloaded as a ZIP.
5. A real `/api/health` endpoint actively pings the local database and is wired as the Docker healthcheck.

---

## ⚙️ Configuration

Copy `.env.example` to `.env` (Docker Compose loads it for `${VAR}` substitution). Do not commit `.env`.

| Variable | Purpose | Default |
|----------|---------|---------|
| `ABACUS_API_KEY` | Abacus.AI API key | *(empty)* |
| `ABACUS_DEPLOYMENT_IDS` | Optional deployment scope narrowing | *(empty)* |
| `ABACUS_EXTERNAL_APPLICATION_IDS` | Optional external application scope | *(empty)* |
| `ABACUS_CONVERSATION_TYPES` | Optional conversation-type filter | *(empty)* |
| `APP_ALLOW_UI_API_KEY` | Allow entering the API key in the UI | `true` |
| `APP_ALLOW_PERSISTENT_API_KEY` | Allow persisting the API key locally | `true` |
| `APP_BASIC_AUTH_USER` / `APP_BASIC_AUTH_PASSWORD` | Optional Basic Auth (both required to enable) | *(empty = off)* |
| `APP_DATA_DIR` | Data/backup directory inside the container | `/data` |

### Ports & Storage

- Web UI + API on port **8080**
- Backups and the local database live under `APP_DATA_DIR` (`/data`), backed by the `abacus_backup_data` volume

---

## 📝 What's New in v1.0.0

First stable release of the Abacus Backup Chat Export Manager:

- ✅ Versioning: `APP_VERSION` is `1.0.0`; `GET /api/health` returns `version`, and each backup `manifest.json` can include `app_version`
- ✅ Open WebUI export format (`*_openwebui.json` + `openwebui_import.json`)
- ✅ Backup overview `index.html` at every backup root (table of chats, links, manifest, errors)
- ✅ Selected-export fix: matching now uses the canonical `type:deployment:id` key, preventing over-export of duplicate IDs
- ✅ HTML/Markdown export flattens nested `segments` so deployment conversations include full assistant turns
- ✅ Chat table pagination (10 / 50 / 100 rows) and sidebar view switching
- ✅ Print/PDF-friendly `*_Konversation.html` (A4 margins, page breaks, safe Markdown subset)
- ✅ English UI, API messages, and generated HTML
- ✅ MIT `LICENSE` and `SECURITY.md` at the repository root

**Unreleased (in progress):**
- ⏳ Per-call API timeout handling (120 s) with skip-and-continue behavior and a timeout UI warning
- ⏳ Timed-out item summary (`timed_out_items`) with a "Retry timed-out items" button
- ⏳ Export-hang fix: `ThreadPoolExecutor` shutdown no longer blocks the job after a timeout

> See [CHANGELOG.md](CHANGELOG.md) for the complete history.

---

## 🐛 Troubleshooting

### UI Cannot Connect
- Check the backend URL in the frontend configuration.

### Authentication Fails
- Verify the Abacus API key and its permissions.

### A Backup Job Stalls
- Inspect backend logs with `docker compose logs -f`. Long-hanging SDK calls are skipped after 120 s and listed as timed-out items to retry.

### Exports Are Empty
- Confirm that conversation scopes were selected and backed up before exporting.

---

## 📦 System Requirements

- **Docker Desktop** for the simplest start, **or**
- **Python 3.11+** for the backend and **Node.js 20+** for the frontend
- An **Abacus.AI API key** with access to the conversations you want to back up
- Backend dependencies pin `fastapi>=0.115`, `uvicorn>=0.30`, `pydantic>=2.7`, `abacusai>=1.4`

---

## 📄 License

This software is licensed under the **MIT License**.

See the [LICENSE](LICENSE) file for full license text.

---

## 🤝 Support & Contributing

### Getting Help
- **Documentation:** See the main [README.md](README.md).
- **Security policy:** See [SECURITY.md](SECURITY.md).
- **Issues:** Report issues in the repository.

### ☕ Support the Project

If you find this project useful, consider supporting its development:

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/mrhymes)

[Support on Buy Me a Coffee](https://buymeacoffee.com/mrhymes)

---

## 👨‍💻 Developer

Developed by [mrhymes26](https://github.com/mrhymes26)

---

## 🔒 Security

This tool is designed for **local or self-hosted use**, so secrets and exported conversations stay under your control:

- **Secret redaction** across all outputs (JSON / Markdown / HTML / error messages)
- **Constant-time Basic Auth** comparison and parameterized SQL throughout
- **Path-traversal protection** on backup paths and static file serving
- **No SSRF surface** — outbound calls go only through the `abacusai` SDK client
- **XSS-safe HTML export** (escaped output, `http(s)` links only)
- **Real `/api/health`** with an active DB ping, wired as the Docker healthcheck

**Please note before exposing beyond localhost (see `todo2026.md`):**
- 🟠 **Basic Auth is off by default** and the container binds `0.0.0.0:8080`. With no auth the entire API (chat downloads, key entry, deletes) is open. **Bind to `127.0.0.1` and/or require auth (or a reverse proxy)** before exposing it.
- 🟠 **Exported chats are stored unencrypted** and unbounded under `/data/backups` — treat the volume as sensitive and consider retention/rotation.
- Store API keys only in local environment/configuration files, and never commit `.env` files or exported chat archives.

---

## 📚 Additional Resources

- **Full Documentation:** [README.md](README.md)
- **Security Policy:** [SECURITY.md](SECURITY.md)
- **Changelog:** [CHANGELOG.md](CHANGELOG.md)
- **Open Tasks & Review Findings:** [todo2026.md](todo2026.md)

---

## ⚠️ Important Notes

- This is a **self-hosted, single-operator tool** — harden the deployment (bind address, auth) before multi-user or networked use.
- Exports may contain **private or business conversation data**; treat backups and ZIPs as sensitive.
- Abacus.AI provides **no web UI export** for chats — data access is via the API/SDK only.

---

**Never lose an Abacus chat again. 💬**

---

*Abacus Backup Chat Export Manager v1.0.0 - Repeatable, self-hosted chat backups.*
