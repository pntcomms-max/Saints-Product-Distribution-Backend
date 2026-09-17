from rest_framework import serializers
from .models import CheckIn


class CheckInSerializer(serializers.ModelSerializer):
    ba_name = serializers.CharField(source="ba.get_full_name", read_only=True)

    class Meta:
        model = CheckIn
        fields = ["id", "ba", "ba_name", "region", "latitude", "longitude", "accuracy_m", "source", "created_at"]
        read_only_fields = ["id", "ba", "region", "created_at"]

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["ba"] = request.user
        validated_data["region"] = request.user.region
        return super().create(validated_data)
