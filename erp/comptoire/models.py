from django.db import models
from users.models import CustomUser
from django.contrib.auth.models import Permission
import json
from decimal import Decimal
# Create your models here.
class ComptoirCustomPermission(Permission):
    class Meta:
        verbose_name = 'Custom Permission'
        verbose_name_plural = 'Custom Permissions'
        
class pointVente(models.Model):
    label = models.CharField(max_length=200)
    entrepot = models.ForeignKey('inventory.Entrepot',on_delete=models.CASCADE, blank=True, null=True, default=None, related_name='mes_points_ventes')
    type_reglement = models.CharField(max_length=200)
    mode_payment = models.ForeignKey('reglements.ModeReglement', on_delete=models.CASCADE , blank=True, null=True, related_name="pointVentes")
    adresse=models.TextField(blank=True, null=True, default="")
    Téléphone = models.TextField(blank=True, null=True, default="")
    fidelite = models.BooleanField(default=True)
    store = models.ForeignKey('clientInfo.store',on_delete=models.CASCADE, default=None, null=True, blank=True)
    
class Emplacement(models.Model):
    Label = models.TextField(blank=True, null=True, default="")
    lieu = models.TextField(blank=True, null=True, default="")   
    store = models.ForeignKey('clientInfo.store',on_delete=models.CASCADE, default=None, null=True, blank=True)
    
class AffectationCaisse(models.Model):
    emplacement =models.ForeignKey(pointVente, on_delete=models.CASCADE, related_name="pos_affectation", blank=True, null=True, default=None)
    CompteTres = models.ForeignKey('clientInfo.CompteEntreprise', on_delete=models.CASCADE, blank=True, null=True, default=None)
    utilisateur = models.ForeignKey('users.CustomUser' , on_delete=models.CASCADE ,  related_name="mon_affectation", blank=True, null=True, default=None)
    store = models.ForeignKey('clientInfo.store',on_delete=models.CASCADE, default=None, null=True, blank=True)

class Cloture(models.Model):
    montant= models.CharField(max_length=100, blank=True, null=True, default='')
    date = models.DateField()  
    utilisateur= models.ForeignKey('users.CustomUser',on_delete=models.CASCADE, blank=True, null=True, default=None)
    collected = models.BooleanField(default=False)
    store= models.ForeignKey('clientInfo.store',on_delete=models.CASCADE, blank=True, null=True, default=None)
    
class BonComptoire(models.Model):
    idBon = models.CharField(
          ("id Bon"), 
          max_length=200,
          blank=False,
          null=False,
          unique=True
    )    
    dateBon = models.DateField()
    pointVente = models.ForeignKey(pointVente, on_delete=models.CASCADE, blank=True, null=True, default=None)
    caisse = models.ForeignKey('clientInfo.CompteEntreprise', on_delete=models.CASCADE, blank=True, null=True, default=None)
    observation = models.CharField(
          max_length=4500,
          blank=True,
          null=True,
          default=''
    )  
    totalprice = models.DecimalField(max_digits=15, decimal_places=2,null=True, blank=True, default=0)
    totalremise = models.DecimalField(max_digits=15, decimal_places=2 ,null=True, blank=True, default=0)
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE, related_name="bons_comptoir_store", null=True, blank=True, default=None)
    client = models.ForeignKey('tiers.Client', related_name="mesbons_comptoir",on_delete=models.CASCADE, null=True, blank=True, default=None)
    user = models.ForeignKey(CustomUser, on_delete = models.CASCADE, related_name='mes_bons_comptoire',blank=True, null=True, default=None)

    @property
    def retourBill(self):
        bons_retours = self.bons_retour_compt.all()
        if bons_retours :
            return True
        else:
            return False
        
    @property
    def prix_encaisse(self):
        if (self.totalprice > 0):
            return self.totalprice - self.totalremise
        else:
            return self.totalprice
    @property
    def prix_payed(self):
        if (self.totalprice > 0):
            return self.totalprice
        else:
            mes_verssements = self.verssements.all()
            total_priceversed = sum(Decimal(v.montant) for v in mes_verssements if isinstance(v.montant, (int, float, str)) and v.montant.strip())
            return total_priceversed
    @property
    def prix_to_pay(self):
        sum_of_total_prices = self.produits_en_bon_comptoir.aggregate(models.Sum('totalprice'))['totalprice__sum'] or 0
        return sum_of_total_prices  - self.totalremise
        
    @property
    def prixtotal(self):
        sum_of_total_prices = self.produits_en_bon_comptoir.aggregate(models.Sum('totalprice'))['totalprice__sum'] or 0
        return sum_of_total_prices
        
    @property
    def monentrepot(self):
        return self.pointVente.entrepot.name
    
    @property
    def regle(self):
        total_price = self.prix_to_pay - (self.totalprice - self.totalremise)
        
        if total_price == Decimal('0'):
            return True
        else:
            mes_verssements = self.verssements.all()
            total_priceversed = sum(Decimal(v.montant) if v.montant != '' else Decimal(0) for v in mes_verssements)
            total_priceversed = self.prix_to_pay - total_priceversed

            if total_priceversed == Decimal('0'):
                return True
            else:
                return False
    @property
    def par_verssement(self):
        if len(self.verssements.all())>0:
            return True
        else:
            return False
            
    @property
    def montantrestant(self):
        if (self.totalprice > 0):
         restant = self.prix_to_pay - self.totalprice
        else:
           mes_verssements = self.verssements.all()
           total_priceversed = sum(Decimal(v.montant) for v in mes_verssements if isinstance(v.montant, (int, float, str)) and v.montant.strip())
           restant = self.prix_to_pay - total_priceversed
           
          
        return max(0, restant)
        
    @property
    def get_products(self):
        products = self.produits_en_bon_comptoir.all()
        product_data = []
        for produit in products:
            product_data.append({
                'product_id': produit.stock.id,
                'product_name': produit.stock.name,
                'quantity': produit.quantity,
                'unit_price': float(produit.unitprice),
                'total_price': float(produit.totalprice),
                # Add more fields as needed
            })
        return json.dumps(product_data)
    
class BonRectification(models.Model):
    idBon = models.CharField(
          ("id Bon"), 
          max_length=200,
          blank=False,
          null=False,
          unique=True
    )    
    dateBon = models.DateField()
    pointVente = models.ForeignKey(pointVente, on_delete=models.CASCADE, blank=True, null=True, default=None)
    caisse = models.ForeignKey('clientInfo.CompteEntreprise', on_delete=models.CASCADE, blank=True, null=True, default=None)
    observation = models.CharField(
          max_length=4500,
          blank=True,
          null=True,
          default=''
    )  
    totalprice = models.DecimalField(max_digits=15, decimal_places=2,null=True, blank=True, default=0)
    totalremise = models.DecimalField(max_digits=15, decimal_places=2 ,null=True, blank=True, default=0)
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE, related_name="bons_rectif_store", null=True, blank=True, default=None)
    client = models.ForeignKey('tiers.Client', related_name="mesbons_rectification",on_delete=models.CASCADE, null=True, blank=True, default=None)
    user = models.ForeignKey(CustomUser, on_delete = models.CASCADE, related_name='mes_bons_rectification',blank=True, null=True, default=None)

    @property
    def retourBill(self):
        bons_retours = self.bons_retour_compt.all()
        if bons_retours :
            return True
        else:
            return False
        
    @property
    def prix_encaisse(self):
        if (self.totalprice > 0):
            return self.totalprice - self.totalremise
        else:
            return self.totalprice
        
    @property
    def prix_payed(self):
        if (self.totalprice > 0):
            return self.totalprice
        else:
            mes_verssements = self.verssements.all()
            total_priceversed = sum(Decimal(v.montant) for v in mes_verssements if isinstance(v.montant, (int, float, str)) and v.montant.strip())
            return total_priceversed
        
    @property
    def prix_to_pay(self):
        sum_of_total_prices = self.produits_en_bon_rectification.aggregate(models.Sum('totalprice'))['totalprice__sum'] or 0
        return sum_of_total_prices  - self.totalremise
        
    @property
    def prixtotal(self):
        sum_of_total_prices = self.produits_en_bon_rectification.aggregate(models.Sum('totalprice'))['totalprice__sum'] or 0
        return sum_of_total_prices
        
    @property
    def monentrepot(self):
        return self.pointVente.entrepot.name
    
    @property
    def regle(self):
        total_price = self.prix_to_pay - (self.totalprice - self.totalremise)
        
        if total_price == Decimal('0'):
            return True
        else:
            mes_verssements = self.verssements.all()
            total_priceversed = sum(Decimal(v.montant) if v.montant != '' else Decimal(0) for v in mes_verssements)
            total_priceversed = self.prix_to_pay - total_priceversed

            if total_priceversed == Decimal('0'):
                return True
            else:
                return False
    @property
    def par_verssement(self):
        if len(self.verssements.all())>0:
            return True
        else:
            return False
            
    @property
    def montantrestant(self):
        if (self.totalprice > 0):
         restant = self.prix_to_pay - self.totalprice
        else:
           mes_verssements = self.verssements.all()
           total_priceversed = sum(Decimal(v.montant) for v in mes_verssements if isinstance(v.montant, (int, float, str)) and v.montant.strip())
           restant = self.prix_to_pay - total_priceversed
           
          
        return max(0, restant)
        
    @property
    def get_products(self):
        products = self.produits_en_bon_rectification.all()
        product_data = []
        for produit in products:
            product_data.append({
                'product_id': produit.stock.id,
                'product_name': produit.stock.name,
                'quantity': produit.quantity,
                'unit_price': float(produit.unitprice),
                'total_price': float(produit.totalprice),
                # Add more fields as needed
            })
        return json.dumps(product_data)
    
    
class verssement(models.Model):
    montant= models.CharField(max_length=100, blank=True, null=True, default='')
    date = models.DateField()  
    utilisateur= models.ForeignKey('users.CustomUser',on_delete=models.CASCADE, blank=True, null=True, default=None)
    bon_comptoir_associe = models.ForeignKey(BonComptoire, on_delete = models.CASCADE,  blank=True, null=True, default=None, related_name='verssements')
    bon_rectification_associe = models.ForeignKey(BonRectification, on_delete = models.CASCADE,  blank=True, null=True, default=None ,related_name='verssements')
    store= models.ForeignKey('clientInfo.store',on_delete=models.CASCADE, blank=True, null=True, default=None)
    
    def __str__(self):
	    return "Verssement de : " + str(self.montant) + ", POUR BON NO: = " + str(self.bon_comptoir_associe.idBon)
	    
    @property
    def remaining_amount_after_payment(self):
        # Get all previous verssements for the associated bon_comptoir_associe
        previous_verssements = verssement.objects.filter(
            bon_comptoir_associe=self.bon_comptoir_associe,
            date__lte=self.date
        )

        # Calculate the total amount of previous payments
        total_previous_payments = sum(
            Decimal(v.montant) for v in previous_verssements
            if isinstance(v.montant, (int, float, str)) and v.montant.strip()
        )

        # Calculate the remaining amount after this payment
        remaining_amount = self.bon_comptoir_associe.prix_to_pay - total_previous_payments

        return remaining_amount
    
    @property
    def remaining_amount_after_paymentrectif(self):
        # Get all previous verssements for the associated bon_comptoir_associe
        previous_verssements = verssement.objects.filter(
            bon_comptoir_associe=self.bon_rectification_associe,
            date__lte=self.date
        )

        # Calculate the total amount of previous payments
        total_previous_payments = sum(
            Decimal(v.montant) for v in previous_verssements
            if isinstance(v.montant, (int, float, str)) and v.montant.strip()
        )

        # Calculate the remaining amount after this payment
        remaining_amount = self.bon_rectification_associe.prix_to_pay - total_previous_payments

        return remaining_amount
            
class BonRetourComptoir(models.Model):
    idBon = models.CharField(
          ("id Bon"), 
          max_length=200,
          blank=False,
          null=False,
          unique=True
    )    
    dateBon = models.DateField()
    client = models.ForeignKey('tiers.Client', related_name="bonsretour_compt", on_delete=models.CASCADE, null=True, blank=True, default=None)
    user = models.ForeignKey(CustomUser, on_delete = models.CASCADE, related_name='mes_bons_retourcomptoire', blank=True, null=True, default=None)
    bon_comptoir_associe = models.ForeignKey(BonComptoire, on_delete = models.CASCADE, related_name='bons_retour_compt', blank=True, null=True, default=None)
    bon_rectification_associe = models.ForeignKey(BonRectification, on_delete = models.CASCADE, related_name='bons_retour_compt', blank=True, null=True, default=None)
    decision = models.CharField( max_length=200,blank=False,null=False, default='')

    
    @property
    def myTotalPrice(self):
        total_price = sum([product.totalprice for product in self.produits_en_bon_retourcomptoir.all()])
        return total_price

class ProduitsEnBonRetourComptoir(models.Model):
    BonNo = models.ForeignKey(BonRetourComptoir, on_delete = models.CASCADE, related_name='produits_en_bon_retourcomptoir')
    produit = models.ForeignKey('produits.Product', on_delete = models.CASCADE, related_name='mes_bons_retourcomptoir')    
    totalprice = models.DecimalField(max_digits=15, decimal_places=2)
    unitprice = models.DecimalField(max_digits=15, decimal_places=2)
    quantity = models.IntegerField(default=1)
      
class ProduitsEnBonRectif(models.Model):
    BonNo = models.ForeignKey(BonRectification, on_delete = models.CASCADE, related_name='produits_en_bon_rectification')
    stock = models.ForeignKey('produits.Product', on_delete = models.CASCADE, related_name='bons_rectif')
    entrepot = models.ForeignKey('inventory.Entrepot',on_delete=models.CASCADE, blank=True, null=True, default=None, related_name='produit_rectification')
    quantity = models.IntegerField(default=1)
    unitprice = models.DecimalField(max_digits=15, decimal_places=2)
    totalprice = models.DecimalField(max_digits=15, decimal_places=2)  
    
class ProduitsEnBonComptoir(models.Model):
    BonNo = models.ForeignKey(BonComptoire, on_delete = models.CASCADE, related_name='produits_en_bon_comptoir')
    stock = models.ForeignKey('produits.Product', on_delete = models.CASCADE, related_name='bons_comptoir')
    entrepot = models.ForeignKey('inventory.Entrepot',on_delete=models.CASCADE, blank=True, null=True, default=None, related_name='produit_boncomp')
    quantity = models.IntegerField(default=1)
    unitprice = models.DecimalField(max_digits=15, decimal_places=2)
    totalprice = models.DecimalField(max_digits=15, decimal_places=2)  