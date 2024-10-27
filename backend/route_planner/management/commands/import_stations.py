import csv
from decimal import Decimal

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from ...models import Station


class Command(BaseCommand):
    help = "Import stations from CSV file without geocoding"

    def handle(self, *args, **options):
        csv_file = options["csv_file"]

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
                reader = csv.DictReader(file)
                headers = reader.fieldnames

                # Validate CSV structure
                final_mappings = {}
                for model_field, possible_csv_fields in field_mappings.items():
                    for csv_field in possible_csv_fields:
                        if csv_field in headers:
                            final_mappings[model_field] = csv_field
                            break

                row_count = 0
                stations_added = 0
                for row in reader:
                    row_count += 1  # Moved counter here
                    try:
                        station_data = {}
                        for model_field, csv_field in final_mappings.items():
                            value = row[csv_field].strip()

                            if model_field in ["opis_id", "rack_id"]:
                                station_data[model_field] = int(value)
                            elif model_field == "price":
                                station_data[model_field] = Decimal(value)
                            else:
                                station_data[model_field] = value

                        # Set a default point
                        station_data["location"] = Point(0, 0, srid=4326)

                        # Create or update station
                        station, created = Station.objects.update_or_create(
                            opis_id=station_data["opis_id"], defaults=station_data
                        )
                        stations_added += 1

                        if row_count % 1000 == 0:  # Progress reporting
                            self.stdout.write(f"Processed {row_count} rows...")

                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Error processing row {row_count}: {str(e)}"
                            )
                        )

                self.stdout.write(f"{row_count} rows in CSV.")
                self.stdout.write(f"{stations_added} stations processed successfully.")

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"CSV file not found: {csv_file}"))
            return

        self.stdout.write(
            self.style.SUCCESS(f"{Station.objects.count()} stations in database.")
        )
        self.stdout.write(self.style.SUCCESS("Station import completed"))
