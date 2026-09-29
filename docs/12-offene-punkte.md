# 12 — Offene Punkte · app-abacus-chat-backup

Sammlung aller Marker aus den Dokumenten 01–11, getroffene Annahmen, technische Schulden mit Aufwand- und Risikoschätzung sowie priorisierte nächste Schritte.

[← Zurück zum Index](README.md)

## Alle `NICHT ERMITTELBAR`-Marker

| # | Marker | Dokument | Warum nicht ermittelbar | Wie zu schließen |
|---|---|---|---|---|
| 1 | Patch-Versionen und SHA-256-Digests der Basis-Images `python:3.11-slim` und `node:20-bookworm-slim`; exakte Debian-Version des Runtime-Images | [03](03-stack-und-abhaengigkeiten.md#laufzeitumgebungen), [04](04-container.md#basis-images) | Beide Tags sind beweglich; auf dem Host existiert kein gebautes Abbild, und ein Build erfordert Netzwerkzugriff | Einmalig bauen und `docker image inspect` auswerten; dauerhaft die `FROM`-Zeilen auf `@sha256:…` pinnen |
| 2 | Aufgelöste Versionen der vier Backend-Abhängigkeiten (`fastapi`, `uvicorn`, `pydantic`, `abacusai`) | [03](03-stack-und-abhaengigkeiten.md#tabelle-1a--direkte-abhängigkeiten-backend) | Es existiert **kein** Python-Lockfile und keine eingecheckte virtuelle Umgebung; `requirements.txt` enthält nur Bereiche | `pip freeze` bzw. `uv pip compile` in ein Lockfile schreiben und einchecken |
| 3 | Vollständiger transitiver Abhängigkeitsbaum des Backends inklusive Lizenzen | [03](03-stack-und-abhaengigkeiten.md#tabelle-1a--direkte-abhängigkeiten-backend) | Kein Lockfile, keine Installation vorhanden | Lockfile erzeugen; Lizenzen aus den Paketmetadaten im gebauten Image auslesen |
| 4 | Lizenz des Pakets `abacusai` | [03](03-stack-und-abhaengigkeiten.md#tabelle-1a--direkte-abhängigkeiten-backend), [11](11-sicherheit-compliance.md#lizenz-compliance-fazit) | Paket liegt lokal nicht vor, Netzwerkabfragen ausgeschlossen. **Bis zur Klärung nach Bewertungsmaßstab 🔴** | `pip show abacusai` im gebauten Image oder die `METADATA` des Wheels lesen |
| 5 | Release-Daten der Pakete zur Prüfung „letzter Release älter als 24 Monate" | [03](03-stack-und-abhaengigkeiten.md#veraltete-und-ungepflegte-pakete) | Lockfiles enthalten keine Zeitstempel; Registry-Abfragen ausgeschlossen | `npm outdated` bzw. Registry-Abfrage bei nächster Gelegenheit |
| 6 | Im Image installierte Systempakete mit Version und Lizenz | [04](04-container.md#im-image-installierte-systempakete) | Das Dockerfile installiert keine zusätzlichen Pakete; alles stammt aus dem Basis-Image und wäre nur per `dpkg -l` im laufenden Container zu ermitteln | `docker compose exec … dpkg -l` nach einem Build |
| 7 | UID und GID des Container-Benutzers `app` | [04](04-container.md#laufzeitparameter) | `adduser --system` vergibt die ID dynamisch; der Wert steht erst im gebauten Image | Feste IDs vergeben (`--uid 10001 --gid 10001`) — löst den Marker dauerhaft auf |
| 8 | Image-Gesamtgröße und Größe je Layer | [04](04-container.md#image-größe-und-layer) | Erfordert `docker history` auf einem gebauten Abbild | Nach dem nächsten Build erheben |
| 9 | Konkrete HTTP-Endpunkte, Basis-URL, Rate Limits, Kontingente und Kosten der Abacus.AI-API | [05](05-api.md#konsumierte-externe-api) | Der Code spricht ausschließlich SDK-Methoden an; die URLs stecken im Paket `abacusai`, das lokal nicht installiert ist | Nach der Installation den SDK-Quellcode auswerten oder die Anbieterdokumentation heranziehen |
| 10 | ~~Existenz und Konvention von Git-Release-Tags~~ — **geschlossen 2026-09-29:** es gibt keine Tags (`git tag -l` leer) | [09](09-build-deploy.md#versionierung-und-release-konvention) | — | Release aus `[Unreleased]` schneiden und taggen (siehe P3) |

**Dokumente ohne Marker:** 01, 02, 06, 07, 08, 09, 10 — dort ist jede Aussage aus dem Code belegt.

**Gemeinsame Wurzel:** Sieben der neun offenen Marker (1, 2, 3, 4, 6, 7, 8) verschwinden, sobald **einmal** ein Image gebaut und inspiziert wird. Der Rest hängt an fehlenden Konventionen, nicht an fehlendem Zugriff.

## Getroffene Annahmen

| # | Annahme | Grundlage | Risiko bei Irrtum |
|---|---|---|---|
| 1 | ~~Die Dokumentation beschreibt das Arbeitsverzeichnis, nicht den Commit `73f2b41`~~ — **entfallen 2026-09-29:** alle Härtungen sind committet, der Arbeitsbaum war zum QA-Audit sauber | `PROJEKTSTAND.md`, Abschnitt „Aktivität" | — |
| 2 | `python:3.11-slim` folgt dem aktuellen Debian-Stable | Übliche Bauweise der offiziellen Python-Images; im Tag nicht ausgewiesen | Gering — betrifft nur die Beschreibung, nicht das Verhalten |
| 3 | Die Lizenzen `fastapi` (MIT), `uvicorn` (BSD-3-Clause) und `pydantic` (MIT) entsprechen dem allgemein bekannten Stand | Paketwissen, ausdrücklich als **nicht verifiziert** gekennzeichnet | Gering; alle drei sind permissiv und seit Jahren stabil lizenziert |
| 4 | `ZIEL_LIZENZ` = proprietär gilt auch für dieses Projekt | Vorgabe aus `docs/_doc-spec.md` | **Hoch** — das Projekt trägt eine MIT-Lizenz und `SECURITY.md` geht von einem öffentlichen Repository aus. Möglicherweise ist die Zielvorgabe hier schlicht die falsche |
| 5 | Der Betrieb erfolgt als Einzelplatzwerkzeug hinter Loopback | `SECURITY.md:18`, Kommentar in `compose.yaml:6-8` | Bei Netzbetrieb ohne Basic-Auth ist die Anwendung vollständig offen |
| 6 | Die Angaben zum Ressourcenbedarf in [04](04-container.md#ressourcenbedarf) sind **geschätzt** | Kein laufender Container, keine `docker stats`-Messung | Als Schätzung gekennzeichnet; für Kapazitätsplanung nicht belastbar |
| 7 | ~~`frontend/dist/` bildet nicht zwingend den aktuellen Quellcode ab~~ — **entfallen:** `frontend/dist/` ist nicht mehr versioniert (`git ls-files frontend/dist` leer am 2026-09-29) | `.gitignore:4` | — |

## Technische Schulden

Stand 2026-09-29: erledigte Schulden bleiben durchgestrichen zur Nachvollziehbarkeit stehen. Aufwand: **S** (< 1 Tag) · **M** (1–3 Tage) · **L** (1–2 Wochen) · **XL** (> 2 Wochen). Risiko bezieht sich auf die Folge bei Nichtstun.

| # | Schuld | Aufwand | Risiko | Fundstelle |
|---|---|---|---|---|
| 1 | ~~Härtungen nicht eingecheckt~~ — **erledigt** (committet, Stand 2026-09-29) | S | — | `Dockerfile:27`, `compose.yaml:9-11`, `backend/app/main.py` |
| 2 | **Auth standardmäßig aus**, während alle Endpunkte inklusive Backup-Download und -Löschung dahinter liegen. **Teilweise erledigt:** halbe Konfiguration bricht den Start ab, Port nur an Loopback gebunden; ohne beide Variablen bleibt die API offen | S | mittel | `backend/app/config.py:29-31`, `backend/app/main.py:115-138` |
| 3 | **Keine Retention, keine Verschlüsselung der Sicherungen** — unbefristet wachsender Klartextbestand personenbezogener Daten im selben Volume wie der API-Schlüssel | M | **hoch** | `backend/app/config.py:59-67` |
| 4 | **Stille Truncation der Paginierung** — Teilbackup ohne Fehlermeldung; bei einem Backup-Werkzeug die gefährlichste Fehlerklasse | M | **hoch** | `backend/app/abacus_client.py:141-147` |
| 5 | ~~Timeout-Stub zählt als Erfolg~~ — **erledigt 2026-09-29** (`detail_ok`-Flag) | S | — | `backend/app/backup_engine.py:93-97,177-178` |
| 6 | **Keine Tests, keine CI** — die risikoreichsten Teile (Paginierung, Nachrichtenerkennung, Rollennormalisierung, Vollständigkeitsheuristik, Markdown-Erzeugung) sind reine Funktionen und ohne Infrastruktur testbar. Die Schulden 4, 5 und 12 wären durch Unit-Tests aufgefallen | L | **hoch** | kein Testverzeichnis, keine Workflows |
| 7 | **Kein Retry, kein Backoff, kein 429-Handling** — dafür Lastverstärkung im Fehlerfall, weil `try_call_variants` bei **jedem** Fehler die nächste Variante probiert | M | mittel | `backend/app/abacus_client.py:100-110` |
| 8 | **Kein strukturiertes Logging**, dazu zwei stumm verschluckte Ausnahmen. **Teilweise:** ein `logging`-Logger protokolliert den Auth-Status, es fehlt aber eine Logging-Konfiguration (INFO geht unter uvicorn verloren) | M | mittel | `backend/app/main.py:223-224,372-373` |
| 9 | **Kein Rate-Limit, kein Lockout, kein Auth-Logging** | M | mittel | `backend/app/main.py:87-100` |
| 10 | **Kein Python-Lockfile** — Builds sind nicht reproduzierbar; `abacusai` ohne Obergrenze bei gleichzeitigem Duck-Typing | S | mittel | `backend/requirements.txt:1-4` |
| 11 | **Verwaiste Teil-Backups** — Verzeichnisse ohne Datenbankeintrag sind unsichtbar, nicht löschbar und enthalten personenbezogene Daten | M | mittel | `backend/app/backup_engine.py:63-76` |
| 12 | ~~Executor wird auf dem Erfolgspfad nie heruntergefahren~~ — **erledigt 2026-09-29** (`finally: pool.shutdown(wait=False, cancel_futures=True)`) | S | — | `backend/app/backup_engine.py:14-28` |
| 13 | **Doppelte Exporte organisationsweiter Konversationen** — `include_org_level_conversations` liefert dieselbe Konversation je Deployment, der Dedupe-Schlüssel unterscheidet sie | S | mittel | `backend/app/abacus_client.py:436,292-296` |
| 14 | **Keine Schemaversionierung** — `CREATE TABLE IF NOT EXISTS` ohne Migrationspfad | S | mittel | `backend/app/database.py:17-58` |
| 15 | **Rohe Exception-Texte an den Client** | S | mittel | `backend/app/security.py:97-98` |
| 16 | **Kein CSRF-Schutz** bei Basic-Auth; `POST /api/jobs/{id}/cancel` ist per fremdem Formular auslösbar | S | niedrig | `backend/app/main.py:299-304` |
| 17 | ~~Nicht-ASCII-Zugangsdaten erzeugen HTTP 500~~ — **erledigt 2026-09-29** (Bytevergleich) | S | — | `backend/app/security.py:111-114` |
| 18 | ~~Datenverlust bei mehrfach referenzierten Objekten~~ — **erledigt 2026-09-29** (`seen` pfadbezogen) | S | — | `backend/app/exporters.py:57-66` |
| 19 | **Chat-Cache ohne TTL** — `refreshed_at` wird geschrieben, aber nie ausgewertet | S | niedrig | `backend/app/database.py:229-248` |
| 20 | **Deprecated Startup-Hook** `@app.on_event("startup")` statt `lifespan`; dazu eine neue SQLite-Verbindung je `update_job` | S | niedrig | `backend/app/main.py:135`, `backend/app/database.py:99-113` |
| 21 | **Jobtabelle ohne Löschweg** — wächst unbegrenzt, kein `DELETE FROM jobs` im Code | S | niedrig | `backend/app/database.py` |
| 22 | **Toter Code** `mask_secret` im Sicherheitsmodul | S | niedrig | `backend/app/security.py:61-66` |
| 23 | **Version im Code fest auf `1.0.0`**, während `CHANGELOG.md` bereits sechs `[Unreleased]`-Einträge führt; Frontend-Version manuell zu synchronisieren | S | niedrig | `backend/app/models.py:9`, `frontend/package.json:3` |
| 24 | **Frontend-Build-Kette auf Vite 5.x und React 18.x**; `dev` und `preview` binden auf `0.0.0.0` | M | niedrig | `frontend/package.json:7-9,13-24` |
| 25 | ~~`frontend/dist/` eingecheckt~~ — **erledigt** (nicht mehr versioniert, Stand 2026-09-29) | S | — | `.gitignore:4` |

## Empfohlene nächste Schritte

Priorisierung deckungsgleich mit „Offene Probleme nach Priorität" in `PROJEKTSTAND.md` (QA-Audit 2026-09-29).

### P1

1. **Stille Truncation bei Bare-List-Paginierung** (Schuld 4, M) — `backend/app/abacus_client.py:141-146`: liefert eine SDK-Methode eine nackte Liste ohne `page_token`/`has_more`, endet die Schleife nach der ersten Seite, ältere Chats fehlen unbemerkt. Explizites `limit`, bei `len(page) == limit` weiterblättern, im Manifest vermerken.

### P2

2. **Kein Retry/Backoff/`Retry-After`/429-Handling** (Schuld 7, M); `try_call_variants` iteriert auch bei Last-Fehlern weiter und verstärkt die Last.
3. **Doppelexport organisationsweiter Konversationen** (Schuld 13, S) — Dedupe-Schlüssel enthält `deployment_id` (`backend/app/abacus_client.py:292-294`).
4. **Backups unverschlüsselt und ohne Retention** unter `/data/backups`, im selben Volume wie die API-Schlüsseldatei (Schuld 3, M).
5. **`abacusai>=1.4` ohne Obergrenze** trotz Duck-Typing auf Methodensignaturen; kein Python-Lockfile (Schuld 10, S) — schließt zugleich die Marker 2, 3 und 4.
6. **Keine Tests, keine CI** (Schuld 6, L) — die reinen Funktionen (Paginierung, `_best_message_list`, `_normalize_role`, Markdown-Erzeugung, `safe_filename`) sind ohne Infrastruktur testbar; dazu E2E gegen einen Fake-SDK-Client.

### P3

7. **Logging nur teilweise** (Schuld 8): Logger vorhanden, aber keine Logging-Konfiguration; zwei `except`-Pfade verschlucken Ausnahmen.
8. **Vite 5.4.21**, `dev`/`preview` mit `--host 0.0.0.0` (Schuld 24).
9. **`@app.on_event("startup")`** (`backend/app/main.py:135`) statt `lifespan` (Schuld 20); keine Schemaversionierung per `PRAGMA user_version` (Schuld 14).
10. **Rate-Limit/Lockout/Auth-Logging** an `/api/connect` und Auth-Middleware (Schuld 9); CSRF-Schutz bei Basic-Auth (Schuld 16); generische Fehlermeldungen mit Korrelations-ID (Schuld 15).
11. **Reconciliation verwaister Teil-Backups** (Schuld 11); Chat-Cache-TTL (Schuld 19); Löschweg für die Jobtabelle (Schuld 21); toter Code `mask_secret` (Schuld 22).
12. **Versionierung ordnen** (Schuld 23): Release aus `[Unreleased]` schneiden, `APP_VERSION` anheben, Tag setzen.
13. **Lizenzfrage entscheiden:** `LICENSE` ist MIT, `docs/` nimmt „proprietär" an; bei MIT eine `NOTICE` für Apache-2.0-/CC-BY-4.0-Anteile.

Ergänzend ohne Priorität im Audit: **einmal bauen und inspizieren** (S) — schließt sieben der neun offenen Marker (Digests, Systempakete, UID/GID, Layer-Größen, Backend-Versionen und -Lizenzen).

## Marker in diesem Dokument

Dieses Dokument sammelt die Marker der Dokumente 01–11; eigene Marker enthält es nicht.
