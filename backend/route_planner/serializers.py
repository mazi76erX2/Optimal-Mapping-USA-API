from rest_framework import serializers


class RouteRequestSerializer(serializers.Serializer):
    start_address = serializers.CharField(
        max_length=255,
        help_text="Starting address (e.g., '350 5th Ave, New York, NY 10118')",
    )
    end_address = serializers.CharField(
        max_length=255,
        help_text="Ending address (e.g., '20 W 34th St, New York, NY 10001')",
    )

    def validate(self, attrs):
        """Validate that both addresses are provided"""
        if not attrs.get("start_address"):
            raise serializers.ValidationError("Start address is required")
        if not attrs.get("end_address"):
            raise serializers.ValidationError("End address is required")
        return attrs


class FuelStopSerializer(serializers.Serializer):
    name = serializers.CharField()
    address = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    price = serializers.FloatField()
    location = serializers.ListField(
        child=serializers.FloatField(), min_length=2, max_length=2
    )


class RouteResponseSerializer(serializers.Serializer):
    start_address = serializers.CharField()
    end_address = serializers.CharField()
    route = serializers.ListField(
        child=serializers.ListField(
            child=serializers.FloatField(), min_length=2, max_length=2
        )
    )
    total_distance = serializers.FloatField()
    fuel_stops = FuelStopSerializer(many=True)
    total_fuel_cost = serializers.FloatField()
