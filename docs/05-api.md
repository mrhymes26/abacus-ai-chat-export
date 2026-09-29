# 05 — API · app-abacus-chat-backup

Bereitgestellte HTTP-Endpunkte, konsumierte externe Schnittstellen und alle sonstigen Ein- und Ausgabewege.

[← Zurück zum Index](README.md)

Maschinenlesbare Beschreibung der bereitgestellten Endpunkte: [openapi.yaml](openapi.yaml) (OpenAPI 3.1, aus dem Code erzeugt — im Projekt existierte keine Spezifikation).

## Bereitgestellte Endpunkte

Alle Endpunkte liegen unter demselben Origin wie die Oberfläche. Die interaktive Dokumentation ist **abgeschaltet**: `docs_url=None, redoc_url=None, openapi_url=None` — im Code damit begründet, dass sie bei deaktivierter Basic-Auth die vollständige API-Oberfläche offenlegen würde (`backend/app/main.py:57-59`).

| Methode | Pfad | Zweck | Auth | Request | Response | Fehlercodes | Idempotenz | Rate Limit |
|---|---|---|---|---|---|---|---|---|
| `GET` | `/api/health` | Liveness und DB-Ping; liefert `status`, `version`, `uptime_s`, `checks[]`, optional `commit` | **öffentlich** (einziger Pfad in der Ausnahmeliste) | — | JSON, `Cache-Control: no-store` | `503` wenn der SQLite-Ping fehlschlägt | ja | keiner |
| `POST` | `/api/connect` | Verbindung zu Abacus.AI aufbauen; optional API-Key aus der Oberfläche übernehmen und lokal speichern | Basic (wenn aktiv) | `ConnectRequest` (optional, Default leer) | `ConnectionResult` | `400` Verbindung fehlgeschlagen oder `remember_locally` ohne Key; `403` UI-Key-Eingabe bzw. Persistenz deaktiviert; `422` Schemafehler | **nein** — schreibt bei `remember_locally` die Key-Datei | keiner |
| `GET` | `/api/status` | Zustandsbild für die Oberfläche: Key-Quellen, Verbindungsstatus, wirksame und gespeicherte Scopes, Datenverzeichnis. **Nebenwirkung:** versucht eine stille Verbindung und ggf. eine Scope-Discovery | Basic | — | `StatusResponse` | — (Fehler werden verschluckt) | nein (Nebenwirkung) | keiner |
| `DELETE` | `/api/api-key` | Löscht die lokal gespeicherte API-Key-Datei | Basic | — | `{"deleted": bool}` | — | ja | keiner |
| `GET` | `/api/conversation-scopes` | Liest die manuell gepflegten Scopes aus der JSON-Datei | Basic | — | `ConversationScopes` | — | ja | keiner |
| `PUT` | `/api/conversation-scopes` | Überschreibt die Scope-Datei vollständig; normalisiert Strings, Listen und Trennzeichen | Basic | `ConversationScopes` | `ConversationScopes` (normalisiert) | `422` Schemafehler | ja (voller Ersatz) | keiner |
| `GET` | `/api/chats` | Listet Konversationen. Ohne `refresh` aus dem SQLite-Cache (Antwort trägt dann die Warnung „Loaded from local cache."), sonst frisch von der API inklusive Cache-Aktualisierung | Basic | Query: `include_ai_chat` (bool, Default `true`), `include_deployments` (bool, Default `true`), `refresh` (bool, Default `false`) | `ChatListResponse` | `400` nicht verbunden oder SDK-Fehler | `GET`, aber **nicht** nebenwirkungsfrei: `refresh=true` ersetzt den Cache | keiner |
| `POST` | `/api/export` | Startet einen Backup-Job und liefert sofort dessen ID zurück | Basic | `ExportRequest` | `ExportStartResponse` | `400` `mode=selected` ohne `chat_ids`, leere `formats`, oder nicht verbunden; `503` Job-Manager noch nicht bereit; `422` Schemafehler | **nein** — jeder Aufruf erzeugt einen neuen Job und ein neues Verzeichnis | keiner |
| `GET` | `/api/jobs/{job_id}` | Status, Fortschritt, Fehlerliste und Ergebnis eines Jobs | Basic | Pfad: `job_id` | `BackupJob` | `404` unbekannte Job-ID | ja | keiner — die Oberfläche pollt im **Sekundentakt** |
| `POST` | `/api/jobs/{job_id}/cancel` | Setzt das Abbruchflag und markiert den Job als `cancelled`, sofern er noch läuft | Basic | Pfad: `job_id` | `{"cancelled": true}` | `404` unbekannte Job-ID | ja | keiner |
| `GET` | `/api/backups` | Listet alle Sicherungen, absteigend nach Erstellungszeit, mit Größe und Download-URL | Basic | — | `BackupListResponse` | — | ja | keiner |
| `GET` | `/api/backups/{backup_id}/manifest` | Liefert `manifest.json` von der Platte; existiert die Datei nicht, das in der Datenbank hinterlegte Manifest | Basic | Pfad: `backup_id` | JSON (Manifest) | `404` unbekannte ID; `400` Pfad außerhalb des Backup-Wurzelverzeichnisses | ja | keiner |
| `GET` | `/api/backups/{backup_id}/download` | Liefert das ZIP; erzeugt es beim ersten Aufruf, falls es noch nicht existiert, und schreibt den Pfad zurück in die Datenbank | Basic | Pfad: `backup_id` | `application/zip`, Dateiname `{backup_id}.zip` | `404` unbekannte ID; `400` Pfadprüfung fehlgeschlagen | ja im Ergebnis, **nein** im Effekt (erzeugt ggf. das ZIP) | keiner |
| `DELETE` | `/api/backups/{backup_id}` | Löscht Verzeichnis **und** Datenbankeintrag; verlangt eine ausdrückliche Bestätigung | Basic | Pfad: `backup_id`; Query: `confirm` (bool, Pflicht `true`) | `{"deleted": true}` | `400` ohne `confirm=true`; `404` unbekannte ID; `400` Pfadprüfung fehlgeschlagen | ja | keiner |
| `GET` | `/assets/{datei}` | Statische Bundle-Dateien, nur gemountet, wenn `APP_STATIC_DIR/assets` existiert | Basic | — | JS/CSS | `404` | ja | keiner |
| `GET` | `/{beliebiger-pfad}` | SPA-Fallback: existiert die Datei unterhalb von `APP_STATIC_DIR`, wird sie geliefert, sonst `index.html` | Basic | — | HTML bzw. Datei | `404` bei Pfad außerhalb des Wurzelverzeichnisses | ja | keiner |

Belege in Reihenfolge: `backend/app/main.py:168-187, 190-211, 214-234, 237-240, 243-245, 248-250, 253-276, 279-288, 291-296, 299-304, 307-309, 312-318, 321-333, 336-345, 431-448`.

### Anmerkungen zu einzelnen Endpunkten

**`GET /api/status` hat Nebenwirkungen.** Der Handler versucht zunächst eine stille Verbindung (`_try_connect_silently`) und startet, falls verbunden und noch kein Scope bekannt ist, eine vollständige Scope-Discovery über die Abacus-API. Schlägt eine der beiden Aktionen fehl, wird die Ausnahme kommentarlos verschluckt (`backend/app/main.py:214-224,361-373`). Ein scheinbar harmloser Statusabruf kann damit mehrere API-Aufrufe an Abacus.AI auslösen.

**`GET /api/chats` liefert standardmäßig veraltete Daten.** Ist der Cache gefüllt, wird er ohne Altersprüfung zurückgegeben — es gibt **keine TTL**. Der einzige Hinweis ist die Warnung „Loaded from local cache." in der Antwort (`backend/app/main.py:259-263`). Nur `refresh=true` erzwingt einen frischen Abruf.

**Die Filterparameter wirken unterschiedlich.** Bei einem Cache-Treffer filtert `_filter_items` lokal; bei einem Frischabruf werden `include_ai_chat` und `include_deployments` an die Ladelogik durchgereicht und entscheiden, welche SDK-Aufrufe überhaupt stattfinden (`backend/app/main.py:262,267-272`).

**`chat_ids` sind keine reinen IDs.** Für `mode=selected` erwartet das Backend den kanonischen Schlüssel `type:deployment_id_or_empty:id`, denselben, den das Frontend über `chatSelectionKey` bildet. Eine nackte Konversations-ID trifft nichts (`backend/app/backup_engine.py:260-267`, `frontend/src/components/ChatTable.tsx:21-23`).

**Nicht alle `ExportRequest`-Felder sind über die Oberfläche erreichbar.** `deployment_ids`, `external_application_ids`, `conversation_types` und `types` existieren im Modell und werden serverseitig ausgewertet (`backend/app/backup_engine.py:240-251,270-275`), das Frontend sendet aber nur `mode`, `chat_ids`, ein festes `types`-Paar, `formats` und `zip` (`frontend/src/api.ts:69-79`). Ein API-Aufruf von Hand kann den Suchbereich also feiner steuern als die Oberfläche.

## Authentifizierung

| Aspekt | Umsetzung | Beleg |
|---|---|---|
| Verfahren | HTTP Basic Authentication, ein einziges Zugangspaar aus der Umgebung | `backend/app/config.py:74-75`, `backend/app/main.py:87-100` |
| Aktivierung | Nur wenn **beide** Variablen gesetzt sind; sonst ist die gesamte API offen | `backend/app/config.py:29-31` |
| Halbe Konfiguration | Startet **nicht** — `RuntimeError` im Startup-Hook mit Nennung der fehlenden Variablen | `backend/app/main.py:115-125` |
| Ausnahmen | Genau ein Pfad: `/api/health`, als `frozenset` mit Begründung (HomeLAB_UX-Polling, Container-Healthcheck) | `backend/app/main.py:66-68` |
| Vergleich | `hmac.compare_digest` für Benutzername und Passwort auf UTF-8-Bytes — Zugangsdaten mit Umlauten ergeben seit 2026-09-29 `401` statt `500` | `backend/app/security.py:111-114` |
| Antwort bei Fehlschlag | `401` mit `WWW-Authenticate: Basic` und dem Text „Authentication required" | `backend/app/main.py:95-99` |
| Granularität | Keine — es gibt keine Rollen und keine endpunktweise Prüfung; wer authentifiziert ist, darf alles | keine weitere Prüfung in den Handlern |

## CORS

**Nicht vorhanden — und das ist hier korrekt.** Es gibt keine `CORSMiddleware`, keinen `allow_origins`-Eintrag und keine Header-Manipulation für Cross-Origin-Anfragen. Grund: Das Frontend wird als statisches Bundle aus demselben Origin ausgeliefert (`Dockerfile:20`, `backend/app/main.py:431-448`) und ruft die API ausschließlich über relative Pfade auf (`frontend/src/api.ts:18`). Der im Portfolio verbreitete Befund `allow_origins=["*"]` existiert in diesem Projekt nicht.

Im Entwicklungsbetrieb löst der Vite-Dev-Server das Problem per Proxy statt per CORS: `/api` wird auf `http://127.0.0.1:8080` weitergeleitet (`frontend/vite.config.ts:8-10`).

## Versionierung und Pagination

| Thema | Stand |
|---|---|
| API-Versionierung | **Keine.** Kein `/v1`-Präfix, kein `Accept-Version`-Header, keine Deprecation-Kennzeichnung. Die Anwendungsversion ist als `APP_VERSION = "1.0.0"` fest im Code hinterlegt (`backend/app/models.py:9`) und erscheint nur in `/api/health` und im Backup-Manifest |
| Pagination der eigenen API | **Keine.** `/api/chats` und `/api/backups` liefern immer die vollständige Liste; Seitenaufteilung findet ausschließlich im Browser statt (10/50/100 Zeilen, `frontend/src/components/ChatTable.tsx:18-19`) |
| Sortierung | `/api/backups` sortiert serverseitig nach `created_at DESC` (`backend/app/database.py:165`); `/api/chats` sortiert im Cache-Fall nach `updated_at DESC, created_at DESC` (`backend/app/database.py:231`), im Frischabruf gar nicht |

## Sicherheitsheader

Eine zweite Middleware setzt auf **jede** Antwort — auch auf die 401 der Auth-Schicht, da sie äußer registriert ist — folgende Header per `setdefault` (`backend/app/main.py:73-84,105-112`):

| Header | Wert |
|---|---|
| `Content-Security-Policy` | `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'` |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `no-referrer` |

`'unsafe-inline'` ist auf `style-src` beschränkt und im Code mit den Inline-Style-Attributen von React begründet; `script-src` bleibt auf `'self'`.

## Konsumierte externe API

Es gibt genau **einen** externen Dienst.

| Merkmal | Angabe |
|---|---|
| Anbieter | Abacus.AI |
| Zugriffsweg | Ausschließlich über das offizielle Python-SDK `abacusai`; der `ApiClient` wird mit dem API-Key erzeugt (`backend/app/security.py:69-73`) |
| Endpunkte | ⚠️ siehe Marker — der Code kennt nur SDK-**Methoden**, keine URLs |
| Auth-Verfahren | API-Key, an den SDK-Konstruktor übergeben. Herkunft in dieser Reihenfolge: Eingabe in der Oberfläche → Umgebungsvariable `ABACUS_API_KEY` → lokal gespeicherte Datei (`backend/app/abacus_client.py:176-178`) |
| Kosten / Kontingent | ⚠️ siehe Marker |
| Rate Limit | ⚠️ siehe Marker |
| Verhalten bei Ausfall | **Kein Retry, kein Backoff, keine Auswertung von `Retry-After`, kein Circuit Breaker.** Ein Fehler je Item wird protokolliert, der Lauf macht mit dem nächsten Item weiter. Einziger Schutzmechanismus ist ein **Timeout von 120 Sekunden** je SDK-Aufruf; danach gilt das Item als übersprungen und landet in `timed_out_items` (`backend/app/backup_engine.py:9,94-100,162-168`) |
| Lastverstärkung im Fehlerfall | `try_call_variants` probiert bei **jedem** Fehler die nächste Signaturvariante, nicht nur bei Signaturfehlern. Trifft ein Rate-Limit, steigt die Anfragezahl je Item auf die Zahl der Varianten (`backend/app/abacus_client.py:100-110`) |
| Datenschutzrelevanz | **Hoch.** Übertragen wird der API-Key; zurück kommen vollständige Chatverläufe mit allem, was Nutzer je in einen KI-Chat geschrieben haben. Details in [11-sicherheit-compliance.md](11-sicherheit-compliance.md#verarbeitung-personenbezogener-daten) |

### Genutzte SDK-Methoden

Alle zehn Methoden werden vor dem Aufruf per `hasattr` geprüft; fehlt eine, entsteht eine Warnung statt eines Fehlers (`backend/app/abacus_client.py:13-24,220-224`).

| Methode | Verwendung | Fundstelle |
|---|---|---|
| `suggest_abacus_apis` | **Verbindungstest** beim Connect; fehlt sie, wird nur eine Warnung erzeugt und der Client trotzdem als verbunden geführt | `backend/app/abacus_client.py:187-204` |
| `list_chat_sessions` | Auflisten der allgemeinen KI-Chats, mit Paginierung | `backend/app/abacus_client.py:262-273` |
| `get_chat_session` | Volldetails eines KI-Chats; fünf Parametervarianten | `backend/app/abacus_client.py:301-314` |
| `export_chat_session` | SDK-eigener HTML-Export eines KI-Chats | `backend/app/abacus_client.py:327-339` |
| `list_projects` | Erster Schritt der Deployment-Discovery (max. 100 Projekte, eine Seite) | `backend/app/abacus_client.py:374-379` |
| `list_deployments` | Zweiter Schritt: Deployments je Projekt, bis zu fünf Seiten | `backend/app/abacus_client.py:390-395` |
| `list_external_applications` | Discovery der External-Application-IDs, eine Seite | `backend/app/abacus_client.py:409-413` |
| `list_deployment_conversations` | Auflisten der Deployment-Konversationen je Scope, mit `limit: 600` und `include_org_level_conversations: True` | `backend/app/abacus_client.py:430-443` |
| `get_deployment_conversation` | Volldetails einer Deployment-Konversation; kombiniert ID-, Scope- und Detailvarianten mit `limit: 5000` und `include_all_versions: True` | `backend/app/abacus_client.py:316-322,669-680` |
| `export_deployment_conversation` | SDK-eigener HTML-Export einer Deployment-Konversation | `backend/app/abacus_client.py:341-347` |

Zusätzlich wird die Enum-Klasse `abacusai.api_class.enums.DeploymentConversationType` importiert, um Konversationstypen als Fallback-Scopes zu erhalten; schlägt der Import fehl, greift eine im Code fest hinterlegte Liste von 18 Typnamen (`backend/app/abacus_client.py:604-629`).

> ⚠️ NICHT ERMITTELBAR — Quelle fehlt: Konkrete HTTP-Endpunkte, Basis-URL, Rate Limits, Kontingente und Kosten der Abacus.AI-API. Der Code spricht ausschließlich SDK-Methoden an; die zugehörigen URLs stehen im Paket `abacusai`, das lokal nicht installiert ist. Netzwerkabfragen und `pip install` sind für diese Dokumentation ausgeschlossen.

## Weitere Schnittstellen

| Art | Vorhanden? | Details |
|---|---|---|
| MQTT | nein | keine Bibliothek, kein Client im Code |
| WebSocket / SSE | nein | Fortschritt wird per Polling im Sekundentakt geholt (`frontend/src/App.tsx:84-96`); das `websockets`-Paket kommt nur als Extra von `uvicorn[standard]` mit und wird nicht genutzt |
| Message Queue | nein | Jobs laufen prozessintern über `asyncio`-Tasks (`backend/app/jobs.py:31-33`) |
| Cron / Scheduler | nein | kein Zeitplan im Repository |
| Webhooks | nein | weder eingehend noch ausgehend |
| CLI-Kommandos | nein | einziger Einstiegspunkt ist der Uvicorn-Start (`Dockerfile:35`); `scripts/` ist leer |
| Dateiimport | nein | es gibt keinen Upload-Endpunkt |
| **Dateiexport** | **ja** | Der eigentliche Zweck: je Konversation `*.json`, `*.md`, `*_Konversation.html`, optional `*_html.html`/`*_html.meta.json` und `*_openwebui.json`; je Lauf `manifest.json`, `errors.log`, `index.html`, optional `openwebui_import.json` und `backup.zip` (`backend/app/backup_engine.py:110-172,196-218`) |
| **Konfigurationsdateien** | **ja** | `/data/settings/conversation_scopes.json` wird gelesen und über `PUT /api/conversation-scopes` geschrieben; `/data/secrets/abacus_api_key.local` wird über `POST /api/connect` geschrieben und über `DELETE /api/api-key` gelöscht (`backend/app/local_settings.py:12-25`, `backend/app/security.py:35-51`) |

## Marker in diesem Dokument

- ⚠️ NICHT ERMITTELBAR — konkrete HTTP-Endpunkte, Rate Limits, Kontingente und Kosten der Abacus.AI-API (nur SDK-Methoden im Code, Paket lokal nicht vorhanden)
