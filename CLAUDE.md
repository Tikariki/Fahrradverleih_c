# CLAUDE.md – Projekt- und Entwicklungsrichtlinien

Verbindliche Kurzreferenz für die Arbeit in diesem Repository (Aufgabe c).

## Was ist das Projekt

Ein eigenständiges Fahrradverleihsystem mit flexibler Preisgestaltung.

- Backend: Python 3.11+, FastAPI, SQLite (Standardbibliothek `sqlite3`)
- Frontend: Jinja2-Template plus Vanilla JavaScript, kein Build-Schritt
- Tests: pytest
- Sprache im Code: Bezeichner englisch, Fachbegriffe und Texte deutsch

## Befehle

```bash
# Umgebung
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# Starten
python run.py                      # http://127.0.0.1:8000
# alternativ: uvicorn app.server:app --reload

# Beispieldaten
python scripts/seed_demo.py

# Tests
pytest                             # gesamte Suite
pytest tests/test_pricing.py -q    # einzelne Datei
```

Die Datenbank liegt unter `data/rental.db` und ist nicht versioniert. Für einen
frischen Stand `data/` löschen und den Seed erneut ausführen.

## Architekturregeln

Die Abhängigkeiten zeigen nach innen:

```
api ──▶ services ──▶ domain
          │
          ├──▶ repositories (SQLite)
          └──▶ pricing ◀── plugins (Verleiharten)
```

- `app/domain/` kennt weder FastAPI noch SQL noch Dateien.
- `app/api/` enthält keine Fachlogik: Request lesen, Service aufrufen,
  Ergebnis serialisieren.
- `app/services/` orchestriert. Preise entstehen ausschließlich im
  `PricingService`, nie in einem Service oder einer Route.
- `app/repositories/` bildet Domänenobjekte auf SQL ab, keine Fachlogik.
- `app/container.py` ist der einzige Ort, an dem konkrete Klassen instanziiert
  werden.
- Die Verleihart liegt als Modul unter `app/plugins/builtin/bike.py` und wird
  über die Registry eingebunden. Der Kern kennt keine konkreten Typen.

## Geld und Daten

- Beträge sind `Decimal` mit zwei Nachkommastellen, gespeichert als ganzzahlige
  Cent (`app/domain/money.py`). Niemals `float` für Geld.
- Rundung immer über `money()`, `percent_of()` oder `to_cents()`.
- Datumswerte: `date` in der Domäne, ISO-Strings (`JJJJ-MM-TT`) in DB und API.

## Wie erweitere ich was

| Ziel | Ort | Vorgehen |
|---|---|---|
| Neuer Verleihtyp | `app/plugins/builtin/` | `RentalItem`-Unterklasse + `RentalPlugin`, im Modul `PLUGIN = ...` exportieren |
| Neue Preisregel | `app/pricing/rules.py` oder als Plugin | von `PricingRule` erben, `key`, `priority`, `apply()` implementieren |
| Neuer Ausweistyp | `app/plugins/builtin/identity.py` | Eintrag in `id_document_types()` |
| Neue API-Route | `app/api/routes_*.py` + Service | Route bleibt dünn, Logik in den Service |
| Neue Kennzahl | `app/services/dashboard.py` | im `stats()`-Dict ergänzen und im Frontend rendern |
| Neue Tabelle/Spalte | `app/repositories/schema.sql` | Schema ist idempotent, keine Migrationen im Projekt |

## Konventionen im Code

- Typannotationen wo sinnvoll, `from __future__ import annotations` ist gesetzt.
- Fachliche Fehler: `app/domain/errors.py` (`ValidationError`, `NotFoundError`,
  `ConflictError`, `ItemUnavailableError`). Sie tragen ihren HTTP-Status, die
  API-Schicht fängt sie zentral in `app/main.py`.
- Keine `print`-Ausgaben im Anwendungscode. Ausnahme: `scripts/`.
- Docstrings auf Deutsch, kurz. Kommentare erklären das Warum.
- `snake_case` in Python, `camelCase` im JavaScript, `kebab-case` für CSS.

## Tests

- Jede neue Fachregel bekommt mindestens einen Test.
- Tests dürfen nicht vom heutigen Datum abhängen, wenn sie Status prüfen –
  relative Bezugspunkte wie `FUTURE = date.today() + timedelta(days=30)` nutzen.
- Vor jedem Commit: `pytest` muss grün sein (68 Tests).
- Fixtures liegen in `tests/conftest.py` (`make_item`, `make_customer`,
  `make_rental`, `container`, `client`).

## Was man nicht tun soll

- Preise in Services, Routen oder im Frontend berechnen.
- Die Abhängigkeitsrichtung umdrehen (z. B. Domäne importiert FastAPI).
- Geld mit `float` rechnen.
- `data/` oder `__pycache__` committen (`.gitignore` deckt beides ab).
