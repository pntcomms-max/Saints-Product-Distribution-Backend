from rest_framework import serializers
from .models import Alert


class AlertSerializer(serializers.ModelSerializer):
    ba_name = serializers.CharField(source="ba.get_full_name", read_only=True)
    region_name = serializers.CharField(source="ba.region.name", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = Alert
        fields = [
            "id", "kind", "ba", "ba_name", "region_name", "product", "product_name",
            "message", "created_at", "resolved_at",
        ]
        read_only_fields = fields
