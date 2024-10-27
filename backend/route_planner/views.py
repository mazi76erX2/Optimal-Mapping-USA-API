from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .serializers import RouteRequestSerializer, RouteResponseSerializer
from .services import RouteOptimizer
from .models import Route
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError


class RouteOptimizationView(APIView):
    """
    API View for route optimization with fuel stop planning.
    """

    queryset = Route.objects.all()
    serializer_class = RouteRequestSerializer
    permission_classes = [AllowAny]

    def geocode_address(self, address):
        """Convert address to coordinates using Nominatim"""
        print(11111)
        geolocator = Nominatim(user_agent="my_route_optimizer")
        try:
            print(0)
            location = geolocator.geocode(address)
            if location:
                return [location.longitude, location.latitude]
            raise ValueError(f"Could not find coordinates for address: {address}")
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            raise ValueError(f"Geocoding service error: {str(e)}")

    @swagger_auto_schema(
        operation_description="Optimize route between two addresses and find optimal fuel stops",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["start_address", "end_address"],
            properties={
                "start_address": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Starting address",
                    example="350 5th Ave, New York, NY 10118",
                ),
                "end_address": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Ending address",
                    example="20 W 34th St, New York, NY 10001",
                ),
            },
        ),
        responses={
            200: RouteResponseSerializer,
            400: openapi.Response(
                description="Bad Request",
                examples={
                    "application/json": {
                        "error": "Invalid address provided or geocoding failed"
                    }
                },
            ),
            500: openapi.Response(
                description="Internal Server Error",
                examples={
                    "application/json": {"error": "An unexpected error occurred."}
                },
            ),
        },
    )
    def post(self, request):
        try:
            print(222222, flush=True)
            start_address = request.data.get("start_address")
            end_address = request.data.get("end_address")

            if not start_address or not end_address:
                return Response(
                    {"error": "Both start_address and end_address are required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                print(1, flush=True)

                start_coords = self.geocode_address(start_address)
                print(start_coords, flush=True)
                end_coords = self.geocode_address(end_address)
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            optimizer = RouteOptimizer()
            print(3, flush=True)

            route_coords, total_distance = optimizer.get_route(start_coords, end_coords)
            print(route_coords, total_distance, flush=True)
            optimal_stops, total_cost = optimizer.optimize_fuel_stops(
                route_coords, total_distance
            )

            response_data = {
                "start_address": start_address,
                "end_address": end_address,
                "route": route_coords,
                "total_distance": round(total_distance, 2),
                "fuel_stops": [
                    {
                        "name": stop.name,
                        "address": stop.address,
                        "city": stop.city,
                        "state": stop.state,
                        "price": stop.price,
                        "location": [stop.location.x, stop.location.y],
                    }
                    for stop in optimal_stops
                ],
                "total_fuel_cost": round(total_cost, 2),
            }
            print(response_data)

            response_serializer = RouteResponseSerializer(data=response_data)
            print(5)
            response_serializer.is_valid(raise_exception=True)
            print(6)
            return Response(response_serializer.data)

        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
