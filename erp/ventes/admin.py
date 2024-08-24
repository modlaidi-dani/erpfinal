from django.contrib import admin
from .models import BonSortie, ProduitsEnBonSortie, Facture, AvoirVente, ProduitsEnBonDevis, DemandeTransfert, BonGarantie, ProduitsEnBonGarantie

admin.site.register(BonSortie)
admin.site.register(ProduitsEnBonDevis)
admin.site.register(AvoirVente)
admin.site.register(Facture)
admin.site.register(ProduitsEnBonSortie)
admin.site.register(BonGarantie)
admin.site.register(ProduitsEnBonGarantie)
admin.site.register(DemandeTransfert)

