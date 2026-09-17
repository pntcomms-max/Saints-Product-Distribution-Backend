from rest_framework import serializers
from .models import Region, Manufacturer, Brand, Product


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ["id", "name"]


class ManufacturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Manufacturer
        fields = ["id", "name"]


class BrandSerializer(serializers.ModelSerializer):
    manufacturer_name = serializers.CharField(source="manufacturer.name", read_only=True)

    class Meta:
        model = Brand
        fields = ["id", "manufacturer", "manufacturer_name", "name"]


class ProductSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source="brand.name", read_only=True)
    manufacturer_name = serializers.CharField(source="brand.manufacturer.name", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "sku", "unit", "price", "is_active",
            "brand", "brand_name", "manufacturer_name",
        ]
