import os
import sys
import django
from decimal import Decimal

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from properties.models import Property  # noqa: E402


SAMPLE_PROPERTIES = [
    {
        "title": "Skyline Heights - DLF Phase 3",
        "property_type": "apartment",
        "price": Decimal("9800000"),
        "bedrooms": 3,
        "bathrooms": 2,
        "area": 1650,
        "location": "Gurugram",
        "listing_type": "buy",
        "status": "available",
    },
    {
        "title": "Green Acres Plot",
        "property_type": "land",
        "price": Decimal("4200000"),
        "bedrooms": None,
        "bathrooms": None,
        "area": 2400,
        "location": "Hyderabad",
        "listing_type": "lease",
        "status": "available",
    },
    {
        "title": "Riverside House",
        "property_type": "house",
        "price": Decimal("13200000"),
        "bedrooms": 4,
        "bathrooms": 3,
        "area": 2600,
        "location": "Pune",
        "listing_type": "buy",
        "status": "available",
    },
    {
        "title": "Cityline Apartment",
        "property_type": "apartment",
        "price": Decimal("38000"),
        "bedrooms": 2,
        "bathrooms": 2,
        "area": 1180,
        "location": "Bengaluru",
        "listing_type": "rent",
        "status": "available",
    },
    {
        "title": "Tech Park Office",
        "property_type": "commercial",
        "price": Decimal("125000"),
        "bedrooms": None,
        "bathrooms": 2,
        "area": 2100,
        "location": "Mumbai",
        "listing_type": "lease",
        "status": "hold",
    },
]


def main():
    created = 0
    for payload in SAMPLE_PROPERTIES:
        _, was_created = Property.objects.get_or_create(
            title=payload["title"],
            defaults=payload,
        )
        if was_created:
            created += 1
    print(f"Seed complete. Added {created} properties. Total: {Property.objects.count()}")


if __name__ == "__main__":
    main()
