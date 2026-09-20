import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from apps.catalog.models import Region, Manufacturer, Brand, Product
from apps.accounts.models import User
from apps.inventory.models import InventoryItem
from apps.sales.models import Sale
from apps.tracking.models import CheckIn

REGIONS = ["Harare CBD", "Harare High-Density", "Bulawayo", "Mutare", "Gweru", "Masvingo Rural", "Chinhoyi"]

# Approximate real coordinates per region, so seeded check-ins land
# somewhere sensible on the live map instead of all stacking at (0,0).
REGION_COORDS = {
    "Harare CBD": (-17.8292, 31.0522),
    "Harare High-Density": (-17.8583, 31.0300),
    "Bulawayo": (-20.1500, 28.5833),
    "Mutare": (-18.9707, 32.6709),
    "Gweru": (-19.4500, 29.8167),
    "Masvingo Rural": (-20.0637, 30.8277),
    "Chinhoyi": (-17.3667, 30.2000),
}

# Product lines are data, not code: add a manufacturer/brand/product here
# (or via /admin or the API) any time — nothing else needs to change.
CATALOG = {
    "CRP": {
        "Boss": [
            ("Boss Full Flavour 20s", "carton (10 packs)", 38.00),
            ("Boss Menthol 20s", "carton (10 packs)", 39.00),
        ],
        "RG": [
            ("RG Red 20s", "carton (10 packs)", 34.00),
            ("RG Blue 20s", "carton (10 packs)", 34.00),
        ],
    },
}

SUPERVISOR_NAMES = [("Tendai", "Moyo"), ("Rutendo", "Chikwava"), ("Farai", "Ndlovu")]
BA_NAMES = [
    ("Tapiwa", "Muza"), ("Chiedza", "Dube"), ("Blessing", "Sibanda"), ("Rumbidzai", "Gwara"),
    ("Kudakwashe", "Banda"), ("Nyasha", "Chirwa"), ("Tafadzwa", "Zulu"), ("Anesu", "Marufu"),
    ("Panashe", "Moyo"), ("Vimbai", "Ncube"), ("Tinashe", "Gore"), ("Shamiso", "Mabika"),
]


class Command(BaseCommand):
    help = "Seed demo data: regions, CRP/Boss/RG catalog, users, inventory, and 21 days of sales history."

    @transaction.atomic
    def handle(self, *args, **options):
        regions = {name: Region.objects.get_or_create(name=name)[0] for name in REGIONS}

        products = []
        for manu_name, brands in CATALOG.items():
            manufacturer, _ = Manufacturer.objects.get_or_create(name=manu_name)
            for brand_name, product_list in brands.items():
                brand, _ = Brand.objects.get_or_create(manufacturer=manufacturer, name=brand_name)
                for name, unit, price in product_list:
                    sku = name.upper().replace(" ", "-").replace("(", "").replace(")", "")
                    product, _ = Product.objects.get_or_create(
                        sku=sku, defaults={"brand": brand, "name": name, "unit": unit, "price": price},
                    )
                    products.append(product)

        if not User.objects.filter(username="manager").exists():
            manager = User.objects.create_user(
                username="manager", password="changeme123", first_name="Blessing", last_name="Chatora",
                role=User.Role.MANAGER, region=None,
            )
        else:
            manager = User.objects.get(username="manager")

        supervisors = []
        for i, (first, last) in enumerate(SUPERVISOR_NAMES):
            username = f"sup_{first.lower()}"
            sup, _ = User.objects.get_or_create(
                username=username, defaults={
                    "first_name": first, "last_name": last, "role": Role.Supervisor,
                    "region": regions[REGIONS[i * 2 % len(REGIONS)]],
                },
            )
            sup.set_password("changeme123")
            sup.save()
            supervisors.append(sup)

        bas = []
        for i, (first, last) in enumerate(BA_NAMES):
            username = f"ba_{first.lower()}"
            region = regions[REGIONS[i % len(REGIONS)]]
            supervisor = supervisors[i % len(supervisors)]
            ba, _ = User.objects.get_or_create(
                username=username, defaults={
                    "first_name": first, "last_name": last, "role": Role.SALES_REP,
                    "region": region, "supervisor": supervisor,
                },
            )
            ba.set_password("changeme123")
            ba.save()
            bas.append(ba)

        for ba in bas:
            for product in products:
                InventoryItem.objects.get_or_create(
                    ba=ba, product=product, defaults={"quantity": random.randint(2, 27)},
                )

        if not Sale.objects.exists():
            now = timezone.now()
            for d in range(20, -1, -1):
                day = now - timedelta(days=d)
                for ba in bas:
                    for _ in range(random.randint(0, 3)):
                        product = random.choice(products)
                        qty = random.randint(1, 3)
                        Sale.objects.create(
                            ba=ba, product=product, region=ba.region, quantity=qty,
                            unit_price=product.price,
                            created_at=day - timedelta(hours=random.randint(0, 8)),
                        )
                    if random.random() < 0.8:
                        base_lat, base_lng = REGION_COORDS[ba.region.name]
                        # small jitter so BAs in the same region don't
                        # all stack on exactly one map point
                        jitter_lat = base_lat + random.uniform(-0.03, 0.03)
                        jitter_lng = base_lng + random.uniform(-0.03, 0.03)
                        CheckIn.objects.create(
                            ba=ba, region=ba.region, source=CheckIn.Source.MANUAL,
                            latitude=jitter_lat, longitude=jitter_lng,
                            created_at=day - timedelta(hours=random.randint(0, 8)),
                        )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded: {len(regions)} regions, {len(products)} products (CRP/Boss/RG), "
            f"1 manager, {len(supervisors)} supervisors, {len(bas)} BAs. "
            f"Login: manager/changeme123, sup_tendai/changeme123, ba_tapiwa/changeme123 (all password changeme123)."
        ))
