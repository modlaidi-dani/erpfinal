from django.urls import path

from . import views

urlpatterns = [
    path('',views.SellPointsView.as_view(), name='points-sell'),
    path('affectation',views.AffectationsView.as_view(), name='affectations'),
    path('emplacements',views.EmplacementView.as_view(), name='emplacements'),
    path('clotures',views.ClotureView.as_view(), name='clotures'),
    path('verify-password-collection/', views.verifyPassword, name="collect-cloture"),
    path('page-comptoire', views.ComtpoirView.as_view(), name="comptoire-page"),
    path('page-comptoire-rectif', views.ComtpoirRectificationView.as_view(), name="comptoire-rectif-page"),
    path('page-comptoire-full', views.ComtpoirViewFull.as_view(), name="full-comptoire-page"),
    path('retours-comptoir-full', views.ComtpoirRetourViewFull.as_view(), name="full-comptoire-retourpage"),
    path('retours-comptoir', views.ComtpoirRetourView.as_view(), name="comptoire-retourpage"),
    path('ajouterClient/', views.addClient, name="add-client"),
    path('fetchProductsComptoir/', views.fetchProductCompt, name="fetch-prod"),
    path('fidelites-clients/', views.ClientFideliteView.as_view(), name="fidelites"),
    path('supprimerPV/', views.deletePointSell, name="delete-ps"),
    path('modifierPV/', views.editPointVente, name="edit-ps"),
    path('supprimerAffect/', views.supprimerAffectation, name="delete-affectation"),
    path('modifierAffectation/', views.editAffectation, name="edit-aff"),
    path('modifierCloture/', views.editCloture, name="edit-aff"),
    path('supprimerCloture/', views.supprimerCloture, name="supp-cloture"),
    path('ReglementComptoire/', views.ReglementComptoir.as_view(), name="reglements-comptoire"),
]