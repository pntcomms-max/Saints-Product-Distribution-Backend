"""
Shared fixtures for the test suite — not Django tests itself, just the
"give me a manager, a supervisor with one BA, a region, and a product"
setup every other test file needs.
"""
from apps.accounts.models import User
from apps.catalog.models import Region, Manufacturer, Brand, Product
from apps.inventory.models import InventoryItem


def make_org():
    region = Region.objects.create(name="Harare CBD")
    manufacturer = Manufacturer.objects.create(name="CRP")
    brand = Brand.objects.create(manufacturer=manufacturer, name="Boss")
    product = Product.objects.create(
        brand=brand, name="Boss Full Flavour 20s", sku="BOSS-FF-20",
        unit="carton", price="38.00",
    )

    manager = User.objects.create_user(username="manager", password="pw12345!", role=User.Role.MANAGER)
    supervisor = User.objects.create_user(
        username="supervisor", password="pw12345!", role=User.Role.SUPERVISOR, region=region,
    )
    ba = User.objects.create_user(
        username="ba1", password="pw12345!", role=User.Role.BA,
        region=region, supervisor=supervisor,
    )
    other_supervisor = User.objects.create_user(
        username="supervisor2", password="pw12345!", role=User.Role.SUPERVISOR, region=region,
    )
    other_ba = User.objects.create_user(
        username="ba2", password="pw12345!", role=User.Role.BA,
        region=region, supervisor=other_supervisor,
    )

    InventoryItem.objects.create(ba=ba, product=product, quantity=10)
    InventoryItem.objects.create(ba=other_ba, product=product, quantity=10)

    return {
        "region": region, "product": product,
        "manager": manager, "supervisor": supervisor, "ba": ba,
        "other_supervisor": other_supervisor, "other_ba": other_ba,
    }
