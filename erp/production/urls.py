from django.urls import path

from . import views

urlpatterns = [
    path('ordreFabrication', views.OrdresFabricationPage.as_view(), name="ordres-fabrication"),
    path('EditordreFabrication/<str:ordre_id>', views.EditordreFabrication.as_view(), name="edit-ordre-fabrication"),
    path('fetchStockProduction', views.getStock, name="fetch-stocks-production"),
    path('DeleteOrdreFabrication/', views.deleteOrdres, name="delete-ordres-production"),
]