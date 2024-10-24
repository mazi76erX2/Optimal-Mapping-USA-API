#!/bin/sh

# Check if the database has started
if [ "$DATABASE" = "optimal-mapping" ]; then
    echo "Waiting for postgres..."

    while ! nc -z $DATABASE_HOST $DATABASE_PORT; do
        sleep 0.1
    done

    echo "PostgreSQL started"
fi

until cd /app/backend; do
    echo "Waiting for server volume..."
done

set -e

python manage.py migrate --noinput

# Path to the CSV file
CSV_FILE_PATH="/app/backend/fuel-prices-for-be-assessment.csv"

# Check if the CSV file exists and import if it does
if [ -f "$CSV_FILE_PATH" ]; then
    echo "CSV file found. Importing stations..."
    python manage.py import_stations "$CSV_FILE_PATH"
else
    echo "CSV file not found. Skipping import."
fi

exec "$@"