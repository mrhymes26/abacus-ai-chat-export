# Abacus Backup Chat Export Manager

A local Docker web application to backup and export your Abacus.AI chats and deployment conversations using the official Python library `abacusai`.

![Version](https://img.shields.io/badge/version-1.0.0-047857.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)
![Backend](https://img.shields.io/badge/backend-FastAPI-009688.svg)
![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20Vite-61DAFB.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-yellow.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

The app runs locally, connects to Abacus.AI only via API key, and stores backups persistently in a Docker volume. No browser scraping, no Selenium, no Playwright, and no Abacus password login. The **web UI and API user-facing messages are English**; generated HTML uses English copy inside files (some export filenames still use the legacy `_Konversation` suffix—see [HTML](#html)).

**Release:** `1.0.0` (see [CHANGELOG](CHANGELOG.md)). New backups include `app_version` in `manifest.json` alongside `app`. The running app reports the same value from `GET /api/health` (`version`).

**Security:** See [SECURITY.md](SECURITY.md) for how to report vulnerabilities privately.

## Background

Abacus.AI does **not** provide a built-in product feature to download or bulk-export chats from the web UI (no first-party “export conversation” button or similar). Access to conversation data is **only via the official API**, through clients such as the Python SDK (`abacusai`). This application implements that API-backed retrieval and packaging locally—there is no separate Abacus-side export service beyond what the API exposes for your account.

This project was built for a simple need: keep local, inspectable backups of Abacus.AI conversations without manual copy-paste work or browser automation. The goal is a tool that:

- just works locally in Docker
- uses the official `abacusai` SDK
- keeps API keys out of logs, manifests, backup files, and browser storage
- exports selected chats or everything in one run
- creates useful backup formats for humans and developers
- survives container restarts through a persistent Docker volume

## Features

- **API-key connection** - Connect via `.env`, Docker environment, temporary UI input, or explicit local persistence.
- **Official SDK only** - Uses `from abacusai import ApiClient`.
- **No scraping** - No browser automation, Selenium, Playwright, cookies, or password login.
- **Chat discovery** - Loads AI chat sessions and deployment conversations where the SDK/account allows it.
- **Deployment conversation scopes** - Automatically discovers deployment/external application scopes where the SDK allows it; manual overrides are available in the UI.
- **Multi-select export** - Select individual chats or export everything.
- **Export formats** - JSON, Markdown, HTML, Open WebUI import JSON, and optional ZIP archive.
- **Backup history** - View manifests, download ZIPs, and delete local backups.
- **Persistent local storage** - SQLite metadata and backup files live under `/data`.
- **Local API-key persistence** - Optional, clearly marked local storage under `/data/secrets`.
- **Basic Auth option** - Protect the local UI/API with `APP_BASIC_AUTH_USER` and `APP_BASIC_AUTH_PASSWORD`.
- **Docker ready** - One image containing backend and built frontend.

## Screenshots

![Abacus Backup Chat Export Manager — Chats view](docs/preview-ui.png)

*Example mockup — the actual UI may differ slightly.*

The main view shows the chat table with filters, multi-select, pagination, and the export panel (format toggles, mode, ZIP option). Navigation via the sidebar: **Chats**, **Backups**, **Settings**.

After running the app, open:

```text
http://localhost:8080
```

## Requirements

- Docker Desktop or Docker Engine with Docker Compose
- An Abacus.AI API key (see [Abacus.AI API key: how to create and use it](#abacusai-api-key-how-to-create-and-use-it))
- Local port `8080` available

For development:

- Python 3.11+
- Node.js 20+

## Quick Start

```bash
cp .env.example .env
# edit .env: set ABACUS_API_KEY (see "Abacus.AI API key" in README), or paste the key in the UI under Settings
docker compose up -d --build
```

Open:

```text
http://localhost:8080
```

Check status:

```bash
docker compose ps
```

Stop the app:

```bash
docker compose down
```

## Installation

### Option 1: Docker Compose

```bash
git clone https://github.com/OWNER/REPO.git
cd REPO
cp .env.example .env
docker compose up -d --build
```

Replace `https://github.com/OWNER/REPO.git` with your fork or upstream clone URL.

### Option 2: Docker Build

```bash
docker build -t abacus-backup-manager:local .
docker run --rm -p 8080:8080 \
  -e ABACUS_API_KEY="your-api-key" \
  -e APP_DATA_DIR=/data \
  -v abacus_backup_data:/data \
  abacus-backup-manager:local
```

## Configuration

Configuration can be provided through `.env`, Docker Compose environment variables, or the UI where supported.

| Variable | Default | Description |
| --- | --- | --- |
| `ABACUS_API_KEY` | empty | Abacus.AI API key. Recommended for regular use; see [Abacus.AI API key: how to create and use it](#abacusai-api-key-how-to-create-and-use-it). |
| `ABACUS_DEPLOYMENT_IDS` | empty | Deployment IDs for deployment conversations. |
| `ABACUS_EXTERNAL_APPLICATION_IDS` | empty | External application IDs for deployment conversation listing. |
| `ABACUS_CONVERSATION_TYPES` | empty | Conversation type scopes required by some SDK/account setups. |
| `APP_DATA_DIR` | `/data` | Container data directory. |
| `APP_ALLOW_UI_API_KEY` | `true` | Allows API-key entry in the UI. |
| `APP_ALLOW_PERSISTENT_API_KEY` | `true` | Allows the "store locally" UI mode for API keys. |
| `APP_BASIC_AUTH_USER` | empty | Optional Basic Auth username. |
| `APP_BASIC_AUTH_PASSWORD` | empty | Optional Basic Auth password. |

Example:

```env
ABACUS_API_KEY=
ABACUS_DEPLOYMENT_IDS=
ABACUS_EXTERNAL_APPLICATION_IDS=
ABACUS_CONVERSATION_TYPES=
APP_ALLOW_UI_API_KEY=true
APP_ALLOW_PERSISTENT_API_KEY=true
APP_BASIC_AUTH_USER=
APP_BASIC_AUTH_PASSWORD=
```

## Abacus.AI API key: how to create and use it

This app authenticates to Abacus.AI **only** with an API key (no password login in the browser). Create the key in your Abacus.AI account, then supply it to the container or the web UI.

### 1. Create an API key

1. **Sign up or sign in** at [Abacus.AI](https://abacus.ai/).
2. Open the **API Keys** area in your account. The official Python SDK getting-started guide points to the dashboard at **[abacus.ai/app/profile/apikey](https://abacus.ai/app/profile/apikey)** (sign-in required).
3. Use **Generate** / **Create API key** (wording may vary slightly in the product UI).
4. **Copy the key once** when it is shown. Many products only display the full secret at creation time—store it in a password manager or your local `.env` immediately.
5. **Do not** commit API keys to git, paste them into public chats, or share screenshots that include the key.

Official references:

- [Python SDK — Getting started](https://api.abacus.ai/help/python-sdk/getting-started) (prerequisites include generating a key from the API Keys dashboard).
- [Abacus.AI help / API](https://abacus.ai/help/api/) for broader platform documentation.

### 2. Provide the key to this application

Pick **one** primary method (you can still override from the UI when allowed):

| Method | What to do |
| --- | --- |
| **`.env` / Compose** | Set `ABACUS_API_KEY` in `.env` (see [Quick Start](#quick-start)) or under `environment:` in `compose.yaml`, then `docker compose up -d --build` (or restart the stack) so the container sees the new value. |
| **Docker run** | Pass `-e ABACUS_API_KEY="..."` when starting the container. |
| **Web UI** | Open **Settings**, enter the key, click **Test connection**. By default the key stays in **server memory only**. If you enable optional persistence, it is written under `/data/secrets/` inside the volume (see [Privacy and Security](#privacy-and-security)). |

If `APP_ALLOW_UI_API_KEY` is set to `false`, API key entry in the UI is disabled and you must use environment configuration.

### 3. Rotate or revoke a key

1. In the Abacus.AI **API Keys** dashboard, **create a new key**.
2. Update this app: change `ABACUS_API_KEY` in `.env` (and recreate the container), or enter the new key under **Settings** and **Test connection**.
3. After backups work with the new key, **revoke or delete** the old key in the Abacus.AI dashboard so it cannot be misused.

### 4. If the key stops working

- Confirm the key was not rotated or expired on the Abacus.AI side.
- After editing `.env`, **restart** the Docker container so the process reloads environment variables.
- Use **Test connection** in the UI to surface SDK-level errors (for example missing methods for your account type).

## Usage

### 1. Connect

1. Open the web UI.
2. If you have not set `ABACUS_API_KEY` in the environment, create a key as described in [Abacus.AI API key: how to create and use it](#abacusai-api-key-how-to-create-and-use-it), then enter it under **Settings** (or set it in `.env` first).
3. Click **Test connection**.
4. The app discovers available Abacus SDK methods.

API keys are never returned to the frontend. If entered in the UI, the key is kept in server memory by default. If you explicitly enable local persistence, it is stored under:

```text
/data/secrets/abacus_api_key.local
```

### 2. Deployment Conversation Scopes

The app automatically tries to discover scopes through the official SDK:

- `list_projects`
- `list_deployments`
- `list_external_applications`
- SDK conversation type enum fallback

Some Abacus SDK/account setups require at least one scope for `list_deployment_conversations`. The official Abacus documentation lists `deploymentId`, `externalApplicationId`, and `conversationType` for `listDeploymentConversations`; in the Python SDK these are called as `deployment_id`, `external_application_id`, and `conversation_type`.

If autodiscovery is not enough, go to **Settings** and enter one or more manual values in:

- Deployment IDs
- External Application IDs
- Conversation Types

The values are stored locally in:

```text
/data/settings/conversation_scopes.json
```

### 3. Load Chats

Click **Load chats** or **Refresh**. The app lists available AI chat sessions and deployment conversations.

Long lists use **pagination**: choose **10**, **50**, or **100** rows per page under the table, with **Previous / Next** for additional pages. **Select all** still selects every row that matches the current filters, not only the visible page.

### 4. Select and Export

1. Select individual chats or choose **Export all** (all exportable chats from the loaded list, independent of checkboxes).
2. Choose export formats: JSON, Markdown, HTML, Open WebUI.
3. **Create ZIP**: when enabled, the server writes per-chat files first, then builds `backup.zip` at the **end** of the job (same folder contents, not a second export). When disabled, only loose files are written; the backup download endpoint can still create the ZIP on first download if needed.
4. Start the export and watch job progress.

### 5. Download Backups

Completed backups appear in **Backup history**. You can:

- view `manifest.json`
- download ZIP
- delete the local backup

## Export Formats

### JSON

Best for complete archival and developers. SDK objects are converted defensively with `.to_dict()`, dictionaries, lists, datetime values, bytes handling, and safe fallbacks.

### Markdown

Best for readable chat transcripts. The exporter searches common message fields such as:

- `messages`
- `chat_messages`
- `conversation`
- `events`
- `history`
- `turns`
- `responses`
- `thread`

If no clear message list is found, Markdown contains a short note and JSON remains the source of truth.

### HTML

Best when the Abacus SDK provides an export method returning HTML or export content. If the SDK only returns metadata or a URL, metadata is stored and no external download is forced.

**Conversation transcript (extra HTML file):** Whenever HTML is included in an export, the app also writes a **print-friendly transcript** per chat. The filename pattern is **`{title}_{id}_Konversation.html`**. The `_Konversation` part is a **legacy suffix** (from the German word *Konversation*) kept so existing backup paths and scripts keep working; the **inside of the file** (labels, hints, layout copy) is **English**, like the web UI.

That transcript is derived from the chat payload (same message detection as Markdown): alternating **user** vs **assistant** (plus **system** when present), timestamps when available, and a short legend at the top. **Assistant bubbles** render a safe subset of Markdown (headings, lists, **bold**, links, blockquotes, and pipe tables) so long BOT replies with web-search style layout stay readable; user messages stay as plain pre-wrapped text. Use this file when you want to see who said what. It is styled for **screen reading** and for **browser print / Save as PDF** (`@media print`, A4-oriented margins, page-break handling). When printing, assistant paragraphs keep **explicit line breaks** from the export text (`white-space: pre-line`), while long lines wrap at **word boundaries** with hyphenation where the browser supports it; very long user lines still use `pre-wrap` with safe wrapping. For many **deployment** conversations, the API stores the assistant’s answer in nested **`segments`** (not in the top-level `text` field); the export flattens those so the preview matches the full thread. The **authoritative, lossless** copy of the session is still **`*.json`**, including `history` and all segment objects.

If you select **only HTML** as export format (JSON/Markdown unchecked), each chat produces **only** the transcript file `*_Konversation.html` — no SDK `*_html.*` artifacts — ideal for a single handoff document (PDF/print). When HTML is combined with other formats, SDK artifacts (`*_html.*`) are still written alongside JSON/Markdown as needed.

Files are written next to the other formats with a `*_html` stem: raw HTML (or text/binary when the response is not HTML) uses a normal extension (e.g. `.html`, `.txt`, `.bin`). When the SDK returns a structured object, the main document is `*_html.html` if HTML is embedded in the payload, and a sidecar `*_html.meta.json` holds the full structured response (not a misleading `*.export.json` name).

Each backup folder also contains **`index.html`** at the root: an overview page with links to every exported file (and to `manifest.json` / `errors.log`). Open it in a browser after unzipping — relative links work offline.

### Open WebUI

Best when you want to import Abacus.AI conversations into Open WebUI. The exporter creates:

- one `*_openwebui.json` file per converted chat
- one root-level `openwebui_import.json` containing all successfully converted chats from the backup job

`openwebui_import.json` follows Open WebUI's documented chat import shape: a JSON array, each item with `chat.history.messages`, `chat.history.currentId`, and `user` / `assistant` roles. If a chat payload does not expose recognizable text messages, the job records a conversion warning for that item and still keeps the JSON backup as source of truth.

### ZIP

Best for portable backup packages. ZIP contains `manifest.json`, `errors.log`, and all exported files. It is produced **after** all chats in the job are processed (or generated on first download if the job ran without up-front ZIP creation).

## Technical Details

- **Backend:** Python 3.11, FastAPI `>=0.115`, Uvicorn `>=0.30`, Pydantic `>=2.7`
- **Frontend:** React, TypeScript, Vite, TailwindCSS
- **Abacus SDK:** `abacusai>=1.4`
- **Database:** SQLite (via Python `sqlite3`, WAL mode)
- **Backup storage:** `/data/backups`
- **Container port:** `8080`
- **Runtime command:** `uvicorn app.main:app --host 0.0.0.0 --port 8080`

### Architecture

```mermaid
flowchart LR
  Browser["Browser UI"] --> API["FastAPI API"]
  API --> SDK["abacusai.ApiClient"]
  SDK --> Abacus["Abacus.AI"]
  API --> DB["SQLite /data/app.db"]
  API --> Backups["/data/backups"]
  API --> Settings["/data/settings"]
  API --> Secrets["/data/secrets"]
```

### Project Structure

```text
.
├── Dockerfile
├── compose.yaml
├── LICENSE
├── SECURITY.md
├── CHANGELOG.md
├── .env.example
├── .gitignore
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── main.py          — FastAPI routes, middleware, static SPA serving
│       ├── models.py        — Pydantic models, APP_NAME, APP_VERSION
│       ├── abacus_client.py — AbacusService wrapper around abacusai SDK
│       ├── backup_engine.py — Export job runner, folder layout, manifest
│       ├── exporters.py     — JSON/Markdown/HTML/Open WebUI/ZIP writers
│       ├── database.py      — SQLite (jobs, backups, cached chats)
│       ├── jobs.py          — JobManager (async wrapper, cancel flags)
│       ├── config.py        — Settings dataclass, env variable parsing
│       ├── security.py      — API key storage, masking, Basic Auth helpers
│       ├── local_settings.py — Conversation scope file read/write helpers
│       └── utils.py         — Date, filename, JSON, path utilities
└── frontend/
    ├── package.json
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── api.ts
        ├── types.ts
        └── components/
            ├── Layout.tsx
            ├── ChatTable.tsx
            ├── ExportPanel.tsx
            ├── JobProgress.tsx
            ├── BackupHistory.tsx
            ├── ApiKeyPanel.tsx
            ├── ConnectionStatus.tsx
            ├── ConversationScopesPanel.tsx
            └── Toast.tsx
```

## API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Healthcheck (`app`, `version`) |
| `POST` | `/api/connect` | Test API key and discover SDK methods |
| `DELETE` | `/api/api-key` | Delete locally stored API key |
| `GET` | `/api/status` | App status and config summary |
| `GET` | `/api/conversation-scopes` | Read stored conversation scopes |
| `PUT` | `/api/conversation-scopes` | Save conversation scopes |
| `GET` | `/api/chats` | List chats (`include_ai_chat`, `include_deployments`, `refresh` query params) |
| `POST` | `/api/export` | Start export job |
| `GET` | `/api/jobs/{job_id}` | Read job progress |
| `POST` | `/api/jobs/{job_id}/cancel` | Cancel job best-effort |
| `GET` | `/api/backups` | List backups |
| `GET` | `/api/backups/{backup_id}/manifest` | Read manifest |
| `GET` | `/api/backups/{backup_id}/download` | Download ZIP |
| `DELETE` | `/api/backups/{backup_id}?confirm=true` | Delete local backup |

## Privacy and Security

- Uses the official Abacus.AI Python SDK.
- No Abacus password login.
- No browser scraping or browser automation.
- API key is never returned to the frontend.
- API key is not written to SQLite.
- API key is not written to manifests, backups, or error logs.
- UI-entered API keys are not stored in browser `localStorage`.
- Optional persistent API-key storage is local only and clearly marked as unsafe/local.
- Backups contain sensitive chat contents and should be protected accordingly.
- Do not expose this app publicly without additional authentication.

Recommended for shared networks:

```env
APP_BASIC_AUTH_USER=admin
APP_BASIC_AUTH_PASSWORD=a-long-local-password
```

## Troubleshooting

### "Could not load deployment conversations"

Autodiscovery and manual scopes did not yield a usable SDK scope. Add at least one value under **Settings**: deployment ID, external application ID, or conversation type.

### "Not connected"

- Follow [Abacus.AI API key: how to create and use it](#abacusai-api-key-how-to-create-and-use-it) to verify you have a valid key.
- Click **Test connection** again.
- If using `.env`, restart the container after changing it.

### No chats appear

- Click **Refresh**.
- Verify the API key has access to the relevant Abacus resources.
- Check whether the SDK methods are listed as available in the UI.

### HTML export missing

The SDK may not expose the export method for your account or may return only metadata. JSON and Markdown exports still run where possible.

### Port 8080 already in use

Change `compose.yaml`:

```yaml
ports:
  - "8081:8080"
```

Then open `http://localhost:8081`.

## Development

### Backend

PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:APP_DATA_DIR="..\data"
uvicorn app.main:app --reload --port 8080
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8080`.

### Build Checks

```bash
python -c "import ast, pathlib; [ast.parse(p.read_text(encoding='utf-8'), filename=str(p)) for p in pathlib.Path('backend').rglob('*.py')]; print('python syntax ok')"
```

```bash
cd frontend
npm run build
```

```bash
docker build -t abacus-backup-manager:local .
```

## Contributing

Contributions are welcome. Open an issue or submit a pull request with a clear description of the change.

**Names on GitHub (for example next to the README or under “Contributors”):** Those come from **Git commit authors** (`git log`), not from the README text. Tools such as Cursor may commit as a separate identity (for example `cursoragent`). For **new** commits, set your identity in this repository: `git config user.name "Your Name"` and `git config user.email "your-email@example.com"` (use an address [verified on your GitHub account](https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-personal-account-on-github/managing-email-preferences/adding-an-email-address-to-your-github-account) so commits link to your profile). Changing authors on **old** commits rewrites history and is only reasonable before others have cloned the repo widely.

### Maintainer: cutting a GitHub release

1. Ensure `APP_VERSION` in `backend/app/models.py`, the README version badge, and `frontend/package.json` / `package-lock.json` match the release you are tagging.
2. Update [CHANGELOG.md](CHANGELOG.md): move items from `[Unreleased]` into a dated section with the new version (Keep a clean `[Unreleased]` heading for follow-up work).
3. Run checks locally: `npm run build` in `frontend/`, Docker image build if you ship containers.
4. Tag and push: `git tag -a vX.Y.Z -m "Release X.Y.Z"` then `git push origin vX.Y.Z` (replace `X.Y.Z` with the version).
5. On GitHub: **Releases** → **Draft a new release** → choose the tag, set the title to `X.Y.Z`, and paste the matching section from the changelog as release notes. Attach binaries only if you publish artifacts; the default flow is tag plus source archive.

## Changelog

Release history and notable changes: see [CHANGELOG.md](CHANGELOG.md).

## License

This project is licensed under the [MIT License](LICENSE). You may use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the software, subject to the conditions in that file.

Vulnerability reporting: [SECURITY.md](SECURITY.md).

## Support

If you find this project useful and would like to support its development, consider buying me a coffee.

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/mrhymes)

[Support on Buy Me a Coffee](https://buymeacoffee.com/mrhymes)

## Acknowledgments

- [Abacus.AI](https://abacus.ai/) for the platform and official Python SDK.
- [FastAPI](https://fastapi.tiangolo.com/) for the backend framework.
- [React](https://react.dev/) and [Vite](https://vitejs.dev/) for the frontend toolchain.

---

Made for local, practical backups of important Abacus.AI conversations.
