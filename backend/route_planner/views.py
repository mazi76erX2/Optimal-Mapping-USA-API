from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import RouteRequestSerializer, RouteResponseSerializer
from .services import RouteOptimizer


class RouteOptimizationView(APIView):
    """RouteOptimizationView DRF View"""

    def post(self, request):
        serializer = RouteRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        start = serializer.validated_data["start"]
        end = serializer.validated_data["end"]

        optimizer = RouteOptimizer()

        try:
            route_coords, total_distance = optimizer.get_route(start, end)
            optimal_stops, total_cost = optimizer.optimize_fuel_stops(
                route_coords, total_distance
            )

            response_data = {
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

            response_serializer = RouteResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)

            return Response(response_serializer.data)

        except (ValueError, KeyError, TypeError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
