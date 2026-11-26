from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health_view, name="health"),
    path("api/manutencoes/", views.manutencoes_view, name="manutencoes"),
    path("metrics", views.metrics_view, name="metrics"),
    path("metrics/", views.metrics_view, name="metrics_slash"),
]
