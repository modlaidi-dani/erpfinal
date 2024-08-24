from django.urls import path

from . import views

urlpatterns = [
   path('avoirsachats', views.AvoirListView.as_view(), name="list-avoirs-achats"),
   path('ListeProjets', views.ProjetListView.as_view(), name="list-projets"),
   path('AjouterProjet', views.ProjetListView.as_view(), name="new-project"),
   path('new-achat', views.StockAchatView.as_view(), name='new-achat'),
   path('EditBillAchat/<int:id_bill>', views.BonAchatUpdateView.as_view(), name='update-achat'),
   path('Dossier-achat', views.DossierAchatView.as_view(), name='dossier-achat'),
   path('new-commande', views.CommandeAchatView.as_view(), name='new-command'),
   path('new-facture', views.FactureAchatView.as_view(), name='new-facture-achat'),
   path('fetchProductsAchat/', views.fetchProductsAchat, name='fetch-bill-products'),
   path('listLivraisonFournisseur', views.ListAchatView.as_view(), name='list-achat'),
   path('listFactureFournisseur', views.ListFactureView.as_view(), name='list-factures-achats'),
   path('listCommandesFournisseur', views.ListCommandesView.as_view(), name='list-commandes'),
   path('listeDossiersAchat', views.ListDossierAchatView.as_view(), name='list-dossier-achat'),
   path('listReceptionsFournisseur', views.ListReceptionView.as_view(), name='list-receptions'),
   path('listExpedition', views.ListExpeditionView.as_view(), name='list-expeditions'),
   path('NewExpedition', views.ExpeditionView.as_view(), name='new-expedition'),
   path('ReceptionFournisseur', views.ReceptionView.as_view(), name='new-reception'),
   path('DeleteAchat/', views.supprimerBonAchat, name='delete-achat'),
   path('DeleteProjet/', views.supprimerProjet, name='delete-projet'),
]