# 09 — Build und Deployment · app-abacus-chat-backup

Lokales Setup als kopierbare Befehlsfolge, Buildprozess, Artefakte, CI/CD-Stand, Deployment und Rollback.

[← Zurück zum Index](README.md)

## Lokales Setup — Weg 1: Docker Compose (empfohlen)

```bash
# 1. Repository klonen und in das Projekt wechseln
git clone <REPO_URL> && cd app-abacus-chat-backup

# 2. Konfiguration vorbereiten (KEINE echten Werte einchecken)
cp .env.example .env
#    Mindestens setzen, sobald der Dienst ueber Loopback hinaus erreichbar sein soll:
#    APP_BASIC_AUTH_USER und APP_BASIC_AUTH_PASSWORD -- beide oder keine.
#    ABACUS_API_KEY kann leer bleiben; der Schluessel laesst sich auch in der UI eingeben.

# 3. Compose-Datei pruefen (offline, kein Build)
docker compose -f compose.yaml config -q

# 4. Bauen und starten (benoetigt Netzwerk fuer npm ci und pip install)
docker compose up -d --build

# 5. Bereitschaft pruefen
docker compose ps                       # STATUS soll "healthy" zeigen
curl -fsS http://127.0.0.1:8080/api/health

# 6. Oberflaeche oeffnen
#    http://127.0.0.1:8080
```

**Verifikationsstand der einzelnen Schritte:**

| Schritt | Ausgeführt? | Ergebnis |
|---|---|---|
| 3 — `docker compose config -q` | **ja**, am 2026-07-30 | fehlerfrei; die Compose-Datei ist gültig |
| 4 — `docker compose up -d --build` | **nein** | Der Build ruft `npm ci` (`Dockerfile:5`) und `pip install` (`Dockerfile:17`) auf. Netzwerkzugriff zum Auflösen von Abhängigkeiten ist für diese Dokumentation ausgeschlossen |
| 5/6 | **nein** | setzen Schritt 4 voraus |
| Syntaxprüfung des Backends | **ja**, am 2026-07-30 | Alle zwölf Dateien unter `backend/app/` sind syntaktisch gültiges Python (AST-Parse ohne Fehler) |

## Lokales Setup — Weg 2: ohne Docker

Diese Variante braucht **zwei** Prozesse. Sie weicht in einem Punkt von `README.md:48-66` ab: Der Vite-Proxy zeigt fest auf Port **8080** (`frontend/vite.config.ts:9`), das Backend muss also auf 8080 laufen — mit `uvicorn app.main:app --reload` allein startet es auf 8000.

```bash
# Terminal 1 -- Backend
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt      # benoetigt Netzwerk
export APP_DATA_DIR="$PWD/../.localdata"   # sonst schreibt die App nach /data bzw. C:\data
uvicorn app.main:app --reload --port 8080

# Terminal 2 -- Frontend (Dev-Server mit /api-Proxy auf 127.0.0.1:8080)
cd frontend
npm ci                               # benoetigt Netzwerk; nutzt package-lock.json
npm run dev
#    Oberflaeche: http://localhost:5173
```

Wer die Oberfläche **aus dem Backend heraus** ausliefern will statt über den Dev-Server, baut das Bundle und zeigt `APP_STATIC_DIR` darauf:

```bash
cd frontend && npm run build          # erzeugt frontend/dist
export APP_STATIC_DIR="$PWD/dist"     # Backend liefert dann /assets und den SPA-Fallback
```

Belege: `frontend/package.json:7-9`, `backend/app/config.py:59,68`, `backend/app/main.py:431-448`.

## Buildprozess und Artefakte

| Artefakt | Erzeugt durch | Inhalt | Beleg |
|---|---|---|---|
| `frontend/dist/` | `npm run build` = `tsc -b && vite build` | `index.html` plus `assets/index-*.js` und `assets/index-*.css` mit Content-Hash im Namen. Der eingecheckte Vergleichsstand misst 199 624 Byte JS und 17 204 Byte CSS | `frontend/package.json:8`, `frontend/dist/` |
| Container-Image | `docker compose build` bzw. `docker build .` | Zwei Stages: Node-Build, dann Python-Runtime mit kopiertem Bundle | `Dockerfile:1-35` |
| Backup-ZIPs | Zur Laufzeit je Sicherung | Nutzdaten, kein Build-Artefakt | `backend/app/exporters.py:720-728` |

**Der Typecheck ist Teil des Builds.** `tsc -b` läuft mit `strict: true` vor `vite build`; ein Typfehler bricht den Image-Build ab (`frontend/tsconfig.json:10`, `frontend/package.json:8`).

**`frontend/dist/` ist eingecheckt, wird aber nicht ausgeliefert.** Die `.dockerignore` schließt das Verzeichnis aus (`.dockerignore:6`), damit im Image garantiert der frisch gebaute Stand landet. Zugleich steht `dist/` in der `.gitignore` (`.gitignore:4`) — das Verzeichnis ist also von einer früheren Ergänzung erhalten geblieben. Praktische Folge: Der eingecheckte Stand vom 2026-05-16 kann vom Quellcode abweichen und sollte nicht als Referenz für das Verhalten der Oberfläche dienen.

## CI/CD

**Nicht vorhanden.** Es existiert weder `.github/workflows/` noch `.gitea/workflows/` noch `azure-pipelines.yml`, `Jenkinsfile`, `.gitlab-ci.yml` oder ein Pre-Commit-Hook. Es gibt entsprechend:

- keinen automatischen Build,
- keinen automatischen Test (es gibt auch keine Tests),
- keinen Image-Push in eine Registry,
- keine benötigten CI-Secrets.

**Konsequenz:** Jeder Build entsteht lokal auf dem Rechner des Betreibers; es gibt keinen nachvollziehbaren, zentral erzeugten Artefaktstand. **Handlungsoption:** Ein minimaler Workflow mit `docker build` und — sobald Tests existieren — `pytest` würde bereits die drei im projekteigenen Review genannten Fehlerklassen abfangen (`todo2026.md`, Abschnitt „Niedrig", Eintrag „Keine Tests, keine CI").

## Zielumgebungen und Deployment-Verfahren

| Aspekt | Stand |
|---|---|
| Zielumgebung | **Eine:** der Rechner des Betreibers, per Docker Compose. `SECURITY.md:18` bezeichnet die Anwendung ausdrücklich als lokal zu betreibendes Werkzeug |
| Image-Herkunft | `build: .` — lokal gebaut, **kein** Tag aus einer Registry (`compose.yaml:3`) |
| Orchestrierung | Docker Compose, ein Dienst. Kein Kubernetes-Manifest, kein Helm-Chart |
| Infrastructure as Code | **Keines.** Kein Terraform, kein Ansible, kein Pulumi im Projekt |
| Netzexposition | Portmapping `127.0.0.1:8080:8080` — Loopback des Hosts (`compose.yaml:9`) |
| Reverse-Proxy | Nicht Teil des Projekts; im Compose-Kommentar als Alternative zur Basic-Auth genannt (`compose.yaml:6-8`) |
| Neustartverhalten | **Keine `restart`-Policy.** Nach einem Host-Neustart läuft der Container nicht von selbst wieder an |
| Registry-Integration | keine |

### Deployment-Ablauf für eine neue Version

```bash
git pull
docker compose up -d --build          # baut neu und ersetzt den Container
docker compose ps                     # auf "healthy" warten
docker compose logs -f --tail 50      # Startmeldungen pruefen, insbesondere den Auth-Status
```

Das Volume `abacus_backup_data` bleibt dabei erhalten — Sicherungen, Datenbank, API-Key-Datei und Scope-Datei überleben das Deployment (`compose.yaml:22-23,44-45`).

**Vor jedem Deployment prüfen:** Ist `APP_BASIC_AUTH_USER` gesetzt, muss auch `APP_BASIC_AUTH_PASSWORD` gesetzt sein — sonst startet der Container gar nicht, sondern beendet sich mit `RuntimeError` (`backend/app/main.py:115-125`). Das ist beabsichtigtes Fail-fast, überrascht aber, wenn man es nicht kennt.

## Rollback

Es gibt keinen automatisierten Rückweg. Belegbare Vorgehensweise:

```bash
# 1. Auf den letzten funktionierenden Stand zurueck
git log --oneline -10
git checkout <commit-hash>

# 2. Neu bauen und ersetzen
docker compose up -d --build

# 3. Pruefen
curl -fsS http://127.0.0.1:8080/api/health
```

| Rollback-Aspekt | Bewertung |
|---|---|
| Anwendungscode | **unkritisch** — der Container ist zustandslos; alles Persistente liegt im Volume |
| Datenbankschema | **unkritisch in der Praxis.** Es gibt keine Migrationen, also auch keine Rückmigration. Ein älterer Code kann allerdings mit einer neueren Datenbank in Konflikt geraten, wenn zwischenzeitlich Spalten hinzugekommen wären (`backend/app/database.py:17-58`) |
| Sicherungen | **unberührt** — reine Dateien im Volume, unabhängig von der Codeversion lesbar |
| Notfallweg ohne Anwendung | Volume-Inhalt direkt kopieren, siehe [10-betrieb.md](10-betrieb.md#backup-und-restore) |
| Image-Rollback über Tag | **nicht möglich** — es gibt kein Registry-Image und keine versionierten Tags |

## Versionierung und Release-Konvention

| Element | Stand | Beleg |
|---|---|---|
| Anwendungsversion | `APP_VERSION = "1.0.0"`, **fest im Quellcode**. Erscheint in `GET /api/health`, im Backup-Manifest und auf der Backup-Übersichtsseite | `backend/app/models.py:9`, `backend/app/main.py:177`, `backend/app/backup_engine.py:200` |
| Frontend-Version | `1.0.0` in `frontend/package.json:3` — **manuell** mit der Backend-Version synchron zu halten; es gibt keinen Mechanismus dafür | `frontend/package.json:3` |
| Changelog | `CHANGELOG.md` im Keep-a-Changelog-Format mit `[Unreleased]`-Abschnitt und `[1.0.0] — 2026-05-08` | `CHANGELOG.md:1-40` |
| SemVer | Als Konvention erkennbar (`SECURITY.md:5` verspricht Fixes für „die aktuelle Minor-Version der 1.x-Linie"), aber nirgends automatisiert | `SECURITY.md:5` |
| Git-Tags | ⚠️ siehe Marker |
| Release-Artefakt | Keines. Es gibt keinen Release-Prozess, der ein Image oder Archiv erzeugt | — |

Der `[Unreleased]`-Abschnitt des Changelogs enthält bereits sechs Einträge (Timeout-Behandlung, Retry-Schaltfläche, Export-Reihenfolge, Dokumentation) — die Version im Code steht dennoch unverändert auf `1.0.0`. Wer aus `/api/health` auf den Funktionsstand schließt, liegt daneben.

> ⚠️ NICHT ERMITTELBAR — Quelle fehlt: Ob und welche Git-Tags für Releases vergeben wurden. Der Arbeitsstand dieser Dokumentation wertet nur den Dateibestand und die Commit-Historie des Arbeitsverzeichnisses aus; eine Tag-Konvention ist in keiner Datei des Repositories beschrieben.

## Stand des Arbeitsverzeichnisses

Diese Dokumentation beschreibt das **Arbeitsverzeichnis**, nicht den letzten Commit. Zum Zeitpunkt der Erstellung (2026-07-30) sind folgende Dateien geändert und **nicht committet**:

| Datei | Änderung |
|---|---|
| `Dockerfile` | `adduser --system --group app`, `chown -R app:app`, `USER app` ergänzt |
| `compose.yaml` | Portmapping auf `127.0.0.1:8080:8080` geändert, `security_opt: no-new-privileges:true` ergänzt |
| `backend/app/main.py` | Security-Header-Middleware, `_check_auth_config()`, `docs_url=None/redoc_url=None/openapi_url=None`, Logger |
| `.env.example` | Warnhinweis zur Basic-Auth; zusätzlich der beim Erstellen dieser Dokumentation ergänzte Abschnitt mit den fünf fehlenden Variablen |
| `todo2026.md` | Review-Stand aktualisiert |
| `MONETARISIERUNGSBEWERTUNG.md` | neu, nicht getrackt |

**Konsequenz:** Wer den Commit `73f2b41` deployt, bekommt einen **root-Container ohne Security-Header, mit offener API-Dokumentation und LAN-weitem Portmapping**. Der erste Schritt vor jedem weiteren Vorhaben sollte das Einchecken dieser Änderungen sein.

## Marker in diesem Dokument

- ⚠️ NICHT ERMITTELBAR — Existenz und Konvention von Git-Release-Tags
