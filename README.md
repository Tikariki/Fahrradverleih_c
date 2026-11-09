# RadVerleih – eigenständiges Fahrradverleihsystem

Abgabe zu **Aufgabe c)**. Ein vollständiges Verleihsystem für Fahrräder, das
unabhängig vom Ski-Projekt installiert, gestartet und getestet werden kann. Die
Architektur orientiert sich an Aufgabe a) und b) (Schichtentrennung, zentrale
Preisberechnung), der fachliche Kern ist jedoch eigenständig: Fahrräder,
Rahmenhöhen, Radtypen und E-Bike-Aufschläge.

## Funktionen

**Fahrräder verwalten**

- Fahrräder anlegen, bearbeiten und löschen
- Felder je Fahrrad: Radtyp (City, Mountain, Rennrad, E-Bike), Rahmengröße
  (XS–XL), optional Helm inklusive
- Kategorien (Standard, Premium, Kinder) mit eigener Preiswirkung
- Löschen wird bei vorhandener Verleihhistorie zu Deaktivieren, damit alte
  Vorgänge nachvollziehbar bleiben

**Verfügbarkeit und Verleih**

- Status je Rad: verfügbar, verliehen, deaktiviert
- Verfügbarkeitsprüfung für einen Zeitraum (`GET /api/items/available`)
- Verleihbeginn als Datum, Verleihdauer in Tagen
- Doppelverleihungen werden abgelehnt
- Rückgabe verbuchen, überfällige Vorgänge automatisch markiert
- Verleihhistorie pro Fahrrad und pro Kunde

**Kunden und Ausweise**

- Vorname, Nachname, E-Mail, Telefon
- Ausweis mit Typ und Nummer, optional als Scan oder Foto (JPG, PNG, PDF, 5 MB)
- vier Ausweistypen: Personalausweis, Reisepass, Führerschein, Studentenausweis
- ohne hinterlegten Ausweis lehnt das System den Verleih ab

**Dashboard**

- Kennzahlen: verliehen, verfügbar, aktive Vorgänge, Einnahmen (Tag/Monat/gesamt)
- anstehende Rückgaben der nächsten sieben Tage, überfällige Vorgänge markiert
- Bestandsverteilung, Verwaltung von Rädern, Kunden und Vorgängen
- Live-Preisvorschau beim Anlegen eines Verleihs

## Preisgestaltung

Die Preisberechnung ist zentral und modular: eine Kette unabhängiger Regeln,
sortiert nach Priorität. Preise entstehen nur in `app/pricing/service.py`.

| Priorität | Regel | Wirkung |
|---|---|---|
| 10 | `duration` | Tagespreis × Dauer, ab 4 Tagen −10 %, ab 7 Tagen −20 % |
| 30 | `bike_ebike_surcharge` | E-Bike: +20 % auf den Grundpreis |
| 40 | `category` | Premium +15 %, Kinder −10 % auf den Zwischenstand |

Beispiel: E-Bike, 45,00 € pro Tag, 7 Tage
`315,00 − 20 % = 252,00 + 20 % = 302,40 €`

Staffel und Kategorie-Zuordnung sind Konstruktorparameter und ohne
Codeänderung anpassbar. Der festgeschriebene Preis eines Verleihs bleibt von
späteren Regeländerungen unberührt.

## Schnellstart

Voraussetzung: Python 3.11 oder neuer.

**Windows (PowerShell oder VS-Code-Terminal)**

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/seed_demo.py
python run.py
```

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/seed_demo.py
python run.py
```

Danach im Browser:

- Dashboard: <http://127.0.0.1:8000>
- API-Dokumentation: <http://127.0.0.1:8000/docs>

Das Projekt läuft standardmäßig auf Port 8000. Wenn parallel zum Ski-Projekt
gestartet, vorher `PORT` ändern oder das andere Projekt beenden – beide nutzen
denselben Port.

`scripts/seed_demo.py` legt neun Fahrräder, vier Kunden und acht Verleihvorgänge
an. Der Seed bricht ab, wenn die Datenbank bereits Gegenstände enthält.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

68 Tests decken Preisberechnung (inklusive E-Bike-Aufschlag), Verleih- und
Rückgabeprozesse, Verfügbarkeit, Kunden- und Ausweisverwaltung sowie die
HTTP-Schnittstelle ab.

## Projektstruktur

```
.
├── app/
│   ├── main.py            App-Factory, zentrale Fehlerbehandlung, Dashboard-Route
│   ├── server.py          ASGI-Einstiegspunkt (uvicorn app.server:app)
│   ├── container.py       Composition Root: verdrahtet alle Implementierungen
│   ├── config.py          Pfade und Einstellungen (über Umgebungsvariablen)
│   ├── domain/            Entitäten, Wertobjekte, fachliche Fehler, Geldrechnung
│   ├── pricing/           Preisregeln und Preisdienst
│   ├── plugins/           Verleihart "bike" und Ausweistypen als Module
│   ├── services/          Geschäftslogik: items, customers, rentals, dashboard
│   ├── repositories/      SQLite-Zugriff, Schema
│   ├── api/               HTTP-Routen und Transport-Schemata
│   ├── templates/         Dashboard (Jinja2)
│   └── static/            CSS und JavaScript des Dashboards
├── tests/                 pytest-Suite
├── scripts/seed_demo.py   Beispieldaten
├── docs/architecture.md   Architekturbeschreibung
├── run.py                 Startskript
├── requirements.txt       Laufzeitabhängigkeiten
└── CLAUDE.md              Projekt- und Entwicklungsrichtlinien
```

## Architektur in Kürze

```
api (HTTP) ──▶ services ──▶ domain
                   │
                   ├──▶ repositories ──▶ SQLite
                   └──▶ pricing ◀── plugins (Verleihart "bike")
```

- **domain** enthält keine Infrastruktur und kein HTTP.
- **pricing** kennt nur `PriceRequest`/`PriceState`; Regeln liefern Positionen.
- **services** orchestrieren Verfügbarkeit, Preis, Persistenz und Regeln.
- **api** ist eine dünne Fassade und übersetzt fachliche Fehler in HTTP-Codes.
- **container.py** ist der einzige Ort, an dem konkrete Klassen entstehen.

Details: [docs/architecture.md](docs/architecture.md)

## API-Überblick

| Methode | Pfad | Zweck |
|---|---|---|
| GET | `/api/meta` | Verleihtyp, Ausweistypen, Preisregeln |
| GET | `/api/dashboard` | Kennzahlen für das Dashboard |
| GET | `/api/items` | Fahrräder (`include_inactive`, `type_key`) |
| GET | `/api/items/available` | freie Räder (`start`, `days`) |
| POST | `/api/items` | Fahrrad anlegen |
| PUT | `/api/items/{id}` | Fahrrad bearbeiten |
| DELETE | `/api/items/{id}` | löschen bzw. deaktivieren |
| GET | `/api/customers` | Kunden |
| POST | `/api/customers` | Kunde anlegen |
| POST | `/api/customers/{id}/document` | Ausweis hinterlegen (multipart) |
| GET | `/api/rentals` | Vorgänge (`status`, `item_id`, `customer_id`, `limit`) |
| POST | `/api/rentals` | Verleih anlegen |
| POST | `/api/rentals/quote` | Preis berechnen ohne Buchung |
| POST | `/api/rentals/{id}/return` | Rückgabe verbuchen |

Fachliche Fehler kommen als JSON: `{"error": "item_unavailable", "message": "..."}`
mit passendem Status (404, 409, 422).

## Konfiguration

| Variable | Standard | Bedeutung |
|---|---|---|
| `RENTAL_DATA_DIR` | `./data` | Ablage für Datenbank und Uploads |
| `RENTAL_DB_PATH` | `<data>/rental.db` | Pfad der SQLite-Datei |
| `RENTAL_UPLOAD_DIR` | `<data>/uploads` | Ziel für Ausweis-Scans |
| `RENTAL_PLUGIN_PATHS` | leer | zusätzliche Verleihart-Module |
| `RENTAL_CURRENCY` | `EUR` | Währungskennzeichen für die Anzeige |

## Bewusste Entscheidungen und Grenzen

- **SQLite statt Server-Datenbank**: keine Installation nötig, ein File,
  ausreichend für einen Verleihschalter; Wechsel wäre auf `repositories/`
  begrenzt.
- **Server-gerendertes Dashboard mit Vanilla JS**: kein Build-Schritt, keine
  Toolchain-Abhängigkeit.
- **Kein Login**: internes Werkzeug der Verleihstation.
- **Kein Zahlungsverkehr**: Einnahmen werden aus den Verleihbeträgen berechnet.
- **Eigene Datenbank**: Das Projekt nutzt `data/rental.db` in seinem eigenen
  Verzeichnis und ist damit unabhängig vom Ski-Projekt.
