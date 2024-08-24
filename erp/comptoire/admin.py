from django.contrib import admin
from .models import pointVente, BonComptoire, AffectationCaisse, Cloture, ProduitsEnBonRetourComptoir, ProduitsEnBonComptoir, verssement, BonRetourComptoir

admin.site.register(pointVente)
admin.site.register(BonRetourComptoir)
admin.site.register(verssement)
admin.site.register(Cloture)
admin.site.register(AffectationCaisse)
admin.site.register(BonComptoire)
admin.site.register(ProduitsEnBonRetourComptoir)
admin.site.register(ProduitsEnBonComptoir)
# Register your models here.
