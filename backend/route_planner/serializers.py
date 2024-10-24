from rest_framework import serializers


class RouteRequestSerializer(serializers.Serializer):
    """RouteRequestSerializer class"""

    start = serializers.CharField()
    end = serializers.CharField()

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class StationSerializer(serializers.Serializer):
    """StationSerializer class"""

    name = serializers.CharField()
    address = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=8)
    location = serializers.ListField(
        child=serializers.FloatField(), min_length=2, max_length=2
    )

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class RouteResponseSerializer(serializers.Serializer):
    """RouteResponseSerializer class"""

    route = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField())
    )
    total_distance = serializers.FloatField()
    fuel_stops = StationSerializer(many=True)
    total_fuel_cost = serializers.FloatField()

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass
