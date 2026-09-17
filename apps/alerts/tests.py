from django.core.management import call_command
from rest_framework.test import APITestCase
from apps.core.test_utils import make_org
from apps.inventory.models import InventoryItem
from apps.tracking.models import CheckIn
from .models import Alert


class CheckAlertsCommandTests(APITestCase):
    def setUp(self):
        self.org = make_org()

    def test_out_of_stock_creates_alert(self):
        item = InventoryItem.objects.get(ba=self.org["ba"], product=self.org["product"])
        item.quantity = 0
        item.save()

        call_command("check_alerts")

        alerts = Alert.objects.filter(ba=self.org["ba"], kind=Alert.Kind.OUT_OF_STOCK, resolved_at__isnull=True)
        self.assertEqual(alerts.count(), 1)
        self.assertIn(self.org["product"].name, alerts.first().message)

    def test_restocking_auto_resolves_the_alert(self):
        item = InventoryItem.objects.get(ba=self.org["ba"], product=self.org["product"])
        item.quantity = 0
        item.save()
        call_command("check_alerts")
        self.assertEqual(Alert.objects.filter(ba=self.org["ba"], resolved_at__isnull=True).count(), 2)  # out-of-stock + inactive-BA (no checkins yet)

        item.quantity = 20
        item.save()
        CheckIn.objects.create(ba=self.org["ba"], region=self.org["region"])  # also clears inactivity
        call_command("check_alerts")

        self.assertEqual(
            Alert.objects.filter(ba=self.org["ba"], resolved_at__isnull=True).count(), 0,
        )
        # the original alert row still exists, just resolved — not deleted
        self.assertTrue(Alert.objects.filter(ba=self.org["ba"], kind=Alert.Kind.OUT_OF_STOCK).exists())

    def test_running_twice_does_not_duplicate_open_alerts(self):
        item = InventoryItem.objects.get(ba=self.org["ba"], product=self.org["product"])
        item.quantity = 0
        item.save()

        call_command("check_alerts")
        call_command("check_alerts")

        self.assertEqual(
            Alert.objects.filter(ba=self.org["ba"], kind=Alert.Kind.OUT_OF_STOCK, resolved_at__isnull=True).count(),
            1,
        )

    def test_inactive_ba_alert_when_no_recent_checkin(self):
        call_command("check_alerts")
        self.assertTrue(
            Alert.objects.filter(ba=self.org["ba"], kind=Alert.Kind.INACTIVE_BA, resolved_at__isnull=True).exists()
        )

    def test_supervisor_only_sees_own_team_alerts_via_api(self):
        item = InventoryItem.objects.get(ba=self.org["ba"], product=self.org["product"])
        item.quantity = 0
        item.save()
        other_item = InventoryItem.objects.get(ba=self.org["other_ba"], product=self.org["product"])
        other_item.quantity = 0
        other_item.save()
        call_command("check_alerts")

        self.client.force_authenticate(user=self.org["supervisor"])
        resp = self.client.get("/api/alerts/")
        results = resp.data["results"] if "results" in resp.data else resp.data
        ba_ids = {r["ba"] for r in results}
        self.assertIn(self.org["ba"].id, ba_ids)
        self.assertNotIn(self.org["other_ba"].id, ba_ids)

    def test_resolve_endpoint_marks_resolved(self):
        item = InventoryItem.objects.get(ba=self.org["ba"], product=self.org["product"])
        item.quantity = 0
        item.save()
        call_command("check_alerts")
        alert = Alert.objects.filter(ba=self.org["ba"], kind=Alert.Kind.OUT_OF_STOCK).first()

        self.client.force_authenticate(user=self.org["supervisor"])
        resp = self.client.post(f"/api/alerts/{alert.id}/resolve/")
        self.assertEqual(resp.status_code, 200)
        alert.refresh_from_db()
        self.assertIsNotNone(alert.resolved_at)
