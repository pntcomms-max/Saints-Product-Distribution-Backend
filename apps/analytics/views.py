from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Count, F
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import IsSupervisorOrAbove
from apps.accounts.models import User
from apps.sales.models import Sale, SalesOrder
from apps.inventory.models import InventoryItem
from apps.tracking.models import CheckIn
from apps.catalog.models import Product


class ManufacturerDashboardView(APIView):
    """
    Analytics endpoint isolated per Manufacturer (e.g. CRP Cigarettes).
    """
    permission_classes = [IsSupervisorOrAbove]

    def get(self, request, manufacturer_id):
        orders = SalesOrder.objects.filter(
            orderitem__product__manufacturer_id=manufacturer_id
        ).distinct()

        total_revenue = orders.aggregate(total=Sum('total_amount'))['total'] or 0.00
        total_orders = orders.count()
        unique_outlets_reached = orders.values('customer_store').distinct().count()

        product_performance = Product.objects.filter(
            manufacturer_id=manufacturer_id
        ).annotate(
            total_units_sold=Sum('orderitem__quantity'),
            total_sales_value=Sum(F('orderitem__quantity') * F('wholesale_price'))
        ).values('id', 'name', 'sku', 'unit_type', 'total_units_sold', 'total_sales_value')

        return Response({
            "manufacturer_id": manufacturer_id,
            "overview": {
                "total_revenue": total_revenue,
                "total_orders_fulfilled": total_orders,
                "outlets_reached": unique_outlets_reached,
            },
            "product_breakdown": list(product_performance)
        }, status=status.HTTP_200_OK)


class DemandForecastView(APIView):
    """
    Predictive restock signal per product based on trailing sell-through rate.
    Uses GPS/sales_rep scoping rather than legacy regional groupings.
    """
    permission_classes = [IsSupervisorOrAbove]

    def get(self, request):
        window_days = int(request.query_params.get("window_days", 14))
        horizon_days = int(request.query_params.get("horizon_days", 7))
        cutoff = timezone.now() - timedelta(days=window_days)

        sales_qs = Sale.objects.filter(created_at__gte=cutoff)
        stock_qs = InventoryItem.objects.all()

        if request.user.role == "SUPERVISOR":
            sales_qs = sales_qs.filter(sales_rep__supervisor=request.user)
            stock_qs = stock_qs.filter(sales_rep__supervisor=request.user)

        sold_by_product = {
            row["product_id"]: row["total_qty"]
            for row in sales_qs.values("product_id").annotate(total_qty=Sum("quantity"))
        }

        stock_by_product = {
            row["product_id"]: row["total_qty"]
            for row in stock_qs.values("product_id").annotate(total_qty=Sum("quantity"))
        }

        products = Product.objects.filter(is_active=True)
        results = []

        for product in products:
            sold = sold_by_product.get(product.id, 0)
            daily_rate = sold / window_days
            projected = daily_rate * horizon_days
            on_hand = stock_by_product.get(product.id, 0)
            days_left = (on_hand / daily_rate) if daily_rate > 0 else (999 if on_hand > 0 else 0)

            if on_hand == 0 and sold == 0:
                continue

            results.append({
                "product": product.name,
                "product_id": product.id,
                "brand": product.brand.name if hasattr(product, 'brand') and product.brand else None,
                "manufacturer": product.manufacturer.name if hasattr(product, 'manufacturer') and product.manufacturer else None,
                "daily_rate": round(daily_rate, 2),
                "projected_need_horizon": round(projected, 1),
                "on_hand": on_hand,
                "days_left": round(days_left, 1) if days_left < 999 else None,
                "urgency": "CRITICAL" if days_left < 4 else ("WATCH" if days_left < 8 else "OK"),
            })

        results.sort(key=lambda r: r["days_left"] if r["days_left"] is not None else float("inf"))
        return Response({
            "window_days": window_days, 
            "horizon_days": horizon_days,
            "generated_at": timezone.now(), 
            "results": results,
        })


class LiveMapView(APIView):
    """
    GPS-centric live tracking map for sales reps / field agents.
    """
    permission_classes = [IsSupervisorOrAbove]

    def get(self, request):
        sales_reps = User.objects.filter(role__in=["SALES_REP", "BA"]).select_related("supervisor")
        if request.user.role == "SUPERVISOR":
            sales_reps = sales_reps.filter(supervisor=request.user)

        results = []
        for sales_rep in sales_reps:
            last_checkin = CheckIn.objects.filter(sales_rep=sales_rep).order_by("-created_at").first()
            today_total = Sale.objects.filter(
                sales_rep=sales_rep, 
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).aggregate(t=Sum("amount"))["t"] or 0
            
            out_of_stock = InventoryItem.objects.filter(sales_rep=sales_rep, quantity=0).count()
            low_stock = InventoryItem.objects.filter(sales_rep=sales_rep, quantity__gt=0, quantity__lte=5).count()
            is_stale = (not last_checkin) or (timezone.now() - last_checkin.created_at > timedelta(hours=6))

            results.append({
                "sales_rep_id": sales_rep.id,
                "name": sales_rep.get_full_name(),
                "supervisor_id": sales_rep.supervisor_id,
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
    """Manager/Supervisor KPIs using direct GPS/user tracking."""
    permission_classes = [IsSupervisorOrAbove]

    def get(self, request):
        now = timezone.now()
        today_start = now - timedelta(hours=24)
        week_start = now - timedelta(days=7)

        sales_qs = Sale.objects.all()
        sales_rep_qs = User.objects.filter(role__in=["SALES_REP", "BA"])
        stock_qs = InventoryItem.objects.all()
        checkins_qs = CheckIn.objects.all()

        if request.user.role == "SUPERVISOR":
            sales_qs = sales_qs.filter(sales_rep__supervisor=request.user)
            sales_rep_qs = sales_rep_qs.filter(supervisor=request.user)
            stock_qs = stock_qs.filter(sales_rep__supervisor=request.user)
            checkins_qs = checkins_qs.filter(sales_rep__supervisor=request.user)

        today_total = sales_qs.filter(created_at__gte=today_start).aggregate(t=Sum("amount"))["t"] or 0
        week_total = sales_qs.filter(created_at__gte=week_start).aggregate(t=Sum("amount"))["t"] or 0
        active_today = checkins_qs.filter(created_at__gte=today_start).values("sales_rep").distinct().count()
        out_of_stock = stock_qs.filter(quantity=0).count()

        top_sales_reps = list(
            sales_qs.filter(created_at__gte=week_start)
            .values("sales_rep_id", "sales_rep__first_name", "sales_rep__last_name")
            .annotate(total=Sum("amount"))
            .order_by("-total")[:5]
        )

        return Response({
            "cash_today": today_total,
            "cash_last_7_days": week_total,
            "active_bas_today": active_today,
            "total_bas": sales_rep_qs.count(),
            "out_of_stock_lines": out_of_stock,
            "top_sales_rep": top_sales_reps,
        })