from django.urls import path

from .views import RouteOptimizationView

urlpatterns = [
    path("optimize-route/", RouteOptimizationView.as_view(), name="optimize-route"),
]
