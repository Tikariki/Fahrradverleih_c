# Architektur

## Überblick

Klassische Schichtenarchitektur mit einer klaren Regel: Geschäftslogik liegt in
`services`, Preise entstehen nur in `pricing`, HTTP kennt keine Fachlogik.

```
┌──────────────────────────────────────────────────────────────┐
│  Browser-Dashboard (Jinja2 + Vanilla JS)   Swagger UI        │
└───────────────────────────┬──────────────────────────────────┘
                            │ HTTP/JSON, multipart
┌───────────────────────────▼──────────────────────────────────┐
│  app/api/          Routen, Transport-Schemata, Deps          │
│  app/main.py       App-Factory, Fehler-Handler, /            │
└───────────────────────────┬──────────────────────────────────┘
                            │ Service-Aufrufe
┌───────────────────────────▼──────────────────────────────────┐
│  app/services/     ItemService, CustomerService,             │
│                    RentalService, DashboardService           │
└──────┬────────────────────┬───────────────────────┬──────────┘
       │                    │                       │
┌──────▼──────┐   ┌─────────▼────────┐   ┌──────────▼─────────┐
│ app/pricing │   │ app/repositories │   │ app/domain         │
│ Regeln,     │   │ SQLite-Zugriff   │   │ Entitäten, Geld,   │
│ Preisdienst │   │                  │   │ Fehler             │
└─────────────┘   └──────────────────┘   └────────────────────┘
```

`app/container.py` verdrahtet alle Implementierungen und wird von
`create_app()` genau einmal pro Prozess aufgebaut.

## Domänenmodell

```
          ┌──────────────────────────┐
          │ RentalItem  (ABC)        │
          │  name, category          │
          │  daily_rate: Decimal     │
          │  attributes: dict        │
          │  validate()              │
          │  attribute_fields()      │
          └──────────▲───────────────┘
                     │ erbt
                     │
                  ┌──┴───┐
                  │ Bike │
                  └──────┘

   Customer 1 ──── * Rental * ──── 1 RentalItem
      │
      └── IdDocument (Typ + Nummer + optionaler Scan)
```

Wichtige Entscheidungen:

- **`RentalItem` ist eine abstrakte Basisklasse, kein Datenbank-Record.** Die
  typspezifischen Felder liegen in `attributes` (JSON) und werden über
  `attribute_fields()` deklariert. Daraus baut die Oberfläche ihre Formulare und
  die Domäne validiert die Werte.
- **`Rental` schreibt den Preis beim Anlegen fest** (`daily_rate`, `total`,
  `price_lines`). Regeländerungen wirken nicht rückwirkend.
- **Ein Verleihzeitraum ist halboffen** `[start_date, start_date + days)`. Ein
  Anschlussverleih am Rückgabetag ist daher ohne Konflikt möglich.

## Preispipeline

```
RentalItem ─┐
Verleihdauer├─▶ PriceRequest ──▶ [Regel 10] ──▶ [Regel 30] ──▶ [Regel 40] ──▶ PriceQuote
Startdatum  │                     Duration      E-Bike         Kategorie      (Positionen
Kunde      ─┘                     setzt base    addiert         rechnet auf    + Summe)
                                                               base
```

- `PricingService` hält die Regeln sortiert nach `priority` und führt sie aus.
- Jede Regel entscheidet über `applies(request)`, ob sie gilt, und liefert über
  `apply(request, state)` null oder mehr `PriceLine`.
- `DurationRateRule` (Priorität 10) setzt `state.base`. Alle späteren Regeln
  rechnen auf diesen Zwischenstand – die Reihenfolge ist fachlich bedeutsam.
- Objektabhängige Regeln (`item.pricing_rules()`) überschreiben Regeln mit
  gleichem `key`. So kann ein einzelner Gegenstand eine Sonderregel bekommen,
  ohne die globale Konfiguration zu ändern.

Neue Preisregeln brauchen keine Änderung an bestehendem Code: von `PricingRule`
erben, `key`, `priority` und `apply()` implementieren, beim `PricingService`
registrieren. Staffel und Kategorie-Zuordnung sind Konstruktorparameter und
lassen sich ohne Codeänderung anpassen.

## Verleiharten als Module

`app/plugins/builtin/` enthält das Modul `bike.py` für die Verleihart sowie
`identity.py` für die Ausweistypen. Jedes Modul exportiert
ein `PLUGIN`-Objekt; der Loader sammelt sie beim Start ein, die `PluginRegistry`
prüft auf doppelte Schlüssel und stellt Typen, Preisregeln und Ausweistypen
bereit. Das Dashboard liest diese Metadaten über `GET /api/meta` und baut seine
Formulare daraus – ein neuer Typ erscheint ohne Frontend-Änderung.

## Persistenz

Drei Tabellen, keine Migrationen (Schema ist idempotent, `schema.sql`):

```sql
customers (id, first_name, last_name, email, phone,
           id_type, id_number, id_file, created_at)

items     (id, name, type_key, category, daily_rate_cents,
           attributes, active, created_at)

rentals   (id, item_id, customer_id, start_date, days, due_date,
           daily_rate_cents, total_cents, price_lines, created_at, returned_at)
```

- Beträge als ganzzahlige Cent, Attribute und Rechnungspositionen als JSON.
- `due_date` ist redundant zu `start_date + days`, macht aber Bereichsabfragen
  („heute fällig", „überfällig") ohne Rechnen in SQL möglich.
- `foreign_keys = ON`. Ein Gegenstand mit Verleihhistorie wird nicht gelöscht,
  sondern deaktiviert (`ItemService.delete_item`).

## Fehlerbehandlung

| Klasse | HTTP | Beispiel |
|---|---|---|
| `ValidationError` | 422 | Verleihdauer 0, unbekannter Verleih- oder Ausweistyp |
| `NotFoundError` | 404 | Gegenstand, Kunde oder Vorgang existiert nicht |
| `ConflictError` | 409 | Kunde ohne Ausweis, doppelte Rückgabe, Kunde mit Historie löschen |
| `ItemUnavailableError` | 409 | Gegenstand im Zeitraum bereits verliehen oder deaktiviert |

Die API-Schicht registriert einen einzigen Handler (`app/main.py`) und liefert
`{"error": <code>, "message": <text>}`. Services kennen kein HTTP.

## Entwurfsentscheidungen (kurz begründet)

1. **FastAPI statt Flask/Django.** Automatische OpenAPI-Dokumentation,
   Typprüfung der Eingaben über Pydantic, geringer Boilerplate.
2. **SQLite über die Standardbibliothek.** Keine Serverinstallation, ein File,
   für einen Verleihschalter ausreichend. Ein Wechsel auf PostgreSQL beträfe nur
   `app/repositories/`.
3. **Attribute als JSON statt einer Spalte je Verleihart.** Neue Verleiharten
   brauchen keine Schemaänderung. Preis der Entscheidung: SQL kann typspezifische
   Felder nicht filtern – für dieses System nicht nötig.
4. **Eine Regelkette statt einer Formel.** Rabatte, Zuschläge und Pauschalen sind
   unabhängig testbar und in der Reihenfolge dokumentiert.
5. **Vanilla JS statt Framework.** Kein Build-Schritt, kein `node_modules`, die
   Oberfläche bleibt für Dritte lesbar. Die API ist so geschnitten, dass ein
   späterer Wechsel auf ein Framework ohne Backend-Änderung möglich ist.
