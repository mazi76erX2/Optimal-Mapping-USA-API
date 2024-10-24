# Optimal-Mapping-USA-API
An API that takes inputs of start and finish location both within the USA written in Django

## Guide

1. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows
```

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set up environment variables (copy .env.example to .env and fill in values)

3. Start services:

```bash
docker-compose up -d
```

4. Run migrations:

```bash
python manage.py migrate
```

5. Import stations:

```bash
python manage.py import_stations fuel-prices-for-be-assessment.csv
```

6. Run tests:

```bash
pytest
```

## API Usage

POST /api/optimize-route/

```json
{
    "start": "New York, NY",
    "end": "Los Angeles, CA"
}
```

Response:

```json
{
    "route": [[lat1, lon1], [lat2, lon2], ...],
    "total_distance": 2789.5,
    "fuel_stops": [
        {
            "name": "Station Name",
            "address": "Station Address",
            "city": "City",
            "state": "ST",
            "price": "3.499",
            "location": [lat, lon]
        }
    ],
    "total_fuel_cost": 975.33
}
```
