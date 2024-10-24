import csv
from decimal import Decimal
import time

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut  # Import GeocoderTimedOut exception

from ...models import Station


class Command(BaseCommand):
    """Import stations from csv file"""

    help = "Import fuel stations from CSV file"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to the CSV file")

    def handle(self, *args, **options):
        geolocator = Nominatim(user_agent="route_optimizer")
        stations: list[Station] = []

        with open(options["csv_file"], "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                opis_id = int(row["OPIS Truckstop ID"])

                # Check if station already exists
                try:
                    Station.objects.get(opis_id=opis_id)
                    self.stdout.write(
                        self.style.WARNING(
                            f"Station with OPIS ID {opis_id} already exists. Skipping."
                        )
                    )
                    continue
                except ObjectDoesNotExist:
                    pass

                # Geocode the address with rate limiting
                address = f"{row['Address']}, {row['City']}, {row['State']}"
                try:
                    location = geolocator.geocode(address)
                    time.sleep(1)  # Respect rate limits

                    if location:
                        station = Station(
                            opis_id=opis_id,
                            name=row["Truckstop Name"].strip(),
                            address=row["Address"].strip(),
                            city=row["City"].strip(),
                            state=row["State"].strip(),
                            rack_id=int(row["Rack ID"]),
                            price=Decimal(row["Retail Price"]),
                            location=Point(location.longitude, location.latitude),
                        )
                        stations.append(station)

                except GeocoderTimedOut as e:  # Catch specific exception
                    self.stdout.write(
                        self.style.WARNING(f"Failed to geocode {address}: {str(e)}")
                    )

            # Bulk create stations
            Station.objects.bulk_create(stations, ignore_conflicts=True)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully imported {len(stations)} new stations"
                )
            )
