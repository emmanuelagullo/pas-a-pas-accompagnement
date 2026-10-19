from django.urls import path
from . import views

app_name = "personnes"
urlpatterns = [
    path("<uuid:pk>/fiche.pdf", views.fiche_pdf, name="fiche_pdf"),
    path("", views.liste, name="liste"),
    path("creer/", views.creer, name="creer"),
    path("<uuid:pk>/", views.detail, name="detail"),
]
