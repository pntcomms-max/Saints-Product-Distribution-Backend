from rest_framework import serializers
from apps.catalog.models import Product
from .models import Sale, record_sale_and_decrement_stock


class SaleSerializer(serializers.ModelSerializer):
    ba_name = serializers.CharField(source="ba.get_full_name", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    region_name = serializers.CharField(source="region.name", read_only=True)

    class Meta:
        model = Sale
        fields = [
            "id", "ba", "ba_name", "product", "product_name", "region", "region_name",
            "quantity", "unit_price", "amount", "latitude", "longitude", "note", "created_at",
        ]
        read_only_fields = ["id", "unit_price", "amount", "region", "created_at"]


class LogSaleSerializer(serializers.Serializer):
    """Used by the `log_sale` action — the real-world entry point a BA hits."""
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.filter(is_active=True))
    quantity = serializers.IntegerField(min_value=1)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True, default="")

    def save(self, **kwargs):
        request = self.context["request"]
        return record_sale_and_decrement_stock(
            ba=request.user,
            product=self.validated_data["product"],
            quantity=self.validated_data["quantity"],
            latitude=self.validated_data.get("latitude"),
            longitude=self.validated_data.get("longitude"),
            note=self.validated_data.get("note", ""),
        )
