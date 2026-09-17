"""
Run this periodically (cron every 5-15 minutes, or Celery beat if you
add it later) to detect stock and inactivity conditions, persist them
as Alert rows (deduplicated — see Alert.Meta.constraints), and push
notify the affected BA's supervisor + all managers for anything newly
detected.

    */10 * * * * cd /path/to/backend && venv/bin/python manage.py check_alerts

Also auto-resolves alerts whose underlying condition has cleared (stock
restocked, BA checked in again) so the alerts list only ever shows what's
actually still true.
"""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.inventory.models import InventoryItem
from apps.tracking.models import CheckIn
from apps.alerts.models import Alert
from apps.alerts.push import send_push_to_users

INACTIVITY_THRESHOLD = timedelta(hours=6)


class Command(BaseCommand):
    help = "Detect stock/inactivity conditions, persist Alert rows, and push-notify supervisors/managers."

    def handle(self, *args, **options):
        created_count = 0
        resolved_count = 0

        bas = User.objects.filter(role=User.Role.BA).select_related("supervisor", "region")
        managers = list(User.objects.filter(role=User.Role.MANAGER))

        for ba in bas:
            notify_targets = ([ba.supervisor] if ba.supervisor else []) + managers

            # --- stock conditions ---
            for item in InventoryItem.objects.filter(ba=ba).select_related("product"):
                if item.status == "OUT":
                    created, alert = self._open_or_get(
                        ba=ba, kind=Alert.Kind.OUT_OF_STOCK, product=item.product,
                        message=f"{ba.get_full_name()} is out of {item.product.name}",
                    )
                elif item.status == "LOW":
                    created, alert = self._open_or_get(
                        ba=ba, kind=Alert.Kind.LOW_STOCK, product=item.product,
                        message=f"{ba.get_full_name()} is low on {item.product.name} ({item.quantity} left)",
                    )
                else:
                    resolved_count += self._resolve_all(ba, Alert.Kind.OUT_OF_STOCK, item.product)
                    resolved_count += self._resolve_all(ba, Alert.Kind.LOW_STOCK, item.product)
                    continue

                if created:
                    created_count += 1
                    self._notify(alert, notify_targets)
                # if status is LOW, make sure no stale OUT_OF_STOCK alert lingers, and vice versa
                if item.status == "OUT":
                    resolved_count += self._resolve_all(ba, Alert.Kind.LOW_STOCK, item.product)
                elif item.status == "LOW":
                    resolved_count += self._resolve_all(ba, Alert.Kind.OUT_OF_STOCK, item.product)

            # --- inactivity ---
            last_checkin = CheckIn.objects.filter(ba=ba).order_by("-created_at").first()
            inactive = (not last_checkin) or (timezone.now() - last_checkin.created_at > INACTIVITY_THRESHOLD)
            if inactive:
                created, alert = self._open_or_get(
                    ba=ba, kind=Alert.Kind.INACTIVE_BA, product=None,
                    message=f"{ba.get_full_name()} hasn't checked in for over {INACTIVITY_THRESHOLD.seconds // 3600}h",
                )
                if created:
                    created_count += 1
                    self._notify(alert, notify_targets)
            else:
                resolved_count += self._resolve_all(ba, Alert.Kind.INACTIVE_BA, None)

        self.stdout.write(self.style.SUCCESS(
            f"check_alerts: {created_count} new alert(s), {resolved_count} auto-resolved."
        ))

    def _open_or_get(self, *, ba, kind, product, message):
        existing = Alert.objects.filter(ba=ba, kind=kind, product=product, resolved_at__isnull=True).first()
        if existing:
            if existing.message != message:
                # keep the message fresh (e.g. quantity changed) without spamming a new push
                existing.message = message
                existing.save(update_fields=["message"])
            return False, existing
        alert = Alert.objects.create(ba=ba, kind=kind, product=product, message=message)
        return True, alert

    def _resolve_all(self, ba, kind, product):
        qs = Alert.objects.filter(ba=ba, kind=kind, product=product, resolved_at__isnull=True)
        count = qs.count()
        qs.update(resolved_at=timezone.now())
        return count

    def _notify(self, alert, targets):
        targets = [t for t in targets if t is not None]
        if not targets:
            return
        sent = send_push_to_users(
            targets, title="Route & Stock alert", body=alert.message,
            data={"alert_id": alert.id, "kind": alert.kind, "ba_id": alert.ba_id},
        )
        if sent:
            alert.notified_at = timezone.now()
            alert.save(update_fields=["notified_at"])
