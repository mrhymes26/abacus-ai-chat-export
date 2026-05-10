# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Added

- **Open WebUI export:** Optional format `openwebui` writes per-chat `*_openwebui.json` and root `openwebui_import.json` for importing conversations into Open WebUI (see README).

### Fixed

- **Selected export:** Backend matched selection IDs against bare `item.id`, so duplicate IDs across deployments could export far more chats than selected. Matching now uses only the canonical key `type:deployment_id_or_empty:id`, aligned with the UI (`chatSelectionKey`).
- **Konversation / Markdown:** Many deployment conversations keep the assistant’s visible text in nested **`segments`** while the `text` field is empty. The export now flattens `segments` (incl. collapsible/routing blocks) so `*_Konversation.html` and Markdown include full assistant turns. **Complete raw data** (incl. all keys) remains in **`*.json`**.

### Changed

- **UI navigation:** Sidebar switches views between **Chats** (table, export, job progress), **Backups**, and **Settings** (API key, connection status, conversation scopes) so the main workflow stays focused.
- **Conversation scopes:** Panel copy distinguishes automatic SDK discovery from optional manual narrowing; labels and hints are clearer for typical backup use.
- **Deployment conversation detail:** Fetch uses extended parameter variants (higher limit, `include_all_versions`) and records a warning when history length may be incomplete versus `total_events`.
- **HTML-only export:** If the job request contains **only** `html` in `formats`, the backup writes **`{stem}_Konversation.html`** per chat only (no SDK `*_html.*` side files). Combined with other formats, the SDK export still runs and `*_Konversation.html` is always included when HTML is selected.
- **Print / PDF:** `*_Konversation.html` includes screen hint (hidden when printing), `@page` A4 margins, `break-inside: avoid` on messages, and print color adjustment for PDF export from Chrome/Edge/Firefox.
- **Backup overview:** Every export writes **`index.html`** at the backup root — a navigable HTML summary (table of chats, links to exported files, plus `manifest.json` / `errors.log`). `manifest.json` includes `"index_html": "index.html"`.
- **Chat table:** Long lists show the first 10 rows by default; optional expand/collapse with a note that “select all” applies to the full filtered list.
- **Export panel:** Explains job flow, ZIP timing, and “all” vs “selection” modes.
- **Conversation scopes:** Long scope lists use a preview (first 10 lines) with expand to edit the full textarea.
- **Status / Conversation Scopes:** Long lists of scope chips use the same preview (10 chips) with expand/collapse and scrollable areas.
- **HTML export files:** Sidecar for structured SDK responses renamed from `*.export.json` to `*.meta.json`; HTML export base name uses `_html` (e.g. `Title_id_html.html` / `Title_id_html.meta.json`) so filenames no longer contain a misleading `.export.` segment.

### Documentation

- **README:** Documents Open WebUI export files (`*_openwebui.json`, `openwebui_import.json`) and import behavior.
- **README:** Clarifies collapsed chat list, export/ZIP behavior, and related UX notes.
- **README:** Notes that Abacus.AI does not offer a web UI export for chats; data access is via the API/SDK only.
