from django.conf import settings
from django.urls import include, path
from django.contrib import admin

from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

from search import views as search_views
import notifications.urls
from clientInfo import urls as clientInfo_urls
from users import urls as users_urls
from users import views as users_views
from tiers import urls as tiers_urls
from produits import urls as produits_urls
from inventory import urls as inventory_urls
from inventory import views as inventory_views
from achats import urls as achats_url
from ventes import urls as ventes_url
from reglements import urls as reglements_urls
from produits import views as produits_views
from comptoire import urls as comptoire_urls
from comptoire import views as comptoire_views
from users import views as users_views
from target import urls as target_urls
from statistiques import urls as statistique_urls
from logistique import urls as logistique_urls
from production import urls as production_urls
from production import views as productionviews
from gestionRH import urls as gestion_urls

urlpatterns = [
    path('control-yerisi-girilmez/clearcache/', include('clearcache.urls')),
    path("control-yerisi-girilmez/", admin.site.urls),
    path("girilmez/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("search/", search_views.search, name="search"),
    path("inbox/notifications/", include(notifications.urls, namespace='notifications')),
    path('home/', include(users_urls)),
    path('client/',include(clientInfo_urls)),
    path('tiers/',include(tiers_urls)),
    path('produits/', include(produits_urls)),
    path('view-product/<str:product_ref>/', produits_views.ProductDetailsView.as_view(), name='view-product'),
    path('stock/', include(inventory_urls)),
    path('ventes/', include(ventes_url)),
    path('achats/', include(achats_url)),
    path('reglements/', include(reglements_urls)),
    path('target/', include(target_urls)),
    path('statistiques/', include(statistique_urls)),
    path('comptoire/', include(comptoire_urls)),
    path('gestionRh/', include(gestion_urls)),
    path('accounts/login/', users_views.loginInto,name="accounts"),
    path('verify-password-validation/', inventory_views.verifyPassword, name="validate-bontr"),
    path('comptoire/fetchStock/', inventory_views.getStock, name="fetch-stocks"),
    path('mark_notification_as_read/', users_views.marknotificationread, name="mark-read"),
    path('logistiques/', include(logistique_urls)),
    path('production/', include(production_urls)),
    path('production/addOrdreFabrication/', productionviews.OrdresFabricationNew.as_view(), name='new-ordre-fabrication'),
    path('production/fetchStockProduction/', productionviews.getStock, name='fetch-stocks-production'),
    path('get_sales/', inventory_views.get_sales, name='get_sales'),
    path('logCordinates/', inventory_views.logCordinates, name='set_cord'),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns = urlpatterns + [
    # For anything not caught by a more specific rule above, hand over to
    # Wagtail's page serving mechanism. This should be the last pattern in
    # the list:
     path("", include(wagtail_urls)),
    # Alternatively, if you want Wagtail pages to be served from a subpath
    # of your site, rather than the site root:
    # path("pages/", include(wagtail_urls)),
]
