# 11 — Sicherheit und Compliance · app-abacus-chat-backup

Authentifizierung, Umgang mit dem Abacus-API-Schlüssel, Verarbeitung personenbezogener Daten, priorisierte Sicherheitsbefunde und Lizenz-Fazit.

[← Zurück zum Index](README.md)

> **Wichtiger Hinweis zum Stand:** Die Security-Header-Middleware, die Prüfung halb konfigurierter Auth, die Abschaltung von `/docs`, der unprivilegierte Container-Benutzer und die Loopback-Bindung des Ports liegen als **nicht committete Änderungen** im Arbeitsverzeichnis (`git status`: `M backend/app/main.py`, `M Dockerfile`, `M compose.yaml`). Der zuletzt eingecheckte Stand `73f2b41` hat **keine** dieser Härtungen. Wer diesen Commit deployt, deployt einen root-Container mit offener API-Dokumentation und LAN-weitem Portmapping. Alle Aussagen unten beziehen sich auf das Arbeitsverzeichnis.

## Authentifizierung und Autorisierung

### Verfahren

HTTP Basic Authentication mit genau einem Zugangspaar, durchgesetzt in einer einzigen Middleware.

| Eigenschaft | Umsetzung | Beleg |
|---|---|---|
| Geltungsbereich | **Alle** Pfade außer `/api/health` — die Middleware läuft vor jedem Routing | `backend/app/main.py:87-100` |
| Verhalten ohne Konfiguration | **fail-open**: Sind beide Variablen leer, ist `basic_auth_enabled` falsch und jede Anfrage geht ungeprüft durch | `backend/app/config.py:29-31` |
| Verhalten bei halber Konfiguration | **fail-fast**: `RuntimeError` im Startup-Hook, der Container startet nicht | `backend/app/main.py:115-125` |
| Vergleich der Zugangsdaten | `hmac.compare_digest` für Benutzername und Passwort | `backend/app/security.py:111` |
| Header-Verarbeitung | Schemaprüfung case-insensitiv, Base64-Dekodierung in `try/except`, Trennung am **ersten** `:` — Passwörter mit Doppelpunkt funktionieren | `backend/app/security.py:101-110` |
| Antwort bei Fehlschlag | 401 mit `WWW-Authenticate: Basic` und dem Text „Authentication required" | `backend/app/main.py:95-99` |
| Ausnahmeliste | `frozenset({"/api/health"})`, im Code begründet mit HomeLAB_UX-Polling und Container-Healthcheck | `backend/app/main.py:66-68` |
| Sichtbarkeit des Zustands | Beim Start wird der Auth-Status protokolliert — `INFO` bei aktiv, `WARNING` mit ausdrücklicher Nennung der offenen Backup-Downloads bei inaktiv | `backend/app/main.py:126-132` |

Die Mechanik selbst ist sauber: Konstantzeitvergleich, robuste Header-Verarbeitung, minimale Ausnahmeliste mit Begründung, lauter Hinweis auf den offenen Zustand. Der Schwachpunkt ist nicht die Umsetzung, sondern der **Standardzustand**.

### Rollenmodell

| Rolle | Rechte | Durchsetzungsort im Code |
|---|---|---|
| Anonym bei aktiver Auth | Nur `GET /api/health` | `backend/app/main.py:66-68,89` |
| Anonym bei **inaktiver** Auth (Standard) | **Vollzugriff auf alles** — Chatlisten, Start und Abbruch von Jobs, Download **und Löschen** aller Sicherungen, Eingabe und Persistierung eines fremden API-Schlüssels | keine Prüfung, `backend/app/config.py:29-31` |
| Authentifiziert | Vollzugriff auf alle Endpunkte | keine weitere Prüfung in den Handlern |
| Inhaber des API-Schlüssels | Bestimmt implizit, welche Konversationen überhaupt erreichbar sind — die eigentliche Autorisierung liegt bei Abacus.AI | `backend/app/abacus_client.py:170-218` |

Es gibt **keine** Rollendifferenzierung, keine Sitzungen, kein Benutzerverzeichnis und keine endpunktbezogene Rechteprüfung. Insbesondere sind die schreibenden Routen (`POST /api/export`, `PUT /api/conversation-scopes`, `DELETE /api/backups/{id}`, `DELETE /api/api-key`) durch **dieselbe** Schranke geschützt wie die lesenden — und damit im Standardzustand gar nicht.

## Umgang mit Secrets

### Der Abacus-API-Schlüssel

Dies ist die zentrale Frage bei einem Backup-Werkzeug für fremde Chatverläufe: **Woher bekommt das Werkzeug die Zugangsdaten, und wo liegen sie danach?**

| Aspekt | Stand | Beleg |
|---|---|---|
| Drei mögliche Quellen | 1. Eingabe in der Weboberfläche (`POST /api/connect` mit `api_key`) · 2. Umgebungsvariable `ABACUS_API_KEY` · 3. Datei `<APP_DATA_DIR>/secrets/abacus_api_key.local` | `backend/app/abacus_client.py:176-178` |
| Vorrang | UI-Eingabe → Umgebung → Datei | `backend/app/abacus_client.py:177-178` |
| Übertragung vom Browser | Als JSON-Feld im Klartext über HTTP an `/api/connect`. Die Anwendung selbst terminiert **kein TLS** | `frontend/src/api.ts:32-37`, `frontend/src/components/ApiKeyPanel.tsx:90` (Eingabefeld `type="password"`) |
| Speicherung als Datei | Nur auf ausdrücklichen Wunsch (`remember_locally: true`) und nur, wenn `APP_ALLOW_PERSISTENT_API_KEY` aktiv ist | `backend/app/main.py:198-199,206-208` |
| Dateiformat | **Klartext**, eine Zeile, `chmod 0600` — Fehler beim Setzen der Rechte werden stillschweigend ignoriert (relevant auf Windows-Bind-Mounts) | `backend/app/security.py:35-43` |
| Verschlüsselung at rest | **keine** — weder Datei- noch Volume-Verschlüsselung | `backend/app/security.py:39` |
| Löschbarkeit | `DELETE /api/api-key` entfernt die Datei; die Oberfläche bietet dafür eine Schaltfläche | `backend/app/main.py:237-240`, `frontend/src/App.tsx:113-117` |
| Rotierbarkeit | Ja, aber manuell: alten Schlüssel löschen, neuen setzen, bei Umgebungsvariante Neustart nötig (`get_settings` ist gecacht) | `backend/app/config.py:57` |
| Ausgabe an den Client | **Nie.** `StatusResponse` liefert nur die booleschen Felder `has_env_api_key` und `has_stored_api_key`, nie den Wert | `backend/app/models.py:31-39` |
| Schwärzung | Jeder Schlüssel wird an allen vier Eintrittspunkten registriert und danach rekursiv aus Strings, Listen, Tupeln sowie Dict-Schlüsseln **und** -Werten entfernt — auch aus Exception-Texten | `backend/app/security.py:14-18,25-32,35-43,54-98` |
| Reichweite der Schwärzung | Jede geschriebene Datei: JSON, Markdown, beide HTML-Varianten, Open-WebUI-Export sowie jede HTTP-Fehlermeldung | `backend/app/exporters.py:84,117,241,248,443`, `backend/app/main.py:211,276,358` |
| Grenze der Schwärzung | Nur **registrierte** Werte. Ein fremdes Geheimnis im Chatinhalt bleibt unberührt. Das Set wird zudem nie geleert — auch nicht beim Löschen der Key-Datei | `backend/app/security.py:11,54-58` |

**Bewertung:** Die Schwärzung ist konsequenter umgesetzt als in vergleichbaren Werkzeugen und schließt den gefährlichsten Pfad — den eigenen Schlüssel im Export oder in einer Fehlermeldung. Der offene Punkt ist die **Klartextablage**: Wer Zugriff auf das Volume oder ein Volume-Backup hat, hat den Schlüssel und damit Zugriff auf **alle** Abacus.AI-Konversationen des Kontos, nicht nur auf die bereits gesicherten.

### Basic-Auth-Zugangsdaten

| Aspekt | Stand |
|---|---|
| Speicherort | Ausschließlich Prozessumgebung; im Compose-Betrieb aus einer `.env` neben der Compose-Datei interpoliert (`compose.yaml:20-21`) |
| Ablage im Repository | keine — `.gitignore:1` schließt `.env` aus; getrackt ist nur `.env.example` mit leeren Feldern |
| Hashing | **keines** — das Passwort liegt im Klartext in der Umgebung. Wer `docker inspect` oder `/proc/<pid>/environ` lesen kann, liest es mit |
| Rotation | `.env` ändern, `docker compose up -d`; kein Hot-Reload |
| Docker Secrets / Vault | nicht genutzt |

## Verarbeitung personenbezogener Daten

**Dies ist ein Werkzeug, dessen einziger Zweck die Speicherung fremder Gesprächsinhalte ist.** Ein KI-Chatverlauf enthält typischerweise alles, was ein Nutzer je in ein Eingabefeld geschrieben hat: Namen, Adressen, Vertrags- und Gesundheitsangaben, Quellcode, Geschäftsinterna. Alles davon landet unverändert und unverschlüsselt auf der Platte.

| Datenart | Zweck | Rechtsgrundlage-**Kandidat** (Art. 6 DSGVO) | Speicherort | Löschfrist |
|---|---|---|---|---|
| **Vollständige Chatinhalte** (Fragen, Antworten, Zeitstempel, Modellnamen) | Datensicherung und Exportierbarkeit der eigenen Konversationen | Art. 6 Abs. 1 lit. f — berechtigtes Interesse an der Sicherung eigener Daten. Im rein privaten Gebrauch greift zusätzlich die Haushaltsausnahme Art. 2 Abs. 2 lit. c. **Enthalten die Chats Daten Dritter** (z. B. Kundenanfragen), ist eine eigenständige Grundlage erforderlich | `/data/backups/<id>/*/*.json`, `*.md`, `*_Konversation.html`, `*_openwebui.json`, zusätzlich in `backup.zip` — sämtlich Klartext | **keine** — es gibt keine Retention, keine Rotation, keinen Aufräumjob. Löschung nur manuell |
| **Chattitel** | Anzeige und Auswahl in der Oberfläche | wie oben | Tabelle `cached_chats.title`, `manifest.json`, `index.html`, Dateinamen | Titel im Cache bis zum nächsten `refresh=true`; in Manifest und Dateinamen unbegrenzt |
| **Rohdatenvorschau** (bis 24 Schlüssel, Strings auf 300 Zeichen gekürzt) | Fallback-Anzeige, wenn kein Detailabruf möglich war | wie oben | `cached_chats.raw_preview_json`; bei fehlgeschlagenem Detailabruf **auch als vollwertige Exportdatei** | wie oben |
| **Konversations- und Deployment-IDs** | Zuordnung, Deduplizierung, Wiederholungslauf | Art. 6 Abs. 1 lit. f | `jobs`, `backups`, `cached_chats`, `manifest.json`, `errors.log`, `index.html` | unbegrenzt |
| **Fehlertexte** (können Titel und IDs enthalten) | Nachvollziehbarkeit unvollständiger Sicherungen | Art. 6 Abs. 1 lit. f | `jobs.errors_json`, `errors.log`, `index.html` | unbegrenzt |
| **Abacus-API-Schlüssel** | Zugriff auf die Quelldaten | Art. 6 Abs. 1 lit. b/f | `/data/secrets/abacus_api_key.local` (Klartext, `0600`) oder Prozessumgebung | bis zum Löschen über `DELETE /api/api-key` |
| **Basic-Auth-Zugangsdaten** | Zugangsschutz | Art. 6 Abs. 1 lit. f | ausschließlich Prozessumgebung | mit dem Prozess |

**Was das Werkzeug nicht tut:** Es legt keine Nutzerkonten an, protokolliert keine Client-IPs in der Anwendung (nur im Uvicorn-Zugriffslog), setzt keine Cookies, nutzt keinen `localStorage` und sendet keine Telemetrie. Es gibt keinen Tracker, keine Analytics und keine externe Schriftart oder Icon-Quelle — die CSP erlaubt konsequent nur `'self'` (`backend/app/main.py:73-84`).

**Betroffenenrechte.** Auskunft und Löschung sind nur grob umsetzbar: Die kleinste löschbare Einheit ist eine **gesamte Sicherung** (`DELETE /api/backups/{id}?confirm=true`). Eine einzelne Konversation aus einer bestehenden Sicherung zu entfernen, ist über die API nicht möglich — nur durch manuelles Löschen der Dateien, wobei `manifest.json`, `index.html` und das ZIP dann inkonsistent zurückbleiben. Jobzeilen lassen sich überhaupt nicht löschen; es gibt kein `DELETE FROM jobs` im Code.

## Auftragsverarbeiter

| Empfänger | Übermittelte Daten | Bewertung |
|---|---|---|
| **Abacus.AI** | Ausgehend: der API-Schlüssel, Konversations-, Deployment- und External-Application-IDs sowie beim Verbindungstest eine feste englische Beispielabfrage (`backend/app/abacus_client.py:189`). Eingehend: die vollständigen Chatverläufe | Abacus.AI ist bereits **vor** dem Einsatz dieses Werkzeugs Verarbeiter der Daten — das Werkzeug **holt** Daten ab, statt neue dorthin zu senden. Es entsteht kein neues Auftragsverhältnis, aber die bestehende Beziehung zum Anbieter (inklusive Drittlandbezug) bleibt maßgeblich und sollte vertraglich abgesichert sein |
| Sonstige | **keine** | Es gibt keinen weiteren ausgehenden Netzwerkpfad. Die Oberfläche lädt keine externen Schriften, Icons oder Skripte; die CSP erlaubt ausschließlich `'self'` (`backend/app/main.py:73-84`) |

Das ist bemerkenswert sauber: Der einzige Datenabfluss geht an genau den Dienst, von dem die Daten ohnehin stammen.

## Transportverschlüsselung und Verschlüsselung at rest

| Ebene | Stand |
|---|---|
| Browser → Anwendung | **Kein TLS in der Anwendung.** Uvicorn hört auf HTTP/8080 (`Dockerfile:35`). **Konsequenz:** Basic-Auth-Zugangsdaten und ein in der Oberfläche eingegebener API-Schlüssel gehen im Klartext bzw. Base64 über die Leitung. Die Loopback-Bindung (`compose.yaml:9`) entschärft das im Einzelplatzbetrieb vollständig; bei Netzexposition ist ein TLS-terminierender Reverse-Proxy zwingend |
| Anwendung → Abacus.AI | Über das SDK; die Transportsicherheit liegt beim Paket `abacusai`. **TLS-Verifikation wird nirgends deaktiviert** — es gibt kein `verify=False`, kein `ssl._create_unverified_context` und keine entsprechende Umgebungsvariable im Repository |
| At rest — Sicherungen | **keine Verschlüsselung.** Alle Exportdateien und das ZIP liegen im Klartext im Volume; das ZIP ist nicht passwortgeschützt (`backend/app/exporters.py:723`) |
| At rest — Datenbank | **keine Verschlüsselung.** Kein SQLCipher, kein Dateisystem-Krypto in der Compose-Definition |
| At rest — API-Schlüssel | **Klartext** mit `chmod 0600` (`backend/app/security.py:39-43`) |

## Eingabevalidierung

| Eingabequelle | Validierung | Beleg |
|---|---|---|
| Alle JSON-Bodys | Pydantic-Modelle; unbekannte Typen führen zu HTTP 422 | `backend/app/models.py:17-113` |
| `formats`, `types`, `mode`, Job-Status | `Literal`-Typen — nur die definierten Werte sind zulässig | `backend/app/models.py:11-14` |
| Scope-Listen | `field_validator(mode="before")`: `None` → leere Liste, String wird an `[\s,;]+` getrennt und getrimmt, Nicht-Listen werden zu `[]` | `backend/app/models.py:67-83` |
| Umgebungslisten | Dieselbe Trennlogik in `split_env_list` | `backend/app/utils.py:46-50` |
| Boolesche Umgebungsvariablen | Whitelist `{1, true, yes, y, on}`; alles andere ist falsch — **ohne Warnung** bei Tippfehlern | `backend/app/config.py:50-54` |
| Backup-Pfade | `Path(...).resolve()` und `relative_to(backups_dir)`; bei Verletzung HTTP 400 | `backend/app/main.py:414-421` |
| SPA-Dateipfade | `resolve()` plus `relative_to(static_root)`; bei Verletzung HTTP 404 | `backend/app/main.py:438-448` |
| Erzeugte Dateinamen | `safe_filename`: NFKD-Normalisierung, ASCII-Reduktion, alles außer `[A-Za-z0-9_.-]` wird zu `_`, Kürzung auf 90 Zeichen, Trimmen führender Punkte | `backend/app/utils.py:26-30` |
| SQL | Ausschließlich parametrisierte Statements. Die einzige dynamische Stelle ist die `SET`-Klausel in `update_job`, deren Spaltennamen aus **festen Codeaufrufen** stammen und nie aus einem Request | `backend/app/database.py:99-113` |
| HTML-Ausgabe | `html.escape(..., quote=True)` an jeder Einsetzstelle; Links nur mit `http`/`https`-Präfix, sonst wird das Rohmarkup escaped | `backend/app/exporters.py:266-267,577-578,1123-1160` |
| Dateinamen in `index.html` | Zusätzlich `urllib.parse.quote` je Pfadsegment | `backend/app/exporters.py:580-582` |
| Rekursionsschutz | `to_plain_data` bricht bei Tiefe 30 ab, die Nachrichtensuche bei Tiefe 12, die Segmentabflachung bei Tiefe 32 | `backend/app/exporters.py:43,737-739,801-803` |

## Sicherheitsbefunde

Ergebnis der Code-Durchsicht am 2026-07-30, priorisiert. Die von der Spezifikation geforderte Standardliste ist vollständig abgearbeitet; Negativbefunde stehen im Abschnitt darunter.

| # | Schwere | Befund | Fundstelle | Empfehlung |
|---|---|---|---|---|
| 1 | **hoch** | **Härtungen sind nicht eingecheckt.** Security-Header, Auth-Konfigurationsprüfung, abgeschaltete `/docs`, `USER app` und die Loopback-Bindung liegen nur im Arbeitsverzeichnis. Ein Deployment aus `73f2b41` ist ein root-Container mit offener API-Dokumentation, LAN-weitem Portmapping und ohne Security-Header | `git status`: `M backend/app/main.py`, `M Dockerfile`, `M compose.yaml` | Sofort committen. Bis dahin gilt der Git-Stand als unsicher |
| 2 | **hoch** | **Authentifizierung ist standardmäßig aus.** `basic_auth_enabled` ist nur wahr, wenn beide Variablen gesetzt sind; `compose.yaml` liefert beide als leere Defaults. Im Auslieferungszustand sind damit alle Endpunkte außer `/api/health` ungeschützt — einschließlich Download **und Löschung** vollständiger Chat-Backups sowie `POST /api/connect`, über das ein Angreifer einen fremden API-Schlüssel hinterlegen kann. Entschärft, aber nicht behoben, durch die Loopback-Bindung | `backend/app/config.py:29-31`, `compose.yaml:20-21`, `backend/app/main.py:89` | Auth verpflichtend machen: fehlt die Konfiguration, sollte die Anwendung wie bei halber Konfiguration abbrechen statt offen zu starten. Die Warnzeile beim Start ist eine gute Zwischenlösung, kein Ersatz |
| 3 | **hoch** | **Chatverläufe liegen unverschlüsselt und unbefristet im Volume**, zusätzlich als ZIP im selben Verzeichnis. Es gibt keine Retention, keine Rotation, keine Verschlüsselung und keine Löschung einzelner Konversationen. Wer Zugriff auf das Volume oder ein Volume-Backup erhält, hat den vollständigen, dauerhaft wachsenden Gesprächsbestand — plus den API-Schlüssel im selben Volume | `backend/app/config.py:59-67`, `backend/app/exporters.py:81-85,720-728`, kein Retention-Code | Konfigurierbare Aufbewahrung (Höchstalter oder Höchstzahl) mit Aufräumen beim Start; Volume-Verschlüsselung empfehlen und in `SECURITY.md` benennen; optional passwortgeschützte ZIPs |
| 4 | **mittel** | **Kein Rate-Limit und kein Lockout.** Weder die Basic-Auth-Prüfung noch `POST /api/connect` sind begrenzt. Bei Netzexposition ist Passwort-Brute-Force ebenso möglich wie das Durchprobieren fremder API-Schlüssel — letzteres erzeugt zusätzlich Last bei einem Dritten. Fehlversuche werden zudem **nicht protokolliert**, sind also spurlos | `backend/app/main.py:87-100,190-211` | Schlankes In-Memory-Limit auf Auth-Fehlschläge und `/api/connect`; alternativ am Reverse-Proxy. Fehlversuche mindestens auf `WARNING` protokollieren |
| 5 | **mittel** | **Rohe Exception-Texte gehen an den Client.** `safe_error` entfernt registrierte Secrets, gibt sonst aber `str(exc)` unverändert als HTTP-400-`detail` zurück. Damit können interne Pfade, SDK-Interna und Bibliotheksversionen nach außen gelangen | `backend/app/security.py:97-98`, `backend/app/main.py:211,276,358` | Generische Meldung mit Korrelations-ID an den Client, Volltext ins Serverlog |
| 6 | **mittel** | **Kein Logging und zwei stumme Ausnahmepfade.** Es gibt keinerlei Betriebsprotokoll außer zwei Startzeilen; die Scope-Discovery und der stille Verbindungsversuch verschlucken jede Ausnahme vollständig. Ein Sicherheitsvorfall oder ein dauerhaft fehlschlagender Verbindungsaufbau hinterlässt keine Spur | `backend/app/main.py:223-224,372-373` | Strukturiertes Logging konfigurieren; beide Stellen mindestens auf `WARNING` protokollieren |
| 7 | **mittel** | **Stille Truncation bei Listen ohne Paginierungsmetadaten.** Liefert eine SDK-Methode eine nackte Liste ohne Token und ohne `has_more`, endet die Schleife nach Seite 1. `list_chat_sessions` wird ohne explizites `limit` aufgerufen. Bei einem Backup-Werkzeug ist ein stiller Teilexport die gefährlichste Fehlerklasse — er fällt erst auf, wenn man das Backup braucht | `backend/app/abacus_client.py:141-147,265-268` | Explizites `limit` mitgeben und bei `len(page) == limit` offsetbasiert weiterblättern; ins Manifest schreiben, wenn eine Liste exakt an der Seitengrenze endete |
| 8 | **mittel** | **Ein Timeout-Stub zählt als Erfolg.** `failed` wird nur erhöht, wenn **keine** Datei entstand. Nach einem Detail-Timeout bleibt `detail` auf der Vorschau, der JSON-Zweig schreibt daraus trotzdem eine Datei — das Item gilt als gesichert, obwohl der Verlauf nie geladen wurde. Die Zusammenfassung unterschätzt den Datenverlust systematisch | `backend/app/backup_engine.py:93-102,174-175` | Ein `content_ok`-Flag je Item führen; ein Item gilt als fehlgeschlagen, sobald der Detailabruf scheiterte — unabhängig von geschriebenen Stub-Dateien |
| 9 | **niedrig** | **Kein CSRF-Schutz.** Mit Basic-Auth sendet der Browser die Zugangsdaten automatisch mit. `POST /api/jobs/{id}/cancel` benötigt keinen Body und keinen besonderen Content-Type und ist damit per fremdem Formular auslösbar. Die Endpunkte mit JSON-Pflichtbody sowie `DELETE` sind über ein einfaches Formular nicht erreichbar, und `frame-ancestors 'none'` plus `X-Frame-Options: DENY` verhindern Clickjacking | `backend/app/main.py:299-304,73-84` | Zustandsändernde Endpunkte einen Custom-Header verlangen lassen (erzwingt eine Preflight-Prüfung), oder auf ein Token-Verfahren wechseln |
| 10 | **niedrig** | **Nicht-ASCII-Zugangsdaten erzeugen HTTP 500 statt 401.** `hmac.compare_digest` akzeptiert `str` nur bei reinem ASCII und wirft sonst `TypeError`. Der `try/except` umschließt nur Dekodierung und Split, nicht den Vergleich in Zeile 111. Ein Benutzername mit Umlaut führt zum Serverfehler; ein konfiguriertes Passwort mit Sonderzeichen macht jede Anmeldung unmöglich | `backend/app/security.py:101-111` | Beide Seiten vor dem Vergleich nach UTF-8 kodieren |
| 11 | **niedrig** | **Kein Passwort-Hashing im Ruhezustand.** Das Basic-Auth-Passwort steht im Klartext in Umgebung und `.env`; wer `docker inspect` oder `/proc/<pid>/environ` lesen kann, liest es mit | `backend/app/config.py:74-75`, `compose.yaml:20-21` | Statt Klartext einen vorberechneten Hash in der Umgebung ablegen, oder Docker Secrets nutzen |
| 12 | **niedrig** | **Keine Schemaversionierung der Datenbank.** Nur `CREATE TABLE IF NOT EXISTS`; eine bestehende Datenbank erhält keine später ergänzten Spalten und scheitert dann zur Laufzeit statt beim Start | `backend/app/database.py:17-58` | `PRAGMA user_version` als Gate plus Migrationsliste |
| 13 | **niedrig** | **`abacusai>=1.4` ohne Obergrenze bei gleichzeitigem Duck-Typing.** Ein Major-Release bricht nicht laut, sondern still: Signaturvarianten passen nicht mehr, `hasattr` liefert `False`, das Backup bleibt leer. Die drei anderen Abhängigkeiten sind korrekt begrenzt | `backend/requirements.txt:4`, `backend/app/abacus_client.py:75-97` | Auf `<2.0` pinnen und die Grenze bewusst und geprüft anheben |
| 14 | **niedrig** | **Mehrfach referenzierte Objekte gehen im Export verloren.** `_to_plain_data` entfernt die Objekt-ID nach dem Abstieg nicht aus `seen`. Ein Objekt, das legitim an zwei Stellen derselben Struktur vorkommt, wird beim zweiten Vorkommen durch `str(obj)` ersetzt — Inhaltsverlust ohne Fehlermeldung | `backend/app/exporters.py:57-60` | `seen` pfadbezogen führen, also die ID nach dem Abstieg wieder entfernen |
| 15 | **niedrig** | **Toter Code im Sicherheitsmodul.** `mask_secret` ist definiert, wird aber nirgends aufgerufen. Ungenutzte Funktionen in einem Sicherheitsmodul laden dazu ein, sie später ohne Prüfung zu verwenden | `backend/app/security.py:61-66` | Entfernen oder bewusst einsetzen |
| 16 | **niedrig** | **Verwaiste Teil-Backups.** Bricht ein Job ab, bleibt ein Verzeichnis ohne Datenbankeintrag zurück: unsichtbar in der Liste, über die API nicht löschbar, dauerhaft Platz belegend — und es enthält personenbezogene Daten | `backend/app/backup_engine.py:63-76` gegenüber `220-226` | Reconciliation beim Start: Verzeichnisse ohne Datenbankeintrag nachtragen oder entfernen |

### Geprüft, kein Befund

| Prüfpunkt | Ergebnis |
|---|---|
| **Hartkodierte Secrets** | **Keine.** Grep über `backend/app/` und `frontend/src/` nach Zuweisungen von Schlüsseln, Passwörtern und Tokens liefert keinen Treffer. Die einzigen Zugangsdaten kommen aus Umgebung, Request oder Datei |
| **Default-Passwörter** | **Keine.** Es gibt keinen vorbelegten Benutzer und kein Standardpasswort; `.env.example` enthält ausschließlich leere Felder |
| **`CORS: *`** | **Nicht vorhanden.** Es gibt überhaupt keine CORS-Konfiguration — Oberfläche und API teilen sich denselben Origin. Der portfolioweite Wildcard-Befund trifft hier nicht zu |
| **Fehlende AuthN auf schreibenden Routen** | Alle schreibenden Routen liegen hinter derselben Middleware wie die lesenden. Es gibt keinen Endpunkt, der die Auth gezielt umgeht — der einzige Ausnahmepfad `/api/health` ist lesend und gibt keine Konfigurationsdaten preis. **Aber:** Bei Standardkonfiguration ist die Auth komplett aus (Befund 2) |
| **SQL-Injection** | **Nicht vorhanden.** Alle Statements sind parametrisiert; die einzige dynamische `SET`-Klausel bezieht Spaltennamen aus festen Codeaufrufen, nie aus Requests (`backend/app/database.py:99-113`) |
| **`eval` / `exec` / `pickle` / `subprocess`** | **Nicht vorhanden.** Grep über das gesamte Backend liefert keinen Treffer |
| **Deaktivierte TLS-Verifikation** | **Nicht vorhanden.** Kein `verify=False`, kein unverifizierter SSL-Kontext, keine entsprechende Umgebungsvariable |
| **Path Traversal** | **Abgesichert.** Backup-Pfade und SPA-Dateipfade werden per `resolve()` und `relative_to()` gegen ihr Wurzelverzeichnis geprüft (`backend/app/main.py:414-421,438-448`); Backup-IDs gehen nie als Pfadbestandteil in einen Dateizugriff, sondern nur als Datenbankschlüssel. Erzeugte Dateinamen sind auf `[A-Za-z0-9_.-]` reduziert |
| **Datei-Upload** | **Nicht vorhanden** — es gibt keinen Endpunkt, der Dateien entgegennimmt |
| **SSRF** | **Nicht vorhanden.** Ausgehender Verkehr läuft ausschließlich über den SDK-Client; kein Codepfad nimmt eine URL aus einem Request für einen serverseitigen Abruf |
| **XSS im HTML-Export** | **Abgesichert.** `html.escape(quote=True)` an jeder Einsetzstelle; im Markdown-Subset werden nur `http(s)`-Links als `<a>` gerendert und mit `rel="noopener noreferrer"` versehen, alles andere wird escaped (`backend/app/exporters.py:1123-1160`) |
| **XSS in der Oberfläche** | **Abgesichert.** Kein `dangerouslySetInnerHTML`, kein `innerHTML` im Frontend; sämtliche Ausgabe läuft über die React-Textescapierung |
| **Offene Debug-Endpunkte** | **Keine.** `/docs`, `/redoc` und `/openapi.json` sind ausdrücklich abgeschaltet, mit Begründung im Code (`backend/app/main.py:57-59`) |
| **Security-Header** | **Vorhanden:** CSP, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` — gesetzt auf jeder Antwort, auch auf 401. Fehlend: `Strict-Transport-Security` (sinnvollerweise Aufgabe eines TLS-terminierenden Proxys) und `Permissions-Policy` |
| **Container als root** | **Behoben im Arbeitsverzeichnis:** `adduser --system --group app` plus `USER app` (`Dockerfile:25-27`), ergänzt um `no-new-privileges:true` (`compose.yaml:10-11`). Im eingecheckten Stand aber noch nicht enthalten — siehe Befund 1 |
| **Docker-Socket** | **Nicht gemountet.** Es gibt keinen Socket-Zugriff und keine Docker-API-Nutzung |
| **Secrets im Repository** | Getrackt sind nur `.env.example` (leere Felder) und `LICENSE`. Keine Schlüssel, keine Datenbank, keine Backups; `.gitignore:1,10-11` schließt `.env`, `data/` und `backups/` aus |
| **Konstantzeitvergleich** | `hmac.compare_digest` für beide Felder. Die Kurzschlussauswertung überspringt bei falschem Benutzernamen den Passwortvergleich — unkritisch, da der Benutzername kein Geheimnis ist (zur Robustheit siehe Befund 10) |
| **Backup-Integritätsprüfung** | **Vorhanden und ungewöhnlich sorgfältig:** Die Engine vergleicht die Anzahl geladener History-Einträge mit der von der API gemeldeten Gesamtzahl und schreibt das Ergebnis je Item ins Manifest (`backend/app/backup_engine.py:103-108`, `backend/app/exporters.py:120-138`) |

## Lizenz-Compliance-Fazit

`ZIEL_LIZENZ` = **proprietär / nicht zur Weitergabe**.

| Aspekt | Bewertung |
|---|---|
| Eigenes Repository | 🔴 **Widerspruch zur Zielvorgabe.** Das Projekt steht unter **MIT** (`LICENSE:1-21`) und erlaubt damit ausdrücklich Nutzung, Änderung, Weitergabe und Unterlizenzierung durch jeden Empfänger. **Konsequenz:** Eine Weitergabe ist nicht nur möglich, sondern lizenzrechtlich eingeladen. **Handlungsoption:** Entweder die Zielvorgabe für dieses Projekt bewusst auf „offen" korrigieren — wofür `SECURITY.md:11` mit dem Verweis auf GitHub Security Advisories spricht — oder die `LICENSE` durch einen proprietären Text ersetzen und den README-Verweis anpassen. So oder so gehört die Entscheidung dokumentiert |
| Frontend-Abhängigkeitsbaum | 🟢 182 Pakete: 165 × MIT, 11 × ISC, 4 × Apache-2.0, 1 × BSD-3-Clause, 1 × CC-BY-4.0. **Kein GPL, kein LGPL, kein AGPL, kein MPL, kein `unknown`** |
| Apache-2.0 (`typescript` u. a.) | 🟢 unkritisch, **NOTICE-Pflicht bei Weitergabe**. Alle vier Pakete sind Build-Zeit-Werkzeuge und landen nicht im ausgelieferten Bundle |
| CC-BY-4.0 (`caniuse-lite`) | 🟡 **Namensnennungspflicht** bei Weitergabe. Build-Zeit-Datenbank. **Handlungsoption:** NOTICE-Eintrag |
| Backend-Abhängigkeiten | 🔴 **Nicht bewertbar.** Es gibt kein Python-Lockfile und kein gebautes Image; die Lizenz von `abacusai` und der gesamte transitive Baum sind unbekannt. Nach dem Bewertungsmaßstab ist `unknown` wie starkes Copyleft zu behandeln. **Handlungsoption:** Beim nächsten Build die Paketmetadaten aus dem Image auslesen und in [03-stack-und-abhaengigkeiten.md](03-stack-und-abhaengigkeiten.md#tabelle-1a--direkte-abhängigkeiten-backend) nachtragen |
| Container-Basisimages | 🟡 `python:3.11-slim` und `node:20-bookworm-slim` werden unverändert als Basis genutzt; Debian-Pakete bringen eine Mischung permissiver und copyleft-Lizenzen mit, die bei **Weitergabe des Images** relevant würde. Für den reinen Eigenbetrieb unkritisch. Nicht verifiziert, da kein Image vorliegt |

**Gesamtampel: 🔴** — nicht wegen der Abhängigkeiten, die im belegbaren Teil sauber sind, sondern wegen zweier offener Punkte: der **MIT-Lizenz im Widerspruch zur Zielvorgabe** und der **nicht ermittelbaren Backend-Lizenzen**. Beide sind mit überschaubarem Aufwand klärbar.

## Marker in diesem Dokument

Eigene Marker enthält dieses Dokument nicht — alle Sicherheitsbefunde sind mit Fundstelle belegt. Übernommen aus [03-stack-und-abhaengigkeiten.md](03-stack-und-abhaengigkeiten.md#tabelle-1a--direkte-abhängigkeiten-backend) wirkt hier ein Marker fort:

- ⚠️ NICHT ERMITTELBAR — Lizenzen der Backend-Abhängigkeiten inklusive `abacusai`; die Lizenz-Ampel bleibt bis zur Klärung 🔴
