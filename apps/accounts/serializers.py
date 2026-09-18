from rest_framework import serializers
from .models import User, DeviceToken


class UserSerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source="region.name", read_only=True)
    supervisor_name = serializers.CharField(source="supervisor.get_full_name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "first_name", "last_name", "role", "phone",
            "region", "region_name", "supervisor", "supervisor_name",
            "is_active_field_agent", "must_change_password", "date_joined",
        ]
        read_only_fields = ["id", "date_joined"]


class SetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(min_length=1, write_only=True)


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = ["id", "token", "platform", "created_at"]
        read_only_fields = ["id", "created_at"]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "id", "username", "first_name", "last_name", "role", "phone",
            "region", "supervisor", "password",
        ]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
