from django.db import models
from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.snippets.models import register_snippet
# Create your models here.
from django.contrib.auth.models import Permission
from users.models import CustomUser
from django.utils import timezone
from django.http import JsonResponse
from datetime import datetime
from django.db.models import Sum


class ReglementsCustomPermission(Permission):
    class Meta:
        verbose_name = 'Custom Permission'
        verbose_name_plural = 'Custom Permissions'
        
class ModeReglement(models.Model):
    label = models.CharField(max_length=2500 , default="", null=True, blank =True)
    actif = models.BooleanField(default=True)
    num_cheque = models.CharField(max_length=2500 , default="", null=True, blank =True)
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE, default=None, null=True, blank=True)
    def __str__(self):
	    return "Type Reglement : " + str(self.label) 

class depense(models.Model):
    type_depense = models.ForeignKey('TypeDepense', on_delete = models.SET_NULL, related_name='mes_depenses',null=True, blank=True, default=None)
    montant = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    date = models.DateField()
    mode_reglement = models.ForeignKey(ModeReglement, on_delete = models.CASCADE, related_name='reglement_depense')
    caisse = models.ForeignKey('clientInfo.CompteEntreprise', on_delete = models.CASCADE, related_name='depenses')
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, default=None, null=True, blank=True)
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE, default=None, null=True, blank=True)
    
class TypeDepense(models.Model):
    TYPE_DEPENSE_CHOICES = [
        ('salaire', 'Salaire'),
        ('loyer', 'Loyer'),
        ('divers', 'Divers'),
    ]

    type = models.CharField(max_length=20, choices=TYPE_DEPENSE_CHOICES)
    nom_salarie = models.CharField(max_length=50 ,null=True, blank=True, default="")
    fonction_salarie =models.CharField(max_length=50 ,null=True, blank=True, default="")
    adresse_salarie =models.CharField(max_length=50 ,null=True, blank=True, default="")
    tlfn_salarie =models.CharField(max_length=50 ,null=True, blank=True, default="")
    numero_local= models.CharField(max_length=50 ,null=True, blank=True, default="")
    adresse_local = models.CharField(max_length=50 ,null=True, blank=True, default="")
    designation = models.CharField(max_length=50 ,null=True, blank=True, default="")
    date_creation = models.DateTimeField(auto_now_add=True)
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE, default=None, null=True, blank=True)
    
class EcheanceReglement(models.Model):
    label = models.CharField(max_length=2500 , default="", null=True, blank =True)
    actif = models.BooleanField(default=True)
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE, default=None, null=True, blank=True)
    def __str__(self):
	    return "echeance Reglement : " + str(self.label) 

class HistoriqueMontantRecuperer(models.Model):
    montant = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    date = models.DateField()
    client = models.ForeignKey('tiers.Client', on_delete = models.CASCADE, related_name='montant_envoye' , null=True, blank=True, default =None)
    def __str__(self):
	    return self.montant 
    
class Reglement(models.Model):
    Reglement_Type_CHOICES = [
        ("paiement", "paiement"),
        ("remboursement", "remboursement"),
    ]
    montantSource = models.ForeignKey(HistoriqueMontantRecuperer, on_delete = models.CASCADE, related_name='rep_reglements', null=True, blank=True, default =None) 
    codeReglement = models.CharField( max_length=30,default="", blank=True, null=True) 
    type_reglement = models.CharField( max_length=100, choices=Reglement_Type_CHOICES) 
    collected = models.BooleanField(default=False)
    client = models.ForeignKey('tiers.Client', on_delete = models.CASCADE, related_name='client_reglements')
    mode_reglement = models.ForeignKey(ModeReglement, on_delete = models.CASCADE, related_name='reglements_type')
    dateReglement = models.DateField()
    num_cheque = models.CharField( max_length=100,default="", blank=True, null=True) 
    note = models.TextField(default="", blank=True, null=True) 
    piece_jointe = models.FileField(upload_to="pj", blank=True, null=True)
    BonS = models.ForeignKey('ventes.BonSortie', on_delete = models.CASCADE, related_name='bonS_reglements', default=None, null=True, blank=True)
    facture = models.ForeignKey('ventes.Facture', on_delete = models.CASCADE, related_name='facture_reglements', default=None, null=True, blank=True)
    montant = models.DecimalField(max_digits=15, decimal_places=2)
    CompteEntreprise = models.ForeignKey('clientInfo.CompteEntreprise', on_delete = models.CASCADE, related_name='client_reglements')
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE, default=None, null=True, blank=True)
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, default=None, null=True, blank=True)
    
    @property
    def montantSourceRamasse(self):
        if self.montantSource is None:
             return 0
        else:
            return float(self.montantSource.montant)
        
    def __str__(self):
	    return " codeReglement  " + str(self.codeReglement) 
 
class ReglementFournisseur(models.Model):
    Reglement_Type_CHOICES = [
        ("paiement", "paiement"),
        ("remboursement", "remboursement"),
    ]

    codeReglement = models.CharField( max_length=30,default="", blank=True, null=True) 
    type_reglement = models.CharField( max_length=100, choices=Reglement_Type_CHOICES) 
    collected = models.BooleanField(default=False)
    fournisseur = models.ForeignKey('tiers.Fournisseur', on_delete = models.CASCADE, related_name='fournisseur_reglements')
    mode_reglement = models.ForeignKey(ModeReglement, on_delete = models.CASCADE, related_name='reglements_typefournisseur')
    dateReglement =models.DateField()
    BonA = models.ForeignKey('achats.BonAchat', on_delete = models.CASCADE, related_name='bonAchats_reglements', default=None, null=True, blank=True)
    facture = models.ForeignKey('achats.FactureAchat', on_delete = models.CASCADE, related_name='factureAchats_reglements', default=None, null=True, blank=True)
    montant = models.DecimalField(max_digits=15, decimal_places=2)
    CompteEntreprise = models.ForeignKey('clientInfo.CompteEntreprise', on_delete = models.CASCADE, related_name='fournisseurs_reglements')
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE, default=None, null=True, blank=True)
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, default=None, null=True, blank=True)

    def __str__(self):
	    return " codeReglement  " + str(self.codeReglement) 

class ClotureReglements(models.Model):
    montant= models.CharField(max_length=100, blank=True, null=True, default='')
    date = models.DateField()  
    utilisateur= models.ForeignKey('users.CustomUser',on_delete=models.CASCADE, blank=True, null=True, default=None)
    collected = models.BooleanField(default=False)
    montant_collected = models.CharField(max_length=100, blank=True, null=True, default='')
    caisse = models.ForeignKey('clientInfo.CompteEntreprise', on_delete = models.CASCADE, related_name='clotures_reg', blank=True, null=True, default=None)
    store= models.ForeignKey('clientInfo.store',on_delete=models.CASCADE, blank=True, null=True, default=None) 
 
class montantCollected(models.Model):     
    montant= models.CharField(max_length=100, blank=True, null=True, default='')
    date = models.DateField()  
    utilisateur= models.ForeignKey('users.CustomUser',on_delete=models.CASCADE, blank=True, null=True, default=None)
    caisse = models.ForeignKey('clientInfo.CompteEntreprise', on_delete = models.CASCADE, related_name='montantcollected_reg', blank=True, null=True, default=None)
    store= models.ForeignKey('clientInfo.store',on_delete=models.CASCADE, blank=True, null=True, default=None)  

class mouvementCaisse(models.Model):
    date =models.DateField()
    CompteEntreprise = models.ForeignKey('clientInfo.CompteEntreprise', on_delete = models.CASCADE, related_name='mouvements_sortie', default=None, null=True, blank=True)
    CompteEntrepriseDestinataire = models.ForeignKey('clientInfo.CompteEntreprise', on_delete = models.CASCADE, related_name='mouvements_recu', default=None, null=True, blank=True)
    debit = models.DecimalField(max_digits=15, decimal_places=2)
    credit = models.DecimalField(max_digits=15, decimal_places=2)
    motif = models.CharField( max_length=100,default="", blank=True, null=True)
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, default=None, null=True, blank=True)
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE, default=None, null=True, blank=True)
    