from django.db import models
from wagtail.snippets.models import register_snippet
from clientInfo.models import store
from users.models import CustomUser
from tiers.models import Client
from django.contrib.auth.models import Permission
from comptoire.models import ProduitsEnBonComptoir, ProduitsEnBonRetourComptoir, BonComptoire
from ventes.models import ProduitsEnBonSortie
from decimal import Decimal
# Create your models here.
from django.db.models import Q
from django.db.models import F

class InventoryCustomPermission(Permission):
    class Meta:
        verbose_name = 'Custom Permission'
        verbose_name_plural = 'Custom Permissions'

class Entrepot(models.Model): 
   store = models.ForeignKey(store,on_delete=models.CASCADE, related_name='store_entrepot', blank=True, null=True, default=None)
   name= models.CharField(max_length=100)
   adresse = models.CharField(max_length=100 , default="", null=True, blank=True)
   ville = models.CharField(max_length=100)
   codePostal = models.CharField(max_length=100 , default="", null=True, blank=True)
   phone = models.CharField(max_length=100, default="", null=True, blank=True)
   def __str__(self) :
         return self.name
   def get_responsables(self):
       users = self.responsables.all()
       list_responsables = []
       for user in users :
           list_responsables.append(user.username)
       return list_responsables
   def get_stocks(self):
       return self.inventories.all()

class InventaireAnnuel(models.Model):
    codeInv = models.CharField(max_length=100)
    dateInv = models.DateField()
    datecloture = models.DateField()
    note = models.TextField()
    entrepot = models.ForeignKey(Entrepot, on_delete=models.CASCADE, related_name="entrepot_inventaire", blank =False, null=False)
    store =models.ForeignKey(store,on_delete = models.CASCADE, related_name='store_inventaires')

class BonRetourAncien(models.Model):
    idBon = models.CharField(
          ("id Bon"), 
          max_length=200,
          blank=False,
          null=False,
          unique=True
    )    
    dateBon = models.DateField()
    totalPrice = models.IntegerField(default=0)
    bonL =  models.CharField(max_length=100)
    entrepot = models.ForeignKey(Entrepot, on_delete = models.CASCADE, related_name='entrepot_retourancien', blank=True, null=True, default = None) 
    client =  models.CharField(max_length=100)
    valide = models.BooleanField(blank=True, null=True, default=False)
    store =models.ForeignKey(store,on_delete = models.CASCADE, related_name='store_bons_retour_ancien')
    user =models.ForeignKey(CustomUser,on_delete = models.CASCADE, related_name='mes_bons_retour_ancien', blank=True, null=True, default=None)

    def get_produits(self):
         return self.produits_en_bon_retourancien.all()
         
    @property
    def entrepotname(self):
        return self.entrepot.name
    
    @property
    def total_price_retour(self):
        return round(sum(Decimal(product.unitprice) * product.quantity for product in self.produits_en_bon_retourancien.all()),2)
        
    def __str__(self):
	    return "Bon no: " + str(self.idBon)

class ProduitsEnBonRetourAncien(models.Model):
    BonNo = models.ForeignKey(BonRetourAncien, on_delete = models.CASCADE, related_name='produits_en_bon_retourancien')
    referenceproduit = models.CharField(max_length=100)    
    nomproduit = models.CharField(max_length=100)  
    totalprice = models.DecimalField(max_digits=15, decimal_places=2)
    unitprice = models.DecimalField(max_digits=15, decimal_places=2)
    reintegrated = models.BooleanField(default=False)
    image = models.FileField(upload_to="media/document") 
    warranty = models.BooleanField(default=False)
    numseries = models.CharField( 
          max_length=200,
          blank=True,
          null=True,
          default = '',  
    )    
    quantity = models.IntegerField(default=1)
  
    def __str__(self):
	    return "Bon no: " + str(self.BonNo.idBon) + ", Item = " + self.nomproduit  	    

class equipeInventaire(models.Model):
    inv_annuel = models.ForeignKey(InventaireAnnuel, on_delete=models.CASCADE, related_name="inventaire_assosiated", blank =False, null = False)
    label_equipe = models.TextField()

class produitEnInventaireAnnuel(models.Model):
    Equipe = models.ForeignKey(equipeInventaire, on_delete=models.CASCADE, related_name="liste_produits")
    product = models.ForeignKey('produits.Product', on_delete=models.CASCADE, related_name='mon_inventaire')
    quantity = models.PositiveIntegerField(default=0)  
    
class Stock(models.Model):
    product = models.ForeignKey('produits.Product', on_delete=models.CASCADE, related_name='mon_stock')
    entrepot = models.ForeignKey(Entrepot, on_delete=models.CASCADE, related_name="inventories")
    quantity = models.PositiveIntegerField(default=0)
    quantity_initial = models.PositiveIntegerField(default=0)
    quantity_pc = models.PositiveIntegerField(default=0)
    quantity_kit = models.PositiveIntegerField(default=0)
    quantity_blocked = models.PositiveIntegerField(default=0)

    @property
    def quantity_detailed(self):
        return self.quantity - self.quantity_blocked
        
    @property
    def get_quantity(self):
        return self.quantity - self.quantity_blocked
           
    def get_quantityBill(self, type_bill):
        return self.quantity - self.quantity_blocked   
              
    def __str__(self):
        return f"{self.product.name} in {self.entrepot.name} - Quantity: {self.quantity}"  
        
    @property
    def historical_entered_quantity(self):
        # Calculate quantity from entry transactions
        entry_quantity = ProduitsEnBonEntry.objects.filter(stock=self.product, BonNo__entrepot=self.entrepot).aggregate(models.Sum('quantity'))['quantity__sum'] or 0
        return self.quantity_initial + entry_quantity
        
    @property
    def historical_received_quantity(self):
        # Calculate quantity from transfer transactions where this stock is the destination
        transfer_arrived_quantity = ProduitsEnBonTransfert.objects.filter(
                stock_arr=self, 
                BonNo__entrepot_arrive=self.entrepot,
                BonNo__automatiquement=F('BonNo__valide')  # Both true or both false
        ).aggregate(models.Sum('quantity'))['quantity__sum'] or 0
        transfer_mag_quantity = ProduitsEnBonTransfertMag.objects.filter(stock_arr=self, BonNo__entrepot_arrive=self.entrepot).aggregate(models.Sum('quantity'))['quantity__sum'] or 0
        return transfer_arrived_quantity + transfer_mag_quantity
        
    @property
    def historical_transfered_quantity(self):
        # Calculate quantity from transfer transactions where this stock is the source
        transfer_departed_quantity = ProduitsEnBonTransfert.objects.filter(
                stock_dep=self, 
                BonNo__entrepot_depart=self.entrepot,
                BonNo__automatiquement=F('BonNo__valide')  # Both true or both false
        ).aggregate(models.Sum('quantity'))['quantity__sum'] or 0
        transfert_mag = ProduitsEnBonTransfertMag.objects.filter(stock_dep=self, BonNo__entrepot_depart=self.entrepot).aggregate(models.Sum('quantity'))['quantity__sum'] or 0
        return transfer_departed_quantity + transfert_mag
    
    @property
    def product_sold_quantity(self):
        produits_en_bon_comptoir = ProduitsEnBonComptoir.objects.filter(
                    stock=self.product,
                )
           # Filter the instances based on the condition specified in monentrepot property
        filtered_produits = [produit for produit in produits_en_bon_comptoir if produit.BonNo.monentrepot == self.entrepot.name]
        
                # Sum up the quantities from the filtered instances
        comptoir_quantity = sum(produit.quantity for produit in filtered_produits)
        produits_en_bon_sortie_list = ProduitsEnBonSortie.objects.filter(
            stock=self.product,
            BonNo__entrepot=self.entrepot
        )

        filtered_produits_en_bon_sortie = [
            produit_en_bon_sortie for produit_en_bon_sortie in produits_en_bon_sortie_list
            if produit_en_bon_sortie.BonNo.get_etat_transfert == True
        ]
        
        # Calculate the sum of quantities for the filtered objects
        sold_quantity = sum(produit_en_bon_sortie.quantity for produit_en_bon_sortie in filtered_produits_en_bon_sortie)
        return sold_quantity + comptoir_quantity
        
    @property
    def product_returned_quantity(self):
        produits_en_bon_comptoir = ProduitsEnBonRetourComptoir.objects.filter(
                    produit=self.product,
                )
           # Filter the instances based on the condition specified in monentrepot property
        filtered_produits = [produit for produit in produits_en_bon_comptoir if produit.BonNo.bon_comptoir_associe.monentrepot == self.entrepot.name ]
        produits_en_bon_retour= ProduitsEnBonRetour.objects.filter(
                    produit=self.product,
                )
        filtered_retour_produits = [produit for produit in produits_en_bon_retour if produit.BonNo.bonL.entrepot == self.entrepot and produit.reintegrated and produit.BonNo.valide]
        comptoir_returned_quantity = sum(produit.quantity for produit in filtered_produits)   
        returned_quantity = sum(produit.quantity for produit in filtered_retour_produits)   

        return comptoir_returned_quantity + returned_quantity

    @property
    def quantity_expected(self):
        total_entered_quantity = self.historical_entered_quantity + self.historical_received_quantity + self.product_returned_quantity
        total_out_quantity = self.product_sold_quantity + self.historical_transfered_quantity
        return total_entered_quantity - total_out_quantity    

class BonTransfertMagasin(models.Model):
    idBon = models.CharField(
          ("id Bon"), 
          max_length=200,
          blank=False,
          null=False,
          unique=True
    )    
    dateBon = models.DateField()
    store_depart = models.ForeignKey('clientInfo.store', on_delete = models.CASCADE, related_name='bontransfert_mag_dep', blank=True)
    entrepot_depart = models.ForeignKey(Entrepot, on_delete = models.CASCADE, related_name='entdep_transfertmag', blank=True)
    store_arrive = models.ForeignKey('clientInfo.store', on_delete = models.CASCADE, related_name='bontransfert_mag_arr', blank=True)
    entrepot_arrive = models.ForeignKey(Entrepot, on_delete = models.CASCADE, related_name='entarr_transfertmag', blank=True)
    automatiquement = models.BooleanField(blank=True, null=True,default=False)
    valide = models.BooleanField(blank=True, null=True, default=False)
    user = models.ForeignKey(CustomUser,on_delete = models.CASCADE, related_name='mes_bons_transfert_mag', blank=True, null=True, default=None)
    store = models.ForeignKey(store, on_delete=models.CASCADE,blank=True , null=True, default=None)
    def get_mystore(self):
        my_products= self.produits_en_bon_transfertMag.all()
        for product in my_products:
            store= product.stock_dep.store
            return store
        
    def __str__(self):
	    return "Bon no: " + str(self.idBon)
	    
class ProduitsEnBonTransfertMag(models.Model):
    BonNo = models.ForeignKey(BonTransfertMagasin, on_delete = models.CASCADE, related_name='produits_en_bon_transfertMag')
    stock_dep = models.ForeignKey(Stock, on_delete = models.CASCADE, related_name='bons_transfertmag_arrive')
    stock_arr = models.ForeignKey(Stock, on_delete = models.CASCADE, related_name='bons_transfertmag_recu')
    quantity = models.IntegerField(default=1)
  
    def __str__(self):
	    return "Bon no: " + str(self.BonNo.idBon) + ",from  Item = " + self.stock_dep.entrepot.name+ ",to   Item = " + self.stock_arr.entrepot.name
	    
class BonRetour(models.Model):
    idBon = models.CharField(
          ("id Bon"), 
          max_length=200,
          blank=False,
          null=False,
          unique=True
    )    
    dateBon = models.DateField()
    totalPrice = models.IntegerField(default=0)
    bonL = models.ForeignKey('ventes.BonSortie', on_delete=models.CASCADE, related_name='MesbonRetours', default=None, null=True, blank=True)
    client =models.ForeignKey('tiers.Client',on_delete = models.CASCADE, related_name='client_bons_retour')
    valide = models.BooleanField(blank=True, null=True, default=False)
    reception_valide = models.BooleanField(blank=True, null=True, default=False)
    store =models.ForeignKey(store,on_delete = models.CASCADE, related_name='store_bons_retour')
    user =models.ForeignKey(CustomUser,on_delete = models.CASCADE, related_name='mes_bons_retour', blank=True, null=True, default=None)

    def get_produits(self):
         return self.produits_en_bon_retour.all()
         
    @property
    def entrepotname(self):
        return self.bonL.entrepot.name
    
     
    @property
    def reintegrated(self):
        return self.produits_en_bon_retour.first().reintegrated
    
    @property
    def total_price_retour(self):
        return round(sum(Decimal(product.unitprice) * product.quantity for product in self.produits_en_bon_retour.all()),2)
        
    def __str__(self):
	    return "Bon no: " + str(self.idBon)

 
class BonEchange(models.Model):
    idBon = models.CharField(
          ("id Bon"), 
          max_length=200,
          blank=False,
          null=False,
          unique=True
    )    
    dateBon = models.DateField()
    totalPrice = models.IntegerField(default=0)
    bonL = models.ForeignKey(BonRetour, on_delete=models.CASCADE, related_name='Mesbonechange', default=None, null=True, blank=True)
    client =models.ForeignKey('tiers.Client',on_delete = models.CASCADE, related_name='client_bons_echange')
    valide = models.BooleanField(blank=True, null=True, default=False)
    store =models.ForeignKey(store,on_delete = models.CASCADE, related_name='store_bons_echange')
    user =models.ForeignKey(CustomUser,on_delete = models.CASCADE, related_name='mes_bons_echange', blank=True, null=True, default=None)
    entrepot = models.ForeignKey('inventory.Entrepot', on_delete = models.CASCADE, related_name='entrepot_bonsechange', default=None, blank=True, null=True)
        
    def __str__(self):
	    return "Bon no: " + str(self.idBon)
 
class BonMaintenance(models.Model):
    idBon = models.CharField(
          ("id Bon"), 
          max_length=200,
          blank=False,
          null=False,
          unique=True
    )    
    dateBon = models.DateField()
    totalPrice = models.IntegerField(default=0)
    bonL = models.ForeignKey(BonRetour, on_delete=models.CASCADE, related_name='Mesbonmaintenance', default=None, null=True, blank=True)
    bonR = models.ForeignKey(BonRetourAncien, on_delete=models.CASCADE, related_name='Mesbonmaintenance', default=None, null=True, blank=True)
    bonLComptoir = models.ForeignKey('comptoire.BonRetourComptoir', on_delete=models.CASCADE, related_name='MesbonmaintenanceComptoir', default=None, null=True, blank=True)
    valide = models.BooleanField(blank=True, null=True, default=False)
    garantie = models.BooleanField(blank=True, null=True, default=False)
    reponse = models.TextField(blank=True, null=True, default="")
    decision = models.TextField(blank=True, null=True, default="")
    store =models.ForeignKey(store,on_delete = models.CASCADE, related_name='store_bons_maintenance')
    user =models.ForeignKey(CustomUser,on_delete = models.CASCADE, related_name='mes_bons_maintenance', blank=True, null=True, default=None)
    entrepot = models.ForeignKey('inventory.Entrepot', on_delete = models.CASCADE, related_name='entrepot_bonsmaintenance', default=None, blank=True, null=True)
    observation = models.TextField(blank=True, null=True, default="")
        
    def __str__(self):
	    return "Bon no: " + str(self.idBon)

class ProduitsEnBonMaintenance(models.Model):
    BonNo = models.ForeignKey(BonMaintenance, on_delete = models.CASCADE, related_name='produits_en_bon_maintenance')
    produit = models.ForeignKey('produits.Product', on_delete = models.CASCADE, related_name='mes_bons_maintenance')
    image1 = models.FileField(upload_to="media/document") 
    image2 = models.FileField(upload_to="media/document") 
    image3 = models.FileField(upload_to="media/document") 
    image4 = models.FileField(upload_to="media/document") 
    quantity = models.IntegerField(default=0) 
    observation = models.TextField(blank=True, null=True, default="")
    
    @property
    def getObservation(self):
        return eval(self.observation) if '\'' in self.observation else list(self.observation)
        
    @property
    def getimage1(self):
        if self.image1:
                return self.image1.url
        else:
                return ''
    @property
    def getimage2(self):
        if self.image2:
                return self.image2.url
        else:
                return ''
    @property
    def getimage3(self):
        if self.image3:
                return self.image3.url
        else:
                return ''
    @property
    def getimage4(self):
        if self.image4:
                return self.image4.url
        else:
                return ''
    def __str__(self):
	    return "Bon no: " + str(self.BonNo.idBon) + ", Item = " + self.produit.name 

class ProduitsEnBonEchange(models.Model):
    BonNo = models.ForeignKey(BonEchange, on_delete = models.CASCADE, related_name='produits_en_bon_echange')
    stock = models.ForeignKey('produits.Product', on_delete = models.CASCADE, related_name='bons_echange')
    quantity = models.IntegerField(default=1)
    unitprice = models.DecimalField(max_digits=15, decimal_places=2)
    totalprice = models.DecimalField(max_digits=15, decimal_places=2)   
    
    def __str__(self):
	    return "Bon no: " + str(self.BonNo.idBon) + ", Item = " + self.stock.name
 
  
class BonReforme(models.Model):
    idBon = models.CharField(
          ("id Bon"), 
          max_length=200,
          blank=False,
          null=False,
          unique=True
    )    
    dateBon = models.DateField()   
    entrepot = models.ForeignKey(Entrepot,on_delete = models.CASCADE, related_name='entrepot_bons_reforme', blank=True, default=None, null=False) 
    bonretour = models.ForeignKey(BonRetour, on_delete=models.CASCADE, related_name='bonretour_bon_reforme', blank=True, default=None, null=False)
    store =models.ForeignKey(store,on_delete = models.CASCADE, related_name='store_bons_reforme')
    user =models.ForeignKey(CustomUser,on_delete = models.CASCADE, related_name='mes_bons_reforme', blank=True, null=True, default=None)

    def get_produits(self):
         return self.produits_en_bon_reforme.all()
    
    def __str__(self):
	    return "Bon no: " + str(self.idBon)

class ProduitsEnBonReforme(models.Model):
    BonNo = models.ForeignKey(BonReforme, on_delete = models.CASCADE, related_name='produits_en_bon_reforme')
    produit = models.ForeignKey('produits.Product', on_delete = models.CASCADE, related_name='mes_bons_reforme')
    quantity = models.IntegerField(default=0) 
    observation = models.TextField(blank=True, null=True, default="")
    def __str__(self):
	    return "Bon no: " + str(self.BonNo.idBon) + ", Item = " + self.produit.name 
 
class BonEntry(models.Model):
    idBon = models.CharField(
          ("id Bon"), 
          max_length=200,
          blank=False,
          null=False,
          unique=True
    )    
    dateBon =models.DateField()
    user =models.ForeignKey(CustomUser,on_delete = models.CASCADE, related_name='mes_bons_entry', blank=True, null=True, default=None)
    fournisseur = models.ForeignKey('tiers.Fournisseur', on_delete = models.CASCADE, related_name='fournisseurs_bons_entry', blank=True , null=True, default=None)
    entrepot = models.ForeignKey(Entrepot, on_delete = models.CASCADE, related_name='Entrepots_bons_entry', blank=True , null=True, default=None)
    store = models.ForeignKey(store, on_delete=models.CASCADE,blank=True , null=True, default=None)
    def get_produits(self):
        return self.produits_en_bon_entry.all()
    
    def __str__(self):
	    return "Bon no: " + str(self.idBon)
 
class BonReintegration(models.Model):
    idBon = models.CharField(
          ("id Bon"), 
          max_length=200,
          blank=False,
          null=False,
          unique=True
    )    
    dateBon =models.DateField()
    user =models.ForeignKey(CustomUser,on_delete = models.CASCADE, related_name='mes_bons_reintegration', blank=True, null=True, default=None)
    bonRetour = models.ForeignKey(BonRetour, on_delete = models.CASCADE, related_name='bonretour_bons_reintegration', blank=True , null=True, default=None)
    entrepot = models.ForeignKey(Entrepot, on_delete = models.CASCADE, related_name='Entrepots_bons_reintegration', blank=True , null=True, default=None)
    store = models.ForeignKey(store, on_delete=models.CASCADE,blank=True , null=True, default=None)
    def get_produits(self):
        return self.produits_en_bon_entry.all()
    
    def __str__(self):
	    return "Bon no: " + str(self.idBon)

class Bonsortiedestock(models.Model):
    idBon = models.CharField(
          ("id Bon"), 
          max_length=200,
          blank=False,
          null=False,
          unique=True
    )    
    dateBon =models.DateField()
    user = models.ForeignKey(CustomUser,on_delete = models.CASCADE, related_name='mes_bons_sortiesstock',blank=True, null=True, default=None)
    bonL = models.ForeignKey('ventes.BonSortie',on_delete = models.CASCADE, related_name='bonsBl_sortiesstock',blank=True , null=True, default=None)
    entrepot = models.ForeignKey(Entrepot, on_delete = models.CASCADE, related_name='Entrepots_bons_sortiesstock', blank=True , null=True, default=None)
    store = models.ForeignKey(store, on_delete=models.CASCADE,blank=True , null=True, default=None)
    Client =models.ForeignKey(Client, on_delete=models.CASCADE,blank=True , null=True, default=None)
    num_doc = models.CharField(max_length=100, null=True, blank=True, default="")
    Date_doc_Sortie = models.DateField(null=True, blank=True)
    num_constat	= models.CharField(max_length=100, null=True, blank=True, default="")
    Date_constat= models.DateField(null=True, blank=True)
    note = models.TextField( null=True, blank=True, default="")
    
    def get_produits(self):
        return self.produits_en_bon_entry.all()
    
    def __str__(self):
	    return "Bon no: " + str(self.idBon)
 
class BonTransfert(models.Model):
    idBon = models.CharField(
          ("id Bon"), 
          max_length=200,
          blank=False,
          null=False,
          unique=True
    )    
    dateBon = models.DateField()
    entrepot_depart = models.ForeignKey(Entrepot, on_delete = models.CASCADE, related_name='bontransfert_env', blank=True)
    entrepot_arrive = models.ForeignKey(Entrepot, on_delete = models.CASCADE, related_name='bontransfert_rec', blank=True)
    automatiquement = models.BooleanField(blank=True, null=True,default=False)
    valide = models.BooleanField(blank=True, null=True, default=False)
    validation_recu = models.BooleanField(blank=True, null=True, default=True) 
    annule = models.BooleanField(blank=True, null=True, default=False) 
    user = models.ForeignKey(CustomUser,on_delete = models.CASCADE, related_name='mes_bons_transfert', blank=True, null=True, default=None)
    store = models.ForeignKey(store, on_delete=models.CASCADE,blank=True , null=True, default=None)
    def get_mystore(self):
        my_products= self.produits_en_bon_transfert.all()
        for product in my_products:
            store= product.stock_dep.entrepot.store
            return store
        
    def __str__(self):
	    return "Bon no: " + str(self.idBon)
    
class ProduitsEnBonRetour(models.Model):
    BonNo = models.ForeignKey(BonRetour, on_delete = models.CASCADE, related_name='produits_en_bon_retour')
    produit = models.ForeignKey('produits.Product', on_delete = models.CASCADE, related_name='mes_bons_retour')    
    totalprice = models.DecimalField(max_digits=15, decimal_places=2)
    unitprice = models.DecimalField(max_digits=15, decimal_places=2)
    reintegrated = models.BooleanField(default=False)
    image = models.FileField(upload_to="media/document") 
    warranty = models.BooleanField(default=False)
    numseries = models.CharField( 
          max_length=200,
          blank=True,
          null=True,
          default = '',  
    )    
    direction = models.CharField( 
          max_length=50,
          blank=True,
          null=True,
          default = '',  
    )    
    quantity = models.IntegerField(default=1)
  
    def __str__(self):
	    return "Bon no: " + str(self.BonNo.idBon) + ", Item = " + self.produit.name   
   
class ProduitsEnBonTransfert(models.Model):
    BonNo = models.ForeignKey(BonTransfert, on_delete = models.CASCADE, related_name='produits_en_bon_transfert')
    stock_dep = models.ForeignKey(Stock, on_delete = models.CASCADE, related_name='bons_transfert_arrive')
    stock_arr = models.ForeignKey(Stock, on_delete = models.CASCADE, related_name='bons_transfert_recu')
    quantity = models.IntegerField(default=1)
  
    def __str__(self):
	    return "Bon no: " + str(self.BonNo.idBon) + ",from  Item = " + self.stock_dep.entrepot.name+ ",to   Item = " + self.stock_arr.entrepot.name
   
class ProduitsEnBonEntry(models.Model):
    BonNo = models.ForeignKey(BonEntry, on_delete = models.CASCADE, related_name='produits_en_bon_entry')
    stock = models.ForeignKey('produits.Product', on_delete = models.CASCADE, related_name='bons_entry')
    quantity = models.IntegerField(default=1)

    def __str__(self):
	    return "Bon no: " + str(self.BonNo.idBon) + ", Item = " + self.stock.name
 
class ProduitsEnBonReintegration(models.Model):
    BonNo = models.ForeignKey(BonReintegration, on_delete = models.CASCADE, related_name='produits_en_bon_reintegration')
    stock = models.ForeignKey('produits.Product', on_delete = models.CASCADE, related_name='bons_reintegration')
    quantity = models.IntegerField(default=1)

    
    def __str__(self):
	    return "Bon no: " + str(self.BonNo.idBon) + ", Item = " + self.stock.name
 
class ProduitsEnBonSortieStock(models.Model):
    BonNo = models.ForeignKey(Bonsortiedestock, on_delete = models.CASCADE, related_name='produits_en_bon_sortie_stock')
    stock = models.ForeignKey('produits.Product', on_delete = models.CASCADE, related_name='bons_sorties_stock')
    quantity = models.IntegerField(default=1)

    
    def __str__(self):
	    return "Bon no: " + str(self.BonNo.idBon) + ", Item = " + self.stock.name