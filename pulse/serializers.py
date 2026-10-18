from django.contrib.auth.models import User
from rest_framework import serializers

from .models import PriceAlert


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['username', 'password', 'email']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class PriceAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceAlert
        fields = ['id', 'origin', 'destination', 'threshold_price', 'status', 'created_at']
        read_only_fields = ['id', 'status', 'created_at']

    def validate_threshold_price(self, value):
        if value <= 0:
            raise serializers.ValidationError('Must be greater than zero.')
        return value

    def validate_origin(self, value):
        return value.upper()

    def validate_destination(self, value):
        return value.upper()