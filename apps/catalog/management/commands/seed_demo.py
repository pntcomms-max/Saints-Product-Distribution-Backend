import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from apps.catalog.models import Manufacturer, Brand, Product
from apps.accounts.models import User
from apps.inventory.models import InventoryItem
from apps.sales.models import Sale
from apps.tracking.models import CheckIn

# GPS target anchors for field sales reps in Zimbabwe
LOCATION_COORDS = [
    (-17.8292, 31.0522),  # Harare CBD
    (-17.8583, 31.0300),  # Harare High-Density
    (-20.1500, 28.5833),  # Bulawayo
    (-18.9707, 32.6709),  # Mutare
    (-19.4500, 29.8167),  # Gweru
    (-20.0637, 30.8277),  # Masvingo
    (-17.3667, 30.2000),  # Chinhoyi
]

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
SALES_REP_NAMES = [
    ("Tapiwa", "Muza"), ("Chiedza", "Dube"), ("Blessing", "Sibanda"), ("Rumbidzai", "Gwara"),
    ("Kudakwashe", "Banda"), ("Nyasha", "Chirwa"), ("Tafadzwa", "Zulu"), ("Anesu", "Marufu"),
    ("Panashe", "Moyo"), ("Vimbai", "Ncube"), ("Tinashe", "Gore"), ("Shamiso", "Mabika"),
]


class Command(BaseCommand):
    help = "Seed demo data: CRP/Boss/RG catalog, GPS field reps, inventory, and 21 days of sales history."

    @transaction.atomic
    def handle(self, *args, **options):
        # 1. Seed Catalog (CRP -> Boss / RG)
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

        # 2. Seed Manager
        if not User.objects.filter(username="manager").exists():
            manager = User.objects.create_user(
                username="manager", password="changeme123", first_name="Blessing", last_name="Chatora",
                role="MANAGER",
            )
        else:
            manager = User.objects.get(username="manager")

        # 3. Seed Supervisors
        supervisors = []
        for first, last in SUPERVISOR_NAMES:
            username = f"sup_{first.lower()}"
            sup, created = User.objects.get_or_create(
                username=username, defaults={
                    "first_name": first, "last_name": last, "role": "SUPERVISOR",
                },
            )
            if created:
                sup.set_password("changeme123")
                sup.save()
            supervisors.append(sup)

        # 4. Seed Sales Reps
        sales_reps = []
        for i, (first, last) in enumerate(SALES_REP_NAMES):
            username = f"rep_{first.lower()}"
            supervisor = supervisors[i % len(supervisors)]
            sales_rep, created = User.objects.get_or_create(
                username=username, defaults={
                    "first_name": first, "last_name": last, "role": "SALES_REP",
                    "supervisor": supervisor,
                },
            )
            if created:
                sales_rep.set_password("changeme123")
                sales_rep.save()
            sales_reps.append(sales_rep)

        # 5. Seed Inventory using sales_rep field
        for rep in sales_reps:
            for product in products:
                InventoryItem.objects.get_or_create(
                    sales_rep=rep, product=product, defaults={"quantity": random.randint(2, 27)},
                )

        # 6. Seed 21 Days of GPS-Tracked Sales & Check-Ins using sales_rep field
        if not Sale.objects.exists():
            now = timezone.now()
            for d in range(20, -1, -1):
                day = now - timedelta(days=d)
                for i, rep in enumerate(sales_reps):
                    base_lat, base_lng = LOCATION_COORDS[i % len(LOCATION_COORDS)]

                    for _ in range(random.randint(0, 3)):
                        product = random.choice(products)
                        qty = random.randint(1, 3)
                        jitter_lat = base_lat + random.uniform(-0.02, 0.02)
                        jitter_lng = base_lng + random.uniform(-0.02, 0.02)

                        Sale.objects.create(
                            sales_rep=rep,
                            product=product,
                            quantity=qty,
                            unit_price=product.price,
                            latitude=jitter_lat,
                            longitude=jitter_lng,
                            created_at=day - timedelta(hours=random.randint(0, 8)),
                        )

                    if random.random() < 0.8:
                        jitter_lat = base_lat + random.uniform(-0.03, 0.03)
                        jitter_lng = base_lng + random.uniform(-0.03, 0.03)
                        CheckIn.objects.create(
                            sales_rep=rep,
                            latitude=jitter_lat,
                            longitude=jitter_lng,
                            created_at=day - timedelta(hours=random.randint(0, 8)),
                        )

        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded GPS-centric demo data! "
            f"Created {len(products)} products (CRP/Boss/RG), "
            f"1 manager, {len(supervisors)} supervisors, {len(sales_reps)} sales reps. "
            f"Login test credentials: manager/changeme123, sup_tendai/changeme123, rep_tapiwa/changeme123"
        ))