from django.core.management.base import BaseCommand
from route_planner.models import Station
from geopy.geocoders import MapQuest
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import csv
import time
import logging
import os
from django.contrib.gis.geos import Point
from decimal import Decimal

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import stations from CSV file"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", nargs="?", type=str, default="stations.csv")

    def geocode_with_retry(self, geolocator, address, max_retries=3):
        """Geocode with retry mechanism"""
        for attempt in range(max_retries):
            try:
                location = geolocator.geocode(address, timeout=3)
                return location
            except (GeocoderTimedOut, GeocoderUnavailable) as e:
                if attempt == max_retries - 1:
                    logger.error(
                        f"Failed to geocode after {max_retries} attempts: {address}"
                    )
                    raise
                time.sleep(2**attempt)
                continue

    def handle(self, *args, **options):
        csv_file = options["csv_file"]

        # Ensure MAP_QUEST_API_KEY is available
        map_quest_api_key = os.getenv("MAP_QUEST_API_KEY")
        if not map_quest_api_key:
            self.stdout.write(
                self.style.ERROR("MAP_QUEST_API_KEY environment variable is not set")
            )
            return

        # Define field mappings from CSV to model
        field_mappings = {
            "opis_id": ["OPIS Truckstop ID"],
            "name": ["Truckstop Name"],
            "address": ["Address"],
            "city": ["City"],
            "state": ["State"],
            "rack_id": ["Rack ID"],
            "price": ["Retail Price"],
        }

        try:
            with open(csv_file, "r", encoding="utf-8") as file:
                self.stdout.write(f"CSV file found. Importing stations...")

                reader = csv.DictReader(file)
                headers = reader.fieldnames
                self.stdout.write(f"CSV Headers found: {headers}")

                # Validate CSV structure and create field mapping
                final_mappings = {}
                missing_fields = []

                for model_field, possible_csv_fields in field_mappings.items():
                    found = False
                    for csv_field in possible_csv_fields:
                        if csv_field in headers:
                            final_mappings[model_field] = csv_field
                            found = True
                            break
                    if not found:
                        missing_fields.append(model_field)

                if missing_fields:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Missing required fields in CSV: {', '.join(missing_fields)}\n"
                            f"Required fields are: {', '.join(field_mappings.keys())}\n"
                            f"Found fields are: {', '.join(headers)}"
                        )
                    )
                    return

                # Initialize counters
                total_processed = 0
                total_success = 0
                total_failed = 0

                # Initialize MapQuest geocoder
                geolocator = MapQuest(api_key=map_quest_api_key, timeout=3)

                for row_number, row in enumerate(reader, start=2):
                    try:
                        total_processed += 1

                        # Map CSV fields to model fields with type conversion
                        station_data = {}
                        for model_field, csv_field in final_mappings.items():
                            value = row[csv_field].strip()

                            # Convert types based on field
                            if model_field in ["opis_id", "rack_id"]:
                                station_data[model_field] = int(value)
                            elif model_field == "price":
                                station_data[model_field] = Decimal(value)
                            else:
                                station_data[model_field] = value

                        # Validate required fields in row
                        empty_fields = [
                            field
                            for field, value in station_data.items()
                            if value is None
                        ]
                        if empty_fields:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Row {row_number}: Missing values for fields: {', '.join(empty_fields)}"
                                )
                            )
                            total_failed += 1
                            continue

                        # Construct address string
                        address_parts = [
                            station_data["address"],
                            station_data["city"],
                            station_data["state"],
                        ]
                        address = ", ".join(filter(None, address_parts))

                        # Debug output
                        self.stdout.write(
                            f"Processing row {row_number}: {station_data['name']} - {address}"
                        )

                        # Check if station already exists
                        if Station.objects.filter(
                            opis_id=station_data["opis_id"]
                        ).exists():
                            self.stdout.write(
                                f"Station with OPIS ID {station_data['opis_id']} already exists, skipping..."
                            )
                            continue

                        try:
                            location = self.geocode_with_retry(geolocator, address)

                            if location:
                                point = Point(
                                    location.longitude, location.latitude, srid=4326
                                )

                                # Create station with all required fields
                                station = Station.objects.create(
                                    **station_data, location=point
                                )
                                total_success += 1
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f"Created station: {station.name} at ({location.latitude}, {location.longitude})"
                                    )
                                )
                            else:
                                total_failed += 1
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"Could not geocode address: {address}"
                                    )
                                )

                        except (GeocoderTimedOut, GeocoderUnavailable) as e:
                            total_failed += 1
                            self.stdout.write(
                                self.style.ERROR(
                                    f"Geocoding error for {address}: {str(e)}"
                                )
                            )
                            continue

                    except Exception as e:
                        total_failed += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f"Error processing row {row_number}: {str(e)}\n"
                                f"Row data: {row}"
                            )
                        )
                        continue

                # Print summary
                self.stdout.write("\nImport Summary:")
                self.stdout.write(f"Total Processed: {total_processed}")
                self.stdout.write(f"Successfully Imported: {total_success}")
                self.stdout.write(f"Failed: {total_failed}")

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"CSV file not found: {csv_file}"))
            return

        self.stdout.write(self.style.SUCCESS("Station import completed"))
