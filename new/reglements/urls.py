from django.urls import path
from . import views

urlpatterns = [
    path('fetchMotifs', views.getMotifs, name="get-motifdep"),
    path('reglements',views.ReglementsView.as_view(), name='reglements'),
    path('HistoriqueMontantsView',views.HistoriqueMontantsView.as_view(), name='historique-montant'),
    path('reglementsToutModes',views.ReglementsView.as_view(), name='reglements-tt'),
    path('reglementsEspece',views.ReglementsEspeceView.as_view(), name='reglements-espece'),
    path('reglementsCheque',views.ReglementsChequeView.as_view(), name='reglements-cheque'),
    path('reglementsVirement',views.ReglementsVirementView.as_view(), name='reglements-virement'),
    path('reglements-fournisseur',views.ReglementsFournisseurView.as_view(), name='reglements-fournisseur'),
    path('reglements-facture',views.ReglementsFactureView.as_view(), name='reglements-factures'),
    path('newReglement',views.ReglementNewView.as_view(), name='new-reglement'),
    path('newReglementFournisseur',views.ReglementFournisseurNewView.as_view(), name='new-reglement-fournisseur'),
    path('newReglementFacture',views.ReglementNewFactureView.as_view(), name='new-reglement-facture'),
    path('typeReglements', views.TypeReglementsView.as_view(), name="types-reglements"),
    path('echeancesReglements', views.EcheanceReglementsView.as_view(), name="echeance"),
    path('etatReglementsBL', views.EtatRegBlView.as_view(), name="etat-reglement-BL"),
    path('etatReglementsBLFournisseur', views.EtatRegBlFournisseurView.as_view(), name="etat-reglement-BL-fournisseur"),
    path('etatReglementsfactures', views.EtatRegFaView.as_view(), name="etat-reglement-fa"),
    path('etatReglementsfacturesFournisseur', views.EtatRegFaFournisseurView.as_view(), name="etat-reglement-fa-fournisseur"),
    path('verify-password-collection/', views.verifyPassword, name="verify-password-collection"), 
    path('verify-password-collection-cloture/', views.verifyPasswordCloture, name="verify-password-collection-cloture"), 
    path('Mouvements-caisse', views.MouvementCaisseView.as_view(), name="mouvements-caisse"),
    path('supprimerMouvement/', views.supprimerMouvement, name="supprimer-mouvement"), 
    path('editMouvement/', views.editMouvement, name="edit-mouvement"), 
    path('etatTresorerie', views.EtatTresorerieView.as_view(), name="etat-tresorerie"),
    path('listeDepenses', views.DepensesListView.as_view(), name="list-depenses"),
    path('salaries', views.SalariesDetailView.as_view(), name="salaries-page"),
    path('loyers', views.LoyerDetailView.as_view(), name="loyers-page"),
    path('loyersEntretien', views.LoyerEntretienView.as_view(), name="loyers-entretien"),
    path('divers', views.DiversDetailView.as_view(), name="divers-page"),
    path('supprimerTypeDepense/', views.supprimerTypeDepense, name="supprimer-typedep"),
    path('modifierTypeDepense/', views.editType, name="modifier-typedep"),
    path('modifierDepense/', views.editDepense, name="modifier-dep"),
    path('supprimerDepense/', views.supprimerDepense, name="supprimer-depense"),
    path('addreglement/', views.saveReglement, name="add-reglement"),
    path('cloturesReglements',views.ClotureReglementsView.as_view(), name='clotures-comm'),
    path('update-reglement/<str:reglement_id>', views.ReglementUpdateView.as_view(), name="update-reglement"),
    path('DeleteReglements/', views.supprimerRegs, name="supprimer-regs"),
]