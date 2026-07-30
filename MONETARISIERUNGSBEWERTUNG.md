# Monetarisierungsbewertung — app-abacus-chat-backup

> Fokus: passives Einkommen · Stand: 2026-07-27
> Teil der Portfolio-Analyse in `../MONETARISIERUNG.md`

| | |
|---|---|
| **Passiv-Verdikt** | `TEIL-PASSIV` |
| **Passiver Umsatz p.a.** | 0–800 € |
| **Einmaliger Aufwand** | 15–25 PT (Auth verpflichtend, Retry/Backoff, Vollständigkeitsgarantie, Tests, Landingpage, Lizenzausgabe) |
| **Laufender Aufwand** | 2–4 h/Monat im Normalbetrieb — **aber sprunghaft 8–20 h**, sobald Abacus.AI das SDK oder die Paginierung ändert |
| **Wiederkehrender Fixkosten** | 50–150 €/Jahr (Domain, Landingpage-Hosting, Gumroad-/Paddle-Gebühren); optional 300–600 €/Jahr, falls je ein Windows-Installer signiert werden soll |

## Kurzurteil
Das ist das einzige Projekt der Gruppe, das man heute verkaufen dürfte — kein Rechtsblocker, ein lauffähiges Docker-Image, ein Dashboard, ein Changelog. Die härteste Wahrheit ist trotzdem: Der Zielkunde zahlt bereits ~10 $/Monat an Abacus.AI und hält Export für eine Selbstverständlichkeit, die im Abo enthalten sein sollte. Die Zahlungsbereitschaft für ein Backup-Add-on zu einem SaaS liegt erfahrungsgemäß nahe null, weil die Nutzererwartung „so etwas ist ein kostenloses GitHub-Repo" lautet. Passiv ist das Modell im Normalbetrieb tatsächlich — bis Abacus.AI eine SDK-Signatur ändert, dann kippt es für zwei Wochen in Vollzeitarbeit, ohne dass ein Cent zusätzlich hereinkommt. Und die aktuelle Codebasis hat genau die Fehlerklasse, die man bei einem Backup-Werkzeug nicht verkaufen darf: Es meldet Erfolg, wo es unvollständig gesichert hat.

## Was es ist
Self-hosted Backup- und Export-Manager für Abacus.AI-Chatkonversationen: FastAPI-Backend, React/Vite-Frontend, lokale SQLite, Docker-Compose. Der Nutzer verbindet sich per API-Key, wählt Konversations-Scopes, startet asynchrone Backup-Jobs, verfolgt den Fortschritt im Dashboard und exportiert nach JSON, Markdown, HTML und ZIP.

## Reifegrad
MVP mit produktnahen Einzelteilen. **Überdurchschnittlich:** Das Secret-Handling ist zentralisiert und konsequent — jeder API-Key wird bei Eintritt registriert und rekursiv aus Strings, Listen, Tupeln und Dict-Schlüsseln entfernt, auch aus Exception-Texten; die Key-Datei bekommt `chmod 0600`; die Basic-Auth vergleicht konstantzeitig. Es gibt **keine** CORS-Middleware und damit auch nicht das im Portfolio verbreitete `allow_origins=["*"]`, weil das Frontend same-origin ausgeliefert wird. Der Health-Endpoint macht einen echten, timeout-geschützten DB-Ping und ist als Docker-`HEALTHCHECK` verdrahtet. Die Backup-Engine schreibt die Anzahl geladener History-Einträge gegen die von der API gemeldete Gesamtzahl ins Manifest — eine echte Selbstkontrolle.

**Dagegen:** Null Tests, kein Logging (`import logging` kommt im gesamten Backend nicht vor, dafür stille `except: pass`-Pfade), keine CI. Basic-Auth ist per Default **aus**, während der Container an `0.0.0.0` bindet und Compose `"8080:8080"` ohne Interface-Präfix veröffentlicht — im Auslieferungszustand liegt der komplette Chatverlauf inklusive PII offen im LAN. Setzt man nur eine der beiden Auth-Variablen, bleibt die Auth still komplett deaktiviert. Kein Retry, kein Backoff, kein 429-Handling gegen die Abacus-API — und `try_call_variants` probiert im Fehlerfall alle Signaturvarianten durch, verstärkt die Last also ausgerechnet dann, wenn die API um Entlastung bittet. Zwei Pfade führen dazu, dass ein unvollständiges Backup als vollständig gilt: Bare-List-APIs werden nach Seite 1 abgeschnitten, und ein Timeout-Stub wird als Erfolg gezählt.

## Passiv-Tauglichkeit
**Teilweise passiv — mit einem konkreten, benennbaren Risiko, das die Passivität periodisch zerstört.**

**Was ohne Zutun Geld brächte:**
- Einmalkauf-Download eines Docker-Images plus `compose.yaml` über Gumroad/Lemon Squeezy. Kein Account, kein Server auf deiner Seite, keine Nutzerdaten bei dir, keine laufenden Betriebskosten pro Kunde. Der Kunde bringt seinen eigenen API-Key mit — das ist architektonisch die passivste denkbare Konstruktion und der eigentliche Trumpf dieses Projekts.
- Onboarding ist nahe null: `docker compose up`, Key eintragen, Job starten. Die Zielgruppe (Abacus-ChatLLM-Nutzer) kann Docker. Das ist der Grund, warum hier — anders als bei `_tool-outlook-rechnungen` — überhaupt „passiv" im Raum steht.

**Was Arbeit bleibt:**
- **Der Plattformbruch ist keine Möglichkeit, sondern ein Termin.** Das Produkt hängt vollständig am `abacusai`-SDK und an undokumentierten Paginierungs-Semantiken. Der Code enthält bereits eine Variantenschleife, weil sich Methodensignaturen unterscheiden — das ist der eingebaute Beweis, dass die Schnittstelle instabil ist. Jede Änderung bricht das Tool für alle Käufer gleichzeitig, und dann kommen alle Mails am selben Tag. Kalkuliere zwei bis drei solcher Ereignisse pro Jahr à 8–20 h.
- **Abacus.AI kann das Feature selbst bauen.** Ein Export-Button im eigenen Produkt macht dieses Tool über Nacht wertlos. Das ist kein hypothetisches Risiko — Export ist eine Standardanforderung, und der Anbieter hat die API bereits.
- **Support-Klasse „Backup".** Ein Kunde, dessen Backup unvollständig war, meldet sich nicht mit einer Frage, sondern mit einem Vorwurf — und zwar zu dem Zeitpunkt, an dem er das Backup braucht. Die drei Vollständigkeitslücken oben müssen **vor** dem ersten Verkauf geschlossen sein, sonst ist das kein Support, sondern Schadensbegrenzung.
- **Rechtstexte-Pflege:** AGB, Widerruf für digitale Inhalte, Datenschutzerklärung, Impressum. Einmal 1 PT, danach gelegentliche Nachpflege.
- **Rückerstattungen:** gering, weil das Produkt vor dem Kauf per Screenshot und Feature-Liste einschätzbar ist und keine Hardwareabhängigkeit hat.

**Was ausdrücklich nicht passiv wäre:** Ein gehostetes SaaS. Dafür müsste man fremde Abacus-API-Keys entgegennehmen und fremde Chatverläufe speichern — genau das, was die Zielgruppe vermeiden will, plus AV-Vertrag, Verfügbarkeitszusage und Ausfälle um 23 Uhr. Dieser Weg ist hier nicht nur unpassiv, sondern produktstrategisch falsch.

## Zielgruppe & Marktgröße
Abacus.AI-ChatLLM-Nutzer (~10 $/Monat/Seat), die Chatverläufe archivieren, migrieren oder aus Compliance-Gründen sichern wollen. Global vermutlich eine niedrige sechsstellige Nutzerbasis. Davon self-hosting-affin: ein niedriger Promillebereich. Zahlungsbereite, erreichbare Zielgruppe: **einige Hundert Personen weltweit** — und die muss man erst finden, denn es gibt keinen Kanal, auf dem sie versammelt sind (kein großes Subreddit, kein Forum mit Reichweite).

## Wettbewerb
- **Abacus.AI selbst** — bietet Export-Funktionen und eine offene API. Der stärkste Wettbewerber ist der Anbieter, dessen Lücke man füllt.
- **50 Zeilen Python.** Wer die API hat, löst das Kernproblem an einem Abend. Das ist der Preisanker: 0 €.
- **Generische Chat-Exporter:** `chatgpt-exporter`, diverse Browser-Extensions für ChatGPT/Claude/Gemini — durchweg kostenlos, teils mit Spendenlink.
- **Kommerziell existiert für diese Nische praktisch nichts.** Das ist ausdrücklich **kein** Signal für eine unentdeckte Lücke, sondern eines für fehlende Nachfrage: Wo Geld zu verdienen wäre, stünde längst jemand.

Preisniveau, gegen das man antritt: null. Der einzige Hebel ist Bequemlichkeit (Dashboard, Job-Fortschritt, vier Exportformate, Docker) — und Bequemlichkeit ist bei technischen Nutzern die am schlechtesten bezahlte Eigenschaft.

## Passiv-taugliche Erlösmodelle
- **Einmalkauf-Download, 15–29 €** (Gumroad/Lemon Squeezy/Paddle). Strukturell echt passiv. Realistisch 10–40 Verkäufe im ersten Jahr bei aktiver Sichtbarkeit, 0–5 ohne. → **0–800 €.**
- **Open-Core:** Kern als OSS auf GitHub, Pro-Modul (Scheduler, Verschlüsselung der Exporte, Retention, S3-Ziel) als bezahlter Zusatz. Passiv, erzeugt zusätzlich Sichtbarkeit — aber verdoppelt die Codebasis und damit den Pflegeaufwand. Realistisch nur, wenn das OSS-Repo Traktion bekommt.
- **GitHub Sponsors** auf ein OSS-Release: passiv, 0–100 €/Jahr.
- *Nicht passiv:* gehostetes SaaS (siehe oben), Individualanpassungen, Migrationsdienstleistung von Abacus zu einem anderen Anbieter.

## Blocker
- **Vertrieblich (Hauptblocker):** Zahlungsbereitschaft nahe null bei einer Zielgruppe, die Software als kostenlos erwartet, plus fehlender Vertriebskanal.
- **Strategisch:** Einzelabhängigkeit von einem Drittanbieter, der die API ändern oder die Funktion selbst nachbauen kann. Ein einziges Produktupdate bei Abacus entwertet das Produkt vollständig.
- **Technisch (verkaufsblockierend, muss vorher raus):** Drei Pfade, in denen ein unvollständiges Backup als vollständig gemeldet wird — stille Truncation bei APIs ohne Paginierungs-Metadaten, Timeout-Stub zählt als Erfolg, doppelte Exporte organisationsweiter Conversations. Bei einem Backup-Werkzeug ist das die einzig wirklich gefährliche Fehlerklasse. Dazu: kein Retry/Backoff/429-Handling bei gleichzeitiger Lastverstärkung im Fehlerfall.
- **Sicherheit (muss vor Auslieferung raus):** Basic-Auth per Default aus bei Bind auf `0.0.0.0` und Portmapping ohne Interface-Präfix; stilles Fail-open, wenn nur eine der beiden Auth-Variablen gesetzt ist; Container läuft als root; `/docs` offen; kein Rate-Limiting auf `/api/connect`, das fremde API-Keys gegen die Abacus-API testet.
- **Rechtlich:** Exportierte Chats liegen unverschlüsselt und unbefristet im Volume — keine Retention, keine Rotation. Als verkauftes Produkt braucht das mindestens einen dokumentierten Hinweis, besser eine konfigurierbare Aufbewahrungsfrist. Ansonsten: keine Lizenz-, Marken- oder ToS-Probleme — `LICENSE` und `SECURITY.md` sind vorhanden, der ausgehende Verkehr läuft ausschließlich über das offizielle SDK. **Das ist das einzige Projekt der Gruppe ohne Rechtsblocker.**

## Rechnung: Aufwand gegen Ertrag
15–25 PT einmalig (Opportunitätskosten 9.000–15.000 €), plus 2–4 h/Monat Grundlast und zwei bis drei Plattformbruch-Ereignisse à 8–20 h — zusammen **50–100 h/Jahr**. Fixkosten 50–150 €/Jahr. Erwarteter Umsatz: **0–800 € p.a.**

Bei optimistischen 800 € und 75 h Jahresaufwand liegt der Stundenlohn bei etwa 10 € — vor Abzug der 15–25 Entwicklungstage, die nie zurückkommen. Bei realistischen 200–300 € ist es ein Verlustgeschäft. **Amortisiert sich nicht** — auch nicht über mehrere Jahre, weil der laufende Aufwand nicht sinkt, während der Umsatz nach dem ersten Jahr typischerweise fällt.

Anders formuliert: Die 15–25 PT sind besser investiert, wenn sie das Tool für den Eigengebrauch sicher und vollständig machen, statt es verkaufbar zu machen.

## Fazit
**Liegenlassen — mit einer Ausnahme.** Als Produkt lohnt es nicht: Der Aufwand ist nicht groß, aber der Ertrag ist kleiner, und das Plattformrisiko hängt permanent darüber.

Falls es dennoch versucht werden soll, ist der einzig sinnvolle Weg **nicht** der Verkauf, sondern **Open Source auf GitHub mit Sponsors-Link** — Aufwand ca. 5 PT für die Sicherheitspunkte, danach kostet es nichts weiter und erzeugt Sichtbarkeit als Referenz. Ein Verkauf käme erst infrage, wenn das OSS-Repo messbare Traktion zeigt (dreistellige Sterne, Issues von Fremden); dann und nur dann lohnt ein Pro-Modul.

Der nächste Schritt in jedem Fall — auch für den reinen Eigengebrauch, Aufwand ca. 1 PT: Portmapping auf `127.0.0.1:8080:8080` ändern, beim Start ohne Auth eine deutliche Warnung ausgeben und bei halb gesetzter Auth-Konfiguration abbrechen, und die drei Vollständigkeitslücken schließen. Ein Backup, dem man nicht trauen kann, ist schlimmer als kein Backup.
