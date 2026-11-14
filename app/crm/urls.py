from django.urls import path

from . import views

app_name = "crm"
urlpatterns = [
    path("", views.kanban, name="kanban"),
    path("oportunidad/<int:pk>/mover/", views.mover, name="mover"),
]
