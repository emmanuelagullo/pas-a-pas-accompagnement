from django.urls import path
from . import views

app_name = "personnes"
urlpatterns = [
    path("", views.liste, name="liste"),
    path("creer/", views.creer, name="creer"),
    path("<uuid:pk>/", views.detail, name="detail"),
]
