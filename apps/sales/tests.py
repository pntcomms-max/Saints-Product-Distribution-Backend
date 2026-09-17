from rest_framework.test import APITestCase
from rest_framework import status
from apps.core.test_utils import make_org
from apps.inventory.models import InventoryItem
from .models import Sale


class LogSaleTests(APITestCase):
    def setUp(self):
        self.org = make_org()
        self.client.force_authenticate(user=self.org["ba"])

    def test_log_sale_decrements_stock_and_creates_sale(self):
        resp = self.client.post("/api/sales/sales/log_sale/", {
            "product": self.org["product"].id, "quantity": 3,
            "latitude": -17.82, "longitude": 31.05,
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["quantity"], 3)
        self.assertEqual(str(resp.data["amount"]), "114.00")  # 3 * 38.00

        item = InventoryItem.objects.get(ba=self.org["ba"], product=self.org["product"])
        self.assertEqual(item.quantity, 7)  # started at 10
        self.assertEqual(Sale.objects.count(), 1)

    def test_log_sale_rejects_more_than_available_stock_with_400_not_500(self):
        resp = self.client.post("/api/sales/sales/log_sale/", {
            "product": self.org["product"].id, "quantity": 999,
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.data)
        self.assertIn("quantity", resp.data)
        # stock must be untouched — the failed sale should not have decremented anything
        item = InventoryItem.objects.get(ba=self.org["ba"], product=self.org["product"])
        self.assertEqual(item.quantity, 10)
        self.assertEqual(Sale.objects.count(), 0)

    def test_ba_cannot_see_another_bas_sales(self):
        self.client.post("/api/sales/sales/log_sale/", {"product": self.org["product"].id, "quantity": 1})
        self.client.force_authenticate(user=self.org["other_ba"])
        self.client.post("/api/sales/sales/log_sale/", {"product": self.org["product"].id, "quantity": 2})

        self.client.force_authenticate(user=self.org["ba"])
        resp = self.client.get("/api/sales/sales/")
        self.assertEqual(resp.status_code, 200)
        results = resp.data["results"] if "results" in resp.data else resp.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["quantity"], 1)

    def test_supervisor_sees_team_sales_not_other_teams(self):
        self.client.post("/api/sales/sales/log_sale/", {"product": self.org["product"].id, "quantity": 1})
        self.client.force_authenticate(user=self.org["other_ba"])
        self.client.post("/api/sales/sales/log_sale/", {"product": self.org["product"].id, "quantity": 2})

        self.client.force_authenticate(user=self.org["supervisor"])
        resp = self.client.get("/api/sales/sales/")
        results = resp.data["results"] if "results" in resp.data else resp.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["ba"], self.org["ba"].id)
