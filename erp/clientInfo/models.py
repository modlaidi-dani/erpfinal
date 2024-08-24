from django.db import models
from wagtail.snippets.models import register_snippet
from django.contrib.auth.models import Permission
from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal
from comptoire.models import BonRetourComptoir

# Create your models here.
class ClientInfoCustomPermission(Permission):
    class Meta:
        verbose_name = 'Custom Permission'
        verbose_name_plural = 'Custom Permissions'
        
class store(models.Model):
    name= models.CharField(max_length=100, null=True, blank=True, default="") 
    location = models.CharField(max_length=100, null=True, blank=True, default="")
    code = models.CharField(max_length=100, null=True, blank=True, default="")
    nAdherent = models.CharField(max_length=100, null=True, blank=True, default="")
    denomination = models.CharField(max_length=100, null=True, blank=True, default="")
    raisonSocial = models.CharField(max_length=100, null=True, blank=True, default="")
    address1 = models.CharField(max_length=300 , null=True, blank=True, default="")
    address2 = models.CharField(max_length=300 , null=True, blank=True, default="")
    address3 = models.CharField(max_length=300 , null=True, blank=True, default="")
    CodePostal=models.CharField(max_length=255, null=True, blank=True, default="")
    phone1 = models.CharField(max_length=30 , null=True, blank=True, default="")
    phone2 = models.CharField(max_length=30 , null=True, blank=True, default="")
    phone3 = models.CharField(max_length=30 , null=True, blank=True, default="")
    fax1 = models.CharField(max_length=30 , null=True, blank=True, default="")
    fax2 = models.CharField(max_length=30 , null=True, blank=True, default="")
    fax3 = models.CharField(max_length=30 , null=True, blank=True, default="")
    mobile1 = models.CharField(max_length=30 , null=True, blank=True, default="")
    mobile2 = models.CharField(max_length=30 , null=True, blank=True, default="")
    mobile3 = models.CharField(max_length=30 , null=True, blank=True, default="")
    monnaie = models.CharField(max_length=10, null=True, blank=True, default="")
    IdentificationFis =models.CharField(max_length=50, null=True, blank=True, default="")
    registreCom =models.CharField(max_length=50, null=True, blank=True, default="")
    articleImpo =models.CharField(max_length=50, null=True, blank=True, default="")
    identifiantStatistique= models.CharField(max_length=50, null=True, blank=True, default="")
    banque=models.CharField(max_length=250, null=True, blank=True, default="")    
    compteBancaire =models.CharField(max_length=250, null=True, blank=True, default="")    
    compteCCP =models.CharField(max_length=250, null=True, blank=True, default="")    
    capitaleSocial =models.CharField(max_length=250, null=True, blank=True, default="")   
    product_variant =models.BooleanField(default=False, null=True, blank=True) 
    
    def __str__(self) :
         return self.location
     
    def get_entrepots(self):
      return self.store_entrepot.all()
    
    @property
    def total_bon_price(self):
        total_bon_sortie_price = self.bonL_store.aggregate(total=Coalesce(Sum('totalPrice'), 0, output_field=DecimalField()))['total']
        total_bon_comptoir_price = self.bons_comptoir_store.aggregate(total=Coalesce(Sum('totalprice'), 0, output_field=DecimalField()))['total']
        retour_comptoirs = BonRetourComptoir.objects.filter(bon_comptoir_associe__store=self)
        total_price_rembourse = sum(retour_comptoir.myTotalPrice for retour_comptoir in retour_comptoirs)
        return round(Decimal((total_bon_sortie_price + total_bon_comptoir_price) - total_price_rembourse),0)
    
    @property
    def bons_counts_per_month(self):
        bons_per_month = []
        for month in range(1, 13):
            bons_comptoire_count = self.bons_comptoir_store.filter(
                dateBon__month=month
            ).count()

            bons_sortie_count = self.bonL_store.filter(
                dateBon__month=month
            ).count()

            total_bons_count = bons_comptoire_count + bons_sortie_count
            bons_per_month.append(total_bons_count)

        return bons_per_month
    
    @property
    def total_retours_per_month(self):
        retours_per_month = []
        for month in range(1, 13):
            retours_count = BonRetourComptoir.objects.filter(
                bon_comptoir_associe__store=self,
                dateBon__month=month
            ).count()
            retours_count = BonRetourComptoir.objects.filter(
                bon_comptoir_associe__store=self,
                dateBon__month=month
            ).count()
            retours_per_month.append(retours_count)

        return retours_per_month
  
class Journal(models.Model):
     label  = models.CharField(max_length=2500 , default="", null=True, blank =True)

class PlanComptableClass(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
    
class PlanComptableAccount(models.Model):
    code = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    comptable_class = models.ForeignKey(PlanComptableClass, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.code} - {self.name}"
 
class CompteEntreprise(models.Model):
    Nature_Compte_CHOICES = [
        ("Caisse", "Caisse"),
        ("Banque", "Banque"),
        ("CCP", "CCP"),
        ("Autres", "Autres"),
    ]
    nature = models.CharField( max_length=30, choices=Nature_Compte_CHOICES ) 
    label  = models.CharField(max_length=2500 , default="", null=True, blank =True)
    numCompte  = models.CharField(max_length=2500 , default="", null=True, blank =True)
    banque = models.ForeignKey('tiers.Banque',on_delete = models.CASCADE, related_name='banque_comptes', default=None, null=True, blank =True)
    agence = models.ForeignKey('tiers.Agence',on_delete = models.CASCADE, related_name='agence_comptes', default=None, null=True, blank =True)
    compteComptable = models.ForeignKey(PlanComptableAccount, on_delete=models.CASCADE, related_name="comptable_compteEntreprise")
    journal = models.CharField(max_length=2500 , default="", null=True, blank =True)
    monnaie = models.CharField(max_length=2500 , default="", null=True, blank =True) 
    store =models.ForeignKey(store,on_delete = models.CASCADE, related_name='entreprise_comptes', default=None, null=True, blank =True)

    @property
    def mon_credit(self):
        credit_by_date = []
        if len(self.mouvements_sortie.all())>0:
            for bon in self.mouvements_sortie.all():            
                date_str = bon.date.strftime("%Y-%m-%d")
                prix_payed_float = float(bon.credit)

                # Check if both dateReglement and caisse already exist in the list
                entry_exists = any(
                    entry['dateBon'] == date_str 
                    for entry in credit_by_date
                )

                if entry_exists:
                    # Update the existing entry with the sum of prix_payed
                    for entry in credit_by_date:
                        if entry['dateBon'] == date_str :
                            entry['montant'] += prix_payed_float
                            break
                else:
                    # Add a new entry to the list
                    credit_by_date.append({'dateBon': date_str, 'montant': prix_payed_float})
        return credit_by_date   
              
    @property
    def mon_debit(self):
        credit_by_date = []
        if len(self.mouvements_recu.all())>0:
            for bon in self.mouvements_recu.all():            
                date_str = bon.date.strftime("%Y-%m-%d")
                prix_payed_float = float(bon.credit)

                # Check if both dateReglement and caisse already exist in the list
                entry_exists = any(
                    entry['dateBon'] == date_str 
                    for entry in credit_by_date
                )

                if entry_exists:
                    # Update the existing entry with the sum of prix_payed
                    for entry in credit_by_date:
                        if entry['dateBon'] == date_str :
                            entry['montant'] += prix_payed_float
                            break
                else:
                    # Add a new entry to the list
                    credit_by_date.append({'dateBon': date_str, 'montant': prix_payed_float})
        return credit_by_date     
	
	
 
class Taxes(models.Model):
    Taxes_Type_CHOICES = [
        ("TVA", "TVA"),
        ("DOUAN", "DOUAN"),
    ]
    libelle = models.CharField(max_length=2500 , default="", null=True, blank =True)
    taux = models.CharField(max_length=2500 , default="", null=True, blank =True)
    type_taxe = models.CharField( max_length=30, choices=Taxes_Type_CHOICES) 
    store =models.ForeignKey(store,on_delete = models.CASCADE, related_name='entreprise_taxes', default=None, null=True, blank =True)
    
class Devise(models.Model):
    reference = models.CharField(max_length=2500 , default="", null=True, blank =True)
    designation = models.CharField(max_length=2500 , default="", null=True, blank =True)
    symbole = models.CharField(max_length=2500 , default="", null=True, blank =True)
    actif = models.BooleanField(default=True)
    store =models.ForeignKey(store,on_delete = models.CASCADE, related_name='entreprise_devise', default=None, null=True, blank =True)
    def __str__(self):
	    return "Devis : " + str(self.reference) 
 
class ValeurDevise(models.Model):
    Devise = models.ForeignKey(Devise,on_delete = models.CASCADE, null=True, blank=True,default=None)
    valeur =  models.CharField(max_length=2500 , default="", null=True, blank =True)
    date= models.DateField(default='2023-08-22', blank=True, null=True)
    store =models.ForeignKey(store,on_delete = models.CASCADE, related_name='entreprise_devises_valeur', default=None, null=True, blank =True)
    
class typeClient(models.Model):
    type_desc = models.CharField(max_length=2500 , default="", null=True, blank =True)
    dateCreation = models.DateField(default='2023-08-22', blank=True, null=True)
    montant_min = models.DecimalField(max_digits=150, decimal_places=2, default=0)
    percent =  models.DecimalField(max_digits=3, decimal_places=2, default=0)
    store =models.ForeignKey(store,on_delete = models.CASCADE, related_name='entreprise_typeClient', default=None, null=True, blank =True)
    def __str__(self):
	    return self.type_desc