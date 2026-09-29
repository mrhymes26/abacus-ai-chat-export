# Projektstand: app-abacus-chat-backup

Stand: 29. September 2026 · QA-Audit mit Build/Test-Lauf (vorherige Erhebung: 11.08.2026, statisch).

## Kurzfassung

Self-hosted Backup- und Export-Manager für Abacus.AI-Chatverläufe (JSON,
Markdown, HTML, Open WebUI, ZIP): FastAPI-Backend, React/Vite-Dashboard, lokale
SQLite, ein Docker-Image. Sauber verpacktes Repo mit `LICENSE` (MIT),
`SECURITY.md`, `CHANGELOG.md`, `RELEASE_README.md`.

**Reifegrad: MVP.** Die Sicherheitshärtungen (Loopback-Bindung, `USER app`,
`/docs` aus, Security-Header, Abbruch bei halber Auth-Konfiguration) sind
committet. Im Audit wurden zwei der drei stillen Unvollständigkeitspfade
(Fehlerzählung, Inhaltsverlust im Export) sowie das Executor-Leck behoben. Offen
bleiben vor allem die stille Truncation bei der Paginierung, fehlendes
Retry/Backoff und das völlige Fehlen von Tests — bis dahin gilt das Tool nicht als
verlässliches Backup.

## Technik

- **Backend:** Python 3.11+, FastAPI + uvicorn, SQLite, `abacusai`-SDK. Module
  unter `backend/app/` (`main.py`, `abacus_client.py`, `backup_engine.py`,
  `exporters.py`, `database.py`, `jobs.py`, `config.py`, `security.py`,
  `local_settings.py`, `utils.py`, `models.py`) — rund 3.470 Zeilen.
- **Frontend:** React + TypeScript + Vite 5.4.21 + Tailwind, 8 Komponenten unter
  `frontend/src/components/`.
- **Betrieb:** Multi-Stage-`Dockerfile` (`USER app`), `compose.yaml` an
  `127.0.0.1:8080`; Backend liefert das React-Bundle same-origin aus.
- **Secrets:** zentrale Registrierung und rekursive Redaction in
  `backend/app/security.py`, `chmod 0600` auf der Schlüsseldatei,
  konstantzeitiger Vergleich; keine getrackte `.env`, nur `.env.example`.

## Aktivität

- Letzter Commit: 2026-08-11 (Zeilenenden-Normalisierung), 20 Commits, **keine
  Tags** — obwohl `CHANGELOG.md` ein `[1.0.0] — 2026-05-08` führt.
- Arbeitsbaum: sauber; die Audit-Änderungen vom 29.09.2026 (siehe unten, samt
  `todo2026.md` und dieser Datei) sind committet.
- Version: `backend/app/models.py:9` `APP_VERSION = "1.0.0"` und
  `frontend/package.json` `1.0.0`, während `CHANGELOG.md` einen gefüllten
  `[Unreleased]`-Block führt — `/api/health` meldet damit einen veralteten Stand.

## Doku

Vorhanden: `README.md` (englisch), `CHANGELOG.md`, `SECURITY.md`, `LICENSE`
(MIT), `RELEASE_README.md`, `todo2026.md`, `MONETARISIERUNGSBEWERTUNG.md`,
`.env.example`, `docs/` (01–12, `DOKUMENTATION.md`, `openapi.yaml`,
`preview-ui.png`). Fehlt: `HANDBUCH.md`.

Drift: `docs/12-offene-punkte.md` führt Schuld 1 („Härtungen nicht
eingecheckt"), Schuld 2 (Fail-open bei halber Auth-Konfiguration) und Schuld 25
(`frontend/dist/` eingecheckt) noch als offen — alle drei sind erledigt
(**Drift behoben 2026-09-29:** `docs/01`–`12` und `docs/README.md` nachgezogen). Ebenso
sind N2 (`/docs` aktiv), M3 (root-Container) und N3 (keine Security-Header) aus
`todo2026.md` erledigt.

## Build/Test (29.09.2026)

- **Keine Testsuite, keine CI** (weder `.github/` noch `.gitea/`).
- `python -m compileall backend/app` → grün.
- Smoke-Skript (venv mit FastAPI) gegen die geänderten Funktionen — Diamant und
  Zyklus im Export, Basic-Auth mit Umlauten, Timeout/Fehler/Erfolg in
  `_call_with_timeout` → grün.
- Frontend nicht gebaut (kein `node_modules` auf dem Share).

## Im Audit behoben (29.09.2026)

Die Audit-Änderungen vom 29.09.2026 sind committet:

- `backend/app/backup_engine.py:14-28` – `_call_with_timeout` fährt den Executor
  in `finally` herunter (vorher unerreichbarer `else`-Zweig, Leck bei jedem
  Erfolg/SDK-Fehler; Schuld 12).
- `backend/app/backup_engine.py` (~91-98, ~180) – `detail_ok`-Flag: Items mit
  Timeout/Fehler beim Detail-Abruf zählen als `failed`, auch wenn eine
  Vorschau-Stub-Datei geschrieben wurde (Schuld 5).
- `backend/app/security.py` (~111) – `basic_auth_matches` vergleicht UTF-8-Bytes
  (Umlaute → 401 statt `TypeError`/HTTP 500; Schuld 17).
- `backend/app/exporters.py:57-66` – `seen` pfadbezogen; mehrfach referenzierte
  Objekte werden nicht mehr durch `str(obj)` ersetzt (Schuld 18).

## Offene Probleme nach Priorität

Quellen: Audit 29.09.2026, `todo2026.md`, `docs/12-offene-punkte.md`.

### P1

- **Stille Truncation bei Bare-List-Paginierung**
  (`backend/app/abacus_client.py:141-146`, Schuld 4): liefert eine SDK-Methode
  eine nackte Liste ohne `page_token`/`has_more`, endet die Schleife nach der
  ersten Seite — ältere Chats fehlen unbemerkt. Explizites `limit`, bei
  `len(page) == limit` weiterblättern, im Manifest vermerken.

### P2

- Kein Retry/Backoff/`Retry-After`/429-Handling (Schuld 7); `try_call_variants`
  iteriert auch bei Last-Fehlern weiter und verstärkt die Last.
- Doppelexport organisationsweiter Konversationen: Dedupe-Schlüssel enthält
  `deployment_id` (`abacus_client.py:292-294`, Schuld 13).
- Backups (Chat-PII) unverschlüsselt und ohne Retention unter `/data/backups`,
  im selben Volume wie die API-Schlüsseldatei (Schuld 3).
- `abacusai>=1.4` ohne Obergrenze trotz Duck-Typing auf Methodensignaturen; kein
  Python-Lockfile (Schuld 10).
- Keine Tests, keine CI (Schuld 6) — die reinen Funktionen (Paginierung,
  `_best_message_list`, `_normalize_role`, Markdown-Erzeugung, `safe_filename`)
  sind ohne Infrastruktur testbar; dazu E2E gegen einen Fake-SDK-Client.

### P3

- Logging nur teilweise: Logger vorhanden, aber keine Logging-Konfiguration;
  zwei `except`-Pfade verschlucken Ausnahmen (Schuld 8).
- Vite 5.4.21, `dev`/`preview` mit `--host 0.0.0.0` (Schuld 24).
- `@app.on_event("startup")` (`main.py:135`) statt `lifespan` (Schuld 20);
  keine Schemaversionierung per `PRAGMA user_version` (Schuld 14).
- Rate-Limit/Lockout/Auth-Logging an `/api/connect` und Auth-Middleware
  (Schuld 9); CSRF-Schutz bei Basic-Auth (Schuld 16); generische Fehlermeldungen
  mit Korrelations-ID (Schuld 15).
- Reconciliation verwaister Teil-Backups (Schuld 11); Chat-Cache-TTL (Schuld 19);
  Löschweg für die Jobtabelle (Schuld 21); toter Code `mask_secret` (Schuld 22).
- Versionierung ordnen: Release aus `[Unreleased]` schneiden, Tag setzen
  (Schuld 23).
- Lizenzfrage: `LICENSE` ist MIT, `docs/` nimmt „proprietär" an; bei MIT eine
  `NOTICE` für Apache-2.0-/CC-BY-4.0-Anteile.

## Empfehlung

Paginierung und Retry als Nächstes angehen und eine pytest-Suite mit Fake-SDK
aufbauen, danach ein Release taggen.
