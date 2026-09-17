from rest_framework.test import APITestCase
from apps.core.test_utils import make_org
from apps.tracking.models import CheckIn
from apps.inventory.models import InventoryItem


class DemandForecastTests(APITestCase):
    """Regression coverage for the None-vs-None sort crash."""

    def setUp(self):
        self.org = make_org()
        self.client.force_authenticate(user=self.org["manager"])

    def test_forecast_does_not_crash_when_multiple_products_have_no_sales_history(self):
        # Need >=2 entries that both resolve to days_left=None so the
        # sort actually has to compare two Nones — a 1-item list would
        # never have triggered the original crash.
        from apps.catalog.models import Product
        second_product = Product.objects.create(
            brand=self.org["product"].brand, name="Boss Menthol 20s",
            sku="BOSS-MENTHOL-20", unit="carton", price="39.00",
        )
        InventoryItem.objects.create(ba=self.org["ba"], product=second_product, quantity=15)

        resp = self.client.get("/api/analytics/demand-forecast/")
        self.assertEqual(resp.status_code, 200)
        results = resp.data["results"]
        self.assertGreaterEqual(len(results), 2)
        # confirms we actually exercised the None/None comparison path
        self.assertTrue(any(r["days_left"] is None for r in results))

    def test_forecast_requires_supervisor_or_above(self):
        self.client.force_authenticate(user=self.org["ba"])
        resp = self.client.get("/api/analytics/demand-forecast/")
        self.assertEqual(resp.status_code, 403)


class LiveMapTests(APITestCase):
    def setUp(self):
        self.org = make_org()

    def test_manager_sees_all_bas_with_locations(self):
        CheckIn.objects.create(ba=self.org["ba"], region=self.org["region"], latitude=-17.8, longitude=31.0)
        CheckIn.objects.create(ba=self.org["other_ba"], region=self.org["region"], latitude=-17.9, longitude=31.1)

        self.client.force_authenticate(user=self.org["manager"])
        resp = self.client.get("/api/analytics/live-map/")
        self.assertEqual(resp.status_code, 200)
        ba_ids = {r["ba_id"] for r in resp.data["results"]}
        self.assertEqual(ba_ids, {self.org["ba"].id, self.org["other_ba"].id})

    def test_supervisor_sees_only_own_team_on_map(self):
        CheckIn.objects.create(ba=self.org["ba"], region=self.org["region"], latitude=-17.8, longitude=31.0)
        CheckIn.objects.create(ba=self.org["other_ba"], region=self.org["region"], latitude=-17.9, longitude=31.1)

        self.client.force_authenticate(user=self.org["supervisor"])
        resp = self.client.get("/api/analytics/live-map/")
        ba_ids = {r["ba_id"] for r in resp.data["results"]}
        self.assertEqual(ba_ids, {self.org["ba"].id})

    def test_stale_flag_true_when_no_checkin_at_all(self):
        self.client.force_authenticate(user=self.org["manager"])
        resp = self.client.get("/api/analytics/live-map/")
        row = next(r for r in resp.data["results"] if r["ba_id"] == self.org["ba"].id)
        self.assertTrue(row["is_stale"])
        self.assertIsNone(row["latitude"])

    def test_stale_flag_false_for_recent_checkin(self):
        CheckIn.objects.create(ba=self.org["ba"], region=self.org["region"], latitude=-17.8, longitude=31.0)
        self.client.force_authenticate(user=self.org["manager"])
        resp = self.client.get("/api/analytics/live-map/")
        row = next(r for r in resp.data["results"] if r["ba_id"] == self.org["ba"].id)
        self.assertFalse(row["is_stale"])
