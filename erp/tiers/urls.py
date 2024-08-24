from django.urls import path

from . import views

urlpatterns = [
   path('clients', views.ClientsDetailView.as_view(), name='customers'),
   path('clientsProspection', views.ClientsProspectionView.as_view(), name='customers-prospection'),
   path('fournisseurs', views.FournisseursDetailView.as_view(), name="fournisseurs"),
   path('addFournisseur/', views.createFournisseur, name='new-fournisseur'),
   path('banques', views.BanquesView.as_view(), name="banques"),
   path('agences', views.AgenceBancairesView.as_view(), name="agences"),
   path('comptesBancaires', views.ComptesBancairesView.as_view(), name="comptesBancaires"),
   path('supprimerClient/', views.supprimerClient, name="supprimer-client"),
   path('supprimerFournisseur/', views.supprimerFournisseur, name="supprimer-fournisseur"),
   path('modifierFournisseur/', views.editFournisseur, name="modifier-fournisseur"),
   path('supprimerBanque/', views.supprimerBanque, name="supprimer-banque"),
   path('modifierBanque/', views.editBanque, name="modifier-banque"),
   path('modifierClient/', views.editClient, name="modifier-client"),
   path('VerifyClient/', views.VerifyClient, name="verifier-client"),
   path('ImportClients/', views.importClients, name="import-clients"),
   path('ajouterClient/', views.ClientAddView.as_view(), name="ajoutertiers-client"),
]