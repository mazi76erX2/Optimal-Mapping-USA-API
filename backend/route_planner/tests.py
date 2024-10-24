from decimal import Decimal
from unittest.mock import patch
from io import StringIO

from django.core.cache import cache
from django.contrib.gis.geos import Point
from django.core.management import call_command

import pytest

from .services import RouteOptimizer
from .models import Station


@pytest.fixture
def sample_stations():
    stations = [
        Station(
            opis_id=1,
            name="Test Station 1",
            address="123 Test St",
            city="TestCity",
            state="TX",
            rack_id=1,
            price=Decimal("3.50"),
            location=Point(-95.123, 29.456),
        ),
        Station(
            opis_id=2,
            name="Test Station 2",
            address="456 Test Ave",
            city="TestTown",
            state="TX",
            rack_id=2,
            price=Decimal("3.25"),
            location=Point(-95.234, 29.567),
        ),
    ]
    Station.objects.bulk_create(stations)
    return stations


@pytest.fixture
def mock_mapquest_response():
    return {
        "info": {"statuscode": 0},
        "route": {
            "distance": 1000,
            "shape": {
                "shapePoints": [
                    29.456,
                    -95.123,
                    29.567,
                    -95.234,
                ]
            },
        },
    }


@pytest.mark.django_db
class TestRouteOptimizer:
    """TestRoutOptimizer class"""

    def __init__(self):
        self.optimizer = RouteOptimizer()

    def setup_method(self):
        cache.clear()

    mock_mapquest_response = {
        "info": {"statuscode": 0},
        "route": {
            "distance": 1000,
            "shape": {
                "shapePoints": [
                    29.456,
                    -95.123,
                    29.567,
                    -95.234,
                ]
            },
        },
    }

    @patch("requests.get")
    def test_get_route(self, mock_get):
        mock_get.return_value.json.return_value = self.mock_mapquest_response

        coords, distance = self.optimizer.get_route("Houston, TX", "Dallas, TX")

        assert len(coords) == 2
        assert distance == 1000

        # Test caching
        cached_result = cache.get("route_Houston, TX_Dallas, TX")
        assert cached_result is not None
        assert cached_result == (coords, distance)

    def test_find_nearby_stations(self):
        point = Point(-95.123, 29.456)
        stations = self.optimizer.find_nearby_stations(point, max_distance=100)

        assert len(stations) == 2
        assert stations[0].price <= stations[1].price

    def test_optimize_fuel_stops(self):
        route_coords = [[29.456, -95.123], [29.567, -95.234]]
        total_distance = 400  # Within MAX_RANGE

        stops, cost = self.optimizer.optimize_fuel_stops(route_coords, total_distance)

        assert len(stops) == 1
        assert cost > 0


@pytest.mark.django_db
def test_import_stations_command():
    csv_content = """\
OPIS Truckstop ID,Truckstop Name,Address,City,State,Rack ID,Retail Price
7,WOODSHED OF BIG CABIN,"I-44, EXIT 283 & US-69",Big Cabin,OK,307,3.00733333
9,KWIK TRIP #796,"I-94, EXIT 143 & US-12 & SR-21",Tomah,WI,420,3.28733333
"""

    with patch("builtins.open", return_value=StringIO(csv_content)):
        with patch("geopy.geocoders.Nominatim.geocode") as mock_geocode:
            mock_geocode.side_effect = [
                Point(-95.123, 29.456),  # Mocked geocode result for the first station
                Point(-95.234, 29.567),  # Mocked geocode result for the second station
            ]

            call_command("import_stations", "dummy.csv")

            stations = Station.objects.all()
            assert stations.count() == 2

            first_station = stations.get(opis_id=7)
            assert first_station.name == "WOODSHED OF BIG CABIN"
            assert first_station.location == Point(-95.123, 29.456)

            second_station = stations.get(opis_id=9)
            assert second_station.name == "KWIK TRIP #796"
            assert second_station.location == Point(-95.234, 29.567)
