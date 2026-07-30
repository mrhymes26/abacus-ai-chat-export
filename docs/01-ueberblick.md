# 01 — Überblick · app-abacus-chat-backup

Allgemeinverständliche Einordnung: Zweck, Nutzen, typischer Anwendungsfall, Abgrenzung und Reifegrad.

[← Zurück zum Index](README.md)

## Worum es geht

Wer Abacus.AI nutzt, führt dort Chats — mit dem allgemeinen KI-Chat und mit einzelnen eigenen Deployments. Diese Verläufe lassen sich in der Weboberfläche von Abacus.AI nicht selbst exportieren; der einzige Weg an die eigenen Daten führt über die API (`CHANGELOG.md`, Abschnitt „Documentation" zum 1.0.0-Release). Dieses Werkzeug schließt genau diese Lücke: Es meldet sich mit einem API-Schlüssel bei Abacus.AI an, listet alle erreichbaren Konversationen auf, lädt sie vollständig herunter und legt sie als Dateisammlung im eigenen Speicher ab — als Rohdaten, als lesbares Transkript und als Datei zum Weiterverwenden in anderen Chat-Werkzeugen.

Der fachliche Kernnutzen in fünf Sätzen:

1. Die eigenen KI-Chatverläufe werden aus einem fremden Dienst herausgelöst und lokal gesichert.
2. Ein Backup-Lauf ist wiederholbar und läuft im Hintergrund, statt Chat für Chat von Hand kopiert zu werden.
3. Jede Sicherung enthält neben den Daten ein Protokoll darüber, was geladen wurde und wo etwas fehlte (`backend/app/backup_engine.py:196-214`).
4. Die Sicherung ist in vier Formaten gleichzeitig verfügbar, darunter ein druckfertiges Gesprächsprotokoll und ein Importformat für Open WebUI (`backend/app/models.py:12`).
5. Alles bleibt beim Betreiber: Es gibt keinen Cloud-Zwischenspeicher, keine Nutzerkonten und keinen Dienst, an den Daten weitergereicht werden (`compose.yaml:22-23`, `backend/app/config.py:59-67`).

## Wichtigste Funktionen

- **Verbinden mit Abacus.AI** über einen API-Schlüssel — wahlweise aus der Umgebung, aus einer lokal gespeicherten Datei oder direkt in der Oberfläche eingegeben (`backend/app/abacus_client.py:170-218`).
- **Konversationen auflisten** in zwei Kategorien: allgemeine KI-Chats (`ai_chat`) und Deployment-Konversationen (`deployment_conversation`); die Liste wird lokal zwischengespeichert (`backend/app/main.py:253-276`).
- **Suchbereiche automatisch ermitteln:** Deployment-IDs und External-Application-IDs werden bei Bedarf selbst über die API entdeckt, wenn der Betreiber sie nicht vorgibt (`backend/app/abacus_client.py:226-246`).
- **Backup-Job starten** für alle oder nur ausgewählte Konversationen; der Job läuft serverseitig weiter, die Oberfläche fragt den Fortschritt im Sekundentakt ab (`frontend/src/App.tsx:81-101`).
- **Vier Exportformate:** vollständige Rohdaten als JSON, Markdown-Transkript, HTML-Gesprächsprotokoll im Messenger-Layout mit A4-Druckaufbereitung, sowie Open-WebUI-Importdateien (`backend/app/backup_engine.py:110-172`).
- **Backup-Übersicht als HTML:** Jede Sicherung bekommt eine `index.html` mit Tabelle aller Chats und relativen Links auf die exportierten Dateien (`backend/app/exporters.py:566-717`).
- **ZIP-Paket** je Sicherung, auf Wunsch direkt beim Job oder später beim ersten Download erzeugt (`backend/app/main.py:321-333`).
- **Verlauf verwalten:** frühere Sicherungen auflisten, Manifest ansehen, herunterladen, löschen (`backend/app/main.py:307-345`).
- **Schlüssel wieder entfernen:** Ein lokal gespeicherter API-Schlüssel lässt sich über die Oberfläche löschen (`backend/app/main.py:237-240`).
- **Selbstkontrolle auf Vollständigkeit:** Meldet die API eine Gesamtzahl an Ereignissen, vergleicht das Werkzeug sie mit der Zahl tatsächlich geladener Einträge und schreibt eine Warnung ins Protokoll, wenn etwas fehlt (`backend/app/backup_engine.py:103-108`, `backend/app/exporters.py:120-138`).

## Typischer Anwendungsfall

Ein Nutzer hat über Monate mit mehreren Abacus.AI-Deployments gearbeitet und möchte die Gespräche sichern, bevor er ein Deployment abschaltet. Er startet den Container, öffnet die Oberfläche unter `http://127.0.0.1:8080`, hinterlegt unter **Settings** seinen API-Schlüssel und lässt ihn optional lokal speichern. In der Ansicht **Chats** klickt er auf Laden — das Werkzeug ermittelt selbst, welche Deployments und externen Anwendungen es gibt, und listet alle gefundenen Konversationen auf. Er wählt entweder alles oder einzelne Zeilen aus, hakt die gewünschten Formate an und startet den Export. Ein Fortschrittsbalken zeigt, welcher Chat gerade geladen wird; bleibt ein Abruf hängen, bricht das Werkzeug ihn nach 120 Sekunden ab, merkt sich den Eintrag und macht mit dem nächsten weiter (`backend/app/backup_engine.py:9,94-100`). Am Ende liegt unter **Backups** eine neue Sicherung mit ZIP-Download; nach dem Entpacken öffnet er `index.html` und klickt sich durch die Gespräche. Für die Einträge, die in den Timeout gelaufen sind, bietet die Oberfläche eine Schaltfläche **Retry timed-out items** an (`frontend/src/App.tsx:161-177`).

## Was das Projekt bewusst nicht tut

| Nicht enthalten | Beleg / Begründung |
|---|---|
| **Kein Mehrbenutzerbetrieb.** Es gibt kein Benutzerverzeichnis, keine Rollen, keine Sitzungen — nur optional ein einziges Basic-Auth-Paar | `backend/app/config.py:26-31`, `backend/app/main.py:87-100` |
| **Kein Zurückschreiben nach Abacus.AI.** Sämtliche SDK-Aufrufe sind lesend oder Export-Aufrufe; es gibt keinen Codepfad, der eine Konversation anlegt oder ändert | `backend/app/abacus_client.py:13-24` |
| **Keine Zeitsteuerung.** Es gibt keinen Cron, keinen Scheduler und keinen Auto-Backup-Modus; jeder Lauf wird von Hand angestoßen | kein Scheduler-Code im Backend; einziger Job-Einstieg ist `POST /api/export` (`backend/app/main.py:279-288`) |
| **Keine Aufbewahrungsregel und kein automatisches Aufräumen.** Sicherungen bleiben liegen, bis sie manuell gelöscht werden | `backend/app/main.py:336-345` ist der einzige Löschpfad; keine Retention-Logik im Repository |
| **Keine Verschlüsselung der Sicherungen.** Chats liegen im Klartext im Volume | `backend/app/exporters.py:81-85,245-249` schreiben unverschlüsselt |
| **Keine Volltextsuche in gesicherten Chats.** Die Oberfläche filtert nur die Liste der Konversationen nach Titel und Typ | `frontend/src/components/ChatTable.tsx:15-16` |
| **Keine Wiederherstellung in Abacus.AI hinein.** „Restore" bedeutet hier: Dateien aus dem ZIP lesen, nicht ein Zurückspielen in den Ursprungsdienst | siehe [10-betrieb.md](10-betrieb.md#backup-und-restore) |

## Reifegrad

**Einstufung: intern produktiv — für den Einzelplatzbetrieb geeignet, für den Netzbetrieb erst nach Härtung.**

Begründung aus dem Code:

| Kriterium | Befund | Beleg |
|---|---|---|
| Tests | **Keine.** Kein Testverzeichnis, keine Test-Abhängigkeit, kein Test-Runner. Ausgerechnet die risikoreichsten Teile — Paginierung, Nachrichtenerkennung, Markdown-Erzeugung — sind reine Funktionen und wären leicht testbar | keine `test`-Dateien im Repository; `backend/requirements.txt:1-4` ohne Testpaket |
| CI/CD | **Keine.** Weder `.github/workflows/` noch `.gitea/workflows/` existieren | Verzeichnisse fehlen |
| Fehlerbehandlung | **Überdurchschnittlich für die Job-Ebene:** je Item eigene Fehlerliste, Timeout-Schutz je SDK-Aufruf, Fortsetzen nach Einzelfehlern, unterbrochene Jobs werden beim Start als `failed` markiert | `backend/app/backup_engine.py:93-108,174-189`, `backend/app/database.py:70-87` |
| Logging | **Nur rudimentär.** Es gibt einen Logger, der aber ausschließlich den Auth-Status beim Start meldet; alle übrigen Vorgänge hinterlassen serverseitig keine Spur, zwei Pfade verschlucken Ausnahmen vollständig | `backend/app/main.py:55,127-132`; `except Exception: pass` in `main.py:223-224`, `except Exception: return` in `main.py:372-373` |
| Authentifizierung | **Vorhanden, aber standardmäßig aus.** Sind beide Basic-Auth-Variablen leer, ist die gesamte API offen; halb konfigurierte Auth bricht seit der jüngsten (noch nicht eingecheckten) Änderung beim Start ab | `backend/app/config.py:29-31`, `backend/app/main.py:87-100,115-132` |
| Migrationen | **Keine Schemaversionierung.** `init()` nutzt ausschließlich `CREATE TABLE IF NOT EXISTS`; nachträglich hinzugefügte Spalten würden auf bestehenden Datenbanken fehlen | `backend/app/database.py:17-58` |
| Reproduzierbare Abhängigkeiten | **Nur zur Hälfte.** Das Frontend hat ein vollständiges `package-lock.json`; das Backend hat **kein** Lockfile, nur Versionsbereiche | `frontend/package-lock.json` vorhanden, `backend/requirements.txt:1-4` |
| Betriebsreife | Healthcheck im Image und in Compose, unprivilegierter Benutzer, `no-new-privileges`, Security-Header, Loopback-Bindung — alles vorhanden, aber **im Arbeitsverzeichnis und nicht committet** | `Dockerfile:25-33`, `compose.yaml:9-11`, `backend/app/main.py:105-112`; `git status` zeigt diese Dateien als geändert |
| Dokumentation | `README.md`, `CHANGELOG.md`, `SECURITY.md`, `LICENSE`, `RELEASE_README.md` und ein detailliertes Review (`todo2026.md`) sind vorhanden | Dateien im Projektwurzelverzeichnis |

Kurz: Die Fachlogik ist für ein Werkzeug dieser Größe ungewöhnlich sorgfältig — insbesondere die durchgängige Schwärzung von Geheimnissen und die Selbstkontrolle auf Backup-Vollständigkeit. Was fehlt, ist die Absicherung drumherum: Tests, CI, Logging und ein eingecheckter Härtungsstand.

## Marker in diesem Dokument

Keine — alle Aussagen sind mit Fundstelle belegt.
