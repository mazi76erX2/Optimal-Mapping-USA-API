from decimal import Decimal
from unittest.mock import patch
from io import StringIO

from django.core.cache import cache
from django.contrib.gis.geos import Point
from django.core.management import call_command
from django.conf import settings

import pytest
import requests

from .services import RouteOptimizer
from .models import Station


@pytest.fixture
def sample_stations():
    """
    Fixture that creates and returns sample gas stations for testing.

    Returns:
        list: List of created Station objects with test data.
    """
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
def mock_mapquest_geocode_response():
    """
    Fixture that provides a mock MapQuest Geocoding API response.

    Returns:
        dict: Mocked response data structure.
    """
    return {"results": [{"locations": [{"latLng": {"lat": 29.456, "lng": -95.123}}]}]}


@pytest.fixture
def mock_mapquest_route_response():
    """
    Fixture that provides a mock MapQuest Directions API response.

    Returns:
        dict: Mocked response data structure.
    """
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
    """
    Test suite for the RouteOptimizer service class.

    Tests route calculation, station finding, and fuel stop optimization functionality.
    """

    def setup_method(self):
        """Set up test environment before each test method."""
        self.optimizer = RouteOptimizer()
        cache.clear()

    @patch("requests.get")
    def test_geocode_station(self, mock_get):
        """Test station geocoding functionality."""
        mock_get.return_value.json.return_value = mock_mapquest_geocode_response

        station = Station.objects.create(
            opis_id=3,
            name="Test Station 3",
            address="789 Test Rd",
            city="TestVille",
            state="TX",
            rack_id=3,
            price=Decimal("3.75"),
            location=Point(0, 0),
        )

        # Test successful geocoding
        result = self.optimizer.geocode_station(station)
        assert result is True
        assert station.location.x == -95.123
        assert station.location.y == 29.456

        # Test caching
        cache_key = f"geocode_789 Test Rd, TestVille, TX"
        assert cache.get(cache_key) is not None

        # Test error handling
        mock_get.side_effect = requests.exceptions.RequestException
        station.location = Point(0, 0)
        result = self.optimizer.geocode_station(station)
        assert result is False

    @patch("requests.get")
    def test_get_route(self, mock_get):
        """Test route retrieval and caching functionality."""
        mock_get.return_value.json.return_value = mock_mapquest_route_response

        coords, distance = self.optimizer.get_route("Houston, TX", "Dallas, TX")

        assert len(coords) == 2
        assert distance == 1000

        # Test caching
        cached_result = cache.get("route_Houston, TX_Dallas, TX")
        assert cached_result is not None
        assert cached_result == (coords, distance)

        # Test error handling
        mock_get.return_value.json.return_value = {
            "info": {"statuscode": 1, "messages": ["Error"]}
        }
        with pytest.raises(ValueError):
            self.optimizer.get_route("Invalid, XX", "Invalid, YY")

    def test_find_nearby_stations(self):
        """Test finding stations near a given point."""
        point = Point(-95.123, 29.456)
        stations = self.optimizer.find_nearby_stations(point, max_distance=100)

        assert len(stations) == 2
        assert stations[0].price <= stations[1].price

    def test_calculate_fuel_cost(self):
        """Test fuel cost calculation."""
        distance = 100
        price = Decimal("3.50")

        cost = self.optimizer.calculate_fuel_cost(distance, price)
        expected_cost = distance / settings.MILES_PER_GALLON * float(price)

        assert cost == expected_cost

    def test_optimize_fuel_stops(self):
        """Test optimization of fuel stops along a route."""
        route_coords = [[29.456, -95.123], [29.567, -95.234]]

        # Test single stop scenario
        total_distance = settings.MAX_RANGE - 50
        stops, cost = self.optimizer.optimize_fuel_stops(route_coords, total_distance)
        assert len(stops) == 1
        assert cost > 0

        # Test multiple stops scenario
        total_distance = settings.MAX_RANGE * 2.5
        stops, cost = self.optimizer.optimize_fuel_stops(route_coords, total_distance)
        assert len(stops) > 1
        assert cost > 0

    def test_get_station_details(self):
        """Test retrieving detailed station information."""
        # Test existing station
        details = self.optimizer.get_station_details(1)
        assert details is not None
        assert details["id"] == 1
        assert details["name"] == "Test Station 1"
        assert "location" in details

        # Test non-existent station
        details = self.optimizer.get_station_details(999)
        assert details is None


@pytest.mark.django_db
def test_import_stations_command():
    """Test the management command for importing stations from CSV."""
    csv_content = """\
OPIS Truckstop ID,Truckstop Name,Address,City,State,Rack ID,Retail Price
7,WOODSHED OF BIG CABIN,"I-44, EXIT 283 & US-69",Big Cabin,OK,307,3.00733333
9,KWIK TRIP #796,"I-94, EXIT 143 & US-12 & SR-21",Tomah,WI,420,3.28733333
"""

    with patch("builtins.open", return_value=StringIO(csv_content)):
        with patch("requests.get") as mock_get:
            mock_get.return_value.json.return_value = {
                "results": [
                    {"locations": [{"latLng": {"lat": 29.456, "lng": -95.123}}]}
                ]
            }

            call_command("import_stations", "dummy.csv")

            stations = Station.objects.all()
            assert stations.count() == 2

            first_station = stations.get(opis_id=7)
            assert first_station.name == "WOODSHED OF BIG CABIN"
            assert first_station.price == Decimal("3.00733333")

            second_station = stations.get(opis_id=9)
            assert second_station.name == "KWIK TRIP #796"
            assert second_station.price == Decimal
