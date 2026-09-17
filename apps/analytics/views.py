from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Count, F
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.accounts.permissions import IsSupervisorOrAbove
from apps.sales.models import Sale
from apps.inventory.models import InventoryItem
from apps.tracking.models import CheckIn
from apps.catalog.models import Region, Product
from apps.accounts.models import User


class DemandForecastView(APIView):
    """
    Predictive restock signal per region x product.

    Method: 14-day trailing sell-through rate -> projected 7-day need,
    compared against current stock on hand across BAs in that region.
    Areas with more concentrated sales naturally dominate the "restock
    now" list without any manual weighting - the model scales with the
    network rather than needing retuning as more BAs/regions are added.
    """
    permission_classes = [IsSupervisorOrAbove]

    def get(self, request):
        window_days = int(request.query_params.get("window_days", 14))
        horizon_days = int(request.query_params.get("horizon_days", 7))
        cutoff = timezone.now() - timedelta(days=window_days)

        sales_qs = Sale.objects.filter(created_at__gte=cutoff)
        # supervisors only see their own team's footprint
        if request.user.role == "SUPERVISOR":
            sales_qs = sales_qs.filter(ba__supervisor=request.user)

        sold_by_region_product = {
            (row["region_id"], row["product_id"]): row["total_qty"]
            for row in sales_qs.values("region_id", "product_id").annotate(total_qty=Sum("quantity"))
        }

        stock_qs = InventoryItem.objects.all()
        if request.user.role == "SUPERVISOR":
            stock_qs = stock_qs.filter(ba__supervisor=request.user)
        stock_by_region_product = {}
        for row in stock_qs.values("ba__region_id", "product_id").annotate(total_qty=Sum("quantity")):
            stock_by_region_product[(row["ba__region_id"], row["product_id"])] = row["total_qty"]

        regions = Region.objects.all()
        products = Product.objects.filter(is_active=True)

        results = []
        for region in regions:
            for product in products:
                key = (region.id, product.id)
                sold = sold_by_region_product.get(key, 0)
                daily_rate = sold / window_days
                projected = daily_rate * horizon_days
                on_hand = stock_by_region_product.get(key, 0)
                days_left = (on_hand / daily_rate) if daily_rate > 0 else (999 if on_hand > 0 else 0)

                if on_hand == 0 and sold == 0:
                    continue  # nothing to report

                results.append({
                    "region": region.name,
                    "region_id": region.id,
                    "product": product.name,
                    "product_id": product.id,
                    "brand": product.brand.name,
                    "manufacturer": product.brand.manufacturer.name,
                    "daily_rate": round(daily_rate, 2),
                    "projected_need_horizon": round(projected, 1),
                    "on_hand": on_hand,
                    "days_left": round(days_left, 1) if days_left < 999 else None,
                    "urgency": "CRITICAL" if days_left < 4 else ("WATCH" if days_left < 8 else "OK"),
                })

        # Sort soonest-to-run-out first. Plain `days_left` sorts fine
        # for real numbers, but comparing two `None` values (infinite
        # runway) directly raises a TypeError in Python 3 — route those
        # through a sentinel instead of sorting on the raw field.
        results.sort(key=lambda r: r["days_left"] if r["days_left"] is not None else float("inf"))
        return Response({
            "window_days": window_days, "horizon_days": horizon_days,
            "generated_at": timezone.now(), "results": results,
        })


class LiveMapView(APIView):
    """
    Latest known position + a quick status snapshot for every BA in
    scope (team for a supervisor, everyone for a manager) — this is
    what the manager/supervisor map screen renders as markers.
    """
    permission_classes = [IsSupervisorOrAbove]

    def get(self, request):
        bas = User.objects.filter(role="BA").select_related("region", "supervisor")
        if request.user.role == "SUPERVISOR":
            bas = bas.filter(supervisor=request.user)

        results = []
        for ba in bas:
            last_checkin = CheckIn.objects.filter(ba=ba).order_by("-created_at").first()
            today_total = Sale.objects.filter(ba=ba, created_at__gte=timezone.now() - timedelta(hours=24)) \
                .aggregate(t=Sum("amount"))["t"] or 0
            out_of_stock = InventoryItem.objects.filter(ba=ba, quantity=0).count()
            low_stock = InventoryItem.objects.filter(ba=ba, quantity__gt=0, quantity__lte=5).count()

            is_stale = (not last_checkin) or (timezone.now() - last_checkin.created_at > timedelta(hours=6))

            results.append({
                "ba_id": ba.id,
                "name": ba.get_full_name(),
                "region": ba.region.name if ba.region else None,
                "supervisor_id": ba.supervisor_id,
                "latitude": last_checkin.latitude if last_checkin else None,
                "longitude": last_checkin.longitude if last_checkin else None,
                "last_checkin_at": last_checkin.created_at if last_checkin else None,
                "is_stale": is_stale,
                "cash_today": today_total,
                "out_of_stock_count": out_of_stock,
                "low_stock_count": low_stock,
            })

        return Response({"generated_at": timezone.now(), "results": results})


class DashboardOverviewView(APIView):
    """Manager-facing KPIs: today/week cash, active BAs, out-of-stock count."""
    permission_classes = [IsSupervisorOrAbove]

    def get(self, request):
        now = timezone.now()
        today_start = now - timedelta(hours=24)
        week_start = now - timedelta(days=7)

        sales_qs = Sale.objects.all()
        ba_qs = User.objects.filter(role="BA")
        stock_qs = InventoryItem.objects.all()
        checkins_qs = CheckIn.objects.all()

        if request.user.role == "SUPERVISOR":
            sales_qs = sales_qs.filter(ba__supervisor=request.user)
            ba_qs = ba_qs.filter(supervisor=request.user)
            stock_qs = stock_qs.filter(ba__supervisor=request.user)
            checkins_qs = checkins_qs.filter(ba__supervisor=request.user)

        today_total = sales_qs.filter(created_at__gte=today_start).aggregate(t=Sum("amount"))["t"] or 0
        week_total = sales_qs.filter(created_at__gte=week_start).aggregate(t=Sum("amount"))["t"] or 0
        active_today = checkins_qs.filter(created_at__gte=today_start).values("ba").distinct().count()
        out_of_stock = stock_qs.filter(quantity=0).count()

        top_bas = list(
            sales_qs.filter(created_at__gte=week_start)
            .values("ba_id", "ba__first_name", "ba__last_name", "ba__region__name")
            .annotate(total=Sum("amount"))
            .order_by("-total")[:5]
        )

        region_breakdown = list(
            sales_qs.filter(created_at__gte=week_start)
            .values(region_name=F("region__name"))
            .annotate(total=Sum("amount"))
            .order_by("-total")
        )

        return Response({
            "cash_today": today_total,
            "cash_last_7_days": week_total,
            "active_bas_today": active_today,
            "total_bas": ba_qs.count(),
            "out_of_stock_lines": out_of_stock,
            "top_brand_ambassadors": top_bas,
            "sales_by_region_7d": region_breakdown,
        })
