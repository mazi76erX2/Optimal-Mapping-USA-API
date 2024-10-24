from typing import Tuple

import requests
from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.core.cache import cache

from .models import Station, FuelStation


class RouteOptimizer:
    """Service to optimize fuel stops along a route"""

    def __init__(self):
        self.miles_per_gallon = settings.MILES_PER_GALLON
        self.max_range = settings.MAX_RANGE
        self.cache_timeout = settings.CACHE_TIMEOUT
        self.map_quest_key = settings.MAP_QUEST_API_KEY

    def get_route(self, start: str, end: str) -> Tuple[list[list[float]], float]:
        """Get route coordinates and total distance using MapQuest API"""
        cache_key = f"route_{start}_{end}"
        cached_result = cache.get(cache_key)

        if cached_result:
            return cached_result

        url = settings.MAP_QUEST_URL
        params = {
            "key": self.map_quest_key,
            "from": start,
            "to": end,
            "routeType": "fastest",
            "doReverseGeocode": False,
            "fullShape": True,
        }

        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data["info"]["statuscode"] != 0:
            raise ValueError(f"Route not found: {data['info']['messages']}")

        # Extract the route shape points
        shape_points = data["route"]["shape"]["shapePoints"]
        coordinates = []
        for i in range(0, len(shape_points), 2):
            coordinates.append([shape_points[i], shape_points[i + 1]])

        total_distance = data["route"]["distance"]

        result = (coordinates, total_distance)
        cache.set(cache_key, result, self.cache_timeout)

        return result

    def find_nearby_stations(
        self, point: Point, max_distance: float = 50
    ) -> list[FuelStation]:
        """Find fuel stations within max_distance miles of the given point"""
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

    def optimize_fuel_stops(
        self, route_coords: list[list[float]], total_distance: float
    ) -> Tuple[list[FuelStation], float]:
        """Find optimal fuel stops along the route"""
        if total_distance <= self.max_range:
            # Find single best station near the starting point
            start_point = Point(route_coords[0][1], route_coords[0][0], srid=4326)
            stations = self.find_nearby_stations(start_point)
            if not stations:
                return [], 0
            return [stations[0]], total_distance / self.miles_per_gallon * float(
                stations[0].price
            )

        num_stops = int(total_distance / self.max_range) + 1
        segment_length = total_distance / num_stops

        optimal_stops: list[FuelStation] = []
        total_cost = 0

        current_position = 0
        while current_position < len(route_coords):
            lat, lon = route_coords[current_position]
            point = Point(lon, lat, srid=4326)
            stations = self.find_nearby_stations(point)

            if stations:
                best_station = stations[0]
                optimal_stops.append(best_station)
                total_cost += (
                    segment_length / self.miles_per_gallon * float(best_station.price)
                )

            # Move to next segment
            current_position += int(len(route_coords) / num_stops)

        return optimal_stops, total_cost
