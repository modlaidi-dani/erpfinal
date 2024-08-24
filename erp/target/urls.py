from django.urls import path

from . import views

urlpatterns = [
    path('target',views.targetView.as_view(), name='target'),
    path('targetetat',views.targetStateView.as_view(), name='stat-target'),
    path('equipes',views.EquipesView.as_view(), name='equipes'),
    path('ajouterEquipe/',views.createEquipe, name='create-equipe'), 
    path('supprimerEquipe/',views.deleteEquipe, name='delete-equipe'), 
    path('modifierEquipe/',views.editEquipe, name='edit-equipe'), 
    path('DeleteTarget/',views.deleteTarget, name='deleteTarget'), 
    path('edit-Target/<str:bill_id>', views.targetEditView.as_view(), name="edit-target"),
    path('DeletePrevision/',views.deletePrevision, name='deletePrevision'), 
    path('previsionGlobale', views.PrevisionGlobaleView.as_view(), name="prev-global"),
    path('statsTarget/<str:target_id>',views.targetstat.as_view(), name='stats-target'), 
    path('etatPrevisions',views.PrevisionStateView.as_view(), name='stat-previsions'),
    path('Prevision',views.PrevisionView.as_view(), name='new-prevision'),
    path('regions',views.RegionsView.as_view(), name='regions'),
    path('supprimerRegion/',views.deleteRegion, name='delete-region'), 
    path('supprimerPrevisionGlobale/',views.deletePrevisionGlobale, name='delete-previsiong'), 
    path('modifierRegion/',views.editRegion, name='edit-region'), 
    path('statsPrevision/<str:target_id>',views.PrevisionState.as_view(), name='stats-prevision'), 
    path('statsPrevision/<str:prevision_id>/<str:wilaya>',views.PrevisionWilayaState.as_view(), name='stats-wilaya-prevision'), 
]