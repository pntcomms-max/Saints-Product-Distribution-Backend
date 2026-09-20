from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import RoleScopedQuerysetMixin
from .models import InventoryItem, StockTransfer, StockTransferStatus
from .serializers import InventoryItemSerializer


class InventoryItemViewSet(RoleScopedQuerysetMixin, viewsets.ModelViewSet):
    """
    ViewSet for tracking inventory items per sales rep / warehouse node.
    Automatically role-scoped via RoleScopedQuerysetMixin.
    """
    queryset = InventoryItem.objects.select_related("sales_rep", "sales_rep__region", "product").all()
    serializer_class = InventoryItemSerializer
    filterset_fields = ["sales_rep", "product", "sales_rep__region"]
    permission_classes = [IsAuthenticated]


class AcceptVanStockTransferView(APIView):
    """
    Called by the Sales Rep mobile app to sign off and accept stock loaded into their van.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, transfer_id):
        try:
            # Ensures the transfer belongs to the logged-in sales rep and is still pending
            transfer = StockTransfer.objects.get(
                id=transfer_id,
                sales_rep=request.user,
                status=StockTransferStatus.PENDING
            )
            transfer.status = StockTransferStatus.ACCEPTED
            transfer.accepted_at = timezone.now()
            transfer.save()
            
            # Stock levels automatically shift from Main Depot -> Transit Van via model signals
            return Response(
                {"status": "SUCCESS", "message": "Van stock handover accepted successfully."},
                status=status.HTTP_200_OK
            )
        except StockTransfer.DoesNotExist:
            return Response(
                {"error": "Pending transfer not found or already processed."},
                status=status.HTTP_404_NOT_FOUND
            )