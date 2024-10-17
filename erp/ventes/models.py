from django.db import models
from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.snippets.models import register_snippet
from django.contrib.auth.models import Permission
from users.models import CustomUser
from django.utils import timezone
from django.http import JsonResponse
from datetime import datetime
from django.db.models import Sum
from decimal import Decimal
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
import ast

class VentesCustomPermission(Permission):
    class Meta:
        verbose_name = 'Custom Permission'
        verbose_name_plural = 'Custom Permissions'

class validationBl(models.Model):
    type_validation = models.CharField(max_length=25, default='', blank=True, null=True )
    percentage =  models.DecimalField(max_digits=15, decimal_places=2, default=0)
    codeBl = models.CharField(max_length=25, default='', blank=True, null=True )
    montantBl = models.DecimalField(max_digits=150, decimal_places=2, default=0)
    solde_note = models.DecimalField(max_digits=150, decimal_places=2, default=0)
    user = models.ForeignKey(CustomUser,on_delete = models.CASCADE, related_name='mes_validation', blank=True, null=True, default=None)
    client_name =  models.CharField(max_length=25, default='', blank=True, null=True )
    
    @property
    def get_datebill(self):
        bill = BonSortie.objects.get(idBon = self.codeBl, client__name=self.client_name, store__id = 1)
        return bill.dateBon
    
class BonSortie(models.Model):
    Reglement_etat_CHOICES = [
        ("non-regle", "non-regle"),
        ("regle", "regle"),     
    ]
    idBon = models.CharField(
          ("id Bon"), 
          max_length=200,
          blank=False,
          null=False,
          unique=False
    )    
    dateBon =models.DateField()
    client =models.ForeignKey('tiers.Client',on_delete = models.CASCADE, related_name='client_bonS')
    totalPrice = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    user =models.ForeignKey(CustomUser,on_delete = models.CASCADE, related_name='mes_bons', blank=True)
    entrepot = models.ForeignKey('inventory.Entrepot', on_delete=models.CASCADE,related_name='entrepot_bons', default=None, blank=True, null=True)
    mode_reglement = models.ForeignKey('reglements.ModeReglement', on_delete = models.CASCADE, related_name='bonL_reglements_type', null=True, blank=True, default=None)
    echeance_reglement = models.ForeignKey('reglements.EcheanceReglement', on_delete = models.CASCADE, related_name='bonL_reglements_echeance', null=True, blank=True, default=None)
    banque_Reglement = models.ForeignKey('tiers.Banque', on_delete=models.CASCADE, related_name='banque_reglements_bonL', blank=True, null=True, default=None )
    num_cheque_reglement = models.CharField(max_length=2500 , default="", null=True, blank =True)
    Remise = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    agenceLivraison = models.CharField(max_length=2500 , default="", null=True, blank =True)
    fraisLivraison = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    fraisLivraisonexterne = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    note = models.TextField(default="")
    valide = models.BooleanField(default=False)
    ferme =  models.BooleanField(default=False)
    modifiable = models.BooleanField(default=False)
    confirmed = models.BooleanField(default=True)
    livre = models.BooleanField(default=False)
    typebl = models.CharField(max_length=200, blank=True, null=True, default='')
    reference_pc = models.CharField(max_length=200, blank=True, null=True, default='') 
    name_pc = models.CharField(max_length=200, blank=True, null=True, default='') 
    store = models.ForeignKey('clientInfo.store', on_delete = models.CASCADE, related_name='bonL_store', null=True, blank=True, default=None)
    
    @property
    def confirmationFile(self):
        if len(self.confrimation_bon.all()) > 0:
            return self.confrimation_bon.first().fichier_confirmation.url
        else:
            return ''
            
    @property
    def confirmationDateTime(self):
        if len(self.confrimation_bon.all()) > 0:
            return self.confrimation_bon.first().dateConfirmation
        else:
            return ''
            
    @property
    def ValidatePar(self):
        validation_object = validationBl.objects.filter(codeBl = self.idBon).first()
        if validation_object is not None:
            return validation_object.user.username
        else: 
            return ''
            
    @property
    def statebill(self):
        if len(self.bon_garantie.all()) == 0 and len(self.bonsL_transports.all()) == 0:
            return 'attente-prep'
        elif len(self.bon_garantie.all()) > 0 and len(self.bonsL_transports.all()) == 0:   
            return 'prep-nonliv' 
        elif len(self.bon_garantie.all()) == 0 and len(self.bonsL_transports.all()) > 0:   
            return 'liv-nonprep' 
        elif len(self.bon_garantie.all()) > 0 and len(self.bonsL_transports.all()) > 0:   
            return 'livre' 
            
    @property
    def formatted_date(self):
        return self.dateBon.strftime('%d/%m/%Y')
        
    def get_produits(self):
         return self.produits_en_bon_sorties.all()
         
    @property
    def get_total_price(self):
        price_part = self.produits_en_bon_sorties.aggregate(total_price=Sum('totalprice'))['total_price']
        total_price = float(price_part) if price_part is not None else float(0)
        
        return total_price
        
    @property
    def garantieprepared(self):
        return len(self.bon_garantie.all()) > 0
        
    @property
    def my_tax(self):
        tax = 0
        for produit in self.produits_en_bon_sorties.all():
            tax += (produit.stock.tva_douan * produit.quantity)
        return round(tax,2)  
        
    @property
    def get_references(self):
        if self.reference_pc != '':
            result_list = []
            if "[" in str(self.reference_pc):
                result_list = ast.literal_eval(self.reference_pc)
                return result_list
            else:
                result_list.append(self.reference_pc)
                return result_list
        else:
            return []
        
    @property
    def get_designations(self):
        result_list = []
        if self.name_pc != '':
            if "[" in str(self.name_pc):
                result_list = ast.literal_eval(self.name_pc)
                return result_list
            else:
                result_list.append(self.name_pc)
                return result_list
        else:
            return []
            
    @property
    def get_etat_transfert(self):
        mon_etat = DemandeTransfert.objects.filter(BonSNo=self).first()
        if mon_etat is not None:
            return mon_etat.etat.lower() == 'true'
        else:
            return True
            
    @property 
    def price_annule(self):
        if len(self.MesbonRetours.all())>0:
            filtered_bons_retour = [bon for bon in self.MesbonRetours.filter(valide=True) if bon.reintegrated]
            result_sum = sum(Decimal(bon.total_price_retour) * Decimal(1.19) for bon in filtered_bons_retour)
            return result_sum
        else:
            return 0
            
    @property
    def get_total_soldprice(self):
        price_part = self.produits_en_bon_sorties.aggregate(total_price=Sum('totalprice'))['total_price']

        if price_part is not None:
            total_price = round((price_part - Decimal(self.Remise)) * Decimal('1.19') , 2)
            return round(total_price, 2) if total_price is not None else 0.00
        else:
            return 0.00
    
    @property
    def total_paid_amount(self):
        return sum(reglement.montant for reglement in self.bonS_reglements.all())
    
    @property
    def total_remaining_amount(self):
        # Assuming get_total_price is a Decimal field
        total_price = Decimal(self.get_total_price)
        remise = Decimal(self.Remise)
        total_paid_amount = Decimal(self.total_paid_amount)

        return  round(((total_price - remise) * Decimal('1.19')) - total_paid_amount, 2)
    
    @property
    def regle(self):
       return round(self.get_total_soldprice,0) == round(self.total_paid_amount,0)
       
    @property   
    def caisseBons(self):
        reglements = sum(reglement.montant for reglement in self.bonS_reglements.all())
        caisse = None
        if reglements != 0 :
            caisse = self.bonS_reglements.first().CompteEntreprise
            return caisse
            
    @property
    def ma_marge(self):
        # All products in the current BonSortie
        products = self.produits_en_bon_sorties.all()
        
        # Set to hold all products from BonRetours linked to the current BonSortie
        excluded_products = set()

        # Find all products in ProduitsEnBonRetour where the BonRetour is linked to the current BonSortie
        related_bon_retours = self.MesbonRetours.all()
        for bon_retour in related_bon_retours:
            for product in bon_retour.produits_en_bon_retour.all():
                excluded_products.add(product.produit.id)  # Store product ids to be excluded

        margin = 0
        for p in products:
            # Only include in margin calculation if not in excluded_products
            if p.stock.id not in excluded_products:
                margin += ((p.stock.prix_vente - p.stock.prix_achat) * p.quantity)
        
        return round(margin, 2)
      
    def get_mystore(self):
        my_products= self.produits_en_bon_sorties.all()
        for product in my_products:
            stock= product.stock.get_Monstock()
            store = stock.entrepot.store
            return store
    
    def __str__(self):
	    return "Bon no: " + str(self.idBon) + "CLient store: " + str(self.client.store.id) +  "BL Store : " + str(self.store.id)
    

class DemandeTransfert(models.Model):
    BonSNo = models.ForeignKey(BonSortie, on_delete = models.CASCADE, related_name='demande_sortie_transfert')
    BonTransfert = models.ForeignKey('inventory.BonTransfert', on_delete = models.CASCADE, related_name='demande_transfert')
    etat = models.CharField(max_length=150, default='', blank=True, null=True)
    
class ConfirmationBl(models.Model):
    BonNo = models.ForeignKey(BonSortie, on_delete = models.CASCADE, related_name='confrimation_bon')
    dateConfirmation =models.DateTimeField()
    dateLivraisonPrevu=models.DateField()
    fichier_confirmation = models.FileField(upload_to="media/document")
    
class ProduitsEnBonSortie(models.Model):
    BonNo = models.ForeignKey(BonSortie, on_delete = models.CASCADE, related_name='produits_en_bon_sorties')
    stock = models.ForeignKey('produits.Product', on_delete = models.CASCADE, related_name='bons_sortie')
    kit = models.TextField(default="")
    quantity = models.IntegerField(default=1)
    unitprice = models.DecimalField(max_digits=15, decimal_places=2)
    totalprice = models.DecimalField(max_digits=15, decimal_places=2)   
    entrepot = models.ForeignKey('inventory.Entrepot', on_delete = models.CASCADE, related_name='mesproduit_bons_sortie', default=None, blank=True, null=True)
    def __str__(self):
	    return "Bon no: " + str(self.BonNo.idBon) + ", Item = " + self.stock.name
	    
    @property
    def getnumSeries(self):
        # Access the associated BonGarantie
        bon_garantie = self.BonNo.bon_garantie.first()
        
        # If bon_garantie is None, return an empty list
        if bon_garantie is None:
            return []
        
        
        # Filter ProduitsEnBonGarantie by product and get their numSeries
        num_series_list = bon_garantie.produits_en_bon_garantie.filter(
            produit=self.stock
        ).values_list('NumeroSeries', flat=True)

        return list(num_series_list)
    def get_product_PBS(self):
        produits_p=[]
        
        try:
            produitproductionBL=self.produits_en_PEnOrdre.all()
            for produit in produitproductionBL:
                stock=produit.ProduitsEnOrdreFabrication.stock
                produit_enpc={
                            'id': stock.id,                      
                            'reference':stock.reference,
                            'name': stock.name,                        
                            'qty_sortante':produit.quantity,

                        }
                produits_p.append(produit_enpc)
        except:
            produits_p=self.stock.get_product_en_production()
            for product in produits_p:
                product["qty_sortante"]=0
        return produits_p

        
class BonGarantie(models.Model):
    idBon = models.CharField(
          ("id Bon"), 
          max_length=200,
          blank=False,
          null=False,
          unique=True
    )    
    dateBon = models.DateField()
    bonLivraisonAssocie = models.ForeignKey(BonSortie, on_delete = models.CASCADE, related_name='bon_garantie',  null=True, blank=True, default=None)
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE, null=True, blank=True, default=None)
    client = models.ForeignKey('tiers.Client', on_delete=models.CASCADE, null=True, blank=True, default=None)
    user = models.ForeignKey(CustomUser, on_delete = models.CASCADE, related_name='mes_bons_garantie', blank=True, null=True, default=None)
    tps_ecoule =   models.CharField( max_length=200, blank=True, null=True, default="" )    
    def get_mystore(self):
        my_products= self.produits_en_bon_garantie.all()
        for product in my_products:
            store= product.stock_dep.entrepot.store
            return store
        
    def __str__(self):
	    return "Bon no: " + str(self.idBon)
       
class ProduitsEnBonGarantie(models.Model):
    BonNo = models.ForeignKey(BonGarantie, on_delete = models.CASCADE, related_name='produits_en_bon_garantie')
    produit = models.ForeignKey('produits.Product', on_delete = models.CASCADE, related_name='mes_bons_garantie')
    quantity = models.IntegerField(default=1)
    livre = models.BooleanField(default=False)
    NumeroSeries = models.TextField(default="") 
    
    @property
    def getnumSeries(self):
        return eval(self.NumeroSeries) if self.NumeroSeries else []
    
    @property
    def getQuantity(self):
        # Access the associated BonSortie through BonGarantie
        bon_sortie = self.BonNo.bonLivraisonAssocie
        
        # If bon_sortie is None, return 0 as no associated BonSortie exists
        if bon_sortie is None:
            return 0
        
        # Filter ProduitsEnBonSortie by product and sum the quantities
        total_quantity = bon_sortie.produits_en_bon_sorties.filter(
            stock=self.produit
        ).aggregate(total_quantity=Sum('quantity'))['total_quantity'] or len(self.getnumSeries)
        
        return total_quantity
        
    def __str__(self):
	    return "Bon no: " + str(self.BonNo.idBon) + ", Item = " + self.produit.name 
 
class BonDevis(models.Model):
    idBon = models.CharField(
          ("id Bon"), 
          max_length=200,
          blank=False,
          null=False,
          unique=True
    )    
    dateBon =models.DateField()
    client =models.ForeignKey('tiers.Client',on_delete = models.CASCADE, related_name='client_bonS_devis')
    user =models.ForeignKey(CustomUser,on_delete = models.CASCADE, related_name='mes_bons_devis',blank=True, null=True, default=None)
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE, null=True, blank=True, default=None)
    def get_produits(self):
         return self.produits_en_bon_devis.all()
    
    @property
    def get_total_price(self):
        price_part = self.produits_en_bon_devis.aggregate(total_price=Sum('totalPrice'))['total_price']
        total_price = price_part
               
    def __str__(self):
	    return "Bon no: " + str(self.idBon)

    
   
class ProduitsEnBonDevis(models.Model):
    BonNo = models.ForeignKey(BonDevis, on_delete = models.CASCADE, related_name='produits_en_bon_devis')
    produit = models.ForeignKey('produits.Product', on_delete = models.CASCADE, related_name='mes_bons_devis')    
    totalPrice = models.DecimalField(max_digits=15, decimal_places=2)
    UnitPrice = models.DecimalField(max_digits=15, decimal_places=2)
    quantity = models.IntegerField(default=1)
  
    def __str__(self):
	    return "Bon no: " + str(self.BonNo.idBon) + ", Item = " + self.produit.name   
 
class BonCommande(models.Model):
    idBon = models.CharField(
          ("id Bon"), 
          max_length=200,
          blank=False,
          null=False,
          unique=True
    )    
    dateBon =models.DateField(default=datetime.now)
    date_reglement = models.DateField(default=datetime.now)
    client =models.ForeignKey('tiers.Client',on_delete = models.CASCADE, related_name='client_bonS_commande')
    mode_reglement = models.ForeignKey('reglements.ModeReglement', on_delete = models.CASCADE, related_name='commande_reglements_type')
    echeance_reg = models.ForeignKey('reglements.EcheanceReglement', on_delete=models.CASCADE)
    valide = models.BooleanField(default=False)
    ferme =  models.BooleanField(default=False)
    regle = models.BooleanField(default=False)
    user =models.ForeignKey(CustomUser,on_delete = models.CASCADE, related_name='mes_bons_commande',blank=True, null=True, default=None)
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE, null=True, blank=True, default=None)

    def __str__(self):
	    return "Bon no: " + str(self.idBon)  
  
class ProduitsEnBonCommande(models.Model):
    BonNo = models.ForeignKey(BonCommande, on_delete = models.CASCADE, related_name='produits_en_bon_commande')
    produit = models.ForeignKey('produits.Product', on_delete = models.CASCADE, related_name='mes_bons_commande')
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    totalPrice = models.DecimalField(max_digits=15, decimal_places=2)
    quantity = models.IntegerField(default=1)

class Facture(models.Model):
    Reglement_etat_CHOICES = [
        ("en Attente", "en Attente"),
        ("Règlement Reçu", "Règlement Reçu"),
        ("Expédié", "Expédié"),
        ("Facture", "Facture"),
        ("Facture Comptabilisé", "Facture Comptabilisé"),
    ]
    codeFacture = models.CharField( max_length=200,blank=False,null=False,unique=True)  
    date_facture = models.DateField()
    date_reglement = models.DateField(default=datetime.now)
    client = models.ForeignKey('tiers.Client', on_delete = models.CASCADE, related_name='client_facture')
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE, null=True, blank=True, default=None)
    BonS = models.ForeignKey(BonSortie, on_delete = models.CASCADE, related_name='bonS_facture', default=None, blank=True, null=True)
    mode_reglement = models.ForeignKey('reglements.ModeReglement', on_delete = models.CASCADE, related_name='facture_reglements_type', null=True, blank=True, default=None)
    echeance_reglement = models.ForeignKey('reglements.EcheanceReglement', on_delete = models.CASCADE, related_name='facture_reglements_echeance', null=True, blank=True, default=None)
    banque_Reglement = models.ForeignKey('tiers.Banque', on_delete=models.CASCADE, related_name='banque_reglements', blank=True, null=True, default=None )
    num_cheque_reglement = models.CharField(max_length=2500 , default="", null=True, blank =True)
    Remise = models.CharField(max_length=20,null=True, blank=True, default='')
    etat_reglement = models.CharField( max_length=30, choices=Reglement_etat_CHOICES) 
    shippingCost = models.DecimalField(max_digits=15, decimal_places=2 , null=True, blank=True)
    totalPrice = models.IntegerField(default=0)
    valide = models.BooleanField(default=False)
    ferme =  models.BooleanField(default=False)
    regle = models.BooleanField(default=False)

    @property
    def formatted_date(self):
        return self.date_facture.strftime('%d/%m/%Y')
        
    @property
    def formatted_duedate(self):
        return self.date_reglement.strftime('%d/%m/%Y')    
        
    @property
    def get_total_price(self):
        total_price = self.produits_en_facture.aggregate(total_price=Sum('totalprice'))['total_price']
        return round(total_price, 2) if total_price is not None else 0.00
    
    @property
    def total_remaining_amount(self):
        return Decimal(self.get_total_price) - Decimal(self.total_paid_amount)
    
    @property
    def total_paid_amount(self):
        return sum(Decimal(reglement.montant) for reglement in self.facture_reglements.all())
        
    def __str__(self):
	    return "Bon no: " + str(self.codeFacture)
	    
class AvoirVente(models.Model):
    BonSortieAssocie = models.ForeignKey(BonSortie, on_delete = models.CASCADE, related_name='avoirs_bonsortie')
    client = models.ForeignKey('tiers.Client', on_delete = models.CASCADE, related_name='avoirs_client')
    codeAvoir = models.CharField(  max_length=200,blank=False,null=False)   
    dateEmission = models.DateField(default=datetime.now)
    motif =  models.CharField(  max_length=200,blank=False,null=False, default="")
    montant = models.CharField(  max_length=200,blank=False,null=False, default="")
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE,blank=True , null=True, default=None)  

class ProduitsEnFacture(models.Model):
    FactureNo = models.ForeignKey(Facture, on_delete = models.CASCADE, related_name='produits_en_facture')
    stock = models.ForeignKey('produits.Product', on_delete = models.CASCADE, related_name='facture')
    quantity = models.IntegerField(default=0)
    unitprice = models.DecimalField(max_digits=15, decimal_places=2,default=0,null=True)
    totalprice = models.DecimalField(max_digits=15, decimal_places=2 ,default=0,null=True)  

    def __str__(self):
	    return "Facture no: " + str(self.FactureNo.codeFacture) + ", Item = " + self.stock.name