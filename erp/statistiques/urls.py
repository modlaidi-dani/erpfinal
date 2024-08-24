from django.urls import path

from . import views

urlpatterns = [
    path('statsClients', views.statsClients.as_view(), name="stats-clients"),
    path('statsFournisseur', views.statsFournisseur.as_view(), name="stats-fournisseurs"),
    path('clientsCA', views.StastCaMa.as_view(), name="clients-CA"),
    path('clients104', views.statsClients104.as_view(), name="clients-104"),
    path('clientsProduits', views.statsClientsSold.as_view(), name="clients-produits"),
]