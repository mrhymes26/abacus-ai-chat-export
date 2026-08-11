# Projektstand: app-abacus-chat-backup

Stand: 11. August 2026 · Erhoben durch statische Analyse (kein Build).

## Kurzfassung

Self-hosted Backup- und Export-Manager für Abacus.AI-Chatkonversationen:
FastAPI-Backend, React/Vite-Dashboard, lokale SQLite, ein Docker-Image. Das
sauberste Repo des Portfolios — 18 Commits, sauberer Arbeitsbaum, `LICENSE`
(MIT), `SECURITY.md`, `CHANGELOG.md`, `RELEASE_README.md`. Die
Sicherheitshärtungen, die die Doku noch als „nicht eingecheckt" führt, **sind
inzwischen committet**. Das Dringendste sind jetzt die drei Stellen, an denen ein
Backup **lautlos unvollständig** wird — bei einem Backup-Werkzeug die gefährlichste
Fehlerklasse — und das vollständige Fehlen von Tests.

## Technik

- **Backend:** Python 3.11+, FastAPI + uvicorn, SQLite, `abacusai`-SDK.
  9 Module unter `backend/app/` (`main.py`, `abacus_client.py`,
  `backup_engine.py`, `exporters.py`, `database.py`, `jobs.py`, `config.py`,
  `security.py`, `local_settings.py`, `utils.py`, `models.py`) — zusammen
  **3.468 Zeilen**.
- **Frontend:** React + TypeScript + Vite + Tailwind, 8 Komponenten unter
  `frontend/src/components/`.
- **Betrieb:** ein Docker-Image (`Dockerfile`), `compose.yaml`; Auslieferung
  same-origin (Backend liefert das React-Bundle aus). Port 8080.
- **Umfang:** 62 getrackte Dateien.
- **Exportformate:** JSON, Markdown, HTML, ZIP, Open WebUI.

## Aktivität

- Letzter Commit: `2026-07-30 up`
- Commits gesamt: **18**
- Tags: **keine** — obwohl `CHANGELOG.md` ein `[1.0.0] — 2026-05-08` führt.
- `git status --short`: **sauber.** Keine uncommitteten Änderungen, keine
  CRLF-Artefakte.

Reifegrad: **funktionsfähig, mit veröffentlichungsnaher Verpackung**
(`RELEASE_README.md`, Badges, Screenshot), aber ohne Tests und ohne CI. Seit dem
30.07.2026 keine Aktivität.

## Doku

Vorhanden: `README.md` (englisch, ausführlich), `CHANGELOG.md` (Keep-a-Changelog,
mit offenem `[Unreleased]`-Block), `SECURITY.md`, `LICENSE` (MIT),
`RELEASE_README.md`, `todo2026.md`, `MONETARISIERUNGSBEWERTUNG.md`,
`.env.example`, `docs/` (01–12, `DOKUMENTATION.md`, `README.md`, `openapi.yaml`,
`preview-ui.png`).

Fehlt: `HANDBUCH.md`. Die Doku ist überwiegend englisch, die Reviews
(`todo2026.md`, `docs/`) sind deutsch.

## Tests

**Keine.** Kein `tests/`-Verzeichnis, keine Test-Abhängigkeiten in
`backend/requirements.txt`, keine CI (weder `.github/` noch `.gitea/`).

`docs/12-offene-punkte.md` (Schuld 6) stuft das als Risiko **hoch** ein und
argumentiert überzeugend: die risikoreichsten Teile (Paginierung,
`_best_message_list`, `_normalize_role`, `_history_complete_by_total_events`,
Markdown-Erzeugung, `safe_filename`) sind reine Funktionen und ohne Infrastruktur
testbar. Die Schulden 4, 5 und 12 wären durch Unit-Tests aufgefallen.

## Offene Punkte

Quelle: `todo2026.md` (Review 2026-07-26) und `docs/12-offene-punkte.md`
(Schulden 1–25). Nachfolgend gegen den Code vom 11.08.2026 abgeglichen.

### Wichtig

- [ ] **Paginierung reparieren** (Schuld 4, `backend/app/abacus_client.py:139-147`).
      Liefert eine SDK-Methode eine nackte Liste ohne `page_token` und ohne
      `has_more`, bricht die Schleife nach der ersten Seite ab — ältere Chats
      werden lautlos nicht gesichert. Explizites `limit` mitgeben, bei
      `len(page) == limit` offsetbasiert weiterblättern, im Manifest vermerken.
- [ ] **Fehlerzählung korrigieren** (Schuld 5,
      `backend/app/backup_engine.py:174-175`). Ein Timeout-Stub wird als Erfolg
      gezählt, weil `item_files` nicht leer ist — die Erfolgsstatistik
      unterschätzt den Datenverlust systematisch. Lösung: `content_ok`-Flag je
      Item.
- [ ] **Doppelexporte organisationsweiter Konversationen** (Schuld 13). Zweiter
      Dedupe-Durchgang auf `(type, id)`.
- [ ] **Auth verpflichtend machen** (Schuld 2, `backend/app/config.py:29-31`).
      `basic_auth_enabled` ist nur `True`, wenn Benutzername **und** Passwort
      gesetzt sind; halbe Konfiguration führt still zu offener API. Die
      Netzexposition ist inzwischen entschärft (Loopback-Bindung), die
      Fail-open-Semantik nicht.
- [ ] **`_call_with_timeout` fährt den Executor nie herunter** (Schuld 12).
      Am 11.08.2026 am Code nachgeprüft, **unverändert zutreffend**:
      `backend/app/backup_engine.py` enthält weiterhin
      `try: return future.result(...) … else: pool.shutdown(wait=True)` — der
      `else`-Zweig ist unerreichbar, weil `return` im `try` ihn überspringt, und
      bei jeder anderen Ausnahme als `TimeoutError` erfolgt gar kein `shutdown`.
      Der Docstring beschreibt exakt die Absicht, die der Code nicht umsetzt.
- [ ] **Testsuite und CI aufbauen** (Schuld 6). Reine Funktionen zuerst, dazu ein
      End-to-End-Test gegen einen Fake-SDK-Client.
- [ ] **`abacusai<2.0` pinnen und Python-Lockfile erzeugen** (Schuld 10).
      Nachgeprüft: `backend/requirements.txt` bindet `fastapi>=0.115,<1.0`,
      `uvicorn[standard]>=0.30,<1.0`, `pydantic>=2.7,<3.0` — aber
      `abacusai>=1.4` **ohne Obergrenze**, ausgerechnet die Abhängigkeit, auf
      deren Methodensignaturen das gesamte Duck-Typing in `abacus_client.py`
      beruht.

### Später

- [ ] Retention und Verschlüsselung der Sicherungen (Schuld 3). Backups liegen
      unbefristet und unverschlüsselt unter `/data/backups`, im selben Volume wie
      die API-Schlüsseldatei.
- [ ] Strukturiertes Logging (Schuld 8). `import logging` kommt im gesamten
      Backend nicht vor; zwei `except`-Pfade verschlucken Ausnahmen vollständig.
- [ ] Reconciliation für verwaiste Teil-Backup-Verzeichnisse (Schuld 11).
- [ ] Retry mit Backoff und `Retry-After` (Schuld 7); `try_call_variants` nur bei
      echten Signaturfehlern weiteriterieren lassen — heute verstärkt es die Last
      genau dann, wenn die API um Entlastung bittet.
- [ ] Rate-Limit, Lockout und Auth-Logging (Schuld 9).
- [ ] Schemaversionierung über `PRAGMA user_version` (Schuld 14).
- [ ] Generische Fehlermeldungen mit Korrelations-ID statt roher Exception-Texte
      (Schuld 15); CSRF-Schutz bei Basic-Auth (Schuld 16); UTF-8-Kodierung vor
      `hmac.compare_digest` (Schuld 17, sonst HTTP 500 statt 401 bei Umlauten).
- [ ] `seen`-Set in `exporters.py:57-60` pfadbezogen führen (Schuld 18) — sonst
      Inhaltsverlust bei mehrfach referenzierten Objekten.
- [ ] Chat-Cache-TTL auswerten (Schuld 19); Löschweg für die Jobtabelle
      (Schuld 21); toter Code `mask_secret` (Schuld 22).
- [ ] `lifespan` statt `@app.on_event("startup")` (Schuld 20).
- [ ] **Versionierung ordnen** (Schuld 23). Nachgeprüft und zutreffend:
      `backend/app/models.py:9` `APP_VERSION = "1.0.0"` und
      `frontend/package.json:3` `"version": "1.0.0"`, während `CHANGELOG.md`
      einen gefüllten `[Unreleased]`-Block führt (Timeout-Handling,
      Retry-Button, HTML-Export-Reihenfolge, README-Nacharbeiten). `/api/health`
      meldet damit einen Funktionsstand, der nicht dem Code entspricht. Release
      schneiden, Tag setzen.
- [ ] Frontend-Build-Kette anheben (Vite 5.x, React 18.x; `dev`/`preview` binden
      auf `0.0.0.0`) — Schuld 24.
- [ ] Lizenzfrage entscheiden (Schuld 13 der Schrittliste): `LICENSE` ist MIT,
      `docs/` nimmt „proprietär" als Zielvorgabe an. Bei MIT zusätzlich eine
      `NOTICE`-Datei für Apache-2.0- und CC-BY-4.0-Anteile.

## Risiken

- **Datenverlust (hoch):** drei unabhängige Pfade, auf denen ein Backup
  unvollständig ist, ohne dass es jemand merkt (Schulden 4, 5, 13). Bei einem
  Werkzeug, dessen einziger Zweck ein vollständiges Backup ist, das
  Kernrisiko — man bemerkt es erst, wenn man das Backup braucht.
- **Datenschutz (hoch):** vollständige Chatverläufe mit PII liegen unbefristet
  und unverschlüsselt im Volume, gemeinsam mit der API-Schlüsseldatei.
- **Secrets: vorbildlich behandelt.** Zentrale Registrierung und rekursive
  Redaction in `backend/app/security.py`, `chmod 0600` auf der Schlüsseldatei,
  konstantzeitiger Vergleich. **Keine getrackte `.env`** — nur `.env.example`.
  Keine Klartext-Schlüssel in Konfigdateien gefunden.
- **Keine Tests, keine CI** — die drei Datenverlust-Befunde wären durch
  Unit-Tests aufgefallen.
- **Veraltete Abhängigkeiten:** `abacusai` ohne Obergrenze bei gleichzeitigem
  Duck-Typing; Frontend-Kette auf Vite 5 / React 18. CVE-Prüfung nicht möglich
  (kein Scanner, kein Netzwerkzugriff).
- **Eingecheckte Binärdateien:** nur `docs/preview-ui.png` (Screenshot).
  Unkritisch.
- **Kein Rate-Limit** an `/api/connect` und in der Auth-Middleware.

## Doku-Drift

**Mehrere Punkte der Doku sind überholt — der Code ist besser als seine
Befundliste.** Nachgeprüft am 11.08.2026, jeweils auch gegen `git show HEAD:…`:

- **Schuld 1 in `docs/12-offene-punkte.md` („Härtungen nicht eingecheckt —
  Security-Header, `USER app`, Loopback-Bindung, Auth-Prüfung, abgeschaltete
  `/docs` liegen nur im Arbeitsverzeichnis", Risiko **hoch**) ist erledigt.**
  In `HEAD` stehen: `Dockerfile:27` `USER app`; `compose.yaml:9`
  `- "127.0.0.1:8080:8080"`; `backend/app/main.py:59`
  `FastAPI(title=APP_NAME, docs_url=None, redoc_url=None, openapi_url=None)`;
  `main.py:108` `response.headers.setdefault("X-Content-Type-Options", "nosniff")`.
  Der Arbeitsbaum ist sauber. Damit sind zugleich die Punkte **N2**
  („`/docs`, `/redoc` und `/openapi.json` sind aktiv"), **M3** („Container läuft
  als root") und **N3** („keine Security-Header") aus `todo2026.md` erledigt,
  ohne dass die Haken gesetzt sind. Der erste Punkt der Liste „Sofort — vor
  jedem weiteren Betrieb" ist gegenstandslos.
- **Schuld 25 („`frontend/dist/` eingecheckt, obwohl in `.gitignore`") ist
  erledigt.** `git ls-files frontend/dist` liefert nichts.
- **Weiterhin zutreffend** (stichprobenartig am Code geprüft): Schuld 2
  (`config.py:29-31` Fail-open), Schuld 12 (unerreichbarer `else`-Zweig),
  Schuld 10 (`abacusai>=1.4` ohne Obergrenze), Schuld 6 (keine Tests, keine CI),
  Schuld 23 (`APP_VERSION = "1.0.0"` gegen gefüllten `[Unreleased]`-Block).
- **Nicht nachgeprüft** (hätte einen Lauf oder tiefere Codeanalyse erfordert):
  Schulden 3, 7, 8, 9, 11, 13, 14, 16, 18, 19, 21, 24.
