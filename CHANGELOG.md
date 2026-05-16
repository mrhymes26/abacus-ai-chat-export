# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Fixed

- **Export hang after timeout:** `ThreadPoolExecutor` used `shutdown(wait=True)` on exit, so a timed-out Abacus SDK call still blocked the job forever. Timeouts now use `shutdown(wait=False)` so the backup continues.
- **HTML export order:** Conversation transcript (`*_Konversation.html`) is written before the optional SDK `export_deployment_conversation` call, so deployment chats still get a readable HTML file when the SDK export hangs.

### Added

- **API timeout handling:** Each `get_chat_detail` and `export_chat_html` SDK call has a 120-second timeout. If the Abacus API does not respond in time, the item is skipped and the job continues with the next chat.
- **Timeout UI warning:** The job progress panel shows a prominent amber warning when items are skipped due to API timeout, so users know immediately without checking the error log.

### Documentation

- **README:** Clarifies English UI/API copy vs. legacy `_Konversation` transcript filename suffix; HTML export section rewritten for clarity.
- **README:** Project structure updated to include all backend modules (`config.py`, `security.py`, `local_settings.py`, `utils.py`) and complete frontend `src/` tree.
- **README:** Technical Details lists exact dependency version ranges from `requirements.txt` (`fastapi>=0.115`, `uvicorn>=0.30`, `pydantic>=2.7`, `abacusai>=1.4`).
- **README:** API Endpoints table documents query parameters for `GET /api/chats`.
- **README:** UI preview mockup screenshot added.

## [1.0.0] — 2026-05-08

First stable release of the Abacus Backup Chat Export Manager.

### Added

- **Versioning:** `APP_VERSION` is `1.0.0`; `GET /api/health` returns `version`, and each backup `manifest.json` includes optional `app_version`. Backup `index.html` shows the version when present.
- **Open WebUI export:** Optional format `openwebui` writes per-chat `*_openwebui.json` and root `openwebui_import.json` for importing conversations into Open WebUI (see README).
- **`LICENSE`:** MIT license at the repository root.
- **`SECURITY.md`:** Security policy and private vulnerability reporting guidance for GitHub.

### Fixed

- **Selected export:** Backend matched selection IDs against bare `item.id`, so duplicate IDs across deployments could export far more chats than selected. Matching now uses only the canonical key `type:deployment_id_or_empty:id`, aligned with the UI (`chatSelectionKey`).
- **HTML transcript / Markdown:** Many deployment conversations keep the assistant’s visible text in nested **`segments`** while the `text` field is empty. The export now flattens `segments` (incl. collapsible/routing blocks) so `*_Konversation.html` and Markdown include full assistant turns. **Complete raw data** (incl. all keys) remains in **`*.json`**.

### Changed

- **`*_Konversation.html`:** Assistant/BOT bubbles render a safe Markdown subset (headings, lists, tables, links, **bold**, `code`, routing blockquotes, “Web Search” / “Search Results” labels) instead of a single pre-wrapped plain block; user messages remain plain text. Export text is tidied so broken `**…**` across blank lines and split markdown table rows (e.g. line breaks inside a cell) read correctly. **Print/PDF:** preserves intentional line breaks in paragraphs (`pre-line`), uses word-boundary wrapping and hyphenation, repeats table header rows, and allows long bubbles to split across pages instead of forcing whole messages onto one sheet.
- **UI navigation:** Sidebar switches views between **Chats** (table, export, job progress), **Backups**, and **Settings** (API key, connection status, conversation scopes) so the main workflow stays focused.
- **Conversation scopes:** Panel copy distinguishes automatic SDK discovery from optional manual narrowing; labels and hints are clearer for typical backup use.
- **Deployment conversation detail:** Fetch uses extended parameter variants (higher limit, `include_all_versions`) and records a warning when history length may be incomplete versus `total_events`.
- **HTML-only export:** If the job request contains **only** `html` in `formats`, the backup writes **`{stem}_Konversation.html`** per chat only (no SDK `*_html.*` side files). Combined with other formats, the SDK export still runs and `*_Konversation.html` is always included when HTML is selected.
- **`*_Konversation.html` (screen + print):** Screen hint for PDF/print (hidden when printing), `@page` A4 margins, and print color adjustment for export from Chrome/Edge/Firefox.
- **Backup overview:** Every export writes **`index.html`** at the backup root — a navigable HTML summary (table of chats, links to exported files, plus `manifest.json` / `errors.log`). `manifest.json` includes `"index_html": "index.html"`.
- **Chat table:** **Pagination** — selectable **10 / 50 / 100** rows per page and **Previous / Next** navigation for large lists (replacing the earlier preview-only expand pattern).
- **Export panel:** Explains job flow, ZIP timing, and “all” vs “selection” modes.
- **Conversation scopes:** Long scope lists use a preview (first 10 lines) with expand to edit the full textarea.
- **Status / Conversation Scopes:** Long lists of scope chips use the same preview (10 chips) with expand/collapse and scrollable areas.
- **HTML export files:** Sidecar for structured SDK responses renamed from `*.export.json` to `*.meta.json`; HTML export base name uses `_html` (e.g. `Title_id_html.html` / `Title_id_html.meta.json`) so filenames no longer contain a misleading `.export.` segment.
- **Language:** Web UI, API `detail` messages, job/backup notifications, and generated HTML (`*_Konversation.html`, backup `index.html`) are in English (`lang="en"` where applicable).
- **`*_Konversation.html`:** Chat bubbles avoid horizontal scroll — `overflow-x` capped, timestamps no longer use `float`/`nowrap` beside text; long ISO times and user text wrap readably.
- **UI:** Storage path (`data_dir`) appears only under **Settings**, not in the sidebar.

### Documentation

- **README:** Documents Open WebUI export files (`*_openwebui.json`, `openwebui_import.json`) and import behavior.
- **README:** Clarifies collapsed chat list, export/ZIP behavior, and related UX notes.
- **README:** Notes that Abacus.AI does not offer a web UI export for chats; data access is via the API/SDK only.
- **README:** License section and badge reference the MIT `LICENSE` file; project structure lists `LICENSE` and `SECURITY.md`.
- **README:** English guide for creating, storing, and rotating your Abacus.AI API key, with links to the official API Keys dashboard and Python SDK getting-started documentation.
- **README:** Contributing section explains that contributor names on GitHub come from Git commit authors, not from README body.
- **`.env.example`:** Short header comments (copy to `.env`; do not commit secrets).
