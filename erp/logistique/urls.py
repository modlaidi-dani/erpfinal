from django.urls import path

from . import views

urlpatterns = [
   path('bons_transport', views.BonTransportListView.as_view(), name="bons-transport"),
   path('pageRequetes', views.RequetesPageView.as_view(), name="page-req"),
   path('pageFiches', views.FichesLivraisonView.as_view(), name="page-fiche"),
   path('pageCourseLivraison', views.PageCoursesLivraisonView.as_view(), name="page-courses"),
   path('PrepareStock/<str:id_bon>', views.PrepareStockView.as_view(), name="prepare-stock"),
   path('bonTransport', views.BonTransportView.as_view(), name="new-transport"),
   path('BonEnInstance', views.BillsNotPreparedView.as_view(), name="instance-bills"),
   path('NewRequete', views.RequeteView.as_view(), name="new-requete"),
   path('NewFiche', views.FicheView.as_view(), name="new-fiche"),
   path('LivraisonCourse', views.LivraisonCourseView.as_view(), name="new-course"),
   path('editRequete/<str:id_bon>', views.EditRequeteView.as_view(), name="edit-requete"),
   path('moyensTransport', views.MoyenTransportView.as_view(), name="moyen-transport"),
   path('reglementTransport', views.ReglementTransportView.as_view(), name="reglements-transport"),
   path('NumerSeries/', views.NumerSeriesView.as_view(), name="prepare-series"),
   path('fetchBills/', views.fetchBills, name="fetch-bills"),
   path('modifierReglement/', views.editReglement, name="edit-reg"),
   path('supprimerRequete/', views.supprimerRequete, name="supp-req"),
   path('supprimerCourses/', views.supprimerCourses, name="supp-crs"),
   path('supprimerReglement/', views.supprimerReglement, name="supp-reg"),
   path('supprimerMoyenTr/', views.supprimerMoyenTransport, name="supp-moy"),
   path('supprimerBonTr/', views.delete_transport_bill, name="supp-bon"),
   path('TrackUsers/', views.TrackUsersView.as_view(), name="track-users"),
]