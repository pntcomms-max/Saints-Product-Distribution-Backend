from rest_framework import serializers
from .models import InventoryItem


class InventoryItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    ba_name = serializers.CharField(source="ba.get_full_name", read_only=True)
    region = serializers.CharField(source="ba.region.name", read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = InventoryItem
        fields = [
            "id", "ba", "ba_name", "region", "product", "product_name",
            "quantity", "low_stock_threshold", "status", "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]
