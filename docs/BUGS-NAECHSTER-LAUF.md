# Kritische Bugs für den nächsten Lauf · app-abacus-chat-backup

Stand: 2026-10-12 · Commit 9cac29d · Branch main
Geprüft: Backend `backend/app/` – `backup_engine.py`, `abacus_client.py`, `main.py`, `jobs.py`, `database.py`, `security.py`, `config.py`, `local_settings.py`, `utils.py`, aus `exporters.py` die Datenumwandlung (`to_plain_data`), Schreibfunktionen, ZIP-Erzeugung und Link-Darstellung; `compose.yaml` · Nicht geprüft: Markdown-/HTML-Darstellung in `exporters.py` im Detail (ca. 700 Zeilen), `models.py` nur in Auszügen, gesamtes React-Frontend, kein Aufruf gegen die echte Abacus.AI-API (SDK `abacusai` lokal nicht installiert), kein Docker-Build · Tests ausgeführt: keine Testsuite vorhanden; Syntaxprüfung (`ast.parse`) aller Backend-Dateien grün; Prüfskript im Scratchpad mit System-Python 3.14 und SDK-Attrappe (Paginierung, Auflistungsfehler, Aufrufvarianten, Schwärzung)

## Übersicht

| ID | Schwere | Titel | Fundstelle | Beleg | Aufwand |
|---|---|---|---|---|---|
| BUG-01 | hoch | Auflistung endet still an Obergrenzen – ältere Chats fehlen im Backup (bekannt, offen) | `backend/app/abacus_client.py:113-147,378,435` | ausgeführt | M |
| BUG-02 | hoch | Fehler beim Auflisten werden verschluckt – Job endet als „completed“ mit 0 oder zu wenigen Chats | `backend/app/abacus_client.py:262-273,448-455`, `backend/app/backup_engine.py:78-79,243-256` | ausgeführt | S |
| BUG-03 | hoch | Jeder an `/api/connect` gesendete Wert wird als Geheimnis geschwärzt – auch in allen späteren Exporten | `backend/app/security.py:54-58,69-82`, `backend/app/main.py:190-211` | ausgeführt | S |
| BUG-04 | hoch | Ausweichvarianten rufen eine Deployment-Konversation ohne Konversations-ID ab | `backend/app/abacus_client.py:75-110,648-680` | Verdacht (Aufrufmuster ausgeführt) | S |

## BUG-01 · Auflistung endet still an Obergrenzen

- **Schwere:** hoch
- **Fundstelle:** `backend/app/abacus_client.py:113-147` (`iter_paginated_results`), `backend/app/abacus_client.py:435` (`"limit": 600`), `backend/app/abacus_client.py:378,385,412` (`max_pages=1`, `projects[:100]`)
- **Was passiert:** Liefert eine SDK-Methode eine nackte Liste ohne `page_token` oder `has_more`, endet die Schleife nach dem ersten Aufruf. Deployment-Konversationen werden mit `limit: 600` angefragt; mehr als 600 je Geltungsbereich kommen nie an. Dieselbe stille Grenze gilt bei 50 Seiten mit Token, bei Projekten (eine Seite, höchstens 100) und bei externen Anwendungen (eine Seite). Es entsteht weder eine Warnung noch ein Eintrag im Manifest.
- **Auslöser / Reproduktion:** Prüfskript: Attrappe mit 1.500 Konversationen, die wie das SDK eine Liste bis `limit` zurückgibt → `iter_paginated_results` liefert 600.
- **Auswirkung:** Das Backup ist unvollständig, meldet aber Erfolg; betroffen sind die ältesten Konversationen.
- **Beleg:** ausgeführt (Scratchpad gegen `iter_paginated_results`) · bekannter P1-Punkt, am aktuellen Code bestätigt
- **Fix-Vorschlag:** Bei nackter Liste weiterblättern, solange `len(page) == limit` (Versatz oder Zeitstempel als Fortsetzung, soweit das SDK es zulässt). Wird eine Grenze erreicht (`limit`, `max_pages`, `[:100]`), eine Warnung erzeugen, die im Job und im Manifest landet (siehe BUG-02 für den Transportweg), und den Job als „mit Vorbehalt“ kennzeichnen.
- **Aufwand / Risiko des Fixes:** M · mittel (Fortsetzungsparameter des SDK müssen geprüft werden)
- **Test, der den Fix belegt:** Unit-Test mit Attrappe: 1.500 Einträge, `limit` 600 → 1.500 geliefert; Attrappe ohne Fortsetzungsmöglichkeit → 600 geliefert und Warnung „Obergrenze erreicht“.
- **Abhängigkeiten:** Braucht das installierte SDK `abacusai` bzw. dessen Signaturen; Abnahme gegen ein Konto mit mehr als 600 Konversationen.

## BUG-02 · Fehler beim Auflisten werden verschluckt

- **Schwere:** hoch
- **Fundstelle:** `backend/app/abacus_client.py:262-273` (KI-Chats), `backend/app/abacus_client.py:448-455` (Deployment-Konversationen je Geltungsbereich), `backend/app/backup_engine.py:78-79` und `243-256` (`_resolve_items`)
- **Was passiert:** `list_all_chats` fängt jeden Fehler der Auflistung ab und legt ihn nur in `last_warnings` ab. `_resolve_items` wertet `last_warnings` nicht aus. Der Job läuft mit der unvollständigen oder leeren Liste weiter und endet mit Status `completed`, `failed: 0`; `errors` und `manifest.json` enthalten keinen Hinweis.
- **Auslöser / Reproduktion:** Prüfskript: Attrappe, deren `list_chat_sessions` „503 Service Unavailable“ wirft; `run_backup_job` mit `mode=all`, `types=["ai_chat"]` → Status `completed`, Fortschritt `total 0, failed 0, percent 100`, `errors: []`, Manifest ohne Fehler; die Warnung steht nur im Dienstobjekt.
- **Auswirkung:** Ein Backup „aller Chats“ kann leer oder um ganze Bereiche gekürzt sein und sieht in Oberfläche und Manifest wie ein erfolgreicher Lauf aus.
- **Beleg:** ausgeführt (Scratchpad, `run_backup_job` gegen temporäres Datenverzeichnis)
- **Fix-Vorschlag:** `list_all_chats` gibt Warnungen zusammen mit den Einträgen zurück (oder `_resolve_items` liest `last_warnings` unmittelbar nach dem Aufruf). Der Job übernimmt sie in `errors`, in `manifest["errors"]` und in ein neues Feld `listing_incomplete`; bei mindestens einem Auflistungsfehler endet der Job mit Status `failed` bzw. einem eigenen Status „unvollständig“ statt `completed`.
- **Aufwand / Risiko des Fixes:** S · niedrig
- **Test, der den Fix belegt:** pytest mit SDK-Attrappe: Auflistungsfehler → Jobstatus nicht `completed`, Fehlertext in `errors` und im Manifest.
- **Abhängigkeiten:** keine

## BUG-03 · Jeder an `/api/connect` gesendete Wert wird als Geheimnis geschwärzt

- **Schwere:** hoch
- **Fundstelle:** `backend/app/security.py:69-73` (`create_client` registriert vor jeder Prüfung), `backend/app/security.py:54-58` (`register_secret`), `backend/app/security.py:76-82` (`redact_secrets_from_text`), `backend/app/main.py:190-211` (`POST /api/connect`), Anwendung der Schwärzung in `backend/app/exporters.py:42-49,89-93`
- **Was passiert:** `create_client` trägt den übergebenen Schlüssel in die prozessweite Schwärzungsliste ein, bevor das SDK ihn prüft. Es gibt keine Mindestlänge und kein Entfernen bei abgelehntem Schlüssel. Jeder Export ersetzt danach jedes Vorkommen dieses Werts durch `[REDACTED_SECRET]` – in Texten, in Schlüsselnamen und in IDs, bis zum Neustart.
- **Auslöser / Reproduktion:** Im Verbindungsdialog versehentlich etwas anderes als den Schlüssel einfügen oder abschicken (ein Wort, eine E-Mail-Adresse, eine ID). Prüfskript: `connect_with_fallback(api_key="er")` schlägt fehl; anschließend schreibt `write_json` aus „Der Server meldet einen Fehler.“ den Text „D[REDACTED_SECRET] S[REDACTED_SECRET]v[REDACTED_SECRET] meldet einen Fehl[REDACTED_SECRET].“ und aus `"role": "user"` wird `"us[REDACTED_SECRET]"`.
- **Auswirkung:** Stille Verfälschung aller danach erzeugten Backups (JSON, Markdown, HTML, Open-WebUI-Import), ohne Fehlermeldung; der Job endet als Erfolg.
- **Beleg:** ausgeführt (Scratchpad; ohne installiertes SDK scheitert der Verbindungsaufbau am Import, die Registrierung steht in `create_client` aber in der ersten Zeile und damit vor jeder SDK-Prüfung)
- **Fix-Vorschlag:** Schlüssel erst nach erfolgreichem Verbindungsaufbau registrieren; in `register_secret` Werte unter einer Mindestlänge (z. B. 20 Zeichen) nie aufnehmen; abgelehnte Schlüssel wieder entfernen. Zusätzlich im Manifest die Zahl der vorgenommenen Schwärzungen ausweisen, damit eine ungewöhnliche Häufung auffällt.
- **Aufwand / Risiko des Fixes:** S · niedrig
- **Test, der den Fix belegt:** pytest: fehlgeschlagener Verbindungsversuch mit kurzem Wert → anschließender `write_json` gibt den Text unverändert aus; erfolgreicher Verbindungsaufbau mit langem Schlüssel → Schlüssel wird geschwärzt.
- **Abhängigkeiten:** keine

## BUG-04 · Ausweichvarianten rufen eine Deployment-Konversation ohne Konversations-ID ab

- **Schwere:** hoch
- **Fundstelle:** `backend/app/abacus_client.py:75-110` (`call_with_supported_kwargs`, `try_call_variants`), `backend/app/abacus_client.py:648-680` (Variantenlisten)
- **Was passiert:** `try_call_variants` probiert bei jedem Fehler die nächste Variante. `call_with_supported_kwargs` streicht Parameter, die die SDK-Methode nicht kennt. Bei Varianten wie `{deployment_id, deploymentConversationId, limit, …}` bleibt nach dem Streichen nur `deployment_id` (plus Optionen) übrig – der Aufruf erfolgt ohne Konversations-ID. Die erste erfolgreiche Antwort wird übernommen und unter Titel und Dateiname des eigentlich angefragten Chats gespeichert.
- **Auslöser / Reproduktion:** Vorübergehender Fehler (Zeitüberschreitung, 5xx, 429) bei den ersten vier Aufrufen einer Konversation mit `deployment_id`. Prüfskript mit Attrappe in SDK-Signatur: Aufrufe 1–4 mit `deployment_conversation_id="conv-123"`, Aufruf 5 mit `deployment_conversation_id=None, deployment_id="dep-1"`; dessen Antwort wird als Ergebnis akzeptiert.
- **Auswirkung:** Falls die echte API einen Aufruf nur mit `deployment_id` beantwortet, landet der Inhalt einer anderen Konversation unter dem Namen der angefragten im Backup. Lehnt die API solche Aufrufe ab, bleibt es bei unnötigen Folgeaufrufen (bekannter Punkt „Lastverstärkung“, Schuld 7).
- **Beleg:** Verdacht (fehlt: Verhalten der echten Abacus.AI-API bei `get_deployment_conversation` ohne Konversations-ID) · das Aufrufmuster selbst ist ausgeführt
- **Fix-Vorschlag:** In `call_with_supported_kwargs` nie aufrufen, wenn dabei der ID-Parameter der Variante gestrichen würde (Pflichtschlüssel je Variante mitgeben). Antwort vor der Übernahme prüfen: die zurückgegebene Konversations-ID muss der angefragten entsprechen. Nur bei Signaturfehlern zur nächsten Variante wechseln, nicht bei Netz- oder Serverfehlern.
- **Aufwand / Risiko des Fixes:** S · niedrig
- **Test, der den Fix belegt:** pytest mit Attrappe: nach Fehlern der ersten Variante erfolgt kein Aufruf ohne Konversations-ID; eine Antwort mit fremder ID wird verworfen und als Fehler des Eintrags geführt.
- **Abhängigkeiten:** Bestätigung des API-Verhaltens braucht einen gültigen Schlüssel.

## Hinweise unterhalb der Schwelle (nicht als Bug geführt)

- `backend/app/backup_engine.py:78`: Die Auflistung läuft ohne Zeitgrenze (`_call_with_timeout` umschließt nur Detail- und HTML-Abruf); hängt der Aufruf, bleibt der Job dauerhaft auf „running“.
- Bekannt und offen laut `PROJEKTSTAND.md`: kein Retry/Backoff (Schuld 7), doppelte Exporte organisationsweiter Konversationen (Schuld 13), unverschlüsselte Backups ohne Aufbewahrungsgrenze (Schuld 3), verwaiste Teil-Backups (Schuld 11), Anmeldung standardmäßig aus bei Loopback-Bindung (Schuld 2).

## Bekannte Befunde, die inzwischen behoben sind

- Executor wird in `finally` heruntergefahren (`backend/app/backup_engine.py:14-28`, Commit `cf227a3`).
- Einträge mit Zeitüberschreitung oder Fehler beim Detailabruf zählen als fehlgeschlagen (`backend/app/backup_engine.py:93-97,177-178`, Commit `cf227a3`).
- Basic-Auth vergleicht UTF-8-Bytes (`backend/app/security.py:101-114`, Commit `cf227a3`).
- Mehrfach referenzierte Objekte werden vollständig exportiert (`backend/app/exporters.py:57-66`, Commit `cf227a3`).
- Halb konfigurierte Anmeldung bricht den Start ab (`backend/app/main.py:115-132`), interaktive API-Dokumentation ist aus (`backend/app/main.py:59`), Port nur an Loopback (`compose.yaml:9`).
