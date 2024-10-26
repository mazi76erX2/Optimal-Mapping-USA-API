from decimal import Decimal
from typing import Tuple

import requests
from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
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

    def geocode_station(self, station: Station) -> bool:
        """Geocode a station and update its location"""
        if station.location.x == 0 and station.location.y == 0:
            try:
                address = f"{station.address}, {station.city}, {station.state}"
                cache_key = f"geocode_{address}"
                cached_location = cache.get(cache_key)

                if cached_location:
                    station.location = cached_location
                    station.save()
                    return True

                url = f"{settings.MAP_QUEST_URL}/geocoding/v1/address"
                params = {
                    "key": self.map_quest_key,
                    "location": address,
                    "maxResults": 1,
                }

                response = requests.get(url, params=params, timeout=10)
                data = response.json()

                if data["results"] and data["results"][0]["locations"]:
                    location = data["results"][0]["locations"][0]["latLng"]
                    point = Point(location["lng"], location["lat"], srid=4326)
                    station.location = point
                    station.save()

                    # Cache the geocoded location
                    cache.set(cache_key, point, self.cache_timeout)
                    return True

            except Exception as e:
                print(f"Error geocoding station {station.opis_id}: {str(e)}")
                return False

        return True

    def get_route(self, start: str, end: str) -> Tuple[list[list[float]], float]:
        """Get route coordinates and total distance using MapQuest API"""
        cache_key = f"route_{start}_{end}"
        cached_result = cache.get(cache_key)

        if cached_result:
            return cached_result

        url = f"{settings.MAP_QUEST_URL}/directions/v2/route"
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

        # Geocode stations if needed
        geocoded_stations = []
        for station in stations:
            if self.geocode_station(station):
                geocoded_stations.append(station)

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
            for station in geocoded_stations
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
            start_point = Point(route_coords[0][1], route_coords[0][0], srid=4326)
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
            lat, lon = route_coords[position]
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
            self.geocode_station(station)  # Ensure station is geocoded

            return {
                "id": station.opis_id,
                "name": station.name,
                "address": station.address,
                "city": station.city,
                "state": station.state,
                "price": float(station.price),
                "location": {
                    "latitude": station.location.y,
                    "longitude": station.location.x,
                },
            }
        except Station.DoesNotExist:
            return None
