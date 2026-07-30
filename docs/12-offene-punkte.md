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
| 10 | Existenz und Konvention von Git-Release-Tags | [09](09-build-deploy.md#versionierung-und-release-konvention) | In keiner Datei des Repositories beschrieben; die Dokumentation wertet nur Dateibestand und Arbeitsverzeichnis aus | `git tag -l` prüfen und die Konvention in `CHANGELOG.md` oder `RELEASE_README.md` festhalten |

**Dokumente ohne Marker:** 01, 02, 06, 07, 08, 10 — dort ist jede Aussage aus dem Code belegt.

**Gemeinsame Wurzel:** Sieben der zehn Marker (1, 2, 3, 4, 6, 7, 8) verschwinden, sobald **einmal** ein Image gebaut und inspiziert wird. Der Rest hängt an fehlenden Konventionen, nicht an fehlendem Zugriff.

## Getroffene Annahmen

| # | Annahme | Grundlage | Risiko bei Irrtum |
|---|---|---|---|
| 1 | Die Dokumentation beschreibt das **Arbeitsverzeichnis**, nicht den Commit `73f2b41` | `git status` zeigt fünf geänderte und eine ungetrackte Datei; die Änderungen enthalten sämtliche Härtungen | Wer nach dem Git-Stand deployt, bekommt eine deutlich unsicherere Anwendung als hier beschrieben — deshalb steht der Hinweis in [04](04-container.md), [09](09-build-deploy.md) und [11](11-sicherheit-compliance.md) |
| 2 | `python:3.11-slim` folgt dem aktuellen Debian-Stable | Übliche Bauweise der offiziellen Python-Images; im Tag nicht ausgewiesen | Gering — betrifft nur die Beschreibung, nicht das Verhalten |
| 3 | Die Lizenzen `fastapi` (MIT), `uvicorn` (BSD-3-Clause) und `pydantic` (MIT) entsprechen dem allgemein bekannten Stand | Paketwissen, ausdrücklich als **nicht verifiziert** gekennzeichnet | Gering; alle drei sind permissiv und seit Jahren stabil lizenziert |
| 4 | `ZIEL_LIZENZ` = proprietär gilt auch für dieses Projekt | Vorgabe aus `docs/_doc-spec.md` | **Hoch** — das Projekt trägt eine MIT-Lizenz und `SECURITY.md` geht von einem öffentlichen Repository aus. Möglicherweise ist die Zielvorgabe hier schlicht die falsche |
| 5 | Der Betrieb erfolgt als Einzelplatzwerkzeug hinter Loopback | `SECURITY.md:18`, Kommentar in `compose.yaml:6-8` | Bei Netzbetrieb ohne Basic-Auth ist die Anwendung vollständig offen |
| 6 | Die Angaben zum Ressourcenbedarf in [04](04-container.md#ressourcenbedarf) sind **geschätzt** | Kein laufender Container, keine `docker stats`-Messung | Als Schätzung gekennzeichnet; für Kapazitätsplanung nicht belastbar |
| 7 | `frontend/dist/` bildet nicht zwingend den aktuellen Quellcode ab | Verzeichnis vom 2026-05-16, steht in `.gitignore` und in `.dockerignore` | Wer den eingecheckten Build als Referenz nimmt, beschreibt möglicherweise einen veralteten Stand der Oberfläche |

## Technische Schulden

Aufwand: **S** (< 1 Tag) · **M** (1–3 Tage) · **L** (1–2 Wochen) · **XL** (> 2 Wochen). Risiko bezieht sich auf die Folge bei Nichtstun.

| # | Schuld | Aufwand | Risiko | Fundstelle |
|---|---|---|---|---|
| 1 | **Härtungen nicht eingecheckt** — Security-Header, `USER app`, Loopback-Bindung, Auth-Prüfung, abgeschaltete `/docs` liegen nur im Arbeitsverzeichnis | S | **hoch** | `git status` |
| 2 | **Auth standardmäßig aus**, während alle Endpunkte inklusive Backup-Download und -Löschung dahinter liegen | S | **hoch** | `backend/app/config.py:29-31` |
| 3 | **Keine Retention, keine Verschlüsselung der Sicherungen** — unbefristet wachsender Klartextbestand personenbezogener Daten im selben Volume wie der API-Schlüssel | M | **hoch** | `backend/app/config.py:59-67` |
| 4 | **Stille Truncation der Paginierung** — Teilbackup ohne Fehlermeldung; bei einem Backup-Werkzeug die gefährlichste Fehlerklasse | M | **hoch** | `backend/app/abacus_client.py:141-147` |
| 5 | **Timeout-Stub zählt als Erfolg** — die Erfolgsstatistik unterschätzt den Datenverlust systematisch | S | **hoch** | `backend/app/backup_engine.py:174-175` |
| 6 | **Keine Tests, keine CI** — die risikoreichsten Teile (Paginierung, Nachrichtenerkennung, Rollennormalisierung, Vollständigkeitsheuristik, Markdown-Erzeugung) sind reine Funktionen und ohne Infrastruktur testbar. Die Schulden 4, 5 und 12 wären durch Unit-Tests aufgefallen | L | **hoch** | kein Testverzeichnis, keine Workflows |
| 7 | **Kein Retry, kein Backoff, kein 429-Handling** — dafür Lastverstärkung im Fehlerfall, weil `try_call_variants` bei **jedem** Fehler die nächste Variante probiert | M | mittel | `backend/app/abacus_client.py:100-110` |
| 8 | **Kein strukturiertes Logging**, dazu zwei stumm verschluckte Ausnahmen — im Betrieb gibt es serverseitig keine Spur | M | mittel | `backend/app/main.py:223-224,372-373` |
| 9 | **Kein Rate-Limit, kein Lockout, kein Auth-Logging** | M | mittel | `backend/app/main.py:87-100` |
| 10 | **Kein Python-Lockfile** — Builds sind nicht reproduzierbar; `abacusai` ohne Obergrenze bei gleichzeitigem Duck-Typing | S | mittel | `backend/requirements.txt:1-4` |
| 11 | **Verwaiste Teil-Backups** — Verzeichnisse ohne Datenbankeintrag sind unsichtbar, nicht löschbar und enthalten personenbezogene Daten | M | mittel | `backend/app/backup_engine.py:63-76` |
| 12 | **Executor wird auf dem Erfolgspfad nie heruntergefahren** — der `else`-Zweig ist unerreichbar, weil `return` im `try`-Block ihn überspringt | S | mittel | `backend/app/backup_engine.py:14-29` |
| 13 | **Doppelte Exporte organisationsweiter Konversationen** — `include_org_level_conversations` liefert dieselbe Konversation je Deployment, der Dedupe-Schlüssel unterscheidet sie | S | mittel | `backend/app/abacus_client.py:436,292-296` |
| 14 | **Keine Schemaversionierung** — `CREATE TABLE IF NOT EXISTS` ohne Migrationspfad | S | mittel | `backend/app/database.py:17-58` |
| 15 | **Rohe Exception-Texte an den Client** | S | mittel | `backend/app/security.py:97-98` |
| 16 | **Kein CSRF-Schutz** bei Basic-Auth; `POST /api/jobs/{id}/cancel` ist per fremdem Formular auslösbar | S | niedrig | `backend/app/main.py:299-304` |
| 17 | **Nicht-ASCII-Zugangsdaten erzeugen HTTP 500** statt 401 | S | niedrig | `backend/app/security.py:101-111` |
| 18 | **Datenverlust bei mehrfach referenzierten Objekten** im Export (`seen`-Set wird nicht pfadbezogen geführt) | S | niedrig | `backend/app/exporters.py:57-60` |
| 19 | **Chat-Cache ohne TTL** — `refreshed_at` wird geschrieben, aber nie ausgewertet | S | niedrig | `backend/app/database.py:229-248` |
| 20 | **Deprecated Startup-Hook** `@app.on_event("startup")` statt `lifespan`; dazu eine neue SQLite-Verbindung je `update_job` | S | niedrig | `backend/app/main.py:135`, `backend/app/database.py:99-113` |
| 21 | **Jobtabelle ohne Löschweg** — wächst unbegrenzt, kein `DELETE FROM jobs` im Code | S | niedrig | `backend/app/database.py` |
| 22 | **Toter Code** `mask_secret` im Sicherheitsmodul | S | niedrig | `backend/app/security.py:61-66` |
| 23 | **Version im Code fest auf `1.0.0`**, während `CHANGELOG.md` bereits sechs `[Unreleased]`-Einträge führt; Frontend-Version manuell zu synchronisieren | S | niedrig | `backend/app/models.py:9`, `frontend/package.json:3` |
| 24 | **Frontend-Build-Kette auf Vite 5.x und React 18.x**; `dev` und `preview` binden auf `0.0.0.0` | M | niedrig | `frontend/package.json:7-9,13-24` |
| 25 | **`frontend/dist/` eingecheckt**, obwohl in `.gitignore` und `.dockerignore` — irreführender Doppelstand | S | niedrig | `frontend/dist/`, `.gitignore:4` |

## Empfohlene nächste Schritte

### Sofort — vor jedem weiteren Betrieb

1. **Härtungen committen** (Schuld 1, S). Solange die Änderungen nur im Arbeitsverzeichnis liegen, ist jeder Deploy aus Git ein root-Container mit offener `/docs`, ohne Security-Header und mit LAN-weitem Portmapping. Ein einziger Commit schließt das.
2. **Auth verpflichtend machen** (Schuld 2, S). Fehlt die Konfiguration vollständig, sollte die Anwendung abbrechen — genau wie bei halber Konfiguration. Der aktuelle Zustand „startet offen und schreibt eine Warnzeile" ist die richtige Zwischenlösung, aber kein Endzustand, wenn hinter der Schranke vollständige Chatverläufe liegen.

### Kurzfristig — die drei Stellen, an denen ein Backup lautlos unvollständig ist

3. **Paginierung reparieren** (Schuld 4, M). Explizites `limit` mitgeben und bei `len(page) == limit` offsetbasiert weiterblättern; im Manifest vermerken, wenn eine Liste exakt an der Seitengrenze endete.
4. **Fehlerzählung korrigieren** (Schuld 5, S). Ein `content_ok`-Flag je Item; ein Item ist fehlgeschlagen, sobald der Detailabruf scheiterte — unabhängig davon, ob eine Stub-Datei entstand.
5. **Doppelexporte entschärfen** (Schuld 13, S). Zweiter Dedupe-Durchgang auf `(type, id)` für organisationsweit markierte Einträge.

Diese drei Punkte betreffen die Kernzusage des Werkzeugs. Ein Backup, das leise unvollständig ist, ist schlimmer als eines, das sichtbar scheitert.

### Mittelfristig — Datenschutz und Betrieb

6. **Retention und Volume-Schutz** (Schuld 3, M). Konfigurierbares Höchstalter oder Höchstzahl mit Aufräumen beim Start; Verschlüsselungsempfehlung in `SECURITY.md`; optional passwortgeschützte ZIPs. Solange das fehlt, wächst ein unverschlüsselter Klartextbestand personenbezogener Daten unbegrenzt — im selben Volume wie der API-Schlüssel.
7. **Logging einführen** (Schuld 8, M). Ohne Betriebsprotokoll ist jede Störungsanalyse Raten; die beiden stummen `except`-Pfade sind der schnellste Anfang.
8. **Reconciliation für verwaiste Verzeichnisse** (Schuld 11, M). Löst zugleich das Problem „Datenbank verloren, Dateien vorhanden" aus [10-betrieb.md](10-betrieb.md#datenbank-verloren-dateien-vorhanden).
9. **Retry mit Backoff und `Retry-After`** (Schuld 7, M), und `try_call_variants` nur noch bei echten Signaturfehlern weiteriterieren lassen.
10. **Python-Lockfile erzeugen und `abacusai<2.0` pinnen** (Schuld 10, S). Schließt zugleich die Marker 2, 3 und 4.

### Danach — Fundament

11. **Testsuite und CI** (Schuld 6, L). Reine Funktionen zuerst: Paginierung, `_best_message_list`, `_normalize_role`, `_history_complete_by_total_events`, Markdown- und Tabellenerzeugung, `safe_filename`. Dazu ein End-to-End-Test gegen einen Fake-SDK-Client und ein Workflow mit `pytest` und `docker build`.
12. **Einmal bauen und inspizieren** (S). Schließt sieben der zehn Marker auf einen Schlag: Digests, Systempakete, UID/GID, Layer-Größen, Backend-Versionen und -Lizenzen.
13. **Lizenzfrage entscheiden** (S). MIT beibehalten und die Zielvorgabe korrigieren, oder proprietär werden und `LICENSE` ersetzen. Bei MIT zusätzlich eine `NOTICE`-Datei für Apache-2.0 und CC-BY-4.0 anlegen.
14. **Versionierung ordnen** (Schuld 23, S). `APP_VERSION` beim Release erhöhen, `CHANGELOG.md` schließen, Git-Tag setzen — dann ist `/api/health` wieder eine belastbare Auskunft über den Funktionsstand.

## Marker in diesem Dokument

Dieses Dokument sammelt die Marker der Dokumente 01–11; eigene Marker enthält es nicht.
