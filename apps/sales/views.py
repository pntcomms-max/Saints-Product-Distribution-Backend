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
