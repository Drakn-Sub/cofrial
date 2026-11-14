from django.urls import path

from . import views

app_name = "logistica"
urlpatterns = [
    path("", views.torre_control, name="torre"),
    path("alerta/<int:pk>/tomar/", views.tomar_alerta, name="tomar"),
]
