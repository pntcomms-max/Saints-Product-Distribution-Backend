from rest_framework import serializers
from .models import Region, Manufacturer, Brand, Product


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ["id", "name"]


class ManufacturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Manufacturer
        fields = ['id', 'name', 'contact_person', 'email', 'phone', 'is_active', 'created_at']


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
        fields = ('id', 'manufacturer', 'manufacturer_name', 'name', 'sku', 
            'unit_type', 'units_per_carton', 'cartons_per_case', 
            'wholesale_price', 'retail_price', 'is_active')
