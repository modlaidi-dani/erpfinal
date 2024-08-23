from django.urls import path

from . import views

urlpatterns = [
    path('identification/<str:mag_id>', views.EntrepriseIdentificationView.as_view(), name='identification'),
    path('identification/<str:year>/<str:mag_id>', views.EntrepriseIdentificationView.as_view(), name='identification'),
    path('identification', views.EntrepriseIdentificationView.as_view(), name='identification'),
    path('newOrganization', views.NewStoreView.as_view(), name='new-org'),
    path('typeClient', views.TypeClientsView.as_view(), name="types-clients"),
    path('comptesTresorerie', views.comptesTresorerieView.as_view(), name="compte-tresorerie"),
    path('Edit-devise/<int:devise_id>', views.DeviseUpdateView.as_view(), name="update-devise"),
    path('Edit-TypeClient/<int:id_typecl>', views.TypeClientsUpdateView.as_view(), name="update-typeclient"),
    path('Devise', views.DeviseView.as_view(), name="devise-list"),
    path('DeviseValeurs', views.DeviseValueView.as_view(), name="devise-value-list"),
    path('taxes/<str:type_tax>', views.TaxesView.as_view(), name='taxes'),
    path('detail/<str:model_type>/<int:pk>/', views.DetailsPage.as_view(), name='detail'),
    path('DeleteTypes/', views.DeleteTypes, name='supprimer-types'),
    path('ModifierType/', views.ModifierType, name='edit-types'),
    path('editCompte/', views.ModifierCompte, name='edit-compte'),
    path('deleteCompte/', views.DeleteComptes, name='delete-compte'),
]