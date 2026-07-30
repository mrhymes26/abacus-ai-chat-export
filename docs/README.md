# Dokumentation · app-abacus-chat-backup (Abacus Backup Chat Export Manager)

Abacus.AI bietet keinen Weg, eigene Chatverläufe über die Weboberfläche zu exportieren — der Zugang führt ausschließlich über die API. Dieses Werkzeug schließt die Lücke: Es meldet sich mit einem API-Schlüssel an, findet die erreichbaren KI-Chats und Deployment-Konversationen selbstständig, lädt sie vollständig herunter und legt sie lokal ab — als Rohdaten (JSON), als Transkript (Markdown), als druckfertiges Gesprächsprotokoll (HTML) und als Importdatei für Open WebUI, gebündelt in einem ZIP mit navigierbarer Übersichtsseite. Backend ist FastAPI mit SQLite, Frontend eine React-Oberfläche, die aus demselben Container ausgeliefert wird. Alles bleibt beim Betreiber: ein einziger ausgehender Netzwerkpfad, keine Nutzerkonten, keine Telemetrie.

## Dokumentenübersicht

| Dokument | Inhalt |
|---|---|
| [01-ueberblick.md](01-ueberblick.md) | Allgemeinverständlich: Zweck, Funktionen, typischer Anwendungsfall, Abgrenzung, Reifegrad |
| [02-architektur.md](02-architektur.md) | Systemkontext, Komponenten mit Verantwortlichkeiten, Verzeichnisstruktur, sechs nachträgliche ADRs |
| [03-stack-und-abhaengigkeiten.md](03-stack-und-abhaengigkeiten.md) | Laufzeiten, direkte Abhängigkeiten, Lizenzübersicht über 182 Frontend-Pakete, offene Backend-Lizenzfrage |
| [04-container.md](04-container.md) | Multi-Stage-Dockerfile, Ports, Volume, Healthcheck, Startup- und Shutdown-Verhalten, Compose-Topologie |
| [05-api.md](05-api.md) | 14 API-Endpunkte plus Bundle-Auslieferung, Auth, Security-Header, konsumierte Abacus-SDK-Methoden |
| [06-datenmodell.md](06-datenmodell.md) | SQLite-Schema, Dateiablage je Sicherung, Zwischenspeicher, Löschkonzept für personenbezogene Daten |
| [07-prozesse.md](07-prozesse.md) | Verbinden, Auflisten, Backup-Lauf, Download und Löschen — je als Sequenzdiagramm; Jobzustandsautomat |
| [08-konfiguration.md](08-konfiguration.md) | Alle 15 Umgebungsvariablen mit Fundstelle, Vorrangreihenfolge, Feature-Flags, Umgebungsunterschiede |
| [09-build-deploy.md](09-build-deploy.md) | Setup als kopierbare Befehlsfolge, Buildartefakte, fehlende CI, Deployment, Rollback, Versionierung |
| [10-betrieb.md](10-betrieb.md) | Logging, Health, Volume-Sicherung mit konkretem Restore, 13 Störungsbilder, Wartung, Skalierungsgrenzen |
| [11-sicherheit-compliance.md](11-sicherheit-compliance.md) | Auth, Umgang mit dem API-Schlüssel, personenbezogene Daten, 16 priorisierte Befunde, Lizenz-Fazit |
| [12-offene-punkte.md](12-offene-punkte.md) | Alle Marker, Annahmen, 25 technische Schulden mit Aufwand und Risiko, priorisierte nächste Schritte |

Maschinenlesbare Schnittstellenbeschreibung: [openapi.yaml](openapi.yaml) (OpenAPI 3.1, aus dem Code erzeugt — im Projekt existierte keine Spezifikation).

## Schnellstart

```bash
cd app-abacus-chat-backup && cp .env.example .env   # APP_BASIC_AUTH_USER/PASSWORD: beide oder keine
docker compose config -q                            # Compose-Datei pruefen (offline)
docker compose up -d --build                        # baut Frontend und Backend (benoetigt Netzwerk)
curl -fsS http://127.0.0.1:8080/api/health          # muss 200 mit status ok liefern
# Oberflaeche: http://127.0.0.1:8080 -- API-Schluessel unter "Settings" hinterlegen
```

Variante ohne Docker und Details: [09-build-deploy.md](09-build-deploy.md#lokales-setup--weg-2-ohne-docker).

## Stand

| Feld | Wert |
|---|---|
| Datum | 2026-07-30 |
| Git-Commit | `73f2b4103d11f6f18831959a3f97051f549d38e6` (`73f2b41`, 2026-07-22, „docs: RELEASE_README.md ergaenzt") |
| Branch | `main` |
| Arbeitsverzeichnis | **nicht sauber** — die Dokumentation beschreibt den Stand des Arbeitsverzeichnisses, nicht den des Commits. Geändert: `Dockerfile`, `compose.yaml`, `backend/app/main.py`, `.env.example`, `todo2026.md`; neu: `MONETARISIERUNGSBEWERTUNG.md`. Die Änderungen enthalten **sämtliche Sicherheitshärtungen** (unprivilegierter Benutzer, Loopback-Bindung, Security-Header, abgeschaltete `/docs`) |
| Projektversion | `1.0.0` (`backend/app/models.py:9`, `frontend/package.json:3`) |
| Tests | **Keine vorhanden.** Verifiziert wurden am 2026-07-30 stattdessen: AST-Parse aller zwölf Backend-Module (fehlerfrei) und `docker compose config -q` (gültig). Ein Image-Build unterblieb, weil er Netzwerkzugriff erfordert |
| Lizenz-Ampel | 🔴 — MIT-Lizenz im Widerspruch zur Zielvorgabe „proprietär", dazu nicht ermittelbare Backend-Lizenzen. Details in [11-sicherheit-compliance.md](11-sicherheit-compliance.md#lizenz-compliance-fazit) |

## Die drei wichtigsten Erkenntnisse

1. **Die Sicherheitshärtungen sind nicht eingecheckt.** Wer `73f2b41` deployt, bekommt einen root-Container mit offener API-Dokumentation, ohne Security-Header und mit LAN-weitem Portmapping — hinter dem vollständige Chatverläufe und der API-Schlüssel liegen.
2. **Drei Codepfade lassen ein Backup lautlos unvollständig werden:** die nach Seite 1 abbrechende Paginierung, der als Erfolg gezählte Timeout-Stub und die doppelt gezählten organisationsweiten Konversationen. Bei einem Backup-Werkzeug ist der stille Teilexport die gefährlichste Fehlerklasse.
3. **Der Umgang mit dem API-Schlüssel ist vorbildlich, die Ablage der Nutzdaten nicht.** Der Schlüssel wird zentral registriert und rekursiv aus jeder Datei und jeder Fehlermeldung geschwärzt — die gesicherten Chatverläufe selbst liegen unverschlüsselt und unbefristet im Volume, ohne Aufbewahrungsregel und ohne Möglichkeit, eine einzelne Konversation zu löschen.
