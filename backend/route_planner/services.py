from decimal import Decimal
from typing import Tuple, List
import requests
from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point, LineString
from django.contrib.gis.measure import D
from django.core.cache import cache

from .models import FuelStation, Station


class RouteOptimizer:
    """Service to optimize fuel stops along a route"""

    def __init__(self):
        self.miles_per_gallon = settings.MILES_PER_GALLON
        self.max_range = settings.MAX_RANGE
        self.cache_timeout = settings.CACHE_TIMEOUT
        self.map_quest_key = settings.MAP_QUEST_API_KEY

    def get_route(
        self, start_coords: List[float], end_coords: List[float]
    ) -> Tuple[list[list[float]], float]:
        """Get route coordinates and total distance using MapQuest API"""
        print("Get Route", start_coords, end_coords, flush=True)
        cache_key = f"route_{start_coords}_{end_coords}"
        print("cache_key", flush=True)
        print(cache_key, flush=True)
        # cached_result = cache.get(cache_key)
        # print(cached_result, flush=True)

        # if cached_result:
        #     return cached_result
        print("Cached", flush=True)

        url = f"{settings.MAP_QUEST_URL}/directions/v2/route"
        params = {
            "key": self.map_quest_key,
            "from": f"{start_coords[1]},{start_coords[0]}",  # lat,lon
            "to": f"{end_coords[1]},{end_coords[0]}",  # lat,lon
            "routeType": "fastest",
            "doReverseGeocode": False,
            "fullShape": True,
        }

        response = requests.get(url, params=params, timeout=10)
        # print(response, flush=True)
        data = response.json()
        print(data, flush=True)
        # print(data["info"]["statuscode"], flush=True)

        # if data["info"]["statuscode"] != 0:
        #     raise ValueError(f"Route not found: {data['info']['messages']}")

        # Extract the route shape points
        shape_points = data["route"]["shape"]["shapePoints"]
        coordinates = []
        for i in range(0, len(shape_points), 2):
            coordinates.append(
                [shape_points[i + 1], shape_points[i]]
            )  # Convert to [lon, lat]

        total_distance = data["route"]["distance"]

        result = (coordinates, total_distance)
        cache.set(cache_key, result, self.cache_timeout)

        return result

    def find_nearby_stations(
        self, point: Point, max_distance: float = 50
    ) -> list[FuelStation]:
        """Find fuel stations within max_distance miles of the given point"""
        print("Find")
        stations = (
            Station.objects.annotate(distance=Distance("location", point))
            .filter(location__distance_lte=(point, D(mi=max_distance)))
            .order_by("price", "distance")[:5]
        )

        return [
            FuelStation(
                id=station.opis_id,
                name=station.name,
                address=station.address,
                city=station.city,
                state=station.state,
                price=station.price,
                location=station.location,
            )
            for station in stations
        ]

    def calculate_fuel_cost(self, distance: float, price: Decimal) -> float:
        """Calculate fuel cost for a given distance and price"""
        return distance / self.miles_per_gallon * float(price)

    def optimize_fuel_stops(
        self, route_coords: list[list[float]], total_distance: float
    ) -> Tuple[list[FuelStation], float]:
        """Find optimal fuel stops along the route"""
        if total_distance <= self.max_range:
            # Find single best station near the starting point
            start_point = Point(route_coords[0][0], route_coords[0][1], srid=4326)
            stations = self.find_nearby_stations(start_point)
            if not stations:
                return [], 0
            return [stations[0]], self.calculate_fuel_cost(
                total_distance, stations[0].price
            )

        # Calculate number of stops needed
        num_stops = int(total_distance / self.max_range) + 1
        segment_length = total_distance / num_stops

        optimal_stops: list[FuelStation] = []
        total_cost = 0

        # Find stops at regular intervals
        for i in range(num_stops):
            position = int((i * len(route_coords)) / num_stops)
            lon, lat = route_coords[position]
            point = Point(lon, lat, srid=4326)
            stations = self.find_nearby_stations(point)

            if stations:
                best_station = stations[0]
                # Avoid duplicate stations
                if not optimal_stops or best_station.id != optimal_stops[-1].id:
                    optimal_stops.append(best_station)
                    total_cost += self.calculate_fuel_cost(
                        segment_length, best_station.price
                    )

        return optimal_stops, total_cost

    def get_station_details(self, station_id: int) -> dict:
        """Get detailed information about a specific station"""
        try:
            station = Station.objects.get(opis_id=station_id)
            return {
                "id": station.opis_id,
                "name": station.name,
                "address": station.address,
                "city": station.city,
                "state": station.state,
                "price": float(station.price),
                "location": {
                    "longitude": station.location.x,
                    "latitude": station.location.y,
                },
            }
        except Station.DoesNotExist:
            return None
