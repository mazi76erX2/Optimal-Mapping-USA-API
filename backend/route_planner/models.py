from dataclasses import dataclass
from decimal import Decimal

from django.contrib.gis.db import models
from django.contrib.gis.geos import Point


@dataclass
class FuelStation:
    """Data class for fuel station information"""

    id: int
    name: str
    address: str
    city: str
    state: str
    price: Decimal
    location: Point


class Station(models.Model):
    """Model for fuel station information"""

    opis_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    rack_id = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=8)
    location = models.PointField(srid=4326)

    class Meta:
        """Meta class for Station model"""

        indexes = [
            models.Index(fields=["state"]),
            models.Index(fields=["price"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} - {self.city}, {self.state}"
