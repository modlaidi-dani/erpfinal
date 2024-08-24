from django.db import models
from users.models import CustomUser
from django.contrib.auth.models import Permission
from django.db.models import Sum
from datetime import datetime
  
class AchatInfoCustomPermission(Permission):
    class Meta:
        verbose_name = 'Custom Permission'
        verbose_name_plural = 'Custom Permissions'


    
class BonCommandeAchat(models.Model):
    idBon = models.CharField(
          ("id Bon"), 
          max_length=200,
          blank=False,
          null=False,
          unique=True
    )    
    dateBon =models.DateField()
    fournisseur =models.ForeignKey('tiers.Fournisseur',on_delete = models.CASCADE, related_name='client_bons_commandeachat', default=None, blank=True, null=True)
    destinataire = models.CharField(max_length=100, blank=True, null=True, default="")
    tauxChange = models.DecimalField(max_digits=15, decimal_places=2)
    Tva = models.DecimalField(max_digits=15, decimal_places=2)
    DDtax = models.DecimalField(max_digits=15, decimal_places=2)
    ttctax = models.DecimalField(max_digits=15, decimal_places=2)
    tauxChange = models.DecimalField(max_digits=15, decimal_places=2)
    livraison = models.ForeignKey('inventory.Entrepot', on_delete = models.CASCADE, default=None, null=True, blank=True)
    mode_reglement = models.ForeignKey('reglements.ModeReglement', on_delete = models.CASCADE, related_name='achat_reglements_type')
    echeance_reglement = models.ForeignKey('reglements.EcheanceReglement', on_delete = models.CASCADE, related_name='achat_reglements_echeance', null=True, blank=True, default=None)
    monnaie = models.ForeignKey('clientInfo.ValeurDevise' , on_delete = models.CASCADE, default=None, null=True, blank=True)
    user =models.ForeignKey(CustomUser,on_delete = models.CASCADE, related_name='mes_bons_commandesachats', default=None, blank=True, null=True)
    store = models.ForeignKey('clientInfo.store',on_delete = models.CASCADE, related_name='store_bons_commandesachat', default=None, blank=True, null=True)

class ProduitsEnBonCommandesAchat(models.Model):
    BonNo = models.ForeignKey(BonCommandeAchat, on_delete = models.CASCADE, related_name='produits_en_bon_commandeachat')
    produit = models.ForeignKey('produits.Product', on_delete = models.CASCADE, related_name='mes_bons_commandesachat')
    prixUnitaireDZ = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    prixUnitairUSD = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    totalPriceDZ = models.DecimalField(max_digits=15, decimal_places=2)
    totalPriceUSD = models.DecimalField(max_digits=15, decimal_places=2)
    transportPercent = models.DecimalField(max_digits=15, decimal_places=2)
    transportPrice = models.DecimalField(max_digits=15, decimal_places=2)
    chargesApproximatively = models.DecimalField(max_digits=15, decimal_places=2)
    chargesPercent = models.DecimalField(max_digits=15, decimal_places=2)
    charges = models.DecimalField(max_digits=15, decimal_places=2)
    taxesUnitaire = models.DecimalField(max_digits=15, decimal_places=2)
    taxesTotal = models.DecimalField(max_digits=15, decimal_places=2)
    Totalcharges = models.DecimalField(max_digits=15, decimal_places=2)
    anda = models.DecimalField(max_digits=15, decimal_places=2)
    DroitRealisation = models.DecimalField(max_digits=15, decimal_places=2)
    quantity = models.IntegerField(default=1)
  
    def __str__(self):
	    return "Bon no: " + str(self.BonNo.idBon) + ", Item = " + self.produit.name   

class DossierAchat(models.Model):
    idDossier = models.CharField(
          ("id Bon"), 
          max_length=200,
          blank=False,
          null=False,
          unique=True
    )    
    dateDossier =models.DateField()
    fournisseur =models.ForeignKey('tiers.Fournisseur',on_delete = models.CASCADE, related_name='client_dossier_achat', default=None, blank=True, null=True)
    facture = models.FileField(upload_to="media/document")
    BonCommande = models.ForeignKey(BonCommandeAchat, on_delete = models.CASCADE, related_name='dossier_achat_commande')
    monnaie = models.CharField(max_length=255, default='')
    MontantEtrange = models.DecimalField(max_digits=35, decimal_places=2, default=0)
    TypePaiement  = models.CharField(max_length=255, default='')
    AvisDebit = models.FileField(upload_to="media/document")
    datePaiement = models.DateField()
    banque_Reglement = models.ForeignKey('tiers.Banque', on_delete=models.CASCADE, related_name='banque_dossierachat', blank=True, null=True, default=None )
    MontantDZD = models.DecimalField(max_digits=35, decimal_places=2, default=0)
    DateValeur = models.FileField(upload_to="media/document")
    DateValeurdate = models.DateField(default=datetime.now)
    DateMontant = models.DateField(default=datetime.now)
    TauxChange = models.CharField(max_length=255, default='')
    user =models.ForeignKey(CustomUser,on_delete = models.CASCADE, related_name='mes_dossier_achat', default=None, blank=True, null=True)
    store = models.ForeignKey('clientInfo.store',on_delete = models.CASCADE, related_name='store_dossier_achat', default=None, blank=True, null=True)
        
     
class BonAchat(models.Model):
    idBon = models.CharField(
          ("id Bon"), 
          max_length=200,
          blank=False,
          null=False,
          unique=True
    )    
    dateBon =models.DateField()
    totalPrice = models.IntegerField(default=0)
    fournisseur =models.ForeignKey('tiers.Fournisseur',on_delete = models.CASCADE, related_name='client_bons_achat', default=None, blank=True, null=True)
    entrepot = models.ForeignKey('inventory.Entrepot',on_delete = models.CASCADE, related_name='entrepot_bonachat', default=None, blank=True, null=True)
    monnaie = models.ForeignKey('clientInfo.ValeurDevise',on_delete = models.CASCADE, related_name='monnaie_bonachat', default=None, blank=True, null=True)
    mode_reglement = models.ForeignKey('reglements.ModeReglement', on_delete = models.CASCADE, related_name='bonachat_reglements_type', default=None, blank=True, null=True)
    echeance_reglement = models.ForeignKey('reglements.EcheanceReglement', on_delete = models.CASCADE, related_name='bonachatt_reglements_echeance', null=True, blank=True, default=None)
    user =models.ForeignKey(CustomUser,on_delete = models.CASCADE, related_name='mes_bons_achat', default=None, blank=True, null=True)
    store = models.ForeignKey('clientInfo.store',on_delete = models.CASCADE, related_name='store_bons_achat', default=None, blank=True, null=True)
   
    @property
    def total_paid_amount(self):
        return sum(reglement.montant for reglement in self.bonAchats_reglements.all())
    
    @property
    def total_remaining_amount(self):
        return self.totalPrice - self.total_paid_amount
        
    def get_produits(self):
         return self.produits_en_bon_achat.all()
    
    def __str__(self):
	    return "Bon no: " + str(self.idBon)  
 
class FactureAchat(models.Model):
    codeFacture = models.CharField( max_length=200,blank=False,null=False,unique=True)  
    date_facture = models.DateField()
    fournisseur = models.ForeignKey('tiers.Fournisseur',on_delete = models.CASCADE, related_name='client_facture_achat', default=None, blank=True, null=True)
    livraison = models.ForeignKey('inventory.Entrepot', on_delete = models.CASCADE, default=None, null=True, blank=True)
    BonAchat = models.ForeignKey(BonAchat,on_delete = models.CASCADE, related_name='bonsachat_facture',blank=True , null=True, default=None)
    mode_reglement = models.ForeignKey('reglements.ModeReglement', on_delete = models.CASCADE, related_name='factureachat_reglements_type')
    echeance_reglement = models.ForeignKey('reglements.EcheanceReglement', on_delete = models.CASCADE, related_name='factureachat_reglements_echeance', null=True, blank=True, default=None)
    monnaie = models.ForeignKey('clientInfo.ValeurDevise' , on_delete = models.CASCADE, default=None, null=True, blank=True)
    user =models.ForeignKey(CustomUser,on_delete = models.CASCADE, related_name='mes_facture_achat', default=None, blank=True, null=True)
    store = models.ForeignKey('clientInfo.store',on_delete = models.CASCADE, related_name='store_bons_factureachat', default=None, blank=True, null=True)
    Remise = models.DecimalField(max_digits=15, decimal_places=2)
    etat_reglement = models.CharField( max_length=250,blank=False,null=False) 
    shippingCost = models.DecimalField(max_digits=15, decimal_places=2 , null=True, blank=True)
    totalPrice = models.IntegerField(default=0)
    valide = models.BooleanField(default=False)
    ferme =  models.BooleanField(default=False)
    regle = models.BooleanField(default=False)
    
    @property
    def get_total_price(self):
        total_price = self.produits_en_factureachats.aggregate(total_price=Sum('totalprice'))['total_price']
        return round(total_price, 2) if total_price is not None else 0.00
    
class ProduitsEnFactureAchat(models.Model):
    FactureNo = models.ForeignKey(FactureAchat, on_delete = models.CASCADE, related_name='produits_en_factureachats')
    stock = models.ForeignKey('produits.Product', on_delete = models.CASCADE, related_name='factures_achat')
    quantity = models.IntegerField(default=0)
    unitprice = models.DecimalField(max_digits=15, decimal_places=2,default=0,null=True)
    totalprice = models.DecimalField(max_digits=15, decimal_places=2 ,default=0,null=True)  

    def __str__(self):
	    return "Facture no: " + str(self.FactureNo.codeFacture) + ", Item = " + self.stock.name    
 
class ProduitsEnBonAchat(models.Model):
    BonNo = models.ForeignKey(BonAchat, on_delete = models.CASCADE, related_name='produits_en_bon_achat')
    produit = models.ForeignKey('produits.Product', on_delete = models.CASCADE, related_name='mes_bons_achat')
    prixUnitaire = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    totalPrice = models.DecimalField(max_digits=15, decimal_places=2)
    quantity = models.IntegerField(default=1)
  
    def __str__(self):
	    return "Bon no: " + str(self.BonNo.idBon) + ", Item = " + self.produit.name   

class AvoirAchat(models.Model):
    BonSortieAssocie = models.ForeignKey(BonAchat, on_delete = models.CASCADE, related_name='avoirs_bonachat')
    fournisseur = models.ForeignKey('tiers.Fournisseur', on_delete = models.CASCADE, related_name='avoirs_fournisseur', blank=True , null=True, default=None)
    codeAvoir = models.CharField(  max_length=200,blank=False,null=False)   
    dateEmission = models.DateField(default=datetime.now)
    motif =  models.CharField(  max_length=200,blank=False,null=False, default="")
    montant = models.CharField(  max_length=200,blank=False,null=False, default="")
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE,blank=True , null=True, default=None) 

class BonReception(models.Model):
    idBon = models.CharField(
          ("id Bon"), 
          max_length=200,
          blank=False,
          null=False,
          unique=True
    )    
    dateBon =models.DateField()
    BonAchat = models.ForeignKey(BonAchat,on_delete = models.CASCADE, related_name='bonsachat_bonreception',blank=True , null=True, default=None)
    entrepot = models.ForeignKey('inventory.Entrepot', on_delete=models.CASCADE, related_name='entrepot_bonreception',blank=True , null=True, default=None)
    expedition = models.ForeignKey('Expedition', on_delete=models.CASCADE, related_name='expedition_bonreception',blank=True , null=True, default=None)
    chauffeur = models.CharField(max_length=100, blank=True, null=True, default="")
    immatriculation = models.CharField(max_length=100, blank=True, null=True, default="")
    unite_monitaire = models.ForeignKey('clientInfo.ValeurDevise',on_delete=models.CASCADE, related_name='unitemonitaire_bonreception',blank=True , null=True, default=None)
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE,blank=True , null=True, default=None)  
    user =models.ForeignKey(CustomUser,on_delete = models.CASCADE, related_name='mes_bons_reception', blank=True, default=None, null=True)
    
class Expedition(models.Model):
    code_bon = models.CharField(
          ("id Bon"), 
          max_length=200,
          blank=False,
          null=False,
          default='',
    )    
    bon_commande = models.ForeignKey(BonCommandeAchat, on_delete = models.CASCADE, related_name='expedition_commandes', blank=True, null=True, default=None)
    Port_debarquement = models.CharField(max_length=100, blank=True, null=True, default="")
    port_embarquement = models.CharField(max_length=100, blank=True, null=True, default="")
    nombre_colis	=models.IntegerField(default=0)
    etat = models.CharField(max_length=100, blank=True, null=True, default="")
    date_depart = models.DateField()
    date_arrive = models.DateField()
    date_remise_transitaire = models.DateField()
    date_domiciliation = models.DateField()
    date_conaissement = models.DateField()
    banque_domiciliation = models.ForeignKey('tiers.Banque', on_delete = models.CASCADE, related_name='expedition_banque', blank=True, null=True, default=None)
    nbr_jours_port =models.IntegerField(default=0)
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE, blank=True , null=True, default=None)  
    user =models.ForeignKey(CustomUser,on_delete = models.CASCADE, related_name='mes_expedition', blank=True , null=True, default=None)

class ProduitsEnBonReception(models.Model):
    BonNo = models.ForeignKey(BonReception, on_delete = models.CASCADE, related_name='produits_en_bon_reception')
    produit = models.ForeignKey('produits.Product', on_delete = models.CASCADE, related_name='mes_bons_reception')
    prixUnitaire = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    totalPrice = models.DecimalField(max_digits=15, decimal_places=2)
    quantity = models.IntegerField(default=0)
  
    def __str__(self):
	    return "Bon no: " + str(self.BonNo.idBon) + ", Item = " + self.produit.name  

class ProjetCredit(models.Model):
    codeProjet = models.CharField(max_length=200, default='', blank=True, null=True) 
    Marque = models.CharField(max_length=200, default='', blank=True, null=True) 
    dateProjet =models.DateField()   
    designation = models.CharField(max_length=200, default='', blank=True, null=True) 
    cnn = models.CharField(max_length=200, default='', blank=True, null=True) 
    FichierProjet = models.FileField(upload_to="media/document")
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE, blank=True , null=True, default=None)  
    user =models.ForeignKey(CustomUser,on_delete = models.CASCADE, related_name='mes_projets', blank=True , null=True, default=None)
    
class CreditNote(models.Model):
    dateEmission = models.DateField() 
    BonAchat = models.ForeignKey(BonAchat, on_delete = models.CASCADE, related_name='bon_achats_credit', default=None, blank=True, null=True)
    Projet= models.ForeignKey(ProjetCredit, on_delete = models.CASCADE, related_name='bon_achats_credit', default=None, blank=True, null=True)
    motifCredit =  models.CharField(max_length=200, default='', blank=True, null=True)  
    totalUsd = models.DecimalField(max_digits=15, decimal_places=2)   
    totalDZ = models.DecimalField(max_digits=15, decimal_places=2)   
    tauxChange = models.DecimalField(max_digits=15, decimal_places=2)   
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE, blank=True , null=True, default=None)  
    user =models.ForeignKey(CustomUser,on_delete = models.CASCADE, related_name='mes_creditd', blank=True , null=True, default=None)
    
class ProduitsEnCreditNote(models.Model):
    Credit = models.ForeignKey(CreditNote, on_delete = models.CASCADE, related_name='produits_en_bon_creditNote')
    produit = models.ForeignKey('produits.Product', on_delete = models.CASCADE, related_name='mes_bons_creditNote')
    puUsdAchat = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    puDaAchat = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    totalPrice = models.DecimalField(max_digits=15, decimal_places=2)
    quantityAchete = models.IntegerField(default=0)

    def __str__(self):
	    return "Bon no: " + str(self.Credit.idBon) + ", Item = " + self.produit.name  	    