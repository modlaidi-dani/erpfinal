from django.contrib import admin
from .models import BonTransfert, Bonsortiedestock, ProduitsEnBonRetourAncien, BonReintegration, BonEntry, BonReforme, ProduitsEnBonMaintenance, BonRetour, BonRetourAncien, ProduitsEnBonTransfert, Stock, ProduitsEnBonReintegration, ProduitsEnBonRetour, Entrepot, BonMaintenance

# Register your models here.
admin.site.register(BonTransfert)
admin.site.register(BonMaintenance)
admin.site.register(Entrepot)
admin.site.register(Stock)
admin.site.register(Bonsortiedestock)
admin.site.register(BonReintegration)
admin.site.register(BonEntry)
admin.site.register(BonReforme)
admin.site.register(BonRetour)
admin.site.register(BonRetourAncien)
admin.site.register(ProduitsEnBonTransfert)
admin.site.register(ProduitsEnBonReintegration)
admin.site.register(ProduitsEnBonRetour)
admin.site.register(ProduitsEnBonMaintenance)
admin.site.register(ProduitsEnBonRetourAncien)