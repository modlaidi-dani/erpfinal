from django.contrib import admin
from .models import BonTransport, FicheLivraisonExterne, CourseLivraison

admin.site.register(BonTransport)
admin.site.register(FicheLivraisonExterne)
admin.site.register(CourseLivraison)
# Register your models here.
