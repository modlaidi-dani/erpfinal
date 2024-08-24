from django.contrib import admin
from .models import Reglement, ModeReglement, EcheanceReglement, mouvementCaisse, montantCollected, ClotureReglements

# Register your models here.
admin.site.register(Reglement)
admin.site.register(ModeReglement)
admin.site.register(EcheanceReglement)
admin.site.register(mouvementCaisse)
admin.site.register(montantCollected)
admin.site.register(ClotureReglements)