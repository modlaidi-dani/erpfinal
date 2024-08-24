from django.shortcuts import render
from django.shortcuts import render
from django.views.generic.base import TemplateView
from django.http import Http404, JsonResponse
from . import models
import json
from django.contrib.auth.decorators import login_required
from django.db import transaction,  IntegrityError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import render, get_object_or_404
from users.models import CustomUser
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from collections import defaultdict
from users.models import MyLogEntry
import plotly.express as px
import plotly.graph_objs as go
import plotly
import numpy as np
import plotly.graph_objs as go
import plotly.express as px
from plotly.subplots import make_subplots
from decimal import Decimal
from django.utils import timezone
from django.core.paginator import Paginator
from django.shortcuts import redirect
from datetime import datetime
from notifications.models import Notification
from clientInfo.models import store, Taxes, ValeurDevise
from produits.models import Product, Category, historique_prix_achat, HistoriqueAchatProduit
from tiers.models import Fournisseur, Banque, Client
from reglements.models import ModeReglement, EcheanceReglement
from inventory.models import  Entrepot
# Create your views here.
from django.db.models import Count
from django.core.exceptions import ValidationError


def fetchProductsAchat(request):
  data = json.loads(request.body)
  bonLivraison = models.BonAchat.objects.get(idBon=data["bonL"])
  produits = bonLivraison.produits_en_bon_achat.all()
  produits_data=[]    
  for product in produits :
      produits_dict = {
              'name': product.produit.name,
              'reference':product.produit.reference,
              'quantity': product.quantity,
              'unitprice': float(product.prixUnitaire),
              'totalprice': float(product.totalPrice),
            } 
      produits_data.append(produits_dict)
  return JsonResponse({'produits':produits_data})

def supprimerBonAchat(request):
     with transaction.atomic():
        data = json.loads(request.body)
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        liste_id = data["liste_ids"]
        for id_bon in liste_id:
            try:
                bon_entry = models.BonAchat.objects.get(idBon= id_bon, store=CurrentStore)
                bon_entry.delete()
            except models.BonEntry.DoesNotExist:
                response_data = {'message': 'Bon ACHAT invalide !'}
               
                return JsonResponse(response_data)
        response_data = {'message': 'Bon ACHAT Supprimé !'}
        return JsonResponse(response_data)

def supprimerProjet(request):
    data = json.loads(request.body)
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    liste_id = data["liste_ids"]
    for id_bon in liste_id:
        bon_c = models.ProjetCredit.objects.get(id=id_bon)
        bon_c.delete()
    return JsonResponse({'message': "Eléments Supprimé !"})

class CommandeAchatView(TemplateView):
    template_name = "achats/bon_commande.html"
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        Currentstore = store.objects.get(pk=store_id)  
        entrepots = Entrepot.objects.filter(store= Currentstore)
        context["entrepots"]=entrepots    
        modeReg = ModeReglement.objects.filter(store= Currentstore) 
        context["modeReg"]=modeReg  
        echeances = EcheanceReglement.objects.filter(store= Currentstore)
        context["echeances"] = echeances 
        banques= Banque.objects.filter(store= Currentstore)
        context["banques"] = banques
        taxtva = Taxes.objects.filter(store= Currentstore, type_taxe="TVA")
        context["taxes"] = taxtva
        monnaie = ValeurDevise.objects.filter(store= Currentstore)
        context["monnaie"] = monnaie
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        stock = Product.objects.filter(store=CurrentStore)

        stock_data = []
        for produit in stock:
            stock_data.append({
                'name': produit.name,
                'reference': produit.reference,
                'prix_achat': float(produit.prix_achat),
            })
        context["stock"] = stock_data
        fournisseurs = Fournisseur.objects.filter(store=Currentstore)
        context["fournisseurs"] = fournisseurs  
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData', '')
        print(dataInvoice)
        if dataInvoice:
           idBon =dataInvoice["IdBon"]
           dateBon =dataInvoice["dateBp"]
           destinataire = dataInvoice['destinataire']
           fournisseur_name = dataInvoice["FournisseurInfo"]["name"]
           fournisseur = Fournisseur.objects.filter(acronym=fournisseur_name).first() if fournisseur_name else None

           entrepot_name = dataInvoice.get("entrepot")
           livraison = Entrepot.objects.get(name=entrepot_name) if entrepot_name else None

           mode_reglement_id = dataInvoice.get("modeReglement")
           mode_reg = ModeReglement.objects.get(id=mode_reglement_id) if mode_reglement_id else None

           echeanceReg_id = dataInvoice.get("echeanceReg")
           echeanceReg = ModeReglement.objects.get(id=echeanceReg_id) if echeanceReg_id else None

           tva_id = dataInvoice.get("tva")
           tva = Taxes.objects.get(id=tva_id) if tva_id else None

           monnaie_id = dataInvoice.get("monnaie")
           monnaie = ValeurDevise.objects.get(id=monnaie_id) if monnaie_id else None
           Currentuser = request.user
           myuser  = CustomUser.objects.get(username=Currentuser.username)   
           store_id = self.request.session["store"]
           CurrentStore = store.objects.get(pk=store_id)                                                                      
           bon_commande = models.BonCommandeAchat(
                idBon=idBon,
                dateBon=dateBon,
                fournisseur=fournisseur,
                destinataire=destinataire,
                livraison=livraison ,
                mode_reglement=mode_reg,
                echeance_reglement= echeanceReg,
                TVA =tva,
                monnaie=monnaie,
                user=myuser,
                store=CurrentStore
           )
           bon_commande.save()
           for product_data in dataInvoice['produits']:
             product_reference = product_data['ref']
             product_obj = Product.objects.get(reference=product_reference, store =CurrentStore)
             new_price = Decimal(product_data['rate'])
             totalPrice = int(product_data["qty"]) * new_price
             models.ProduitsEnBonCommandesAchat.objects.create(
              BonNo=bon_commande,
              produit=product_obj,
              prixUnitaire= new_price,
              quantity=int(product_data["qty"]),
              totalPrice = totalPrice
             )          
        return JsonResponse({'message': "Product Added successfully."})

class FactureAchatView(TemplateView):
    template_name = "achats/facture_achat.html"
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        clients_list = Client.objects.filter(store=CurrentStore)
        clients=[]
        for cl in clients_list:
            cl_dict={
               "client_name" :cl.name,
               "client_address":cl.adresse,
               "client_phone" : cl.phone,                      
            }
            clients.append(cl_dict)
        context["clients"]=clients   
        stock = Product.objects.filter(store=CurrentStore)
        fournisseurs = Fournisseur.objects.filter(store=CurrentStore)
        data = []     
        context["fournisseurs"] = fournisseurs  
        context["stock"] = stock
        bons = models.BonAchat.objects.filter(store=CurrentStore)   
        context["bons_sorties"]=bons
        entrepots = Entrepot.objects.filter(store= CurrentStore)
        context["entrepots"]=entrepots
        modeReg = ModeReglement.objects.filter(store= CurrentStore)
        context["modeReg"]=modeReg  
        echeances = EcheanceReglement.objects.filter(store= CurrentStore)
        context["echeances"] = echeances 
        banques= Banque.objects.filter(store= CurrentStore)
        context["banques"] = banques 
        stock = Product.objects.filter(store=CurrentStore)
        context["stock"] = stock
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData', '')
        if dataInvoice:
            print(dataInvoice)
            bonachat = models.BonAchat.objects.get(idBon=dataInvoice['bonachat'])
            fournisseur = Fournisseur.objects.filter(acronym=dataInvoice['fournisseur']).first()
            date_facture = dataInvoice['dateFacture']
            mode_reglement_id = dataInvoice['modeReglement']
            echeance_reglement_id = dataInvoice['echeance']
            remise = dataInvoice['remise']
            etat_reglement = dataInvoice['etatFacture']
          
            if not mode_reglement_id:
                mode_reglement = None
            else:
                 mode_reglement = ModeReglement.objects.get(id=mode_reglement_id)

            # Check if echeance_reglement is an empty string and set it to None
            if not echeance_reglement_id:
                echeance_reglement = None
            else:
              echeance_reglement = EcheanceReglement.objects.get(id=echeance_reglement_id)
            Currentuser = request.user
            myuser  = CustomUser.objects.get(username=Currentuser.username)   
            store_id = self.request.session["store"]
            CurrentStore = store.objects.get(pk=store_id) 
            # Create the FactureAchat instance within a transaction
            with transaction.atomic():
                last_number = models.FactureAchat.objects.order_by('-id').first()
                if last_number:
                    last_number = last_number.id
                else:
                    last_number = 0
                codeF = last_number+1
                facture_achat = models.FactureAchat.objects.create(
                    codeFacture=codeF,
                    date_facture=date_facture,
                    BonAchat=bonachat,
                    fournisseur=fournisseur,
                    mode_reglement=mode_reglement,
                    echeance_reglement=echeance_reglement,
                    Remise=remise,
                    etat_reglement=etat_reglement,
                    user=myuser,
                    store=CurrentStore
                )
                facture_achat.save()
                
            for produit_data in dataInvoice["produits"]:
                product_ref = produit_data['ref']  # Assuming 'id' is a unique identifier for the product
                stock = Product.objects.get(reference=product_ref, store =CurrentStore)  # Replace 'Product' with your actual model name

                quantity = produit_data['qty']
                unitprice = produit_data['rate']
                totalprice = produit_data['total']

                produit_en_facture_achat = models.ProduitsEnFactureAchat.objects.create(
                    FactureNo=facture_achat,
                    stock=stock,
                    quantity=quantity,
                    unitprice=unitprice,
                    totalprice=totalprice,
                ) 
            return JsonResponse({'message': "Facture Ajouté!"})

class DossierAchatView(TemplateView):
    template_name = "achats/dossier_achat.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        stock = Product.objects.filter(store=CurrentStore)
        bonscomm = models.BonCommandeAchat.objects.filter(store=CurrentStore)
        context['billscomm'] = bonscomm
        stock_data = []
        for produit in stock:
            stock_data.append({
                'name': produit.name,
                'reference': produit.reference,
                'prix_achat': float(produit.prix_achat),
            })
        fournisseurs = Fournisseur.objects.filter(store=CurrentStore)
        entrepots = Entrepot.objects.filter(store=CurrentStore)
        unit_monetaire =  ValeurDevise.objects.filter(store=CurrentStore)
        modeReg = ModeReglement.objects.filter(store= CurrentStore) 
        context["modeReg"]=modeReg  
        echeances = EcheanceReglement.objects.filter(store= CurrentStore)
        context["echeances"] = echeances 
        banques = Banque.objects.filter(store = CurrentStore)
        context["banques"] = banques
        context["monnaie"] = unit_monetaire
        context["fournisseurs"] = fournisseurs  
        context["entrepots"] = entrepots
        context["stock"] = stock_data
        return context
    

    @transaction.atomic
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        if request.method == 'POST':
            print(request.POST)
            store_id = self.request.session["store"]
            CurrentStore = store.objects.get(pk=store_id)
            codedossier = request.POST['codedossier']
            datecreation = request.POST['datecreation']
            datefinalisation = request.POST['datefinalisation']
            fournisseurac = request.POST['fournisseur']
            boncomande = request.POST['boncomande']
            unitm = request.POST['unitm']
            montant = request.POST['montant']
            paiement = request.POST['paiement']
            debitDate = request.POST['debitDate']
            banque = request.POST['banque']
            montantDZ = request.POST['montantDZ']
            valeurDate = request.POST['valeurDate']
            montantDate = request.POST['montantDate']
            echange = request.POST['echange']

            facturefile = request.FILES['facturefile']
            debitfile = request.FILES['debitfile']
            valeurfile = request.FILES['valeurfile']
            fournisseurObj = None
            if fournisseurac != "":
                fournisseurObj = Fournisseur.objects.get(acronym=fournisseurac, store = CurrentStore)

            bonCommande = None
            if boncomande != "":
                bonCommande = models.BonCommandeAchat.objects.get(idBon=boncomande, store = CurrentStore)
            else:
                return JsonResponse({'Message':'Erreur: BonCommande ne peut pas être vide'})
            
            banqueObj = None
            if banque != "":
                banqueObj = Banque.objects.get(nom=banque, store = CurrentStore)
                
            myuser=CustomUser.objects.get(username=self.request.user.username)      
            dossier_achat_instance = models.DossierAchat.objects.create(
                idDossier=codedossier,
                dateDossier=datecreation,
                fournisseur=fournisseurObj,
                facture= facturefile,
                BonCommande=bonCommande,
                monnaie=unitm,
                MontantEtrange=montant,
                TypePaiement=paiement,
                AvisDebit=debitfile,
                datePaiement=debitDate,
                banque_Reglement=banqueObj,
                MontantDZD=montantDZ,
                DateValeur=valeurfile,
                DateValeurdate=valeurDate,
                DateMontant=montantDate,
                TauxChange=echange,
                user=myuser,
                store=CurrentStore
            )

            # Save the instance
            dossier_achat_instance.save()

            # Handle success (redirect, success message, etc.)
        return render(request, 'achats/liste_dossierachats.html')  

class ListExpeditionView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "achats/liste_expeditions.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bongarantie' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        expeditions = models.Expedition.objects.filter(store=selected_store)
        context["expeditions"] = expeditions
        return context

class ExpeditionView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "achats/expedition_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bongarantie' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        expeditions = models.Expedition.objects.filter(store=selected_store)
        context["expeditions"] = expeditions
        return context    
    
class ProjetListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "achats/liste_projets.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bongarantie' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        projets = models.ProjetCredit.objects.filter(store=selected_store)
        context["projets"]=projets
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        if request.method == 'POST':
            print(request.POST)
            code_projet = request.POST.get('codeProjet', '')
            marque = request.POST.get('Marque', '')
            date_projet = request.POST.get('dateProjet', '')
            designation = request.POST.get('designation', '')
            cnn = request.POST.get('cnn', '')
            fichier_projet = request.FILES.get('FichierProjet', None)
            selected_store = get_object_or_404(store, pk=self.request.session["store"])
            myuser=CustomUser.objects.get(username=self.request.user.username)

            # Validation (optional, but recommended)
            if not code_projet or not date_projet or not designation:
                # Add more validation checks as needed
                raise ValidationError("Required fields are missing")

            # Create BoiteArchive instance
            projet = models.ProjetCredit.objects.create(
                codeProjet = code_projet,
                Marque = marque,
                dateProjet = date_projet,
                designation = designation,
                cnn = cnn,
                FichierProjet = fichier_projet,
                store = selected_store,
                user =   myuser,
            )

            # Save the instance
            projet.save()

        return render(request, 'achats/liste_projets.html')
    
class AvoirListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "achats/avoirs_achat_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bongarantie' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        avoirs = models.AvoirAchat.objects.filter(store=selected_store)
        context["avoirs"]=avoirs
        bons = models.BonAchat.objects.filter(store=selected_store)
        context["bons"]=bons
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        if dataInvoice: 
             bonLivraison = models.BonAchat.objects.get(id=dataInvoice["bonLivraison"])
             client_obj = Fournisseur.objects.get(id=dataInvoice["client"])
             date= dataInvoice["date"]
             motif= dataInvoice["motif"]
             montant=dataInvoice["montant"]
             selected_store = get_object_or_404(store, pk=self.request.session["store"])
             year = '23'

             # Find the last AvoirVente object
             last_avoir = models.AvoirAchat.objects.last()

             # Determine the next sequential number
             if last_avoir:
                last_code = last_avoir.codeAvoir
                last_sequence = int(last_code.split('-')[1])
                next_sequence = last_sequence + 1
             else:
                next_sequence = 1

             # Create the codeAvoir using the year and sequential number
             codeAvoir = f"AV{year}-{next_sequence:03d}"
             avoirobject = models.AvoirAchat.objects.create(
                 BonSortieAssocie=bonLivraison,
                 fournisseur=client_obj,
                 codeAvoir=codeAvoir,
                 dateEmission=date,
                 store=selected_store,
                 montant=dataInvoice["montant"],
                 motif=motif
             )
        return JsonResponse({'message': "Avoir Added successfully."})

class ListFactureView(TemplateView):
    template_name = "achats/liste_facturesachat.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs) 
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        factures = models.FactureAchat.objects.filter(store=CurrentStore)
        duplicate_query = Product.objects.values('reference', 'store').annotate(count=Count('id')).filter(count__gt=1)

        # Step 2: Iterate over duplicates and keep one, delete the rest
        for duplicate in duplicate_query:
            reference = duplicate['reference']
            storeprod = duplicate['store']
            duplicate_objects = Product.objects.filter(reference = reference, store =storeprod)
            
            # Keep one (you may want to customize this logic based on your requirements)
            object_to_keep = duplicate_objects.first()
            
            # Delete the duplicates
            duplicate_objects.exclude(pk=object_to_keep.pk).delete()
        context["factures"] = factures
        return context

class BonAchatUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "achats/achat_bill_edit.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return self.request.session["role"] =="manager" 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            bill_id=self.kwargs.get('id_bill')
            bon_reforme = models.BonAchat.objects.get(id=bill_id)
            context["bill"]=bon_reforme
            items =[]
            for produit in bon_reforme.produits_en_bon_achat.all():
                produit_dict ={
                    'ref' : produit.produit.reference,
                    'name': produit.produit.name,
                    'qty':produit.quantity,
                    'rate':float(produit.prixUnitaire),
                    'total':produit.quantity * float(produit.prixUnitaire),
                }
                items.append(produit_dict)
            context["items"]=items
            selected_store = store.objects.get(pk=self.request.session["store"])
            context["selected_store"] = selected_store   
            entrepots = Entrepot.objects.filter(store=selected_store)
            context["entrepots"]=entrepots
            stock = Product.objects.filter(store=selected_store)
            fournisseurs = Fournisseur.objects.filter(store=selected_store)
            entrepots = Entrepot.objects.filter(store=selected_store)
            context["fournisseurs"] = fournisseurs  
            context["entrepots"] = entrepots
            stock_data = []
            for produit in stock:
                stock_data.append({
                    'name': produit.name,
                    'reference': produit.reference,
                    'prix_achat': float(produit.prix_achat),
                })
            context["stock"] = stock_data
            return context
   
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        print(dataInvoice)
        existing_bon_reforme = models.BonAchat.objects.get(idBon=dataInvoice["idBon"])
        existing_bon_reforme.entrepot = Entrepot.objects.get(id=dataInvoice["entrepot"])
        existing_bon_reforme.save()
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        existing_bon_reforme.produits_en_bon_achat.all().delete()
        products = dataInvoice["produits"]
        for product_data in dataInvoice['produits']:
            product_reference = product_data['ref']
            new_price = Decimal(product_data['rate'])
            try:
                product = Product.objects.get(reference=product_reference, store = CurrentStore)
                if product.prix_achat != new_price and new_price != 0:
                    # Calculate the average of the old and new prices
                    average_price = (product.prix_achat + new_price) / 2
                    originalPrice= product.prix_achat
                    # Update the product's price
                    # Create an instance of historique_prix_achat
                    version = product.products.count()  # Get the number of related products (versions)
                    historique = historique_prix_achat.objects.create(
                        product=product,
                        version=version,
                        prix_achat_original=originalPrice,
                        prix_achat_newer=average_price
                    )
            except Product.DoesNotExist:
             # Handle the case when the product is not found
                pass
             # prod_total_price = p.prix_vente * int(product["qty"])
            models.ProduitsEnBonAchat.objects.create(
              BonNo=existing_bon_reforme,
              produit=product,
              prixUnitaire= new_price,
              quantity=int(product_data["qty"]),
              totalPrice = dataInvoice["total"]
             )          
        response_data = {'message': 'Bon Achat edited'}
        return JsonResponse(response_data)
        
class StockAchatView(TemplateView):
    template_name = "achats/achat_bill.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        stock = Product.objects.filter(store=CurrentStore)

        stock_data = []
        for produit in stock:
            stock_data.append({
                'name': produit.name,
                'reference': produit.reference,
                'prix_achat': float(produit.prix_achat),
            })
        fournisseurs = Fournisseur.objects.filter(store=CurrentStore)
        entrepots = Entrepot.objects.filter(store=CurrentStore)
        unit_monetaire =  ValeurDevise.objects.filter(store=CurrentStore)
        modeReg = ModeReglement.objects.filter(store= CurrentStore) 
        context["modeReg"]=modeReg  
        echeances = EcheanceReglement.objects.filter(store= CurrentStore)
        context["echeances"] = echeances 
        context["monnaie"] = unit_monetaire
        context["fournisseurs"] = fournisseurs  
        context["entrepots"] = entrepots
        context["stock"] = stock_data
        return context
    
    @method_decorator(login_required)
    @transaction.atomic
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData', '')
        print(dataInvoice)
        if dataInvoice:
           idBon =dataInvoice["IdBon"]
           dateBon =dataInvoice["dateBp"]
           total = dataInvoice['total']
           client_info = dataInvoice['clientInfo']
           # Create or get the client
           client_name = client_info['name']
           client_address = client_info['address']
           client_phone = client_info['phone']
           
           Currentuser = request.user
           myuser  = CustomUser.objects.get(username=Currentuser.username)
           store_id = self.request.session["store"]
           CurrentStore = store.objects.get(pk=store_id) 
           fournisseur_name = dataInvoice["FournisseurInfo"]["name"]
           fournisseur = Fournisseur.objects.filter(acronym=fournisseur_name, store=CurrentStore).first() if fournisseur_name else None   
           entrepot = Entrepot.objects.get(id=dataInvoice["entrepot"])
           ModeReglement_id = None
           echeance = None
           service = None
           unitm = None

           if "ModeReglement" in dataInvoice:
               mode_reglement_id = dataInvoice["ModeReglement"]
               if mode_reglement_id != '':
                if ModeReglement.objects.get(id=mode_reglement_id):
                   ModeReglement_id = ModeReglement.objects.filter(id=mode_reglement_id).first()

           if "echeance" in dataInvoice:
               echeance_id = dataInvoice["echeance"]   
               if  echeance_id !='':         
                 if EcheanceReglement.objects.get(id=echeance_id):
                   echeance = EcheanceReglement.objects.filter(id=echeance_id).first()

           if "service" in dataInvoice:
               service = dataInvoice["service"]

           if "unitm" in dataInvoice:
               unitm_id = dataInvoice["unitm"]
               if unitm_id !='':
                if ValeurDevise.objects.get(id=unitm_id):
                   unitm = ValeurDevise.objects.filter(id=unitm_id).first()


           bon_entry = models.BonAchat.objects.create(
               idBon=idBon ,
               dateBon=dateBon,
               totalPrice=total ,
               user=myuser, 
               store=CurrentStore, 
               fournisseur=fournisseur,
               entrepot =entrepot,
               monnaie= unitm,
               mode_reglement = ModeReglement_id,
               echeance_reglement= echeance
               )
           current_timestamp = datetime.now()
           logs_saving = MyLogEntry.objects.create(
                author= myuser,
                description= f' A Crer un nouveau bon de livraison fournisseur n°= {bon_entry.idBon}, avec un montant de : {total}  ',
                timestamp = current_timestamp.strftime("%d/%m/%Y at %H:%Mh"),
                store  =CurrentStore
            )
           
           products = dataInvoice["produits"]
           for product_data in dataInvoice['produits']:
            product_reference = product_data['ref']
            new_price = Decimal(product_data['rate'])
            try:
                product = Product.objects.get(reference=product_reference, store = CurrentStore)
                qtyActuelle = product.total_quantity_in_stock
                qtyAchat = int(product_data["qty"])
                prixAchat = Decimal(product_data['rate']) 
                last_historique = HistoriqueAchatProduit.objects.filter(produit=product).order_by('-dateAchat').first()
                prixAchatAct =  last_historique.prix_achat_calcule if last_historique else 0
                prix_achat_calcule = ((prixAchatAct * qtyActuelle) + (prixAchat * qtyAchat)) / (qtyAchat + qtyActuelle)
                HistoriqueAchatProduit.objects.create(
                    produit=product,  
                    qty_qctuelle=qtyActuelle,
                    prix_achat_actuelle=prixAchatAct,
                    qty_achete=qtyAchat,
                    prix_achat=prixAchat,
                    prix_achat_calcule=prix_achat_calcule, 
                    dateAchat=dateBon,
                )
                if product.prix_achat != new_price and new_price != 0:
                    # Calculate the average of the old and new prices
                    average_price = (product.prix_achat + new_price) / 2
                    originalPrice= product.prix_achat
                    # Update the product's price
                    # Create an instance of historique_prix_achat
                    version = product.products.count()  # Get the number of related products (versions)
                    historique = historique_prix_achat.objects.create(
                        product=product,
                        version=version,
                        prix_achat_original=originalPrice,
                        prix_achat_newer=average_price
                    )
            except Product.DoesNotExist:
             # Handle the case when the product is not found
                pass
             # prod_total_price = p.prix_vente * int(product["qty"])
            models.ProduitsEnBonAchat.objects.create(
              BonNo=bon_entry,
              produit=product,
              prixUnitaire= new_price,
              quantity=int(product_data["qty"]),
              totalPrice = dataInvoice["total"]
             )          
        return JsonResponse({'message': "Product Added successfully."})
 
    
class ListCommandesView(TemplateView):
    template_name = "achats/liste_bon_commandes.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        bons = models.BonCommandeAchat.objects.filter(store=CurrentStore)      
        context["bons"] = bons
        return context
 
class ListReceptionView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "achats/liste_bon_receptions.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bongarantie' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
       
        bons = models.BonReception.objects.filter(store=selected_store)
        context["bons"]=bons
        return context

class ReceptionView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "achats/bon_reception.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bongarantie' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
       
        bons = models.BonAchat.objects.filter(store=selected_store)
        context["bons"]=bons
        Fournisseurs = Fournisseur.objects.filter(store=selected_store)
        context["fournisseurs"]=Fournisseurs
        expeditions = models.Expedition.objects.filter(store=selected_store)
        context["expeditions"]=expeditions
        return context
    
class ListAchatView(TemplateView):
    template_name = "achats/liste_bon_achat.html"
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        bons = models.BonAchat.objects.filter(store=CurrentStore)      
        context["bons"] = bons
        fournisseurs = Fournisseur.objects.filter(store=CurrentStore)
        entrepots = Entrepot.objects.filter(store=CurrentStore)
        context["fournisseurs"] = fournisseurs  
        context["entrepots"] = entrepots
        return context
    
class ListDossierAchatView(TemplateView):
    template_name = "achats/liste_dossierachats.html"
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        bons = models.DossierAchat.objects.filter(store=CurrentStore)      
        context["bons"] = bons
        fournisseurs = Fournisseur.objects.filter(store=CurrentStore)
        entrepots = Entrepot.objects.filter(store=CurrentStore)
        context["fournisseurs"] = fournisseurs  
        return context