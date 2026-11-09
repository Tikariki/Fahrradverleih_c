"""Legt realistische Beispieldaten für den Fahrradverleih an.

    python scripts/seed_demo.py

Bricht ab, wenn die Datenbank bereits Gegenstände enthält.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Settings  # noqa: E402
from app.container import build_container  # noqa: E402

TODAY = date.today()


def main() -> None:
    container = build_container(Settings.from_env())

    if container.items.list_items(include_inactive=True):
        print("Datenbank enthält bereits Gegenstände – Seed wird übersprungen.")
        return

    items = {}
    for key, data in {
        "trek": dict(
            type_key="bike", name="Trek FX 2", category="Standard", daily_rate="22.00",
            attributes={"bike_kind": "City", "frame_size": "M", "helmet_included": True},
        ),
        "giant": dict(
            type_key="bike", name="Giant Escape City", category="Standard", daily_rate="20.00",
            attributes={"bike_kind": "City", "frame_size": "S"},
        ),
        "rockhopper": dict(
            type_key="bike", name="Specialized Rockhopper", category="Standard", daily_rate="26.00",
            attributes={"bike_kind": "Mountain", "frame_size": "L", "helmet_included": True},
        ),
        "aspect": dict(
            type_key="bike", name="Scott Aspect 940", category="Standard", daily_rate="24.00",
            attributes={"bike_kind": "Mountain", "frame_size": "M"},
        ),
        "synapse": dict(
            type_key="bike", name="Cannondale Synapse", category="Premium", daily_rate="38.00",
            attributes={"bike_kind": "Rennrad", "frame_size": "L"},
        ),
        "canyon": dict(
            type_key="bike", name="Canyon Endurace", category="Premium", daily_rate="42.00",
            attributes={"bike_kind": "Rennrad", "frame_size": "M"},
        ),
        "kathmandu": dict(
            type_key="bike", name="Cube Kathmandu Hybrid", category="Premium", daily_rate="45.00",
            attributes={"bike_kind": "E-Bike", "frame_size": "L", "helmet_included": True},
        ),
        "ktm": dict(
            type_key="bike", name="KTM Macina Sport", category="Premium", daily_rate="48.00",
            attributes={"bike_kind": "E-Bike", "frame_size": "M"},
        ),
        "kinder": dict(
            type_key="bike", name="Puky Kinderrad 20\"", category="Kinder", daily_rate="14.00",
            attributes={"bike_kind": "City", "frame_size": "XS"},
        ),
    }.items():
        items[key] = container.items.create_item(data)

    customers = {
        "anna": container.customers.create_customer(
            {"first_name": "Anna", "last_name": "Müller", "email": "anna.mueller@example.at",
             "phone": "+43 660 1234567", "id_type": "id_card", "id_number": "AT-4471902"}
        ),
        "stefan": container.customers.create_customer(
            {"first_name": "Stefan", "last_name": "Berger", "email": "s.berger@example.at",
             "id_type": "passport", "id_number": "P-9982114"}
        ),
        "lena": container.customers.create_customer(
            {"first_name": "Lena", "last_name": "Hofer", "phone": "+43 676 9988776",
             "id_type": "drivers_license", "id_number": "F-7712345"}
        ),
        "tobias": container.customers.create_customer(
            {"first_name": "Tobias", "last_name": "Wagner", "email": "t.wagner@example.at",
             "id_type": "student_card", "id_number": "S-5580741"}
        ),
    }

    def rent(item_key: str, customer_key: str, start: date, days: int) -> int:
        rental = container.rentals.create_rental(
            {
                "item_id": items[item_key].id,
                "customer_id": customers[customer_key].id,
                "start_date": start.isoformat(),
                "days": days,
            }
        )
        return rental.id

    # Aktive Verleihe
    rent("kathmandu", "anna", TODAY - timedelta(days=2), 5)
    rent("rockhopper", "stefan", TODAY - timedelta(days=1), 3)
    rent("synapse", "lena", TODAY - timedelta(days=1), 2)
    rent("kinder", "tobias", TODAY, 4)

    # Überfällig
    rent("trek", "tobias", TODAY - timedelta(days=9), 2)

    # Bereits zurückgegeben
    returned_id = rent("giant", "anna", TODAY - timedelta(days=14), 3)
    container.rentals.return_rental(returned_id)
    returned_id = rent("ktm", "stefan", TODAY - timedelta(days=8), 2)
    container.rentals.return_rental(returned_id)
    returned_id = rent("aspect", "lena", TODAY - timedelta(days=20), 4)
    container.rentals.return_rental(returned_id)

    print(f"Seed abgeschlossen: {len(items)} Fahrräder, {len(customers)} Kunden.")


if __name__ == "__main__":
    main()
