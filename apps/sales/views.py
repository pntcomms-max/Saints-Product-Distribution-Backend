from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from apps.accounts.permissions import RoleScopedQuerysetMixin
from .models import Sale
from .serializers import SaleSerializer, LogSaleSerializer


class SaleViewSet(RoleScopedQuerysetMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Sales are created only through `log_sale` (below), never via a raw
    POST to /sales/ — that keeps the stock-decrement guarantee in one place.
    """
    queryset = Sale.objects.select_related("ba", "product", "region").all()
    serializer_class = SaleSerializer
    filterset_fields = ["ba", "product", "region", "ba__region"]

    @action(detail=False, methods=["post"])
    def log_sale(self, request):
        serializer = LogSaleSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        try:
            sale = serializer.save()
        except ValueError as e:
            # record_sale_and_decrement_stock raises plain ValueError for
            # "not enough stock" — translate to a proper 400 instead of
            # letting it fall through as an unhandled 500.
            raise ValidationError({"quantity": str(e)})
        return Response(SaleSerializer(sale).data, status=201)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum
from .models import SalesOrder

class EndOfDayReconciliationView(APIView):
    """
    Submits and calculates daily sales totals vs physical handover totals
    """
    def get(self, request, rep_id):
        orders = SalesOrder.objects.filter(rep_id=rep_id, created_at__date=request.GET.get('date'))
        
        cash_total = orders.filter(payment_method='CASH').aggregate(Sum('total_amount'))['total_amount__sum'] or 0.00
        ecocash_total = orders.filter(payment_method='ECOCASH').aggregate(Sum('total_amount'))['total_amount__sum'] or 0.00
        credit_total = orders.filter(payment_method='CREDIT').aggregate(Sum('total_amount'))['total_amount__sum'] or 0.00
        
        return Response({
            "rep_id": rep_id,
            "cash_collected": cash_total,
            "ecocash_received": ecocash_total,
            "credit_issued": credit_total,
            "grand_total": cash_total + ecocash_total + credit_total
        },   status=status.HTTP_200_OK)