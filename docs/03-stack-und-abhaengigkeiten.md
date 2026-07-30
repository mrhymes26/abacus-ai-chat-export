# 03 — Stack und Abhängigkeiten · app-abacus-chat-backup

Laufzeitumgebungen, direkte Abhängigkeiten mit aufgelösten Versionen, Lizenzübersicht und Bewertung gegen `ZIEL_LIZENZ`.

[← Zurück zum Index](README.md)

## Laufzeitumgebungen

| Laufzeit | Version | Quelle |
|---|---|---|
| Python (Anwendung) | **3.11** (Debian-basiertes Slim-Image) | `Dockerfile:9` — `FROM python:3.11-slim` |
| Node.js (nur Build) | **20** (Debian Bookworm Slim) | `Dockerfile:1` — `FROM node:20-bookworm-slim AS frontend-build` |
| ASGI-Server | `uvicorn`, gestartet mit `--host 0.0.0.0 --port 8080` | `Dockerfile:35` |

Es gibt **keine** `.nvmrc`, kein `engines`-Feld in `frontend/package.json` und keine `python_requires`-Angabe. Die einzigen verbindlichen Versionsaussagen sind die beiden Basis-Images. Der lokale Entwicklungshost ist davon unabhängig; `README.md:35` nennt „Python 3.11+" und „Node.js 20+" als Anforderung.

> ⚠️ NICHT ERMITTELBAR — Quelle fehlt: Die genauen Patch-Versionen der Basis-Images (`python:3.11-slim`, `node:20-bookworm-slim`) und deren Digests. Beide Tags sind beweglich, und es liegt kein gebautes Image vor (`docker images` zeigt kein Abbild dieses Projekts). Ein Build würde `pip install` und `npm ci` und damit Netzwerkzugriff erfordern, was für diese Dokumentation ausgeschlossen ist.

## Backend

### Tabelle 1a — Direkte Abhängigkeiten Backend

Quelle: `backend/requirements.txt:1-4`. **Es existiert kein Lockfile** (kein `uv.lock`, kein `poetry.lock`, kein `requirements.lock`, kein `constraints.txt`), und im Repository liegt keine virtuelle Umgebung. Die folgenden Angaben sind deshalb Versions*bereiche*, keine aufgelösten Versionen.

| Paket | Bereich | Aufgelöste Version | Zweck im Projekt | Lizenz (SPDX) | Scope | Ersetzbarkeit |
|---|---|---|---|---|---|---|
| `fastapi` | `>=0.115,<1.0` | ⚠️ unbekannt | Web-Framework: alle 14 Routen, Request-Validierung über Pydantic-Modelle, die beiden `@app.middleware("http")`-Schichten, `StaticFiles`-Mount und `FileResponse` für ZIP-Downloads (`backend/app/main.py:10-11,59,87,105,434-436`) | MIT (nicht verifiziert) | prod | **schwer** — Routen, Abhängigkeitsinjektion und Pydantic-Integration durchziehen `main.py` vollständig |
| `uvicorn[standard]` | `>=0.30,<1.0` | ⚠️ unbekannt | ASGI-Server, einziger Prozesseinstieg des Containers. Das Extra `standard` zieht `uvloop`, `httptools`, `websockets`, `watchfiles`, `python-dotenv` und `PyYAML` nach | BSD-3-Clause (nicht verifiziert) | prod | **leicht** — austauschbar gegen jeden ASGI-Server (Hypercorn, Granian); der Aufruf steht an genau einer Stelle (`Dockerfile:35`) |
| `pydantic` | `>=2.7,<3.0` | ⚠️ unbekannt | Sämtliche Request-/Response-Verträge in `models.py`, inklusive `field_validator` zur Normalisierung von Scope-Listen und `Literal`-Typen für Formate und Job-Status (`backend/app/models.py:5,67-83,96-109`) | MIT (nicht verifiziert) | prod | **schwer** — 13 Modellklassen, tief in FastAPI verwoben |
| `abacusai` | `>=1.4` | ⚠️ unbekannt | Der einzige Zugang zu den Nutzdaten: `ApiClient` wird mit dem API-Key erzeugt (`backend/app/security.py:69-73`), zehn Methoden werden dynamisch genutzt (`backend/app/abacus_client.py:13-24`), zusätzlich wird `abacusai.api_class.enums.DeploymentConversationType` für Fallback-Scopes importiert (`backend/app/abacus_client.py:604-608`) | ⚠️ unbekannt | prod | **schwer** — es gibt keine dokumentierte REST-Alternative; ein Ersatz bedeutet, das komplette Adaptermodul gegen rohes HTTP neu zu schreiben |

**Auffällig:** `abacusai` ist die einzige Abhängigkeit **ohne Obergrenze**, und zugleich diejenige, die per Introspektion angesprochen wird. Genau diese Kombination bricht bei einem Major-Release nicht laut, sondern still: Signaturvarianten passen nicht mehr, `hasattr` liefert `False`, und das Backup bleibt leer statt zu scheitern (`backend/app/abacus_client.py:75-97,220-224`). Der Befund ist im projekteigenen Review als offener Punkt notiert (`todo2026.md`, Abschnitt „Niedrig", Eintrag zu `backend/requirements.txt:4`).

> ⚠️ NICHT ERMITTELBAR — Quelle fehlt: Alle vier aufgelösten Backend-Versionen. Es gibt kein Lockfile, keine eingecheckte virtuelle Umgebung und kein gebautes Image; `pip install` ist für diese Dokumentation ausgeschlossen. Die tatsächlich installierten Versionen hängen davon ab, wann das Image zuletzt gebaut wurde.

> ⚠️ NICHT ERMITTELBAR — Quelle fehlt: Der vollständige transitive Abhängigkeitsbaum des Backends inklusive Lizenzen. `abacusai` zieht erfahrungsgemäß einen umfangreichen Datenanalyse-Unterbau nach; ohne Installation lässt sich weder die Paketliste noch deren Lizenzverteilung belegen.

> ⚠️ NICHT ERMITTELBAR — Quelle fehlt: Die Lizenz von `abacusai`. Das Paket liegt lokal nicht vor, und Netzwerkabfragen sind ausgeschlossen. **Konsequenz gegen `ZIEL_LIZENZ` (proprietär):** Eine unbekannte Lizenz ist nach dem Bewertungsmaßstab 🔴 zu behandeln — sie kann ein Copyleft oder eine kommerzielle Nutzungsgrenze enthalten. **Handlungsoption:** Beim nächsten Build `pip show abacusai` bzw. die `METADATA` im Image auslesen und das Ergebnis hier nachtragen; bis dahin gilt das Projekt als nicht weitergabefähig.

## Frontend

### Tabelle 1b — Direkte Abhängigkeiten Frontend

Quelle: `frontend/package-lock.json` (`lockfileVersion: 3`, 182 Pakete im Baum). Die Versionen sind die **aufgelösten** Werte aus dem Lockfile, nicht die Bereiche aus `package.json`.

| Paket | Aufgelöste Version | Zweck im Projekt | Lizenz (SPDX) | Scope | Ersetzbarkeit |
|---|---|---|---|---|---|
| `react` | 18.3.1 | UI-Bibliothek; die gesamte Oberfläche ist eine Funktionskomponente mit Hooks, ohne Router und ohne State-Bibliothek (`frontend/src/App.tsx:1,39-101`) | MIT | prod | **schwer** — neun Komponenten und der gesamte Zustandsfluss |
| `react-dom` | 18.3.1 | Mountet die Anwendung per `createRoot` in `#root` (`frontend/src/main.tsx`) | MIT | prod | **schwer** — untrennbar von `react` |
| `lucide-react` | 0.468.0 | Icon-Set der Oberfläche, u. a. die vier Formatsymbole im Export-Panel (`frontend/src/components/ExportPanel.tsx:11-16`) | ISC | prod | **leicht** — reine Präsentation, ersetzbar durch Inline-SVG; senkt zugleich die Bundle-Größe |
| `vite` | 5.4.21 | Build-Werkzeug: erzeugt `frontend/dist/`; im Dev-Modus zusätzlich Proxy von `/api` auf `127.0.0.1:8080` (`frontend/vite.config.ts:6-11`) | MIT | dev | **mittel** — Ersatz möglich, erfordert aber neue Build- und Proxy-Konfiguration |
| `@vitejs/plugin-react` | 4.7.0 | JSX-Transformation und Fast Refresh im Vite-Build (`frontend/vite.config.ts:2,5`) | MIT | dev | **mittel** — an Vite gebunden |
| `typescript` | 5.9.3 | Typprüfung vor dem Build (`tsc -b && vite build`, `frontend/package.json:8`); `strict: true` (`frontend/tsconfig.json:10`) | **Apache-2.0** | dev | **mittel** — Aufgabe von TypeScript wäre ein Rückschritt, aber technisch möglich |
| `tailwindcss` | 3.4.19 | Sämtliches Styling erfolgt über Utility-Klassen direkt im JSX; es gibt keine eigenen CSS-Klassen außer in `index.css` | MIT | dev | **schwer** — jede Komponente ist vollständig in Tailwind-Klassen ausgedrückt |
| `postcss` | 8.5.13 | Verarbeitungskette für Tailwind und Autoprefixer (`frontend/postcss.config.js`) | MIT | dev | **leicht** — Infrastrukturbaustein von Tailwind |
| `autoprefixer` | 10.5.0 | Ergänzt Hersteller-Präfixe im erzeugten CSS | MIT | dev | **leicht** |
| `@types/react` | 18.3.28 | Typdefinitionen für React | MIT | dev | **leicht** |
| `@types/react-dom` | 18.3.7 | Typdefinitionen für React-DOM | MIT | dev | **leicht** |

Bemerkenswert: Die Laufzeitabhängigkeiten des Frontends bestehen aus genau **drei** Paketen. Alles Weitere ist Build-Werkzeug und landet nicht im ausgelieferten Bundle.

### Tabelle 2 — Lizenzübersicht über den gesamten Frontend-Abhängigkeitsbaum

Quelle: Auswertung des `license`-Feldes aller 182 Einträge in `frontend/package-lock.json`.

| Lizenz | Anzahl Pakete | Beispielpakete | Bewertung gegen `ZIEL_LIZENZ` (proprietär) |
|---|---|---|---|
| MIT | 165 | `react`, `react-dom`, `vite`, `tailwindcss`, `postcss`, `@babel/core` | 🟢 unkritisch — Weitergabe nur mit Lizenztext und Copyright-Vermerk |
| ISC | 11 | `lucide-react`, `anymatch`, `glob-parent`, `electron-to-chromium` | 🟢 unkritisch — funktional äquivalent zu MIT |
| Apache-2.0 | 4 | `typescript`, `baseline-browser-mapping`, `didyoumean`, `ts-interface-checker` | 🟢 unkritisch, **aber NOTICE-Pflicht bei Weitergabe** (§4 der Lizenz). Alle vier sind reine Build-Zeit-Pakete und landen nicht im Bundle |
| BSD-3-Clause | 1 | `source-map-js` | 🟢 unkritisch — Namensnennung im Begleitmaterial |
| CC-BY-4.0 | 1 | `caniuse-lite` | 🟡 **Namensnennungspflicht** bei Weitergabe der enthaltenen Browser-Datenbank. Build-Zeit-Paket, wird nicht mit ausgeliefert. **Handlungsoption:** NOTICE-Eintrag, falls das Repository je weitergegeben wird |

**Kein GPL, kein LGPL, kein AGPL, kein MPL, kein `unknown`, kein Dual-Licensing und keine kommerzielle Lizenz mit Nutzungsgrenze im gesamten Frontend-Baum.** Das ist ein sauberes Ergebnis; der einzige Handlungspunkt ist eine NOTICE-Datei für Apache-2.0 und CC-BY-4.0, und auch der nur im Fall einer Weitergabe.

## Eigene Lizenz des Projekts

Das Repository enthält eine **MIT-Lizenz** (`LICENSE:1-21`, Copyright 2026 „Abacus Backup Chat Export Manager contributors"). Das steht in direktem Widerspruch zu `ZIEL_LIZENZ` = *proprietär / nicht zur Weitergabe*: MIT erlaubt jedem Empfänger ausdrücklich Nutzung, Änderung, Weitergabe und Unterlizenzierung. **Konsequenz:** Wer eine Kopie erhält, darf sie legal weiterverbreiten und kommerziell verwerten. **Handlungsoption:** Entweder die Zielvorgabe für dieses Projekt bewusst auf „offen" korrigieren — dazu passt, dass `SECURITY.md:11` von GitHub Security Advisories und öffentlichem Repository ausgeht — oder die `LICENSE` durch einen proprietären Text ersetzen und den README-Verweis (`README.md:132-134`) anpassen. Die Entscheidung gehört dokumentiert, nicht implizit gelassen.

## Veraltete und ungepflegte Pakete

> ⚠️ NICHT ERMITTELBAR — Quelle fehlt: Release-Daten der Pakete. Ein Lockfile enthält keine Zeitstempel, und Abfragen der Registry sind für diese Dokumentation ausgeschlossen. Die Prüfung „letzter Release älter als 24 Monate" lässt sich damit nicht belegen.

Belegbar ist stattdessen der **Stand der Major-Linien**:

| Paket | Aufgelöste Version | Beobachtung | Beleg |
|---|---|---|---|
| `react` / `react-dom` | 18.3.1 | 18.3.x ist die letzte Version der 18er-Linie; die 19er-Linie existiert und wird nicht genutzt | `frontend/package-lock.json`, `frontend/package.json:13-14` |
| `vite` | 5.4.21 | Aktuellster Stand der 5.x-Linie. Das projekteigene Review ordnet diese Linie als nicht mehr patchgepflegt ein und empfiehlt den Sprung auf eine neuere Major-Version | `todo2026.md`, Abschnitt „Niedrig", Eintrag zu `frontend/package.json:6-8,20` |
| `tailwindcss` | 3.4.19 | 3.x-Linie; die 4er-Linie mit anderer Konfigurationsform wird nicht genutzt | `frontend/package-lock.json` |

Praktische Einordnung zur Vite-Frage: Vite dient hier **ausschließlich dem Build**. Das Produktivartefakt ist statisches HTML/JS, das FastAPI ausliefert — der Vite-Dev-Server läuft im Container nie. Relevant bleibt, dass die Skripte `dev` und `preview` explizit auf `0.0.0.0` binden (`frontend/package.json:7,9`), was auf einem Entwicklungsrechner die Vorbedingung der bekannten Dev-Server-Schwachstellen dieser Familie erfüllt.

## Schwachstellen-Scan

**Nicht durchgeführt.** Weder `syft` noch `grype` sind auf dem Host verfügbar (`docs/_doc-spec.md`, Abschnitt „Verfügbare Toolchain"), und `npm audit` bzw. `pip-audit` würden Netzwerkzugriff erfordern. Es wird hier folglich **keine** Aussage über bekannte CVEs getroffen — weder positiv noch negativ.

## Marker in diesem Dokument

- ⚠️ NICHT ERMITTELBAR — Patch-Versionen und Digests der beiden Basis-Images (kein gebautes Image, Build netzwerkgebunden)
- ⚠️ NICHT ERMITTELBAR — aufgelöste Versionen der vier Backend-Abhängigkeiten (kein Python-Lockfile)
- ⚠️ NICHT ERMITTELBAR — transitiver Abhängigkeitsbaum des Backends inklusive Lizenzen
- ⚠️ NICHT ERMITTELBAR — Lizenz von `abacusai` (🔴-Bewertung bis zur Klärung)
- ⚠️ NICHT ERMITTELBAR — Release-Daten zur Beurteilung ungepflegter Pakete
