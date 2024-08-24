from django.urls import path

from . import views

urlpatterns = [
    path('fetchStock', views.getStock, name="fetch-stocks"),
    path('produits', views.ProduitsView.as_view(), name='produits'),
    path('EtatStockWeekly', views.EtatStockWeekly.as_view(), name='etat-stockweek'),
    path('QtysFacture', views.QuantiteFactureView.as_view(), name='qtys-facture'),
    path('addProduct', views.AddProductView.as_view(), name='new-product'),
    path('GetProductHistorique', views.FilltheProductHistory, name="getHistory"),
    path('ListePrix', views.PrixListView.as_view(), name='liste-prix'),
    path('archive-verification', views.ArchiveListView.as_view(), name='list-archive'),
    path('produitsVerification', views.ProduitsVerifView.as_view(), name='produits-verif'),
    path('MagproduitsVerification', views.ProduitsVerifMagView.as_view(), name='mag-produits-verif'),
    path('view-product/<str:product_ref>', views.ProductDetailsView.as_view(), name='view-product'),
    path('modifier-product/<str:product_ref>', views.ProductUpdateView.as_view(), name='update-product'),
    path('famillesProduits', views.FamilleView.as_view(), name="familles-list"),
    path('SupprimerProduit/', views.DeleteProductView, name="delete-produit"),   
    path('stockstate/', views.stockState.as_view(), name="state-stcok"),   
    path('editArchive/<str:archive_id>', views.UpdateArchiveMagView.as_view(), name="edit-archive"), 
    path('DeleteCategories/', views.supprimerCategorie, name="delete-category"),   
    path('ModifierFamille/', views.editCategory, name="edit-category"),   
    path('DeleteArchive/', views.supprimerArchive, name="supprimer-archive"),    
    path('fetchArchiveProducts/', views.getArchiveProducts, name="fetch-prods"),
    path('blockProduct/', views.ProductBlockView, name='block-product'),
    path('importProduct/', views.ImportProducts, name='import-product'),
    path('importProductPrice/', views.ImportProductsPrice, name='import-product-price'),
    path('importProductPriceCarton/', views.importProductPriceCarton, name='import-product-priceCart'),
    path('LoadOtherProducts', views.loadallProducts, name='load-products'),
    path('UpdateRepartition', views.UpdateRepartition, name='update-repartition'),
    path('LaunchPromotion', views.LaunchPromotion, name='lancer-promotion'),
]