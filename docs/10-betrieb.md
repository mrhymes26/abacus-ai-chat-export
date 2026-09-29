# 10 — Betrieb · app-abacus-chat-backup

Logging, Health, Sicherung und Wiederherstellung der Anwendungsdaten, Störungsbilder, Wartung und Skalierungsgrenzen.

[← Zurück zum Index](README.md)

## Logging

| Aspekt | Stand | Beleg |
|---|---|---|
| Framework | Python-`logging` mit `logging.getLogger("app")` — **ohne jede Konfiguration**. Es wird kein Handler, kein Level und kein Formatter gesetzt, also greift die Standardkonfiguration von Uvicorn | `backend/app/main.py:55` |
| Format | Klartext im Uvicorn-Standardformat; **kein** JSON, keine Korrelations-ID, kein strukturiertes Feld | keine Formatter-Konfiguration im Repository |
| Ziel | stdout/stderr des Containers, abrufbar über `docker compose logs` | `PYTHONUNBUFFERED=1` in `Dockerfile:12` sorgt für sofortige Ausgabe |
| Was tatsächlich geloggt wird | **Genau zwei Zeilen, beide beim Start:** `INFO` „Basic auth ACTIVE (public paths: /api/health)." oder `WARNING` „Basic auth DISABLED - the API is open, including chat backup downloads. …" | `backend/app/main.py:126-132` |
| Zugriffslog | Das Standard-Zugriffslog von Uvicorn (Methode, Pfad, Status) | Uvicorn-Default, nicht abgeschaltet |
| Was **nicht** geloggt wird | Jobstart und Jobende, Item-Fehler, SDK-Fehler, Verbindungsversuche, Löschvorgänge, fehlgeschlagene Anmeldungen | keine `logger`-Aufrufe außerhalb von `main.py:127,129` |
| Still verschluckte Ausnahmen | Zwei Stellen: die Scope-Discovery in `GET /api/status` (`except Exception: pass`) und der stille Verbindungsversuch (`except Exception: return`) | `backend/app/main.py:223-224`, `backend/app/main.py:372-373` |
| PII im Log | **Keine bewusste Ausgabe.** Chatinhalte, Titel und IDs erscheinen nicht im Serverlog — schlicht deshalb, weil überhaupt nichts geloggt wird. Das Zugriffslog enthält allerdings Pfade wie `/api/backups/<backup_id>/download` und `/api/jobs/<uuid>` | Uvicorn-Zugriffslog |
| Secret im Log | Ausgeschlossen: Der API-Schlüssel taucht in keinem Logaufruf auf, und alle an den Client gehenden Fehlertexte laufen durch `safe_error` | `backend/app/security.py:97-98` |

**Praktische Konsequenz:** Die einzige belastbare Fehlerquelle im Betrieb ist die `errors.log` **innerhalb** einer Sicherung bzw. das Feld `errors` der Job-API. Serverseitig gibt es keine Spur. Wenn ein Backup dauerhaft leer bleibt, sieht der Betreiber im Log nichts.

## Health und Metriken

| Endpunkt / Signal | Inhalt | Beleg |
|---|---|---|
| `GET /api/health` | `status` (`ok`/`degraded`/`down`), `version`, `uptime_s`, `checks[]` mit Name, Status und Latenz der SQLite-Prüfung, optional `commit`. HTTP 503 bei `down`, Header `Cache-Control: no-store` | `backend/app/main.py:168-187` |
| Datenbankprüfung | `SELECT 1`, ausgelagert in einen Thread und mit 2 Sekunden Timeout abgesichert — der Endpunkt kann also nicht hängen | `backend/app/main.py:153-165`, `backend/app/database.py:65-68` |
| Container-Healthcheck | Python-Einzeiler alle 30 s, Timeout 3 s, 3 Versuche, 20 s Karenz | `Dockerfile:32-33`, `compose.yaml:24-29` |
| HomeLAB_UX-Anbindung | Label `homelab.health: /api/health` — das Dashboard fragt denselben Endpunkt ab | `compose.yaml:38` |
| Prometheus / OpenTelemetry | **Nicht vorhanden.** Kein `/metrics`, kein Exporter, kein Tracing | keine entsprechende Abhängigkeit in `backend/requirements.txt` |
| Anwendungsmetriken | Nur indirekt über die API: `GET /api/jobs/{id}` liefert `total`, `done`, `failed`, `percent`; `GET /api/backups` liefert `size_bytes` je Sicherung | `backend/app/database.py:125-144,163-182` |

## Backup und Restore

Zu unterscheiden sind zwei Ebenen: die **Nutzdaten**, die dieses Werkzeug erzeugt, und die **Betriebsdaten** des Werkzeugs selbst.

### Was gesichert werden muss

| Objekt | Ort | Kritikalität |
|---|---|---|
| Alle Sicherungen | `/data/backups/` im Volume `abacus_backup_data` | **hoch** — der eigentliche Wert; nicht rekonstruierbar, wenn die Quelle bei Abacus.AI gelöscht wurde |
| SQLite-Datenbank | `/data/app.db` | **niedrig** — reine Metadaten; verlorene Einträge bedeuten nur eine leere Backup-Liste in der Oberfläche |
| API-Schlüssel | `/data/secrets/abacus_api_key.local` | **mittel** — neu beschaffbar, aber ein Sicherungsmedium mit diesem Klartextschlüssel ist selbst schützenswert |
| Scope-Datei | `/data/settings/conversation_scopes.json` | **niedrig** — leicht neu einzugeben |

### Sicherung des Volumes

```bash
# Anwendung stoppen, damit kein Job mitten im Schreiben ist
docker compose stop

# Volume in ein Archiv auf dem Host sichern
docker run --rm \
  -v abacus_backup_data:/data:ro \
  -v "$PWD":/out \
  alpine tar czf /out/abacus-data-$(date +%F).tar.gz -C /data .

docker compose start
```

Das Archiv enthält Chatverläufe **im Klartext** und den API-Schlüssel — es ist wie ein Passwortspeicher zu behandeln.

### Restore des Volumes

```bash
docker compose down

# Volume neu anlegen (Name muss zum Compose-Projekt passen)
docker volume rm abacus_backup_data
docker volume create abacus_backup_data

# Archiv zurueckspielen
docker run --rm \
  -v abacus_backup_data:/data \
  -v "$PWD":/in \
  alpine tar xzf /in/abacus-data-2026-07-30.tar.gz -C /data

docker compose up -d
curl -fsS http://127.0.0.1:8080/api/health     # muss 200 mit status ok liefern
```

Danach in der Oberfläche unter **Backups** prüfen, ob die Liste wieder gefüllt ist. Fehlt sie, obwohl die Dateien vorhanden sind, ist die `app.db` nicht mit zurückgespielt worden — siehe den nächsten Abschnitt.

### Restore ohne die Anwendung

Der wichtigste Fall: Der Nutzer will an **eine Konversation**, nicht an das System.

```bash
# Variante A -- ZIP ueber die Oberflaeche herunterladen und entpacken
unzip abacus_2026-07-30_09-14-22_1a2b3c4d.zip -d ./restore
xdg-open ./restore/index.html          # Windows: start .\restore\index.html

# Variante B -- direkt aus dem Volume kopieren, ohne die Anwendung zu starten
docker run --rm -v abacus_backup_data:/data:ro -v "$PWD":/out \
  alpine cp -r /data/backups/abacus_2026-07-30_09-14-22_1a2b3c4d /out/
```

`index.html` verlinkt alle Dateien **relativ** und funktioniert daher offline im Browser (`backend/app/exporters.py:580-582,700,711`). Die vollständigen Rohdaten je Konversation stehen in der zugehörigen `*.json`, das lesbare Gespräch in `*_Konversation.html`, das Transkript in `*.md`.

### Datenbank verloren, Dateien vorhanden

Es gibt **keinen** Reimport-Mechanismus: Kein Codepfad liest bestehende Verzeichnisse ein und legt Datenbankeinträge an. Praktische Folgen:

- Die Oberfläche zeigt eine leere Backup-Liste, obwohl alle Dateien vorhanden sind.
- Download und Löschen über die API funktionieren für diese Sicherungen nicht mehr.
- Die Daten selbst sind vollständig erhalten und über das Dateisystem zugänglich.

**Handlungsoption:** Ein kleines Reconciliation beim Start, das Verzeichnisse unter `/data/backups` ohne Datenbankeintrag anhand ihrer `manifest.json` nachträgt. Dasselbe würde auch die verwaisten Teil-Backups abgebrochener Läufe sichtbar und löschbar machen.

## Störungsbilder

| # | Symptom | Ursache | Diagnosebefehl | Behebung |
|---|---|---|---|---|
| 1 | Container startet nicht, im Log steht „Basic auth is only half configured: …" | Genau eine der beiden Basic-Auth-Variablen ist gesetzt. Bewusstes Fail-fast (`backend/app/main.py:115-125`) | `docker compose logs --tail 30` | Beide Variablen setzen oder beide leeren, dann `docker compose up -d` |
| 2 | Log zeigt beim Start „Basic auth DISABLED - the API is open, including chat backup downloads." | Beide Auth-Variablen leer (`backend/app/main.py:129-132`) | `docker compose logs \| grep -i "basic auth"` | Nur akzeptabel bei Loopback-Bindung. Vor jeder Netzexposition beide Variablen setzen |
| 3 | Jeder API-Aufruf antwortet mit 400 „No Abacus.AI API key available." | Keine der drei Schlüsselquellen liefert etwas (`backend/app/abacus_client.py:179-180`) | `curl -u user:pass http://127.0.0.1:8080/api/status` — Felder `has_env_api_key` und `has_stored_api_key` prüfen | `ABACUS_API_KEY` setzen und neu starten, oder den Schlüssel in der Oberfläche eingeben |
| 4 | Chatliste bleibt leer, Antwort enthält die Warnung „Could not load deployment conversations because no supported scope could be set or discovered automatically." | Weder Umgebung noch Scope-Datei liefern einen Scope, und die automatische Discovery war erfolglos (`backend/app/abacus_client.py:284-288`) | `curl -u user:pass "http://127.0.0.1:8080/api/chats?refresh=true"` und `warnings` lesen | Unter **Settings** eine Deployment-ID, External-Application-ID oder einen Konversationstyp eintragen; alternativ `ABACUS_DEPLOYMENT_IDS` setzen |
| 5 | Chatliste zeigt veraltete Einträge, Warnung „Loaded from local cache." | Der Cache hat **keine TTL** und wird ohne `refresh` immer bevorzugt (`backend/app/main.py:259-263`) | Antwort auf `GET /api/chats` prüfen | In der Oberfläche „Aktualisieren" statt „Laden", bzw. `?refresh=true` |
| 6 | Job bleibt scheinbar hängen, `current_item` ändert sich lange nicht | Ein SDK-Aufruf läuft in den 120-Sekunden-Timeout; pro Item können bis zu zwei solcher Aufrufe anfallen (`backend/app/backup_engine.py:9,94,162`) | `curl -u user:pass http://127.0.0.1:8080/api/jobs/<id>` | Abwarten; das Item wird übersprungen und in `timed_out_items` vermerkt. Danach „Retry timed-out items" nutzen |
| 7 | Job steht nach einem Neustart auf `failed` mit „Job was interrupted by a container restart or process exit." | Der Lauf existierte nur im Prozess; beim Start werden hängengebliebene Jobs bereinigt (`backend/app/database.py:70-87`) | `curl -u user:pass http://127.0.0.1:8080/api/jobs/<id>` | Job neu starten. Das angefangene Verzeichnis unter `/data/backups` bleibt verwaist zurück und muss von Hand entfernt werden |
| 8 | Sicherung existiert als Verzeichnis, erscheint aber nicht in der Liste | Der Datenbankeintrag entsteht erst am Ende des Laufs (`backend/app/backup_engine.py:220-226`) | `docker compose exec abacus-backup-manager ls -la /data/backups` gegen `GET /api/backups` halten | Verzeichnis manuell auswerten oder löschen; ein Reimport existiert nicht |
| 9 | Backup gilt als erfolgreich, die JSON-Datei enthält aber nur eine dünne Vorschau | Der Detailabruf schlug fehl oder lief in den Timeout; `detail` blieb auf `raw_preview` stehen, es entstand trotzdem eine Datei — `failed` wird deshalb nicht erhöht (`backend/app/backup_engine.py:93-102,174-175`) | `manifest.json` prüfen: `timed_out_items` und `items[].errors` | Betroffene Items gezielt neu exportieren |
| 10 | Manifest meldet „History may be incomplete (history_items=…, total_events=…)" | Die eingebaute Vollständigkeitskontrolle: weniger geladene Einträge als von der API gemeldete Ereignisse (`backend/app/backup_engine.py:103-108`) | `grep -i "may be incomplete" /data/backups/<id>/errors.log` | Betroffene Konversation erneut exportieren; bei dauerhaftem Auftreten liegt eine Begrenzung auf SDK-Seite vor |
| 11 | Container ist `unhealthy`, `/api/health` liefert 503 | Der SQLite-Ping schlägt fehl — Datei fehlt, Volume nicht eingehängt oder Rechte falsch (`backend/app/main.py:153-165`) | `docker compose ps`, `curl -i http://127.0.0.1:8080/api/health`, `docker compose exec abacus-backup-manager ls -la /data` | Volume-Mount und Besitzverhältnisse prüfen; `chown -R app:app /data` geschieht nur zur Build-Zeit (`Dockerfile:26`) |
| 12 | Oberfläche zeigt nur JSON statt der Anwendung | `APP_STATIC_DIR` zeigt ins Leere; die Anwendung mountet dann weder `/assets` noch den SPA-Fallback (`backend/app/main.py:431-437`) | `docker compose exec abacus-backup-manager ls /app/static` | Image neu bauen, damit der Frontend-Build-Stage durchläuft |
| 13 | Download eines großen Backups läuft in einen Browser-Timeout | Fehlt das ZIP, wird es **synchron im Request** erzeugt (`backend/app/main.py:325-328`) | `docker compose logs -f` während des Downloads | Jobs mit `zip: true` starten, sodass das Archiv bereits vorliegt |

## Wartungsaufgaben

| Aufgabe | Intervall | Warum | Wie |
|---|---|---|---|
| Plattenplatz prüfen | monatlich, bei intensiver Nutzung häufiger | Es gibt **keine** Aufbewahrungsregel; jede Sicherung liegt zusätzlich als ZIP im selben Verzeichnis | `docker system df -v`, `GET /api/backups` liefert `size_bytes` je Eintrag |
| Alte Sicherungen löschen | nach Bedarf | Kein automatisches Aufräumen | `DELETE /api/backups/{id}?confirm=true` oder Schaltfläche in der Oberfläche |
| Verwaiste Verzeichnisse entfernen | nach jedem abgebrochenen Lauf | Verzeichnisse ohne Datenbankeintrag sind über die API unsichtbar | `docker compose exec abacus-backup-manager ls /data/backups` gegen `GET /api/backups` abgleichen |
| API-Schlüssel rotieren | gemäß eigener Richtlinie | Der Schlüssel liegt im Klartext in der Umgebung bzw. in der Datei | `DELETE /api/api-key`, neuen Schlüssel bei Abacus.AI erzeugen, `.env` anpassen, `docker compose up -d` |
| Basisimages aktualisieren | quartalsweise | `python:3.11-slim` und `node:20-bookworm-slim` sind bewegliche Tags ohne Digest-Pin | `docker compose build --pull && docker compose up -d` |
| Frontend-Abhängigkeiten prüfen | halbjährlich | Vite 5.x, React 18.x — siehe [03-stack-und-abhaengigkeiten.md](03-stack-und-abhaengigkeiten.md#veraltete-und-ungepflegte-pakete) | `npm outdated` im Verzeichnis `frontend` |
| Volume sichern | vor jedem Update, sonst monatlich | Einziger Ort der Nutzdaten | siehe [Sicherung des Volumes](#sicherung-des-volumes) |
| Jobtabelle beobachten | jährlich | Es gibt **keinen** Löschweg für Jobzeilen; die Tabelle wächst unbegrenzt | `docker compose exec abacus-backup-manager python -c "import sqlite3;print(sqlite3.connect('/data/app.db').execute('select count(*) from jobs').fetchone())"` |

## Skalierungsverhalten und bekannte Grenzen

| Grenze | Beschreibung | Beleg |
|---|---|---|
| **Single-Instance, zwingend** | Jobs leben als `asyncio`-Task im Prozess; ein zweiter Container kennt weder das Abbruchflag noch den laufenden Task. Zusätzlich teilen sich beide dieselbe SQLite-Datei | `backend/app/jobs.py:20-33` |
| **Kein horizontales Skalieren** | Ohne gemeinsamen Zustandsspeicher und ohne Queue ist ein zweiter Replikat-Container nicht sinnvoll | keine Queue im Repository |
| **SQLite-Sperren** | WAL ist aktiv und `timeout=30` gesetzt, aber jede Operation öffnet eine eigene Verbindung. Bei parallelen Jobs mit hoher Fortschrittsfrequenz sind `database is locked`-Situationen möglich | `backend/app/database.py:22,60-63` |
| **Prozessspeicher wächst mit dem Lauf** | Bei aktivem Open-WebUI-Format sammelt die Engine **alle** konvertierten Chats des Laufs bis zum Jobende im Speicher | `backend/app/backup_engine.py:70,132,208-211` |
| **Geteilter SDK-Client** | Alle Jobs nutzen denselben `AbacusService`; `last_warnings` und die entdeckten Scopes werden von parallelen Läufen überschrieben | `backend/app/main.py:52`, `backend/app/jobs.py:19` |
| **Keine Begrenzung paralleler Jobs** | Jeder `POST /api/export` startet sofort einen weiteren Lauf; es gibt keine Warteschlange und kein Limit | `backend/app/jobs.py:26-33` |
| **Sequenzieller Durchsatz** | Innerhalb eines Laufs wird streng ein Item nach dem anderen verarbeitet. Bei 1 000 Konversationen und je 2 Sekunden Antwortzeit dauert ein Lauf über eine halbe Stunde; ein einziger Timeout kostet zusätzlich 120 Sekunden | `backend/app/backup_engine.py:84-189` |
| **Hängende Worker-Threads** | Seit 2026-09-29 wird jeder Executor im `finally` heruntergefahren; ein in den Timeout gelaufener SDK-Aufruf lebt aber als Thread weiter, bis das SDK zurückkehrt | `backend/app/backup_engine.py:14-28` |
| **`GET /api/backups` wird langsam** | `size_bytes` wird bei jedem Aufruf durch rekursives Durchlaufen jedes Backup-Verzeichnisses berechnet | `backend/app/utils.py:93-104`, `backend/app/database.py:179` |
| **Kein Rate-Limit** | Weder für Basic-Auth-Versuche noch für `POST /api/connect`; ohne vorgelagerten Proxy ist beides unbegrenzt versuchbar | keine Limiter-Middleware in `main.py` |
| **Keine Ressourcengrenzen** | Compose setzt weder CPU- noch Speichergrenze | `compose.yaml` ohne `deploy`/`mem_limit` |

## Marker in diesem Dokument

Keine — alle Aussagen sind mit Fundstelle belegt.
