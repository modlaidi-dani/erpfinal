from django.db import models
from wagtail.snippets.models import register_snippet
from clientInfo.models import store, typeClient
from users.models import CustomUser
from django.contrib.auth.models import Permission
from achats.models import BonAchat,FactureAchat
from reglements.models import ReglementFournisseur
from decimal import Decimal
import ast

class TiersCustomPermission(Permission):
    class Meta:
        verbose_name = 'Custom Permission'
        verbose_name_plural = 'Custom Permissions'

class Banque(models.Model):
    nom  = models.CharField(max_length=2500 , default="", null=True, blank =True) 
    code  = models.CharField(max_length=2500 , default="", null=True, blank =True) 
    bic  = models.CharField(max_length=2500 , default="", null=True, blank =True) 
    actif = models.BooleanField(default=True)
    store = models.ForeignKey(store, on_delete=models.CASCADE, related_name='banque_store', blank=True, null=True, default=None)

class Agence(models.Model):
    banque = models.ForeignKey(Banque,on_delete = models.CASCADE, related_name='banque_agence', default=None, null=True, blank =True) 
    code  = models.CharField(max_length=2500 , default="", null=True, blank =True) 
    adresse = models.CharField(max_length=2500 , default="", null=True, blank =True) 
    actif = models.BooleanField(default=True) 
    store = models.ForeignKey(store, on_delete=models.CASCADE, related_name='agence_store', blank=True, null=True, default=None)
     
class Fournisseur(models.Model):
    fournisseur_Type_CHOICES = [
        ("PME", "PME"),
        ("Institutionnel", "Institutionnel"),
        ("Automobile", "Automobile"),
        ("Revendeur", "Revendeur"),
        ("BTPH", "BTPH"),
        ("Industrie", "Industrie"),
        ("Autre", "Autre"),
    ]
    codeFournisseur =models.CharField(max_length=25)
    acronym = models.CharField(max_length=150)
    raison_Social = models.CharField(max_length=150)
    adresse = models.CharField(max_length=250, default="")
    phone = models.CharField(max_length=150, default="")
    email = models.CharField(max_length=150, default="")
    typefournisseur = models.CharField( max_length=25, choices=fournisseur_Type_CHOICES, default="Autre")   
    fournisseurEtrange = models.BooleanField()
    fournisseurClient = models.CharField(max_length=150, default="")
    store = models.ForeignKey(store, on_delete=models.CASCADE, related_name='fournisseur_store', blank=True, null=True, default=None)
    
    @property
    def total_bonachat_price(self):
        # Get all related BonAchat objects for this Fournisseur
        bons_achat = BonAchat.objects.filter(fournisseur=self)
        
        # Calculate the total price by summing up totalPrice values
        total_price = sum(bon.totalPrice for bon in bons_achat)
        
        return total_price
    
    @property
    def credit_reglements(self):
        # Get all related BonAchat objects for this Fournisseur
        bons_achat = BonAchat.objects.filter(fournisseur=self)
        
        # Create a list to store dictionaries with date and total price information
        total_prices = []
        
        for bon in bons_achat :            
            if len(bon.bonAchats_reglements.all()) > 0:
                for reglement in bon.bonAchats_reglements.all():
                    date_str = reglement.dateReglement.strftime("%Y-%m-%d")
                    prix_payed_float = float(reglement.montant)
                    
                    caisse = reglement.CompteEntreprise.label
                
                    # Check if both dateReglement and caisse already exist in the list
                    entry_exists = any(
                        entry['date'] == date_str and entry['caisse'] == caisse
                        for entry in total_prices
                    )

                    if entry_exists:
                        # Update the existing entry with the sum of prix_payed
                        for entry in total_prices:
                            if entry['date'] == date_str and entry['caisse'] == caisse:
                                entry['prix_payed'] += prix_payed_float
                                break
                    else:
                        # Add a new entry to the list
                        total_prices.append({'date': date_str, 'caisse': caisse, 'montant': prix_payed_float})
                        
        return total_prices
        
    @property
    def total_prix_paye(self):
        # Get all related ReglementFournisseur objects for this Fournisseur
        reglements = ReglementFournisseur.objects.filter(fournisseur=self)

        # Calculate the total amount paid by summing up the montant values
        total_montant = sum(reglement.montant for reglement in reglements)

        return total_montant
    @property
    def reste_prix_due(self):
        # Calculate the difference between total paid and total due
        return self.total_bonachat_price - self.total_prix_paye
    
    @property
    def total_factureachat_price(self):
        # Get all related BonAchat objects for this Fournisseur
        factures_achat = FactureAchat.objects.filter(fournisseur=self)
        
        # Calculate the total price by summing up totalPrice values
        total_price = sum(Decimal(bon.get_total_price) for bon in factures_achat)
        
        return total_price
    
    @property
    def total_prix_paye_facture(self):
        # Get all related ReglementFournisseur objects for this Fournisseur
        reglements = ReglementFournisseur.objects.filter(fournisseur=self, facture__isnull=False)

        # Calculate the total amount paid by summing up the montant values
        total_montant = sum(Decimal(reglement.montant) for reglement in reglements)

        return total_montant
    @property
    def reste_prix_due_facture(self):
        # Calculate the difference between total paid and total due
        return self.total_factureachat_price - self.total_prix_paye_facture
    def __str__(self):
	    return "fournisseur : " + str(self.acronym)
 
class Region(models.Model):
    label = models.CharField(max_length=250, default="", null=True, blank=True)
    wilayas = models.TextField(blank=True, null=True,)
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE, related_name="mes_regions", null=True, blank=True)
    date_created = models.DateTimeField() 
    
    def getClients(self):
        wilayas_list = ast.literal_eval(self.wilayas)
        return Client.objects.filter(region_client__in=wilayas_list, store__id = 1)

    
class Client(models.Model):
    name = models.CharField(max_length=150)
    adresse = models.CharField(max_length=250, default="")
    phone = models.CharField(max_length=150, default="")
    email = models.CharField(max_length=150, default="")
    sourceClient = models.CharField(max_length=150, default="")
    categorie_client = models.ForeignKey(typeClient, on_delete = models.CASCADE, related_name='clients_type', blank=True, null=True, default=None)
    registreCommerce = models.CharField(max_length=150, default="")
    Nif = models.CharField(max_length=150, default="")
    Nis = models.CharField(max_length=150, default="")
    num_article = models.CharField(max_length=150, default="")
    region_client = models.CharField(max_length=150, default="")
    solde = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    store = models.ForeignKey(store, on_delete=models.CASCADE, related_name='client_store', blank=True, null=True, default=None)
    user = models.ForeignKey(CustomUser,on_delete = models.CASCADE, related_name='mes_clients', blank=True, null=True, default=None)
    valide  = models.BooleanField(default=True)
    NisDoc = models.FileField(upload_to="media/document")
    NifDoc = models.FileField(upload_to="media/document")
    RCDoc = models.FileField(upload_to="media/document")
    AIDoc = models.FileField(upload_to="media/document")
    
    @property
    def getEtatClient(self):
        if len(self.ma_prospection.all()) >0:
            if self.ma_prospection.last().etatProspection == 'confirme':
                return 'true' if self.valide else 'false'
            else:
                return self.ma_prospection.last().etatProspection          
        else:
                return 'true' if self.valide else 'false' 
                
    @property
    def total_amount(self):
        return sum(Decimal(bon.get_total_soldprice) for bon in self.client_bonS.exclude(idBon__startswith='BECH'))
    
    @property
    def total_rembourse(self):
        return sum(Decimal(reglement.montant) for reglement in self.client_reglements.filter(BonS__isnull=False, type_reglement ="Remboursement"))
        
    @property
    def total_annule(self):
        filtered_bons_retour = [bon for bon in self.client_bons_retour.filter(valide=True) if bon.reintegrated]

        result_sum = sum(Decimal(bon.total_price_retour) * Decimal(1.19) for bon in filtered_bons_retour)
        return result_sum
    
    @property
    def remaining_amount(self):
        return round(self.total_amount + self.solde - (self.total_paid_amount + self.total_rembourse + self.total_annule),0)
    
    @property
    def total_paid_amount(self):
        return sum(Decimal(reglement.montant) for reglement in self.client_reglements.all())
    
    @property
    def total_amount_facture(self):
        return sum(Decimal(bon.get_total_price) for bon in self.client_facture.all())
    
    @property
    def remaining_amount_facture(self):
        return self.total_amount_facture - self.total_paid_amount_facture
    
    @property
    def total_paid_amount_facture(self):
        return sum(Decimal(reglement.montant) for reglement in self.client_reglements.filter(facture__isnull=False))
    
    def get_CA(self):
        client_bons = self.client_bonS.all()
        total_CA= 0
        for bon in client_bons:
              total_CA += bon.totalPrice              

        return total_CA   
      
    @property
    def Solde_comptoir(self):
        client_bons = self.mesbons_comptoir.all()
        bons_retourcompt = self.bonsretour_compt.all()
        total_CA = sum(bon.totalprice for bon in client_bons) - sum(bon.myTotalPrice for bon in bons_retourcompt)
        return total_CA
        
    @property
    def mon_credit(self):
        # Create a list to store dictionaries with dateBon and montant
        credit_by_date = []
        for bon in self.bonsretour_compt.all():
            # Check if the bon is not paid
            date_str = bon.dateBon.strftime("%Y-%m-%d")
            montant_float = float(bon.myTotalPrice)
            caisse = bon.bon_comptoir_associe.pointVente.pos_affectation.first().CompteTres.label

            credit_by_date.append({'dateBon': date_str, 'caisse':caisse, 'montant': montant_float})
        
        for bon in self.client_bonS.exclude(idBon__startswith='BECH'):            
            if len(bon.bonS_reglements.filter(type_reglement ="Remboursement")) > 0:
                for reglement in bon.bonS_reglements.filter(type_reglement ="Remboursement"):
                    date_str = reglement.dateReglement.strftime("%Y-%m-%d")
                    prix_payed_float = float(reglement.montant)
                    
                    caisse = reglement.CompteEntreprise.label
                
                    # Check if both dateReglement and caisse already exist in the list
                    entry_exists = any(
                        entry['dateBon'] == date_str and entry['caisse'] == caisse
                        for entry in credit_by_date
                    )

                    if entry_exists:
                        # Update the existing entry with the sum of prix_payed
                        for entry in credit_by_date:
                            if entry['dateBon'] == date_str and entry['caisse'] == caisse:
                                entry['prix_payed'] += prix_payed_float
                                break
                    else:
                        # Add a new entry to the list
                        credit_by_date.append({'dateBon': date_str, 'caisse': caisse, 'montant': prix_payed_float})
                        
        return credit_by_date 
    
    @property
    def myproductssold(self):
        # Create a list to store dictionaries with dateBon and montant
        stats = []
        components = ['cpu', 'mb', 'ram', 'cpuc', 'ssd', 'psu', 'gpu', 'case', 'casef' ,'moniteur', 'claviers', 'souris']
        for bon in self.client_bonS.exclude(idBon__startswith='BECH'):  
            if len(bon.produits_en_bon_sorties.all()) >0:        
                for produit_sold in bon.produits_en_bon_sorties.all(): 
                    comp = produit_sold.stock.category.pc_component if produit_sold.stock.category is not None else '' 
                    qte = produit_sold.quantity
                    
                    date_str = bon.dateBon.strftime("%Y-%m-%d")
                    entry_exists = any(
                        entry['dateBon'] == date_str and entry['composant'] == comp
                        for entry in stats
                    )

                    if entry_exists:
                        # Update the existing entry with the sum of prix_payed
                        for entry in stats:
                            if entry['dateBon'] == date_str and entry['composant'] == comp:
                                entry['quantity_sold'] += qte
                                entry['montant_sold'] += qte * float(produit_sold.unitprice) * float(1.19)
                                
                                break
                    else:
                        # Add a new entry to the list
                        stats.append({'dateBon': date_str, 'composant': comp, 'quantity_sold': qte, 'montant_sold': qte * float(produit_sold.unitprice) * float(1.19)})         
        return stats 
        
    @property
    def mon_debit(self):
        # Create a list to store dictionaries with dateBon and prix_payed
        debit_by_date = []

        # Iterate through BonComptoir instances related to the client
        for bon in self.mesbons_comptoir.all():
            # print(bon.idBon)
            if not bon.par_verssement:
                # Convert datetime.date to string and Decimal to float
                date_str = bon.dateBon.strftime("%Y-%m-%d")
                caisse = bon.pointVente.pos_affectation.first().CompteTres.label
                prix_payed_float = float(bon.prix_payed- bon.totalremise)

                # Check if both dateBon and caisse already exist in the list
                entry_exists = any(
                    entry['dateBon'] == date_str and entry['caisse'] == caisse
                    for entry in debit_by_date
                )

                if entry_exists:
                    # Update the existing entry with the sum of prix_payed
                    for entry in debit_by_date:
                        if entry['dateBon'] == date_str and entry['caisse'] == caisse:
                            entry['prix_payed'] += prix_payed_float
                            break
                else:
                    # print("pris payer")
                    # if bon.totalremise != 0:
                    #     print(bon.prix_payed)
                    #     print(bon.totalremise)
                        
                        
                    #     print(prix_payed_float)
                    
                    
                    
                    # Add a new entry to the list
                    debit_by_date.append({'dateBon': date_str, 'caisse': caisse, 'prix_payed': prix_payed_float})
            else:
                verssements = bon.verssements.all() 
                for verssement in verssements:  
                    # print("verment")
                    montant_v = 0
                    date_str =verssement.date.strftime("%Y-%m-%d")
                    caisse = bon.pointVente.pos_affectation.first().CompteTres.label
                    montant_v = float(verssement.montant or 0)
                    # print(montant_v)
                    
                    debit_by_date.append({'dateBon': date_str, 'caisse': caisse, 'prix_payed': montant_v})
                    
        for bon in self.client_bonS.exclude(idBon__startswith='BECH'):            
            if len(bon.bonS_reglements.all()) > 0:
                for reglement in bon.bonS_reglements.all():
                    date_str = reglement.dateReglement.strftime("%Y-%m-%d")
                    prix_payed_float = float(reglement.montant)
                    
                    caisse = reglement.CompteEntreprise.label
                
                    # Check if both dateReglement and caisse already exist in the list
                    entry_exists = any(
                        entry['dateBon'] == date_str and entry['caisse'] == caisse
                        for entry in debit_by_date
                    )

                    if entry_exists:
                        # Update the existing entry with the sum of prix_payed
                        for entry in debit_by_date:
                            if entry['dateBon'] == date_str and entry['caisse'] == caisse:
                                entry['prix_payed'] += prix_payed_float
                                break
                    else:
                        # Add a new entry to the list
                        debit_by_date.append({'dateBon': date_str, 'caisse': caisse, 'prix_payed': prix_payed_float})

        verssements = self.client_reglements.filter(facture__isnull=True, BonS__isnull=True) 
        for verssement in verssements:  
            montant_v = 0
            date_str =verssement.dateReglement.strftime("%Y-%m-%d")
            caisse = verssement.CompteEntreprise.label
            montant_v = float(verssement.montant or 0)
            debit_by_date.append({'dateBon': date_str, 'caisse': caisse, 'prix_payed': montant_v})
        return debit_by_date
     
     
    @property
    def margin_total(self):
        debit_by_date = []
        for bon in self.client_bonS.exclude(idBon__startswith='BECH'):
                # Convert datetime.date to string and Decimal to float
                date_str = bon.dateBon.strftime("%Y-%m-%d")
                entrepot_str = bon.entrepot.name
                prix_payed_float = float(bon.ma_marge)

                # Check if both dateBon and caisse already exist in the list
                entry_exists = any(
                    entry['dateBon'] == date_str and
                    entry['entrepot'] == entrepot_str
                    for entry in debit_by_date
                )

                if entry_exists:
                    # Update the existing entry with the sum of prix_payed
                    for entry in debit_by_date:
                        if entry['dateBon'] == date_str :
                            entry['montant'] += prix_payed_float
                            break
                else:
                    # Add a new entry to the list
                    debit_by_date.append({'dateBon': date_str, 'entrepot': entrepot_str, 'user': self.user.username, 'montant': prix_payed_float})  
        return debit_by_date      
    
    @property
    def get_chiffre_affaire(self):
        debit_by_date = []
        for bon in self.client_bonS.exclude(idBon__startswith='BECH'):
                # Convert datetime.date to string and Decimal to float
                date_str = bon.dateBon.strftime("%Y-%m-%d")
                entrepot_str = bon.entrepot.name
                prix_payed_float = float(bon.get_total_price) * float(1.19) 

                # Check if both dateBon and caisse already exist in the list
                entry_exists = any(
                    entry['dateBon'] == date_str and
                    entry['entrepot'] == entrepot_str
                    for entry in debit_by_date
                )

                if entry_exists:
                    # Update the existing entry with the sum of prix_payed
                    for entry in debit_by_date:
                        if entry['dateBon'] == date_str :
                            entry['montant'] += prix_payed_float
                            break
                else:
                    # Add a new entry to the list
                    debit_by_date.append({'dateBon': date_str,'entrepot': entrepot_str, 'user': self.user.username, 'montant': prix_payed_float, 'montantA': float(bon.price_annule)})  
        return debit_by_date      
             
    @property
    def loyalty_points(self):
        client_bonc = self.mesbons_comptoir.all()
        client_bons = self.client_bonS.exclude(idBon__startswith='BECH')
        total_CA = self.Solde_comptoir
        return total_CA // 1000
        
    @property
    def getNifDoc(self):
        if self.NifDoc:
                return self.NifDoc.url
        else:
                return ''
    @property
    def getNisDoc(self):
        if self.NisDoc:
                return self.NisDoc.url
        else:
                return ''
    @property
    def getNifDoc(self):
        if self.NifDoc:
                return self.NifDoc.url
        else:
                return ''
    @property
    def getRCDoc(self):
        if self.RCDoc:
                return self.RCDoc.url
        else:
                return ''
    @property
    def getAIDoc(self):
        if self.AIDoc:
                return self.AIDoc.url
        else:
                return ''
                
    def __str__(self):
	    return "CLient : " + str(self.name) +  "Store : " + str(self.store.id)

class ProspectionClient(models.Model):
    client = models.ForeignKey(Client,on_delete = models.CASCADE, related_name='ma_prospection', blank=True, null=True, default=None)
    SourceClient  = models.CharField(max_length=250, default="", null=True, blank=True)
    etatProspection = models.CharField(max_length=250, default="", null=True, blank=True)

    @property
    def getLastTentative(self):
        if len(self.mes_tentative.all()) >0:
            return {
                'user': self.mes_tentative.last().user.username,
                'dateTime': self.mes_tentative.last().dateDebutTentative.strftime('%d/%m/%y - %H:%M'),
                'etat': self.etatProspection,
            }         
        else:
            return {
                'user': self.client.user.username,
                'dateTime': '',
                'etat': self.client.getEtatClient,
            }      

class Tentatives(models.Model):
    propspection = models.ForeignKey(ProspectionClient,on_delete = models.CASCADE, related_name='mes_tentative', blank=True, null=True, default=None)  
    user = models.ForeignKey(CustomUser,on_delete = models.CASCADE, related_name='mes_tentatives', blank=True, null=True, default=None)
    dateDebutTentative = models.DateTimeField()
    dateFinTentative = models.DateTimeField()
    MoyenContact = models.CharField(max_length=250, default="", null=True, blank=True)
    note = models.CharField(max_length=250, default="", null=True, blank=True)
    
class CompteBancaire(models.Model):
    client = models.ForeignKey(Client,on_delete = models.CASCADE, related_name='compte_bancaire_client', blank=True, null=True, default=None)
    fournisseur = models.ForeignKey(Fournisseur,on_delete = models.CASCADE, related_name='compte_bancaire_client', blank=True, null=True, default=None)
    labelCompte = models.CharField(max_length=250, default="", null=True, blank=True)
    Banque = models.ForeignKey(Banque, on_delete=models.CASCADE, related_name='compte_banque_client', blank=True, null=True, default=None)
    Agence = models.ForeignKey(Agence, on_delete=models.CASCADE, related_name='compte_banque_client', blank=True, null=True, default=None)
    TypeCompte= models.TextField(blank=True, null=True)
    compteclient=models.TextField(blank=True, null=True)
    num_compte = models.IntegerField(null=True, blank=True)
    cle=models.IntegerField(null=True, blank=True)
    IBAN=models.IntegerField(null=True, blank=True)
                                   