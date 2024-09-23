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
from notifications.signals import notify
from django.db.models import Q
from inventory.models import Entrepot, Stock, BonTransfert, ProduitsEnBonTransfert, BonRetour, ProduitsEnBonRetour, BonRetourAncien
from clientInfo.models import store,typeClient
from tiers.models import Client, Banque
from produits.models import Product, Category
from reglements.models import ModeReglement, EcheanceReglement
from comptoire.models import BonComptoire, ProduitsEnBonComptoir, BonRetourComptoir, ProduitsEnBonRetourComptoir, BonRectification
from django.db.models import Count
import ast
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.db.models import Sum, F
from datetime import datetime, timedelta
import asyncio
from asgiref.sync import sync_to_async
from datetime import datetime
import asyncio
from asgiref.sync import sync_to_async
from datetime import datetime
from django.utils.timezone import now

def markLivre(request):
   data = json.loads(request.body)
   Bon = models.BonSortie.objects.get(id=data["idbon"])
   if not Bon.livre :
       Bon.livre = True
       Bon.save()
       return JsonResponse({'message': "Bon Marqué Livré !"})
   else:
       Bon.livre = False
       Bon.save()
       return JsonResponse({'message': "Bon Marqué Non-Livré !"})

def markProduitLivre(request):
   data = json.loads(request.body)
   Bon = models.ProduitsEnBonGarantie.objects.get(id=data["id"])
   if not Bon.livre :
       Bon.livre = True
       Bon.save()
       return JsonResponse({'message': "Produit Marqué Livré !"})

@sync_to_async
def get_store(pk):
    return get_object_or_404(store, pk=pk)

@sync_to_async
def get_total_price(bon):
    return bon.get_total_price()

def fetch_rest_bills(selected_store, current_month):
    rest_bills = list(models.BonSortie.objects.filter(
        store=selected_store, dateBon__month__lt=current_month
    ).order_by('-dateBon').select_related(
        'entrepot', 'client', 'user', 'mode_reglement', 'banque_Reglement'
    ).prefetch_related(
        'produits_en_bon_sorties__stock'
    ))
    
    for bon in rest_bills:
        bon.total_price_computed = bon.get_total_price
        bon.prepared = bon.garantieprepared
        bon.etat = bon.statebill
        bon.etat_transfert = bon.get_etat_transfert
        bon.client_solde = bon.client.total_amount
    
    return rest_bills

async def getRestBills(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)

    current_month = now().month
    selected_store = await get_store(request.session["store"])

    rest_bills = await sync_to_async(fetch_rest_bills)(selected_store, current_month)

    bills_data = []
    for bon in rest_bills:
        produits_en_bon_sorties = bon.produits_en_bon_sorties.all()

        async def get_variant_data(produit):
            return {
                "name": produit.stock.reference,
                "reference": produit.stock.name,
                "price": produit.unitprice,
                "tva": produit.stock.tva,
                "priceachat": produit.totalprice,
                "quantity": produit.quantity,
            }

        tasks = [get_variant_data(produit) for produit in produits_en_bon_sorties]
        variants_data = await asyncio.gather(*tasks)

        bills_data.append(
            {
                "id": bon.id,
                "reference": bon.idBon,
                "date": bon.dateBon,
                "entrepot": bon.entrepot.name if bon.entrepot else '',
                "note": bon.note,
                "client": bon.client.name,
                "source": bon.client.sourceClient,
                "client_adrees": bon.client.adresse,
                "client_solde": bon.client_solde,
                "user": bon.user.username if bon.user else '',
                "totalHt": bon.total_price_computed,
                "garantie": bon.prepared == True,
                "totalprice": round(float(bon.total_price_computed) * 1.19, 0),
                "prixpayed": bon.totalPrice,
                "modereglement": bon.mode_reglement.label if bon.mode_reglement else '',
                "modereglementID": bon.mode_reglement.id if bon.mode_reglement else '',
                "banque": bon.banque_Reglement.pk if bon.banque_Reglement else '',
                "cheque": bon.num_cheque_reglement,
                "livraison": bon.fraisLivraisonexterne,
                "etat": bon.etat,
                "livre": bon.livre == True,
                "remise": bon.Remise,
                "valide": bon.valide == True,
                "transfert_valide": bon.etat_transfert == True,
                "modifiable": bon.modifiable == True,
                "agenceliv": bon.agenceLivraison,
                "showVariants": False,
                "variants": variants_data,
            }
        )

    return JsonResponse({'bills': bills_data})

def confirmBill(request):
    if request.method == 'POST':
        # Extract form data from POST request
        bon_no_idBon = request.POST.get('selectedBL')
        bon_no_id = request.POST.get('billId')
        date_livraison_prevu = request.POST.get('dateLivraison')
        fichier_confirmation = request.FILES.get('LivraisonFile')
        with transaction.atomic():
            print(request.POST)
            try:
                
                # Fetch the related BonSortie instance
                bon_no = models.BonSortie.objects.get(pk=bon_no_id)

                confirmation_bl = models.ConfirmationBl(
                    BonNo=bon_no,
                    dateConfirmation = datetime.today(),
                    dateLivraisonPrevu=date_livraison_prevu,  
                    fichier_confirmation=fichier_confirmation
                )
                confirmation_bl.save()
                bon_no.confirmed = True
                bon_no.save()
                return render(request, 'ventes/invoice_page.html')
            except models.BonSortie.DoesNotExist:
                return HttpResponse("Bon de Livraison not found.", status=404)
    else:
        return render(request, 'ventes/invoice_page.html')
        
class ProduitsNonLivreListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/listeproduitsNonLivre.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bonlivraison' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)       
        # store_id = self.kwargs.get('store_id')
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        date_filter = datetime(2024, 4, 24)

        # Update the query to include the date condition
        filtered_produits = models.ProduitsEnBonGarantie.objects.all()
        produits_en_bon_garantie = [prod for prod in filtered_produits if 'non livré' in prod.getnumSeries or 'Non livré' in prod.getnumSeries]
        users_list = []
        data=[]
        for produit in produits_en_bon_garantie:
          if  produit.BonNo.bonLivraisonAssocie is not None: 
            data.append({
                'id': produit.id,
                'BonNo': produit.BonNo.idBon,
                'client': produit.BonNo.client.name,
                'user': produit.BonNo.bonLivraisonAssocie.user.username,
                'dateBon': produit.BonNo.bonLivraisonAssocie.dateBon,
                'entrepot': produit.BonNo.bonLivraisonAssocie.entrepot.name,
                'BonL': produit.BonNo.bonLivraisonAssocie.idBon,
                'produit': produit.produit.name,  # Assuming 'name' is a field in the Product model
                'quantity': produit.quantity,
                'NumeroSeries': produit.getnumSeries,
            })
            if produit.BonNo.bonLivraisonAssocie.user.username not in users_list:
                users_list.append(produit.BonNo.bonLivraisonAssocie.user.username)
        context['list'] = data
        context["users"] = users_list
        return context
        
def ModifierRecouvrementInfo(request):
    data = json.loads(request.body)
    Bon = models.BonSortie.objects.get(id=data["id"])
    modereg = None
    if data['ModeReglement'] :
        modereg = ModeReglement.objects.get(id = data['ModeReglement'])
        
    banque = None
    if data['banque'] :
        banque = Banque.objects.get(id = data['banque'])
        
    num_cheque = ''
    if data['numCheque'] :
        num_cheque = data['numCheque']
        
    datePaiement = ''
    if data['datePaiement'] :
        datePaiement = data['datePaiement']
    Bon.mode_reglement = modereg
    Bon.banque_Reglement = banque
    Bon.num_cheque_reglement = num_cheque
    Bon.etat_reglement  =  datePaiement
    Bon.save()
    return JsonResponse({'message': "Informations de Recouvrement Ajouté !"})
    
def getStock(request):
   data = json.loads(request.body)
   my_entrepot = Entrepot.objects.get(name=data["nomEnt"])
   type_bill = ''
   if 'type' in data:
    type_bill = data["type"]
   Currentuser = request.user
   myuser = CustomUser.objects.get(username=Currentuser.username)
   stocks = my_entrepot.get_stocks()
   stock_data=[]
   for stock in stocks:
        product_name = stock.product.name
        entrepot_name = stock.entrepot.name
        quantite_diva = 0
        if request.session['store'] == '1':
            quantity = stock.get_quantityBill(type_bill)
        else:
            quantity = stock.quantity
            quantite_diva = stock.product.qty_in_store
        price = stock.product.prix_vente
        reference = stock.product.reference
        entrepot=stock.entrepot.name
        categorie=stock.product.category.pc_component if stock.product.category is not None else ""

        if data.get("typeclient","") != "":
            if request.session['store'] != '1':
                price = stock.product.get_price_per_type(data["typeclient"], '')
            else:
                price = stock.product.get_price_per_type(data["typeclient"], type_bill)
        if price != 0 :
            stock_info = {
                "product_name": product_name,
                "entrepot_name": entrepot_name,
                "quantity": quantity,
                "reference": reference,
                "entrepot":entrepot,
                "categorie":categorie if categorie != 'casef' else 'extras',
                "qty_diva": quantite_diva,
                "qtePerCarton": stock.product.QuantityPerCarton,
                "quantity_facturer":quantity - quantite_diva,
                "price": price,
                "prix_livraison": stock.product.prix_livraison,
                "tax": stock.product.tva_douan,
            }
            stock_data.append(stock_info)
   return JsonResponse({'stocks':stock_data})

class InvoiceEditedListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/invoiceedited_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bonlivraison' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)       
        # store_id = self.kwargs.get('store_id')
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        bon_sorties = models.BonSortie.objects.filter(store = selected_store)

        filtered_bon_sorties = []

        for bon_sortie in bon_sorties:
            # Check if any associated BonGarantie exists
            if  bon_sortie.bon_garantie.exists():
                # Get the associated BonGarantie
                bon_garantie = bon_sortie.bon_garantie.first()
                
                # Gather product references and quantities from BonSortie
                bon_sortie_products = {
                    produit.stock.reference: produit.quantity
                    for produit in bon_sortie.produits_en_bon_sorties.all()
                }
                
                # Gather product references and quantities from BonGarantie
                bon_garantie_products = {
                    produit.produit.reference: produit.quantity
                    for produit in bon_garantie.produits_en_bon_garantie.all()
                }
                
                # Check if the same product references exist in both and if their quantities match
                if bon_sortie_products != bon_garantie_products:
                    filtered_bon_sorties.append(bon_sortie)
        context['list'] = filtered_bon_sorties
        return context
        
def deleteComptoirBill(request):
    data = json.loads(request.body)
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    liste_id = data["liste_ids"]
    for id_bon in liste_id:
        bon_c = BonComptoire.objects.get(idBon=id_bon, store=CurrentStore)
        with transaction.atomic():
                # Get the associated product transfers
                produits_transfert =ProduitsEnBonComptoir.objects.filter(BonNo=bon_c)
                my_entrepot =Entrepot.objects.get(name=bon_c.monentrepot, store=CurrentStore)           
                # Iterate over the product transfers and update stock quantities
                for produit_transfert in produits_transfert:                
                    mon_stock = Stock.objects.get(entrepot=my_entrepot, product=produit_transfert.stock)
                    quantity = produit_transfert.quantity               
                    # Update the source warehouse stock quantity
                    mon_stock.quantity += quantity                
                    mon_stock.save()
                
                    produit_transfert.delete()
                # Delete the transfer bill
                bon_c.delete()
    return JsonResponse({'message': "Eléments Supprimé !"})
 
def deleteComptoirRetourBill(request):
    data = json.loads(request.body)
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    liste_ids = data["liste_ids"]
    for id_bon in liste_ids:
        if id_bon.startswith("RCOMPT"):
            bon_c = BonRetourComptoir.objects.get(idBon=id_bon, bon_comptoir_associe__store=CurrentStore)
            with transaction.atomic():
                # Get the associated product transfers
                produits_transfert = ProduitsEnBonRetourComptoir.objects.filter(BonNo=bon_c)
                entrepot_name = bon_c.bon_comptoir_associe.monentrepot
                my_entrepot = Entrepot.objects.get(name=entrepot_name, store=CurrentStore)
    
                for produit_transfert in produits_transfert:
                    quantity_product = produit_transfert.quantity
    
                    # Check if the quantity is zero
    
                    mon_stock = Stock.objects.get(entrepot=my_entrepot, product=produit_transfert.produit )
                    
                    if mon_stock.quantity == 0:
                        return JsonResponse({'message': "Bon ne peut pas être supprimé ! Produits de bon vide"})
    
                    # Update the source warehouse stock quantity
                    mon_stock.quantity -= quantity_product
                    mon_stock.save()
    
                    produit_transfert.delete()
    
                bon_c.delete()
        elif id_bon.startswith("BRA"):
            bon_c = BonRetourAncien.objects.get(idBon=id_bon, store=CurrentStore)
            with transaction.atomic():
                bon_c.delete()
        else:
            bon_c = BonRetour.objects.get(idBon=id_bon, store=CurrentStore)
            with transaction.atomic():
                # Get the associated product transfers
                produits_transfert =  ProduitsEnBonRetour.objects.filter(BonNo=bon_c)
                my_entrepot = bon_c.bonL.entrepot
                if not bon_c.valide :
                    bon_c.delete()
                else:    
                    for produit_transfert in produits_transfert:
                        quantity_product = produit_transfert.quantity
        
                        # Check if the quantity is zero
        
                        mon_stock = Stock.objects.get(entrepot=my_entrepot, product=produit_transfert.produit )
                        
                        if mon_stock.quantity == 0:
                            return JsonResponse({'message': "Bon ne peut pas être supprimé ! Produits de bon vide"})
        
                        # Update the source warehouse stock quantity
                        mon_stock.quantity -= quantity_product
                        mon_stock.save()
        
                        produit_transfert.delete()
        
                    bon_c.delete()
    return JsonResponse({'message': "Comptoir bill and associated records deleted successfully."})        

def fetchPrice(request):
    data = json.loads(request.body)
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    stocks = Product.objects.filter(store = CurrentStore)
    stock_data=[]
    for product in stocks:
            name = product.name
            Currentuser = request.user
            myuser = CustomUser.objects.get(username=Currentuser.username)
            if myuser.role == 'manager':
                quantity = sum(stock.quantity for stock in product.mon_stock.all())
            else:
                quantity = sum(stock.get_quantity for stock in product.mon_stock.all())
                
            reference = product.reference
            stock_info = {
                "name": name,
                "quantity": quantity,
                "reference": reference,                  
                'rate':product.get_price_per_type(data["clientType"], ''),
                'prix_livraison': product.prix_livraison,
                'tax': product.tva_douan,
                'price': product.get_price_per_type(data["clientType"], ''),
            }
            stock_data.append(stock_info)   

    return JsonResponse({'price_variants':stock_data})

def fetchProducts(request):
  data = json.loads(request.body)
  print(data)
  bonLivraison = models.BonSortie.objects.get(idBon=data["bonL"])
  produits = bonLivraison.produits_en_bon_sorties.all()
  produits_data=[]    
  for produit in produits :
        produit_dict={
            "produit_ref" :produit.stock.reference,
            "produit_name" :produit.stock.name,
            "produit_qty":produit.quantity,
            "produit_tva": float(produit.stock.tva),
            "produit_livraison": float(produit.stock.prix_livraison),
            "produit_unitprice": float(produit.unitprice) if produit.unitprice is not None else None,                    
            "produit_freeprice": float(produit.unitprice) - float(produit.stock.prix_livraison),                    
        }
        produits_data.append(produit_dict)
  return JsonResponse({'produits':produits_data})

def addClient(request):
    data = json.loads(request.body)
    dataInvoice = data
    nom_client = dataInvoice["nomClient"] 
    adresse_client = dataInvoice["adresse"]
    phone_client = dataInvoice["phone"]
    categorie = dataInvoice["catclient"]
    Currentuser = request.user
    myuser  = CustomUser.objects.get(username=Currentuser.username)
    store_id = request.session["store"]
    my_store = store.objects.get(pk=store_id)
    category_client = None
    if categorie != 'null':
        category_client = typeClient.objects.get(id=categorie)

    client = Client.objects.create(
        name = nom_client,
        adresse = adresse_client,
        phone = phone_client,
        categorie_client= category_client,
        store = my_store,
        user=myuser
    )
    
    return JsonResponse({'success': True})
 
def deleteInvoiceBill(request):
    data = json.loads(request.body)
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    liste_id = data["liste_ids"]
    for id_bon in liste_id:
        bon_c = models.BonSortie.objects.get(idBon=id_bon, store=CurrentStore)
        with transaction.atomic():
                # Get the associated product transfers
                produits_transfert = models.ProduitsEnBonSortie.objects.filter(BonNo=bon_c)
                my_entrepot = Entrepot.objects.get(name=bon_c.entrepot, store=CurrentStore)           
                # Iterate over the product transfers and update stock quantities
                for produit_transfert in produits_transfert:                
                    mon_stock = Stock.objects.get(entrepot=my_entrepot, product=produit_transfert.stock)
                    quantity = produit_transfert.quantity               
                    # Update the source warehouse stock quantity
                    mon_stock.quantity += quantity                
                    mon_stock.save()
                
                    produit_transfert.delete()

                bon_c.delete()
    return JsonResponse({'message': "Eléments Supprimé !"})   

def delete_devis_bill(request):
    data = json.loads(request.body)
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    liste_ids = data["liste_ids"]
    for id_bon in liste_ids:
        bon_c = models.BonDevis.objects.get(idBon=id_bon, store=CurrentStore)
        with transaction.atomic():
            bon_c.delete()
    return JsonResponse({'message': "Bons de devis Supprimés."})   
     
def delete_garantie_bill(request):
    data = json.loads(request.body)
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    liste_ids = data["liste_ids"]
    for id_bon in liste_ids:
        bon_c = models.BonGarantie.objects.get(idBon=id_bon, store=CurrentStore)
        with transaction.atomic():
            bon_c.delete()
    return JsonResponse({'message': "Bons de garantie Supprimés."})     
   
def delete_facture_bill(request):
    data = json.loads(request.body)
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    liste_ids = data["liste_ids"]
    for id_bon in liste_ids:
        bon_c = models.Facture.objects.get(codeFacture=id_bon, store=CurrentStore)
        with transaction.atomic():
            bon_c.delete()
    return JsonResponse({'message': "Factures Supprimées."})  
 
  
class GarantieComptView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/bon_garantieCompt.html"
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
        bill_id=self.kwargs.get('id_bon')
        
        invoice = BonComptoire.objects.get(id=bill_id)
        idBon = invoice.idBon
        dateBon = invoice.dateBon
        client_name= invoice.client.name
        client_address = invoice.client.adresse
        client_phone= invoice.client.phone
        products_enBon = invoice.produits_en_bon_comptoir.all()
        items=[]
        for product in products_enBon:
             produit_dict={
               "produit_ref" :product.stock.reference,
               "produit_name" :product.stock.name,
               "produit_qty":product.quantity,
               "produit_unitPrice" : float(product.unitprice),
               "prdouit_totalPrice":float(product.totalprice)            
              }
             items.append(produit_dict)
        context["bill"] = invoice    
        context["idBon"] = idBon
        context["dateBon"] = dateBon
        context["client_name"]= client_name
        context["client_address"]= client_address
        context["client_phone"] = client_phone
        context["items"]=items
       
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        context["selected_store"] = selected_store    
        store_id = self.request.session["store"]
        my_store = store.objects.get(pk=store_id)
     
        entrepots = Entrepot.objects.filter(store= my_store)
          # Step 3: Get all the stocks associated with each Entrepot
        all_stocks = []
        for entrepot in entrepots:
            stocks_for_entrepot = entrepot.get_stocks()
            all_stocks.extend(stocks_for_entrepot)

        context["stock"] = all_stocks
        current_year = datetime.now().strftime('%y')
        current_month = datetime.now().strftime('%m')
        last_number = models.BonGarantie.objects.order_by('-id').first()
        if last_number:
            last_number = last_number.id
        else:
            last_number = 0
        codeBon = f'FIG{current_year}{current_month}-{last_number + 1:04d}'
        context["code"] = codeBon
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')

        if dataInvoice: 
           print(dataInvoice)
           Currentuser = self.request.user
           myuser  = CustomUser.objects.get(username=Currentuser.username)
           store_id = self.request.session["store"]
           CurrentStore = store.objects.get(pk=store_id)
           current_year = datetime.now().strftime('%y')
           current_month = datetime.now().strftime('%m')
           last_number = models.BonGarantie.objects.order_by('-id').first()
           if last_number:
                last_number = last_number.id
           else:
                last_number = 0
           codeBon = f'FIG{current_year}{current_month}-{last_number + 1:04d}'
           dateBon = dataInvoice["dateBp"]
           client = Client.objects.filter(name=dataInvoice["clientInfo"]["name"], store=CurrentStore).first()
           bon_garantie = models.BonGarantie.objects.create(
              idBon = codeBon,
              dateBon = dateBon,
              tps_ecoule = dataInvoice["time"],
              store = CurrentStore,
              client = client,
              user =myuser
            )
           bon_garantie.save()
           products =dataInvoice["produits"]
           for product in products :
              produit = Product.objects.get(reference = product["ref"], store = CurrentStore)
              NumeroSeries = product["numSeries"]
              qty= product["qty"]
              models.ProduitsEnBonGarantie.objects.create(
                BonNo = bon_garantie,
                produit = produit,
                NumeroSeries = NumeroSeries 
              )
           return JsonResponse({'Message':'bill created Succesfully'})
           
class InvoicePCListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/invoicepc_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bonlivraison' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)       
        # store_id = self.kwargs.get('store_id')
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        if(myuser.role =='manager') or (myuser.username =='ziad') or (myuser.role=='DIRECTEUR EXECUTIF') or (myuser.role=='gestion-stock') :
            bons_sorties = models.BonSortie.objects.filter(store=selected_store, reference_pc__isnull=False, reference_pc__gt='').order_by('-id')
        else:
            bons_sorties = models.BonSortie.objects.filter(store=selected_store, user=myuser, reference_pc__isnull=False, reference_pc__gt='').order_by('-id')
        context["bons_sorties"] = bons_sorties
        entrepots = Entrepot.objects.filter(store=selected_store)
        context["entrepots"] = entrepots
        users_bills = CustomUser.objects.filter(EmployeeAt=selected_store)
        context["users"]=users_bills
        
        return context
     
class BILLMAG54UpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/invoice_bill_mag54_update.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bonlivraison' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        bill_id = self.kwargs.get('bill_id')
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        invoice = models.BonSortie.objects.get(id=bill_id)
        idBon = invoice.idBon
        dateBon = invoice.dateBon
        client_name = invoice.client.name
        client_address = invoice.client.adresse
        client_phone = invoice.client.phone
        clients = Client.objects.filter(store=CurrentStore, valide= True)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        
        context["clients"]=clients    
        products_enBon = invoice.produits_en_bon_sorties.all()
        entrepots = Entrepot.objects.filter(store= CurrentStore)
        context["entrepots"]=entrepots    
        modeReg = ModeReglement.objects.filter(store= CurrentStore) 
        context["modeReg"]=modeReg  
        echeances = EcheanceReglement.objects.filter(store= CurrentStore)
        context["echeances"] = echeances 
        banques= Banque.objects.filter(store= CurrentStore)
        context["banques"] = banques
        items=[]
        for product in products_enBon:
             produit_dict={
               "produit_ref" :product.stock.reference,
               "produit_name" :product.stock.name,
               "produit_qty":product.quantity,
               "produit_unitprice": float(product.unitprice) if product.unitprice is not None else None,                    
              }
             items.append(produit_dict)
          
        context["bill"] = invoice

        context["items"]=items
       
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        context["selected_store"] = selected_store    
        store_id = self.request.session["store"]
        my_store = store.objects.get(pk=store_id)
     
        entrepots = Entrepot.objects.filter(store=my_store)
          # Step 3: Get all the stocks associated with each Entrepot
        all_stocks = []
        for entrepot in entrepots:
            stocks_for_entrepot = entrepot.get_stocks()
            all_stocks.extend(stocks_for_entrepot)

        context["stock"] = all_stocks
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        data = data.get('formData', '')
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        try:
             with transaction.atomic():
                # Get the existing BonComptoir instance
                idbon = data["IdBon"]
                bon_comptoir = models.BonSortie.objects.select_for_update().get(idBon=idbon)
                # Handle stock updates for deleted entries
                for produit in bon_comptoir.produits_en_bon_sorties.all():
                    myentrepot = Entrepot.objects.get(name = data["entrepotBon"], store = CurrentStore)
                    stock_entry = Stock.objects.get(product=produit.stock, entrepot=myentrepot)
                    stock_entry.quantity += produit.quantity
                    stock_entry.save()
                    produit.delete()
                    
                client_name = data["clientInfo"]["name"]
                client_instance = Client.objects.filter(name=client_name).first()
                bon_comptoir.client = client_instance
                bon_comptoir.totalPrice = data.get('total', bon_comptoir.totalPrice)
                bon_comptoir.Remise = data.get('remise', bon_comptoir.Remise)
                myentrepot = Entrepot.objects.get(name = data["entrepotBon"], store = CurrentStore)
                # Save the updated BonComptoir
                for product in data["produits"]:            
                    p = Stock.objects.get( Q(product__name=product["name"]) & Q(entrepot=myentrepot))
                    new_quantity = p.quantity - int(product["qty"]) ## la quantité dans l'entrepot qui convient
                    if new_quantity < 0:
                         # If any product has insufficient quantity, return a response to inform the user
                        return JsonResponse({'error': f"Stock Insuffisant pour  : {product['name']}", 'prompt_user': True})            
                    p.quantity = new_quantity
                    p.save()  
                    
                bon_comptoir.save()
                    
                for produit in data["produits"]:
                    produit_inst = Product.objects.get(reference=produit["ref"], store = CurrentStore)
                    produit_inst.TotalQte -= int(produit["qty"])
                    produit_inst.save()
                    qty = int(produit['qty'])
                    rate = float(produit['rate'])
                    total = int(qty) * float(rate)
                    models.ProduitsEnBonSortie.objects.create(
                        BonNo = bon_comptoir,
                        stock = produit_inst,
                        quantity = qty,
                        unitprice = rate,
                        totalprice =total
                    )
                        
        except models.BonSortie.DoesNotExist:
            return JsonResponse({'error': "Bon Livraison not found.", 'prompt_user': False})    
        
        return JsonResponse({'success': "Bon Livraison modifié.", 'prompt_user': False})
    
class StockSellDIVAUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/invoice_billd_edit.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bonlivraison' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        bill_id = self.kwargs.get('bill_id')
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        try:
            bill_id = kwargs['bill_id']
            invoice = models.BonSortie.objects.get(id=bill_id)
            # rest of your code
        except models.BonSortie.DoesNotExist:
            raise Http404(f"Bon {bill_id} n'existe Pas")
        except ValueError as e:
            # Log the error along with additional information like user details
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in get_context_data: {e}, User: {self.request.user}, Bill ID: {bill_id}")
            # re-raise the error to maintain the normal flow
            raise
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        if myuser.role != 'manager' and myuser.role != 'DIRECTEUR EXECUTIF' and myuser.username != 'younes_facturation' and not invoice.modifiable:
            raise PermissionDenied("Vous avez pas la permission d'accéder au.")
       
        idBon = invoice.idBon
        dateBon = invoice.dateBon.strftime('%d/%m/%Y')
        client_name = invoice.client.name
        client_address = invoice.client.adresse
        client_phone = invoice.client.phone
        client_solde = float(invoice.client.remaining_amount),
        clients = Client.objects.filter(store=CurrentStore, valide= True)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        
        context["clients"]=clients    
        products_enBon = invoice.produits_en_bon_sorties.all()
        entrepots = Entrepot.objects.filter(store= CurrentStore)
        context["entrepots"]=entrepots    
        modeReg = ModeReglement.objects.filter(store= CurrentStore) 
        context["modeReg"]=modeReg  
        echeances = EcheanceReglement.objects.filter(store= CurrentStore)
        context["echeances"] = echeances 
        banques= Banque.objects.filter(store= CurrentStore)
        context["banques"] = banques
        items=[]
        for product in products_enBon:
             produit_dict={
               "produit_ref" :product.stock.reference,
               "produit_name" :product.stock.name,
               "produit_qty":product.quantity,
               "produit_tva": float(product.stock.tva),
               "produit_tax": float(product.stock.tva_douan),
               "produit_livraison": float(product.stock.prix_livraison),
               "produit_unitprice": float(product.unitprice) if product.unitprice is not None else None,                    
               "produit_freeprice": float(product.unitprice) - float(product.stock.prix_livraison),                    
              }
             items.append(produit_dict)
          
        context["bill"] = invoice
        print(context["bill"])
        context["items"]=items
        if(myuser.role =='manager'):
          bons_retour = BonRetour.objects.filter(store=CurrentStore)
        else:    
          bons_retour = BonRetour.objects.filter(store=CurrentStore, user = myuser)
        context["bons_commandes"]= bons_retour
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        context["selected_store"] = selected_store    
        store_id = self.request.session["store"]
        my_store = store.objects.get(pk=store_id)
     
        entrepots = Entrepot.objects.filter(store=my_store)
          # Step 3: Get all the stocks associated with each Entrepot
        all_stocks = []
        for entrepot in entrepots:
            stocks_for_entrepot = entrepot.get_stocks()
            all_stocks.extend(stocks_for_entrepot)
        my_entrepot = invoice.entrepot
        stocks = my_entrepot.get_stocks()
        stock_data=[]
        type_client = invoice.client.categorie_client.id
        for stock in stocks:
                product_name = stock.product.name
                entrepot_name = stock.entrepot.name
                
                if myuser.role == 'manager':
                    quantity = stock.quantity
                else:
                    quantity = stock.get_quantity
                price = stock.product.get_price_per_type(type_client,'')
                reference = stock.product.reference
                entrepot= stock.entrepot.name
                categorie= stock.product.category.Libellé if stock.product.category is not None else ''

                stock_info = {
                    "product_name": product_name,
                    "entrepot_name": entrepot_name,
                    "quantity": quantity,
                    "reference": reference,
                    "entrepot":entrepot,
                    "categorie":categorie,
                    "price": float(price),
                    "tax": float(stock.product.tva_douan),
                    "prix_livraison": float(stock.product.prix_livraison),
                }
                stock_data.append(stock_info)
        types_client = typeClient.objects.filter(store = CurrentStore)      
        typescl_info = []
        for t in types_client:
            typescl_info.append({
                'label': t.type_desc,
                'percent': t.percent
            })  
        context["typespercents"] = typescl_info        
        context["stocks"] = stock_data
        
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        data = data.get('formData', '')
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        try:
             with transaction.atomic():
                # Get the existing BonComptoir instance
                idbon = data["IdBon"]
                bon_comptoir = models.BonSortie.objects.select_for_update().get(id=data["id"])
                # Handle stock updates for deleted entries
                for produit in bon_comptoir.produits_en_bon_sorties.all():
                    myentrepot = Entrepot.objects.get(name = data["entrepotBon"], store = CurrentStore)
                    try:
                        stock_entry = Stock.objects.get(product=produit.stock, entrepot=myentrepot)
                        # If it exists, update the quantity
                        stock_entry.quantity += produit.quantity
                        
                    except Stock.DoesNotExist:
                        # If it doesn't exist, create a new stock entry
                        stock_entry = Stock.objects.create(product=produit.stock, entrepot=myentrepot, quantity=produit.quantity)
                    stock_entry.save()
                    produit.delete()
                
                fraisLivraison = bon_comptoir.fraisLivraison,                  
                fraisLivraison = 0
                if data['fraislivraison'] :
                    fraisLivraison = data['fraislivraison']
                if self.request.session["store"] == '6' :    
                    if bon_comptoir.dateBon != data["dateBp"]:
                        bon_comptoir.dateBon = data["dateBp"]
                        bon_comptoir.save()    
                # fraisLivraisonexterne = bon_comptoir.fraisLivraisonexterne, 
                # if data.get('fraislivraisonext') :
                #     fraisLivraisonexterne = data['fraislivraisonext']    
                bon_comptoir.idBon = idbon
                bon_comptoir.fraisLivraison = fraisLivraison 
                # bon_comptoir.fraisLivraisonexterne = fraisLivraisonexterne 
                client_name = data["clientInfo"]["name"]
                client_instance = Client.objects.filter(name=client_name, store = CurrentStore).first()
                bon_comptoir.client = client_instance
                bon_comptoir.Remise = float(data.get('remise', bon_comptoir.Remise))
                myentrepot = Entrepot.objects.get(name = data["entrepotBon"], store = CurrentStore)
                bon_comptoir.entrepot= myentrepot
                # Save the updated BonComptoir
                for product in data["produits"]:            
                    p = Stock.objects.get( Q(product__reference=product["ref"]) & Q(entrepot=myentrepot))
                    new_quantity = p.quantity - int(product["qty"]) ## la quantité dans l'entrepot qui convient
                    if new_quantity < 0:
                         # If any product has insufficient quantity, return a response to inform the user
                        return JsonResponse({'error': f"Stock Insuffisant pour  : {product['name']}", 'prompt_user': True})            
                bon_comptoir.etat_reglement = data["obs"]    
                bon_comptoir.modifiable=False    
                bon_comptoir.valide=False    
                bon_comptoir.save()
                    
                for produit in data["produits"]:
                    p = Stock.objects.get( Q(product__reference=produit["ref"]) & Q(entrepot=myentrepot))
                    new_quantity = p.quantity - int(produit["qty"]) ## la quantité dans l'entrepot qui convient
                    p.quantity = new_quantity
                    p.save() 
                    produit_inst = Product.objects.get(reference=produit["ref"], store = CurrentStore)
                    produit_inst.TotalQte -= int(produit["qty"])
                    produit_inst.save()
                    qty = int(produit['qty'])
                    rate = float(produit['rateLiv'])
                    total = int(qty) * float(rate)
                    models.ProduitsEnBonSortie.objects.create(
                        BonNo = bon_comptoir,
                        stock = produit_inst,
                        quantity = qty,
                        unitprice = rate,
                        totalprice =total
                    )
                myuser=CustomUser.objects.get(username=self.request.user.username)
                responsable_entrepot = CustomUser.objects.filter(role ="manager")
                if responsable_entrepot:
                 for resp in responsable_entrepot : 
                        notify.send(
                            sender=myuser,
                            recipient=resp,
                            verb=f'Bon de Livraison numero {bon_comptoir.idBon} a été Modifié  par {myuser} , Veuillez valider',
                            description=f'/ventes/edit-bill-diva/{bon_comptoir.id}',
                            level=1,
                        )        
        except models.BonSortie.DoesNotExist:
            return JsonResponse({'error': "Bon Livraison not found.", 'prompt_user': False})    
        
        return JsonResponse({'success': "Bon Livraison modifié.", 'prompt_user': False})

class StockSellDIVACartonUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/invoice_billd_carton_edit.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bonlivraison' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        bill_id = self.kwargs.get('bill_id')
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        try:
            bill_id = kwargs['bill_id']
            invoice = models.BonSortie.objects.get(id=bill_id)
            # rest of your code
        except models.BonSortie.DoesNotExist:
            raise Http404(f"Bon {bill_id} n'existe Pas")
        except ValueError as e:
            # Log the error along with additional information like user details
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in get_context_data: {e}, User: {self.request.user}, Bill ID: {bill_id}")
            # re-raise the error to maintain the normal flow
            raise
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        if myuser.role != 'manager' and myuser.role != 'DIRECTEUR EXECUTIF' and myuser.username != 'younes_facturation' and not invoice.modifiable:
            raise PermissionDenied("Vous avez pas la permission d'accéder au.")
        idBon = invoice.idBon
        dateBon = invoice.dateBon.strftime('%d/%m/%Y')
        client_name = invoice.client.name
        client_address = invoice.client.adresse
        client_phone = invoice.client.phone
        client_solde = float(invoice.client.remaining_amount),
        clients = Client.objects.filter(store=CurrentStore, valide= True)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        
        context["clients"]=clients    
        products_enBon = invoice.produits_en_bon_sorties.all()
        entrepots = Entrepot.objects.filter(store= CurrentStore)
        context["entrepots"]=entrepots    
        modeReg = ModeReglement.objects.filter(store= CurrentStore) 
        context["modeReg"]=modeReg  
        echeances = EcheanceReglement.objects.filter(store= CurrentStore)
        context["echeances"] = echeances 
        banques= Banque.objects.filter(store= CurrentStore)
        context["banques"] = banques
        items=[]
        for product in products_enBon:
             produit_dict={
               "produit_ref" :product.stock.reference,
               "produit_name" :product.stock.name,
               "produit_qty":product.quantity,
               "produit_tva": float(product.stock.tva),
               "produit_tax": float(product.stock.tva_douan),
               "produit_percart": product.stock.QuantityPerCarton,
               "produit_livraison": float(product.stock.prix_livraison),
               "produit_unitprice": float(product.unitprice) if product.unitprice is not None else None,                    
               "produit_freeprice": float(product.unitprice) - float(product.stock.prix_livraison),                    
              }
             items.append(produit_dict)
          
        context["bill"] = invoice

        context["items"]=items
        if(myuser.role =='manager'):
          bons_retour = BonRetour.objects.filter(store=CurrentStore)
        else:    
          bons_retour = BonRetour.objects.filter(store=CurrentStore, user = myuser)
        context["bons_commandes"]= bons_retour
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        context["selected_store"] = selected_store    
        store_id = self.request.session["store"]
        my_store = store.objects.get(pk=store_id)
     
        entrepots = Entrepot.objects.filter(store=my_store)
          # Step 3: Get all the stocks associated with each Entrepot
        all_stocks = []
        for entrepot in entrepots:
            stocks_for_entrepot = entrepot.get_stocks()
            all_stocks.extend(stocks_for_entrepot)
        my_entrepot = invoice.entrepot
        stocks = my_entrepot.get_stocks()
        stock_data=[]
        type_client = invoice.client.categorie_client.id
        for stock in stocks:
                product_name = stock.product.name
                entrepot_name = stock.entrepot.name
                
                if myuser.role == 'manager':
                    quantity = stock.get_quantity
                else:
                    quantity = stock.get_quantity
                price = stock.product.get_price_per_type(type_client, 'carton')
                reference = stock.product.reference
                entrepot= stock.entrepot.name
                categorie=stock.product.category.pc_component if stock.product.category is not None else ""
                if price != 0 :
                    stock_info = {
                        "product_name": product_name,
                        "entrepot_name": entrepot_name,
                        "quantity": quantity,
                        "reference": reference,
                        "entrepot":entrepot,
                        "categorie":categorie,
                        "qtePerCarton": stock.product.QuantityPerCarton,
                        "price": float(price),
                        "prix_livraison": float(stock.product.prix_livraison),
                        "tax": float(stock.product.tva_douan),
                    }
                    stock_data.append(stock_info)
        types_client = typeClient.objects.filter(store = CurrentStore)      
        typescl_info = []
        for t in types_client:
            typescl_info.append({
                'label': t.type_desc,
                'percent': t.percent
            })  
        context["typespercents"] = typescl_info      
        context["stocks"] = stock_data
        categories= Category.objects.filter(store= selected_store, kit = True)
        context["categories"] = categories
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        data = data.get('formData', '')
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        try:
            with transaction.atomic():
                idbon = data["IdBon"]
                bon_comptoir = models.BonSortie.objects.select_for_update().get(id=data["id"])
                for produit in bon_comptoir.produits_en_bon_sorties.all():
                    myentrepot = Entrepot.objects.get(name = data["entrepotBon"], store = CurrentStore)
                    try:
                        stock_entry = Stock.objects.get(product=produit.stock, entrepot=myentrepot)
                        # If it exists, update the quantity
                        stock_entry.quantity += produit.quantity
                        
                    except Stock.DoesNotExist:

                        stock_entry = Stock.objects.create(product=produit.stock, entrepot=myentrepot, quantity=produit.quantity)
                    stock_entry.save()
                    produit.delete()
                
                fraisLivraison = bon_comptoir.fraisLivraison,                  
                fraisLivraison = 0
                if data['fraislivraison'] :
                    fraisLivraison = data['fraislivraison']
                if self.request.session["store"] == '6' :    
                    if bon_comptoir.dateBon != data["dateBp"]:
                        bon_comptoir.dateBon = data["dateBp"]
                        bon_comptoir.save()    
                bon_comptoir.idBon = idbon
                bon_comptoir.fraisLivraison = fraisLivraison 
                client_name = data["clientInfo"]["name"]
                client_instance = Client.objects.filter(name=client_name).first()
                bon_comptoir.client = client_instance
                bon_comptoir.Remise = float(data.get('remise', bon_comptoir.Remise))
                myentrepot = Entrepot.objects.get(name = data["entrepotBon"], store = CurrentStore)
                bon_comptoir.entrepot= myentrepot
                # Save the updated BonComptoir
                for product in data["produits"]:            
                    p = Stock.objects.get( Q(product__reference=product["ref"]) & Q(entrepot=myentrepot))
                    new_quantity = p.quantity - int(product["qty"]) ## la quantité dans l'entrepot qui convient
                    if new_quantity < 0:
                        # If any product has insufficient quantity, return a response to inform the user
                        return JsonResponse({'error': f"Stock Insuffisant pour  : {product['name']}", 'prompt_user': True})            
                bon_comptoir.etat_reglement = data["obs"]    
                bon_comptoir.modifiable=False    
                bon_comptoir.valide=False    
                bon_comptoir.save()
                    
                for produit in data["produits"]:
                    p = Stock.objects.get( Q(product__reference=produit["ref"]) & Q(entrepot=myentrepot))
                    new_quantity = p.quantity - int(produit["qty"]) ## la quantité dans l'entrepot qui convient
                    p.quantity = new_quantity
                    p.save() 
                    produit_inst = Product.objects.get(reference=produit["ref"], store = CurrentStore)
                    produit_inst.TotalQte -= int(produit["qty"])
                    produit_inst.save()
                    qty = int(produit['qty'])
                    rate = float(produit['rateLiv'])
                    total = int(qty) * float(rate)
                    models.ProduitsEnBonSortie.objects.create(
                        BonNo = bon_comptoir,
                        stock = produit_inst,
                        quantity = qty,
                        unitprice = rate,
                        totalprice =total
                    )
                myuser=CustomUser.objects.get(username=self.request.user.username)
                responsable_entrepot = CustomUser.objects.filter(role ="manager")
                if responsable_entrepot:
                 for resp in responsable_entrepot : 
                        notify.send(
                            sender=myuser,
                            recipient=resp,
                            verb=f'Bon de Livraison numero {bon_comptoir.idBon} a été Modifié  par {myuser} , Veuillez valider',
                            description=f'/ventes/edit-bill-diva/{bon_comptoir.id}',
                            level=1,
                        )        
        except models.BonSortie.DoesNotExist:
            return JsonResponse({'error': "Bon Livraison not found.", 'prompt_user': False})    
        
        return JsonResponse({'success': "Bon Livraison modifié.", 'prompt_user': False})
        
         
class ComptoirRetourUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/comptoirretour_bill_update.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bonlivraison' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  
        
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        bill_id=self.kwargs.get('bill_id')
    
        invoice = BonRetourComptoir.objects.get(id=bill_id)
        idBon = invoice.idBon
        dateBon = invoice.dateBon
        totalPrice=invoice.myTotalPrice
        client_name= invoice.client.name
        client_address = invoice.client.adresse
        client_phone= invoice.client.phone
        products_enBon = invoice.produits_en_bon_retourcomptoir.all()
        items=[]
        for product in products_enBon:
            produit_dict={
               "produit_ref" :product.produit.reference,
               "produit_name" :product.produit.name,
               "produit_category" :product.produit.category.Libellé,
               "produit_qty":int(product.quantity),
               "produit_unitPrice" : float(product.unitprice),
               "prdouit_totalPrice":float(product.totalprice)            
            }
            items.append(produit_dict)   
        context["idBon"] = idBon
        context["dateBon"] = dateBon
        context["totalPrice"] = totalPrice
        context["client_name"]= client_name
        context["client_address"]= client_address
        context["client_phone"] = client_phone
        context["bill"]=invoice
        context["items"]=items
        store_id = self.request.session["store"]
        my_store = store.objects.get(pk=store_id)
        all_clients = Client.objects.filter(store=my_store, valide= True)
        context["clients"]=all_clients
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        context["selected_store"] = selected_store    
        
     
        entrepots = Entrepot.objects.filter(store=my_store)
          # Step 3: Get all the stocks associated with each Entrepot
        all_stocks = []
        for entrepot in entrepots:
            stocks_for_entrepot = entrepot.get_stocks()
            all_stocks.extend(stocks_for_entrepot)
        context["entrepots"] = entrepots
        context["stock"] = all_stocks
        bons_ventes = BonComptoire.objects.filter(store=selected_store)
        context["bons_sorties"]=bons_ventes
        entrepots = Entrepot.objects.filter(store= selected_store)
        context["entrepots"]=entrepots    
        modeReg = ModeReglement.objects.filter(store= selected_store) 
        context["modeReg"]=modeReg  
        echeances = EcheanceReglement.objects.filter(store= selected_store)
        context["echeances"] = echeances 
        banques= Banque.objects.filter(store= selected_store)
        context["banques"] = banques
        categories= Category.objects.filter(store= selected_store)
        context["categories"] = categories
        return context
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        data = data.get('formData', '')
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)  
        try:
            with transaction.atomic():
                # Get the existing BonRetourComptoir instance
                bon_retour_comptoir = BonRetourComptoir.objects.get(idBon=data["IdBon"])
                # Handle updates based on the edited data
                # bon_retour_comptoir.dateBon = data.get('dateBon', bon_retour_comptoir.dateBon)
                # Save the updated BonRetourComptoir
                bon_retour_comptoir.save()
                # Get the existing products in the database
                existing_products = bon_retour_comptoir.produits_en_bon_retourcomptoir.all()
                my_entrepotname = bon_retour_comptoir.bon_comptoir_associe.monentrepot
                my_entrepot = Entrepot.objects.get(name=my_entrepotname, store = CurrentStore)
                produits_transfert = ProduitsEnBonRetourComptoir.objects.filter(BonNo=bon_retour_comptoir)
                produits_edited = data.get('produits', [])
                for produit_transfert in produits_transfert:
                    quantity_product = produit_transfert.quantity
                    reference_to_check = produit_transfert.produit.reference
                    # Check if the reference exists in produits_edited list
                    matching_produit = next((produit for produit in produits_edited if produit['ref'] == reference_to_check), None)
                    # Check if the quantity is zero
                    mon_stock = Stock.objects.get(entrepot=my_entrepot, product=produit_transfert.produit)                    
                    if matching_produit :
                        if matching_produit['qty'] == produit_transfert.quantity :
                                continue
                    else:
                        if mon_stock.quantity == 0:
                            print("cannot edit", mon_stock.product.name)
                            return JsonResponse({'message': f"Bon ne peut pas être modifié ! Stock de Produit {produit_transfert.produit.reference} f est Vide!",'prompt_user': True})
                        
                        
                        # Update the source warehouse stock quantity
                        mon_stock.quantity -= quantity_product
                        mon_stock.save()
                        produit_transfert.delete()
                       
                # Handle stock updates and deletions
                for product_data in data.get('produits', []):
                    produit_inst = Product.objects.get(reference=product_data["ref"] , store = CurrentStore)
                    matching_produit = ProduitsEnBonRetourComptoir.objects.filter(BonNo=bon_retour_comptoir, produit=produit_inst).first()
                    if not matching_produit:
                        qty = int(product_data['qty'])
                        rate = float(product_data['rate'])
                        total = int(qty) * rate                    
                        produit_en_bon_retour = ProduitsEnBonRetourComptoir.objects.create(
                            BonNo=bon_retour_comptoir,
                            produit=produit_inst,
                            quantity=qty,
                            unitprice=rate,
                            totalprice=total
                        )
                        p = Stock.objects.get(Q(product__reference=product_data["ref"]) & Q(entrepot__name=my_entrepot) )
                        p.quantity += int(product_data["qty"])
                        p.save()
                    else :
                        continue
        except BonRetourComptoir.DoesNotExist:
            return JsonResponse({'message': "BonRetourComptoir not found.", 'prompt_user': False})

        return JsonResponse({'message': "BonRetourComptoir Moidifé.", 'prompt_user': False}) 
        
class ComptoirUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/comptoir_bill_update.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bonlivraison' in self.request.session.get('permissions', [])
    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))         
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        bill_id=self.kwargs.get('bill_id')
    
        invoice = BonComptoire.objects.get(id=bill_id)
        idBon = invoice.idBon
        dateBon = invoice.dateBon
        totalPrice=invoice.totalprice
        client_name= invoice.client.name
        client_address = invoice.client.adresse
        client_phone= invoice.client.phone
        products_enBon = invoice.produits_en_bon_comptoir.all()
        items=[]
        for product in products_enBon:
            produit_dict={
               "produit_ref" :product.stock.reference,
               "produit_name" :product.stock.name,
               "produit_category" :product.stock.category.Libellé,
               "produit_qty":int(product.quantity),
               "produit_unitPrice" : float(product.unitprice),
               "prdouit_totalPrice":float(product.totalprice)            
              }
            items.append(produit_dict)
          
        context["idBon"] = idBon
        context["dateBon"] = dateBon
        context['verssement'] = invoice.par_verssement
        context['amountverse'] = invoice.prix_payed
        
        context["totalPrice"] = totalPrice
        context["client_name"]= client_name
        context["client_address"]= client_address
        context["client_phone"] = client_phone
        context["bill"]=invoice
        context["items"]=items
        store_id = self.request.session["store"]
        my_store = store.objects.get(pk=store_id)
        all_clients = Client.objects.filter(store=my_store, valide= True)
        context["clients"]=all_clients
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        context["selected_store"] = selected_store    
        
     
        entrepot_bill = Entrepot.objects.get(name=invoice.monentrepot, store=my_store)
          # Step 3: Get all the stocks associated with each Entrepot
        all_stocks = []
       
        stocks_for_entrepot = entrepot_bill.get_stocks()
        all_stocks.extend(stocks_for_entrepot)
        entrepots = Entrepot.objects.filter(store=my_store)
        context["entrepots"] = entrepots
        context["stock"] = all_stocks
        
        entrepots = Entrepot.objects.filter(store= selected_store)
        context["entrepots"]=entrepots    
        modeReg = ModeReglement.objects.filter(store= selected_store) 
        context["modeReg"]=modeReg  
        echeances = EcheanceReglement.objects.filter(store= selected_store)
        context["echeances"] = echeances 
        banques= Banque.objects.filter(store= selected_store)
        context["banques"] = banques
        categories= Category.objects.filter(store= selected_store)
        context["categories"] = categories
        return context
        
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        data = data.get('formData', '')
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        try:
            # Use transaction.atomic to ensure that all changes are made atomically
            with transaction.atomic():
                # Get the existing BonComptoir instance
                idbon = data["IdBon"]
                bon_comptoir = BonComptoire.objects.select_for_update().get(idBon=idbon)

                # # Check if the BonComptoir is already validated, if yes, don't allow editing
                # if bon_comptoir.is_validated:
                #     return JsonResponse({'error': "Cannot edit a validated BonComptoir.", 'prompt_user': False})

                # Handle stock updates for deleted entries
                for produit in bon_comptoir.produits_en_bon_comptoir.all():
                    myentrepot = Entrepot.objects.get(name = data["entrepotBon"], store = CurrentStore)
                    stock_entry = Stock.objects.get(product=produit.stock, entrepot=myentrepot)
                    stock_entry.quantity += produit.quantity
                    stock_entry.save()
                    produit.delete()
                    
                client_name = data["clientInfo"]["name"]
                client_instance = Client.objects.filter(name=client_name).first()
                bon_comptoir.client = client_instance
                bon_comptoir.totalprice = data.get('totalprice', bon_comptoir.totalprice)
                bon_comptoir.totalremise = data.get('totalremise', bon_comptoir.totalremise)
                myentrepot = Entrepot.objects.get(name = data["entrepotBon"], store = CurrentStore)
                # Save the updated BonComptoir
                for product in data["produits"]:            
                    p = Stock.objects.select_for_update().get( Q(product__name=product["name"]) & Q(entrepot=myentrepot))
                    new_quantity = p.quantity - int(product["qty"]) ## la quantité dans l'entrepot qui convient
                    if new_quantity < 0:
                         # If any product has insufficient quantity, return a response to inform the user
                        return JsonResponse({'error': f"Stock Insuffisant pour  : {product['name']}", 'prompt_user': True})            
                    p.quantity = new_quantity
                    p.save()  
                    
                bon_comptoir.save()
                    
                for produit in data["produits"]:
                    print(produit)
                    produit_inst = Product.objects.get(reference=produit["ref"], store = CurrentStore)
                    produit_inst.TotalQte -= int(produit["qty"])
                    produit_inst.save()
                    qty = int(produit['qty'])
                    rate = float(produit['rate'])
                    total = int(qty) * float(rate)
                    ProduitsEnBonComptoir.objects.create(
                        BonNo = bon_comptoir,
                        stock = produit_inst,
                        quantity = qty,
                        unitprice = rate,
                        totalprice =total
                    )

        except  BonComptoire.DoesNotExist:
            return JsonResponse({'error': "BonComptoir not found.", 'prompt_user': False})

        return JsonResponse({'success': "BonComptoir edited successfully.", 'prompt_user': False})
        
class DevisListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/liste_bon_devis.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bondevis' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
  

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        if myuser.role == 'manager':
            bons = models.BonDevis.objects.filter(store=CurrentStore)
        else:
           bons = models.BonDevis.objects.filter(store=CurrentStore, user=myuser) 
        context["bons"]= bons
        return context
    
class GarantieListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/liste_bon_garantie.html"  
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
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        current_month = datetime.now().month
        today = datetime.today()
        first_day_current_month = today.replace(day=1)
        first_day_past_month = (first_day_current_month - timedelta(days=1)).replace(day=1)
        if myuser.role == "manager" or myuser.role == "gestion-stock" or myuser.username == "nadjemeddine" :
            bons = models.BonGarantie.objects.filter(store=CurrentStore).order_by('-idBon')
        else:
            bons = models.BonGarantie.objects.filter(bonLivraisonAssocie__user = myuser, store=CurrentStore).order_by('-idBon')
        context["bons"]= bons
        return context
    
class GarantieView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/bon_garantie.html" 
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
        store_id = self.request.session["store"]
        my_store = store.objects.get(pk=store_id)
        all_bons_sortie = models.BonSortie.objects.filter(store=my_store)
        
        # Step 2: Get all clients
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)

        all_clients = Client.objects.filter(store=my_store, valide= True)


        context["all_bons_sortie"] = all_bons_sortie
        context["all_clients"] = all_clients

        entrepots = Entrepot.objects.filter(store=my_store)
          # Step 3: Get all the stocks associated with each Entrepot
        all_stocks = []
        for entrepot in entrepots:
            stocks_for_entrepot = entrepot.get_stocks()
            all_stocks.extend(stocks_for_entrepot)

        context["stock"] = all_stocks
        context["entrepots"] = entrepots
        current_year = datetime.now().strftime('%y')
        current_month = datetime.now().strftime('%m')
        last_number = models.BonGarantie.objects.order_by('-id').first()
        if last_number:
            last_number = last_number.id
        else:
            last_number = 0
        codeBon = f'FIG{current_year}{current_month}-{last_number + 1:04d}'
        context["code"] = codeBon
        return context
   
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')

        if dataInvoice: 
           print(dataInvoice)
           Currentuser = self.request.user
           myuser  = CustomUser.objects.get(username=Currentuser.username)
           store_id = self.request.session["store"]
           CurrentStore = store.objects.get(pk=store_id)
           current_year = datetime.now().strftime('%y')
           current_month = datetime.now().strftime('%m')
           last_number = models.BonGarantie.objects.order_by('-id').first()
           if last_number:
                last_number = last_number.id
           else:
                last_number = 0
           codeBon = f'FIG{current_year}{current_month}-{last_number + 1:04d}'
           dateBon = dataInvoice["dateBp"]
           client = Client.objects.get(name=dataInvoice["clientInfo"]["name"])
           try:
            AssociatedBL = models.BonSortie.objects.get(idBon=dataInvoice["AssociatedBL"])
           except models.BonSortie.DoesNotExist:
            AssociatedBL = None
           bon_garantie = models.BonGarantie.objects.create(
              idBon = codeBon,
              dateBon = dateBon,
              bonLivraisonAssocie = AssociatedBL,
              store = CurrentStore,
              client = client,
              user =myuser
            )
           bon_garantie.save()
           products =dataInvoice["produits"]
           for product in products :
              produit = Product.objects.get(reference = product["ref"], store = CurrentStore)
              NumeroSeries = product["numSeries"]
              qty= product["qty"]
              models.ProduitsEnBonGarantie.objects.create(
                BonNo = bon_garantie,
                produit = produit,
                quantity=qty,
                NumeroSeries = NumeroSeries 
              )  
           return JsonResponse({'Message':'bill created Succesfully'})

class AvoirListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/avoirs_vente_page.html"
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
        avoirs = models.AvoirVente.objects.filter(store=selected_store)
        context["avoirs"]=avoirs
        bons = models.BonSortie.objects.filter(store=selected_store)
        context["bons"]=bons
        
        return context
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')

        if dataInvoice: 
             bonLivraison = models.BonSortie.objects.get(id=dataInvoice["bonLivraison"])
             client_obj = Client.objects.get(id=dataInvoice["client"])
             date= dataInvoice["date"]
             motif= dataInvoice["motif"]
             montant=dataInvoice["montant"]
             selected_store = get_object_or_404(store, pk=self.request.session["store"])
             year = '23'

             # Find the last AvoirVente object
             last_avoir = models.AvoirVente.objects.last()

             # Determine the next sequential number
             if last_avoir:
                last_code = last_avoir.codeAvoir
                last_sequence = int(last_code.split('-')[1])
                next_sequence = last_sequence + 1
             else:
                next_sequence = 1

             # Create the codeAvoir using the year and sequential number
             codeAvoir = f"AV{year}-{next_sequence:03d}"
             avoirobject = models.AvoirVente.objects.create(
                 BonSortieAssocie=bonLivraison,
                 client=client_obj,
                 codeAvoir=codeAvoir,
                 dateEmission=date,
                 store=selected_store,
                 montant=dataInvoice["montant"],
                 motif=motif
             )
        return JsonResponse({'message': "Avoir Added successfully."})

class GarantieUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/bon_garantieupdate_page.html"
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
        bill_id = self.kwargs.get('bill_id')
        
        invoice = models.BonGarantie.objects.get(id=bill_id)
        idBon = invoice.idBon
        dateBon = invoice.dateBon
        client_name = invoice.client.name
        client_address = invoice.client.adresse
        client_phone = invoice.client.phone
        products_enBon = invoice.produits_en_bon_garantie.all()
        items=[]
        for product in products_enBon:
             produit_dict={
               "produit_ref" :product.produit.reference,
               "produit_name" :product.produit.name,
               "produit_qty":product.getQuantity,
               "produit_numseries":ast.literal_eval(product.NumeroSeries),                       
              }
             items.append(produit_dict)
        context["id"]= invoice.id
        context["bill"]= invoice
        context["idBon"] = idBon
        context["idbonL"] = invoice.bonLivraisonAssocie.idBon if invoice.bonLivraisonAssocie is not None else ''
        context["dateBon"] = dateBon
        context["client_name"]= client_name
        context["client_address"]= client_address
        context["client_phone"] = client_phone
        context["items"]=items
       
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        context["selected_store"] = selected_store    
        store_id = self.request.session["store"]
        my_store = store.objects.get(pk=store_id)
        
        all_stocks=[]
        if invoice.bonLivraisonAssocie is not None:
            products = invoice.bonLivraisonAssocie.produits_en_bon_sorties.all()
            for product in products:
                stock_dict={
                    'reference': product.stock.reference,
                    'name': product.stock.name,
                    'qty': product.quantity,
                    "unitPrice" : float(product.unitprice),
                    "totalPrice":float(product.totalprice), 
                    'numSeries': ['']
                }
                all_stocks.append(stock_dict)

        context["stock"] = all_stocks
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')

        if dataInvoice:  
          with transaction.atomic():  
            Currentuser = self.request.user
            myuser = CustomUser.objects.get(username=Currentuser.username)
            store_id = self.request.session["store"]
            CurrentStore = store.objects.get(pk=store_id)
            current_year = datetime.now().strftime('%y')
            current_month = datetime.now().strftime('%m')
            bon_garantie_id = dataInvoice.get("id")  # Assuming you have a field to identify the existing BonGarantie
            bon_garantie = models.BonGarantie.objects.get(id=bon_garantie_id)

            # Delete existing ProduitsEnBonGarantie instances
            models.ProduitsEnBonGarantie.objects.filter(BonNo=bon_garantie).delete()

            # Recreate ProduitsEnBonGarantie instances based on the updated data
            products = dataInvoice["produits"]
            for product in products:
                produit = Product.objects.get(reference=product["reference"], store = CurrentStore)
                NumeroSeries = product["numSeries"]
                qty = product["qty"]
                models.ProduitsEnBonGarantie.objects.create(
                    BonNo=bon_garantie,
                    produit=produit,
                    quantity=qty,
                    NumeroSeries=NumeroSeries
                )

            # Update other fields of BonGarantie if needed
            bon_garantie.bonLivraisonAssocie = models.BonSortie.objects.get(idBon=dataInvoice["AssociatedBL"])
            bon_garantie.client = Client.objects.filter(name=dataInvoice["clientInfo"]["name"], store = CurrentStore).first()
            bon_garantie.save()

            return JsonResponse({'Message': 'bill updated successfully'})

class GarantieBlView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/bon_garantieBl.html"
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
        bill_id=self.kwargs.get('id_bon')
        
        invoice = models.BonSortie.objects.get(id=bill_id)
        idBon = invoice.idBon
        dateBon = invoice.dateBon
        totalPrice=invoice.totalPrice
        client_name= invoice.client.name
        client_address = invoice.client.adresse
        client_phone= invoice.client.phone
        products_enBon = invoice.get_produits()
        items=[]
        for product in products_enBon:
             produit_dict={
               "produit_ref" :product.stock.reference,
               "produit_name" :product.stock.name,
               "produit_qty":product.quantity,
               "produit_unitPrice" : float(product.unitprice),
               "prdouit_totalPrice":float(product.totalprice)            
              }
             items.append(produit_dict)
        context["bill"] = invoice    
        context["idBon"] = idBon
        context["dateBon"] = dateBon
        context["totalPrice"] = totalPrice
        context["client_name"]= client_name
        context["client_address"]= client_address
        context["client_phone"] = client_phone
        context["items"]=items
       
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        context["selected_store"] = selected_store    
        store_id = self.request.session["store"]
        my_store = store.objects.get(pk=store_id)
     
        entrepots = Entrepot.objects.filter(store = my_store)
          # Step 3: Get all the stocks associated with each Entrepot
        all_stocks = []
        for entrepot in entrepots:
            stocks_for_entrepot = entrepot.get_stocks()
            all_stocks.extend(stocks_for_entrepot)

        context["stock"] = all_stocks
        current_year = datetime.now().strftime('%y')
        current_month = datetime.now().strftime('%m')
        last_number = models.BonGarantie.objects.order_by('-id').first()
        if last_number:
            last_number = last_number.id
        else:
            last_number = 0
        codeBon = f'FIG{current_year}{current_month}-{last_number + 1:04d}'
        context["code"] = codeBon
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        if dataInvoice: 
           print(dataInvoice)
           Currentuser = self.request.user
           myuser  = CustomUser.objects.get(username=Currentuser.username)
           store_id = self.request.session["store"]
           CurrentStore = store.objects.get(pk=store_id)
           current_year = datetime.now().strftime('%y')
           current_month = datetime.now().strftime('%m')
           last_number = models.BonGarantie.objects.order_by('-id').first()
           if last_number:
                last_number = last_number.id
           else:
                last_number = 0
           codeBon = f'FIG{current_year}{current_month}-{last_number + 1:04d}'
           dateBon = dataInvoice["dateBp"]
           AssociatedBL = models.BonSortie.objects.get(idBon=dataInvoice["AssociatedBL"])
           bon_garantie = models.BonGarantie.objects.create(
              idBon = codeBon,
              dateBon = dateBon,
              bonLivraisonAssocie = AssociatedBL,
              tps_ecoule = dataInvoice["time"],
              store = CurrentStore,
              client = AssociatedBL.client,
              user =myuser
            )
           bon_garantie.save()
           products =dataInvoice["produits"]
           for product in products :
              produit = Product.objects.get(reference = product["ref"], store = CurrentStore)
              NumeroSeries = product["numSeries"]
              qty= product["qty"]
              models.ProduitsEnBonGarantie.objects.create(
                BonNo = bon_garantie,
                produit = produit,
                quantity = qty,
                livre = False if product['livre'] == 'true' else True,
                NumeroSeries = NumeroSeries 
              )
           return JsonResponse({'Message':'bill created Succesfully'})

class FactureBlView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/facture_Bl.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_factures' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
        

    def get_context_data(self, *args, **kwargs):
      context = super().get_context_data(*args, **kwargs)
      Currentuser = self.request.user
      store_id = self.request.session["store"]
      CurrentStore = store.objects.get(pk=store_id)
      myuser  = CustomUser.objects.get(username=Currentuser.username)
      selected_store = get_object_or_404(store, pk=self.request.session["store"])
      if  self.kwargs.get('id_bon') :
         bon_associe = models.BonSortie.objects.get(id=self.kwargs.get('id_bon') )
         cl_dict={
               "client_id" :bon_associe.client.id,
               "client_name" :bon_associe.client.name,
               "client_address":bon_associe.client.adresse,
               "client_phone" : bon_associe.client.phone,                      
          }
         context["bill"] = bon_associe
         context["idBon"]= bon_associe.idBon
         context["entrepot"]=  bon_associe.entrepot.name
         stocks = bon_associe.entrepot.get_stocks()
         stock_data=[]
         for stock in stocks:
                product_name = stock.product.name
                entrepot_name = stock.entrepot.name
                if myuser.role == 'manager':
                    quantity = stock.quantity
                else:
                    quantity = stock.get_quantity
                price = stock.product.prix_vente
                reference = stock.product.reference
                entrepot= stock.entrepot.name
                categorie= stock.product.category.Libellé if stock.product.category is not None else ''

                stock_info = {
                    "product_name": product_name,
                    "entrepot_name": entrepot_name,
                    "product_component": stock.product.category.pc_component if stock.product.category is not None else '',
                    "quantity": quantity,
                    "reference": reference,
                    "entrepot":entrepot,
                    "categorie":categorie,
                    "price": float(price),
                    "prix_livraison": float(stock.product.prix_livraison),
                }
                stock_data.append(stock_info)
         context["stocks"] = stock_data
         context["client"]=cl_dict
         produits = bon_associe.produits_en_bon_sorties.all()
         produits_data=[]    
         for produit in produits :
            produit_dict={
               "produit_ref" :produit.stock.reference,
               "produit_name" :produit.stock.name,
               "product_component": produit.stock.category.pc_component if produit.stock.category is not None else '',
               "produit_qty":produit.quantity,
               "produit_tva": float(produit.stock.tva),
               "produit_livraison": float(produit.stock.prix_livraison),
               "produit_unitprice": float(produit.unitprice) if produit.unitprice is not None else None,                    
               "produit_freeprice": float(produit.unitprice) - float(produit.stock.prix_livraison),                    
            }
            produits_data.append(produit_dict)
         context["produits"]=produits_data
         entrepots = Entrepot.objects.filter(store=selected_store)
         context["entrepots"]=entrepots
         modeReg = ModeReglement.objects.filter(store=selected_store)
         context["modeReg"]=modeReg  
         echeances = EcheanceReglement.objects.filter(store=selected_store)
         context["echeances"] = echeances 
         banques= Banque.objects.filter(store=selected_store)
         context["banques"] = banques
         last_facture = models.Facture.objects.order_by('-id').first()
         current_year = str(timezone.now().year)[-2:]
         current_month = timezone.now().strftime('%m')

         if last_facture:
            last_code = last_facture.id
            new_seq = f"{last_code + 1:04d}"
         else:
            new_seq = "0001"

         code_fac = f"FA{current_year}{current_month}-{new_seq}"
         context["code_fac"] = code_fac
      return context
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        if dataInvoice:            
           print(dataInvoice)
           idFacture=dataInvoice["IdBon"]
           dateFacture = dataInvoice["dateFacture"]
           dateReglement = dataInvoice["dateReglement"]
           modeReg = None
           bonAssocie = None
           echeance = None
           if dataInvoice["echeance"] != '':
              echeance = EcheanceReglement.objects.get(id=dataInvoice["echeance"])
           if dataInvoice["BlAssocie"] != '/':
              bonAssocie = models.BonSortie.objects.get(idBon=dataInvoice["BlAssocie"])
           remise = dataInvoice["Remise"]
           etatFacture = dataInvoice["etatFacture"]
           client_name = dataInvoice["clientInfo"]["id"]
           client = Client.objects.get(id=client_name)
           store_id = self.request.session["store"]
           CurrentStore = store.objects.get(pk=store_id)
           Currentuser = self.request.user
           myuser  = CustomUser.objects.get(username=Currentuser.username)
           facture_instance = models.Facture.objects.create(
              codeFacture = idFacture,
              date_facture = dateFacture,
              date_reglement = dateReglement,
              echeance_reglement = echeance,
              BonS = bonAssocie,
              client = client,
              mode_reglement = modeReg,
              Remise =remise,  
              etat_reglement = etatFacture,    
              store=CurrentStore,
                    
           )
           facture_instance.save()
           if modeReg== '2':
              print("reglement par cheque")
              facture_instance.banque_Reglement = Banque.objects.get(id=dataInvoice["banque"])
              facture_instance.num_cheque_reglement = dataInvoice["numCheque"]
              facture_instance.save()
           for product_data in dataInvoice['produits']:
                product = Product.objects.get(reference=product_data["ref"], store = CurrentStore) 
                quantity =int(product_data["qty"])
                unitprice = float(product_data["rateLiv"])
                totalprice = quantity * unitprice
                models.ProduitsEnFacture.objects.create(
                    FactureNo =facture_instance,
                    stock =product,
                    unitprice = unitprice,
                    quantity =quantity,
                    totalprice = totalprice
                )    
        return JsonResponse({'message': "Entrepot Added successfully."})

class FactureUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/facture_bill_update.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_factures' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
        

    def get_context_data(self, *args, **kwargs):
      context = super().get_context_data(*args, **kwargs)
      Currentuser = self.request.user
      store_id = self.request.session["store"]
      CurrentStore = store.objects.get(pk=store_id)
      myuser  = CustomUser.objects.get(username=Currentuser.username)
      selected_store = get_object_or_404(store, pk=self.request.session["store"])
      if  self.kwargs.get('id_bon') :
         bon_associe = models.Facture.objects.get(id =self.kwargs.get('id_bon'))
         cl_dict={
               "client_id" :bon_associe.client.id,
               "client_name" :bon_associe.client.name,
               "client_address":bon_associe.client.adresse,
               "client_phone" : bon_associe.client.phone,                      
         }
         context["bill"]= bon_associe
         context["client"]=cl_dict
         produits = bon_associe.produits_en_facture.all()
         produits_data=[]    
         for produit in produits :
            produit_dict={
               "produit_ref" :produit.stock.reference,
               "produit_name" :produit.stock.name,
               "produit_qty":produit.quantity,
               "produit_tva": float(produit.stock.tva),
               "produit_livraison": float(produit.stock.prix_livraison),
               "produit_unitprice": float(produit.unitprice) if produit.unitprice is not None else None,                    
               "produit_freeprice": float(produit.unitprice) - float(produit.stock.prix_livraison),                    
            }
            produits_data.append(produit_dict)
         context["produits"]=produits_data
         stocks = bon_associe.BonS.entrepot.get_stocks()
         stock_data=[]
         for stock in stocks:
                product_name = stock.product.name
                entrepot_name = stock.entrepot.name
                if myuser.role == 'manager':
                    quantity = stock.quantity
                else:
                    quantity = stock.get_quantity
                price = stock.product.prix_vente
                reference = stock.product.reference
                entrepot= stock.entrepot.name
                categorie= stock.product.category.Libellé if stock.product.category is not None else ''

                stock_info = {
                    "product_name": product_name,
                    "entrepot_name": entrepot_name,
                    "quantity": quantity,
                    "reference": reference,
                    "entrepot":entrepot,
                    "categorie":categorie,
                    "price": float(price),
                    "prix_livraison": float(stock.product.prix_livraison),
                }
                stock_data.append(stock_info)
         context["stocks"] = stock_data
         entrepots = Entrepot.objects.filter(store=selected_store)
         context["entrepots"]=entrepots
         modeReg = ModeReglement.objects.filter(store = selected_store) 
         context["modeReg"]=modeReg  
         echeances = EcheanceReglement.objects.filter(store = selected_store) 
         context["echeances"] = echeances 
         banques= Banque.objects.filter(store = selected_store) 
         context["banques"] = banques
      return context
      
      
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        if dataInvoice:   
         with transaction.atomic(): 
            Currentuser = self.request.user
            myuser = CustomUser.objects.get(username=Currentuser.username)
            store_id = self.request.session["store"]
            CurrentStore = store.objects.get(pk=store_id)
            current_year = datetime.now().strftime('%y')
            current_month = datetime.now().strftime('%m')
            bon_garantie_id = dataInvoice.get("id")  # Assuming you have a field to identify the existing BonGarantie
            bon_garantie = models.Facture.objects.get(id=bon_garantie_id)
            bon_garantie_id = dataInvoice.get("id")  # Assuming you have a field to identify the existing BonGarantie
            bon_garantie = models.Facture.objects.get(id=bon_garantie_id)
            bon_garantie.Remise = dataInvoice.get("remise")
            print('edit',dataInvoice["dateFacture"])
            print('original',bon_garantie.date_facture)
            if bon_garantie.date_facture != dataInvoice["dateFacture"]:
                bon_garantie.date_facture = dataInvoice["dateFacture"]
                bon_garantie.save()
            if bon_garantie.date_reglement != dataInvoice["dateReglement"]:
                bon_garantie.date_reglement = dataInvoice["dateReglement"]
                bon_garantie.save()
            # Delete existing ProduitsEnBonGarantie instances
            modeReglement = dataInvoice["modeReglement"]
            modeReg = None
            if modeReglement != "":
             modeReg = ModeReglement.objects.get(id=modeReglement)
            bonAssocie = None
            echeance = None
            if dataInvoice["echeance"] != '':
                echeance = EcheanceReglement.objects.get(id=dataInvoice["echeance"])
            if dataInvoice["BlAssocie"] != '/':
              bonAssocie = models.BonSortie.objects.get(idBon=dataInvoice["BlAssocie"])
            # Recreate ProduitsEnBonGarantie instances based on the updated data
            models.ProduitsEnFacture.objects.filter(FactureNo=bon_garantie).delete()
            for product_data in dataInvoice['produits']:
                product = Product.objects.get(reference=product_data["ref"], store = CurrentStore) 
                quantity =int(product_data["qty"])
                unitprice = float(product_data["rateLiv"])
                totalprice = quantity * unitprice
                models.ProduitsEnFacture.objects.create(
                    FactureNo =bon_garantie,
                    stock =product,
                    unitprice = unitprice,
                    quantity =quantity,
                    totalprice = totalprice
                )   
            bon_garantie.BonS = bonAssocie
            bon_garantie.client = Client.objects.get(name=dataInvoice["clientInfo"]["name"], store = CurrentStore)
            bon_garantie.save()

            return JsonResponse({'Message': 'bill updated successfully'})
        
class FactureView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/facture_bill.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_factures' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        if(myuser.role =='manager'):
         clients_list = Client.objects.filter(store=CurrentStore, valide= True)
         clients=[]
         for cl in clients_list:
            cl_dict={
               "client_name" :cl.name,
               "client_address":cl.adresse,
               "client_type" : cl.categorie_client.id,
               "client_phone" : cl.phone,                      
            }
            clients.append(cl_dict)
         context["clients"]=clients    
         context["selected_store"] = selected_store
         bons_sortie = models.BonSortie.objects.filter(store=CurrentStore) 
         context["bons_sorties"] = bons_sortie   
        else:
          clientsList = Client.objects.filter(user=Currentuser, valide= True)
          clients=[]
          for cl in clientsList:
            cl_dict={
               "client_name" :cl.name,
               "client_address":cl.adresse,
               "client_phone" : cl.phone, 
               "client_type" : cl.categorie_client.id,                     
              }
            clients.append(cl_dict)
          selected_store = get_object_or_404(store, pk=self.request.session["store"])
          context["selected_store"] = selected_store
          context["clients"]=clients  
          bons_sortie = models.BonSortie.objects.filter(user=myuser) 
          context["bons_sorties"] = bons_sortie       
        entrepots = Entrepot.objects.filter(store= selected_store)
        context["entrepots"]=entrepots
        modeReg = ModeReglement.objects.filter(store= selected_store)
        context["modeReg"]=modeReg  
        echeances = EcheanceReglement.objects.filter(store= selected_store)
        context["echeances"] = echeances 
        banques= Banque.objects.filter(store= selected_store)
        context["banques"] = banques
        last_facture = models.Facture.objects.order_by('-id').first()
        current_year = timezone.now().year
        current_month = timezone.now().strftime('%m')

        if last_facture:
            last_code = last_facture.id
            new_seq = f"{last_code + 1:04d}"
        else:
            new_seq = "0001"

        code_fac = f"FA{current_year}{current_month}-{new_seq}"
        context["code_fac"] = code_fac
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        if dataInvoice:            
           print(dataInvoice)
           idFacture=dataInvoice["IdBon"]
           dateFacture = dataInvoice["dateFacture"]
           dateReglement = dataInvoice["dateReglement"]
           modeReglement = dataInvoice["modeReglement"]
           modeReg = None
           if modeReglement != "":
            modeReg = ModeReglement.objects.get(id=modeReglement)
           bonAssocie = None
           echeance = None
           if dataInvoice["echeance"] != '':
              echeance = EcheanceReglement.objects.get(id=dataInvoice["echeance"])
           if dataInvoice["BlAssocie"] != '':
              bonAssocie = models.BonSortie.objects.get(idBon=dataInvoice["BlAssocie"])
           remise = dataInvoice["remise"]
           etatFacture = dataInvoice["etatFacture"]
           client_name = dataInvoice["clientInfo"]["name"]
           client = Client.objects.get(name=client_name, store = CurrentStore)
           facture_instance = models.Facture.objects.create(
              codeFacture = idFacture,
              date_facture = dateFacture,
              date_reglement = dateReglement,
              echeance_reglement = echeance,
              client = client,
              BonS = bonAssocie,
              mode_reglement = modeReg,
              store = CurrentStore,
              Remise =remise,  
              etat_reglement = etatFacture,          
           )
           facture_instance.save()
           if modeReglement == '2':
              facture_instance.banque_Reglement = Banque.objects.get(id=dataInvoice["banque"])
              facture_instance.num_cheque_reglement = dataInvoice["numCheque"]
              facture_instance.save()
           for product_data in dataInvoice['produits']:
                product = Product.objects.get(reference=product_data["ref"], store = CurrentStore) 
                quantity =int(product_data["qty"])
                unitprice = float(product_data["rateLiv"])
                totalprice = quantity * unitprice
                models.ProduitsEnFacture.objects.create(
                    FactureNo =facture_instance,
                    stock =product,
                    unitprice = unitprice,
                    quantity =quantity,
                    totalprice = totalprice
                )    
        return JsonResponse({'message': "Entrepot Added successfully."})

class FactureListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/factures_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_factures' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
   
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        factures= models.Facture.objects.filter(store= selected_store).order_by('codeFacture')
        context["factures"]=factures
        return context

class DevisView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/devis_bill.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bondevis' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
        
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        stock = Product.objects.filter(store=CurrentStore) 
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        if myuser.role == 'manager' or myuser.role == "DIRECTEUR EXECUTIF":
            clients_list = Client.objects.filter(store=CurrentStore, valide= True)  
        else :
            clients_list = Client.objects.filter(user=Currentuser, valide= True)  
        clients=[]
        for cl in clients_list:
            cl_dict={
               "client_name" :cl.name,
               "client_address":cl.adresse,
               "client_phone" : cl.phone, 
               "client_type" : cl.categorie_client.id,
              }
            clients.append(cl_dict)
        context["clients"]=clients    
        current_year = datetime.now().strftime('%y')
        current_month = datetime.now().strftime('%m')
        last_number = models.BonDevis.objects.order_by('-id').first()
        if last_number:
            last_number = last_number.id
        else:
            last_number = 0
        codeBon= f'DV{current_year}{current_month}-{last_number + 1:04d}'
        context["code"]=codeBon
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData', '')
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        if dataInvoice:
           idBon =dataInvoice["IdBon"]
           dateBon =dataInvoice["dateBp"]
           client_address = dataInvoice["clientInfo"]["address"]
           client_phone = dataInvoice["clientInfo"]["phone"]
           Currentuser = request.user
           myuser  = CustomUser.objects.get(username=Currentuser.username)
         # Assuming you have access to the current user
           client, created = Client.objects.get_or_create(
                name=dataInvoice["clientInfo"]["name"],
                defaults={
                  "adresse": client_address,
                  "phone": client_phone,
                  "user": myuser,
               }
            )          
           current_year = datetime.now().strftime('%y')
           current_month = datetime.now().strftime('%m')
           last_number = models.BonDevis.objects.order_by('-id').first()
           if last_number:
                last_number = last_number.id
           else:
                last_number = 0
           codeBon= f'DV{current_year}{current_month}-{last_number + 1:04d}'
           bon_entry = models.BonDevis(
            idBon=codeBon,
            dateBon=dateBon,
            client =client,
            store=CurrentStore,
            user=myuser
           )
           bon_entry.save()     

           for product_data in dataInvoice['produits']:
                product = Product.objects.get(reference=product_data["ref"], store = CurrentStore) 
                models.ProduitsEnBonDevis.objects.create(
                    BonNo=bon_entry,
                    produit =product,
                    UnitPrice = float(product_data["rateLiv"]),
                    totalPrice = float(product_data["rateLiv"]) * int(product_data["qty"]),
                    quantity=int(product_data["qty"]),
                )          
        return JsonResponse({'message': "Bon de Devis Créé!.","code":codeBon})
  
class DevisUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/devis_bill_update.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bondevis' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        bill_id = self.kwargs.get('bill_id')
        
        invoice = models.BonDevis.objects.get(id=bill_id)
        idBon = invoice.idBon
        dateBon = invoice.dateBon
        client_name = invoice.client.name
        client_address = invoice.client.adresse
        client_phone = invoice.client.phone
        products_enBon = invoice.produits_en_bon_devis.all()
        items=[]

        for product in products_enBon:
             produit_dict={
               "produit_ref" :product.produit.reference,
               "produit_name" :product.produit.name,
               "produit_qty":product.quantity,
               "produit_tva": float(product.produit.tva),
               "produit_livraison": float(product.produit.prix_livraison),
               "produit_tax": float(product.produit.tva_douan),
               "produit_unitprice": float(product.UnitPrice) if product.UnitPrice is not None else 0,                    
               "produit_freeprice": float(product.UnitPrice) - float(product.produit.prix_livraison) - float(product.produit.tva_douan),                    
             }
             items.append(produit_dict)
          
        context["bill"] = invoice

        context["items"]=items
        context["id"]= invoice.id
        clienttype_id = invoice.client.categorie_client.id
        stocks = Product.objects.filter(store = CurrentStore)
        stock_data=[]
        for product in stocks:
                name = product.name
                quantity = product.total_quantity_in_stock
                reference = product.reference
                stock_info = {
                    "name": name,
                    "quantity": quantity,
                    "reference": reference,                  
                    'rate':float(product.get_price_per_type(clienttype_id, '')),
                    'prix_livraison': float(product.prix_livraison),
                    "produit_tax": float(product.tva_douan),
                    'price': float(product.get_price_per_type(clienttype_id, '')),
                }
                stock_data.append(stock_info)      
        context["stock"] = stock_data
        types_clients = typeClient.objects.filter(store= CurrentStore)
        context["types_clients"] = types_clients
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')

        if dataInvoice:    
            Currentuser = self.request.user
            myuser = CustomUser.objects.get(username=Currentuser.username)
            store_id = self.request.session["store"]
            CurrentStore = store.objects.get(pk=store_id)
            current_year = datetime.now().strftime('%y')
            current_month = datetime.now().strftime('%m')
            bon_garantie_id = dataInvoice.get("id")  # Assuming you have a field to identify the existing BonGarantie
            bon_garantie = models.BonDevis.objects.get(id=bon_garantie_id)

            # Delete existing ProduitsEnBonGarantie instances
            models.ProduitsEnBonDevis.objects.filter(BonNo=bon_garantie).delete()

            # Recreate ProduitsEnBonGarantie instances based on the updated data
            
            for product_data in dataInvoice['produits']:
                product = Product.objects.get(reference=product_data["ref"], store = CurrentStore) 
                models.ProduitsEnBonDevis.objects.create(
                    BonNo=bon_garantie,
                    produit =product,
                    UnitPrice = float(product_data["rateLiv"]),
                    totalPrice = float(product_data["rateLiv"]) * int(product_data["qty"]),
                    quantity=int(product_data["qty"]),
                )    

            bon_garantie.save()

            return JsonResponse({'message': 'Bon Devis Modifié!'})
        
class InvoiceListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/invoice_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bonlivraison' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)       
        # store_id = self.kwargs.get('store_id')
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        current_month = datetime.now().month
        if(myuser.role =='manager') or (myuser.role == 'Finance') or (myuser.role=='DIRECTEUR EXECUTIF') :
            today = datetime.today()
            first_day_current_month = today.replace(day=1)
            # Get the first day of the past month
            first_day_past_month = (first_day_current_month - timedelta(days=1)).replace(day=1)
            
            # Filter objects with dateBon greater than or equal to the first day of the past month
            bons_sorties = models.BonSortie.objects.filter(
                store=selected_store
            ).exclude(
                Q(typebl="KIT") | Q(typebl="carton")
            ).order_by('-id')
            
            context["bons_sorties"] = bons_sorties
        elif myuser.role=='gestion-stock':
            bons_sorties = models.BonSortie.objects.filter(
                store=selected_store,
                valide = True,
                reference_pc__exact='',
                entrepot__name ="Depot principal Reghaia"
            ).exclude(client__name="Annulé --- Annulé").filter(Q(bon_garantie__isnull=True)).exclude(Q(typebl="KIT") | Q(typebl="carton")).order_by('-id')  # Sort by date in descending order
            context["bons_sorties"] = bons_sorties
            
        else:
          bons_sorties = models.BonSortie.objects.filter(store=selected_store, user=myuser).exclude(Q(typebl="KIT") | Q(typebl="carton")).order_by('-id')     
          context["bons_sorties"] =bons_sorties
        entrepots = Entrepot.objects.filter(store=selected_store)
        context["entrepots"] = entrepots
        users_bills = CustomUser.objects.filter(EmployeeAt=selected_store)
        context["users"]=users_bills
        modeReg = ModeReglement.objects.filter(store= selected_store) 
        context["modeReg"]=modeReg  
        echeances = EcheanceReglement.objects.filter(store= selected_store)
        context["echeances"] = echeances 
        banques= Banque.objects.filter(store= selected_store)
        context["banques"] = banques
        return context 
    
class InvoiceCartonListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/invoice_page_cartons.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bonlivraison' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
        # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)       
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        current_month = datetime.now().month
        if(myuser.role =='manager') or (myuser.role == 'Finance') or (myuser.role=='DIRECTEUR EXECUTIF') :
            today = datetime.today()
            first_day_current_month = today.replace(day=1)
            # Get the first day of the past month
            first_day_past_month = (first_day_current_month - timedelta(days=1)).replace(day=1)
            
            # Filter objects with dateBon greater than or equal to the first day of the past month
            bons_sorties = models.BonSortie.objects.filter(
                store=selected_store,
                typebl="carton"
            ).order_by('-id')
            
            context["bons_sorties"] = bons_sorties
        elif myuser.role=='gestion-stock':
            bons_sorties = models.BonSortie.objects.filter(
                store=selected_store,
                valide = True,
                reference_pc__exact='',
                 typebl="carton",
                entrepot__name ="Depot principal Reghaia"
            ).exclude(client__name="Annulé --- Annulé").filter(Q(bon_garantie__isnull=True)).order_by('-id')  # Sort by date in descending order
            context["bons_sorties"] = bons_sorties
            
        else:
          bons_sorties = models.BonSortie.objects.filter(store=selected_store, user=myuser, typebl="carton").order_by('-id')     
          context["bons_sorties"] =bons_sorties
        entrepots = Entrepot.objects.filter(store=selected_store)
        context["entrepots"] = entrepots
        users_bills = CustomUser.objects.filter(EmployeeAt=selected_store)
        context["users"]=users_bills
        modeReg = ModeReglement.objects.filter(store= selected_store) 
        context["modeReg"]=modeReg  
        echeances = EcheanceReglement.objects.filter(store= selected_store)
        context["echeances"] = echeances 
        banques= Banque.objects.filter(store= selected_store)
        context["banques"] = banques
        return context 
     
class ComptoirListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/comptoirebills_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bonlivraison' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)       
        # store_id = self.kwargs.get('store_id')
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        current_month = datetime.now().month
        if(myuser.role =='manager') or (myuser.role =='DIRECTEUR EXECUTIF') or (myuser.role =='manager mag54'):
          bons_sorties = BonComptoire.objects.filter(store=selected_store).order_by('-id')
          context["bons_sorties"] =bons_sorties
        else:
          bons_sorties = BonComptoire.objects.filter(store=selected_store, user=myuser).order_by('-id')       
          context["bons_sorties"] =bons_sorties
        entrepots = Entrepot.objects.filter(store=selected_store)
        context["entrepots"] = entrepots
        users_bills = CustomUser.objects.filter(EmployeeAt=selected_store)
        context["users"]=users_bills
        return context
    
class ComptoirRectificationListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/comptoirebillsrectif_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bonlivraison' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)       
        # store_id = self.kwargs.get('store_id')
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        if(myuser.role =='manager') or (myuser.role =='DIRECTEUR EXECUTIF'):
          bons_sorties = BonRectification.objects.filter(store=selected_store).order_by('dateBon')
          context["bons_sorties"] =bons_sorties
        else:
          bons_sorties = BonRectification.objects.filter(store=selected_store, user=myuser).order_by('dateBon')       
          context["bons_sorties"] =bons_sorties
        entrepots = Entrepot.objects.filter(store=selected_store)
        context["entrepots"] = entrepots
        users_bills = CustomUser.objects.filter(EmployeeAt=selected_store)
        context["users"]=users_bills
        return context
    
class ComptoirRetourListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/comptoireretourbills_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'inventory.can_see_bonretour' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)       
        # store_id = self.kwargs.get('store_id')
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        if(myuser.role =='manager') or (myuser.role == 'Finance'):
          bons_sorties = BonRetourComptoir.objects.filter(bon_comptoir_associe__store=selected_store)
          bons_retour = BonRetour.objects.filter(store=selected_store)
          bons_retoura = BonRetourAncien.objects.filter(store=selected_store)
          context["bons_retour"] = bons_retour
          context["bons_sorties"] = bons_sorties
          context["bons_retoura"] = bons_retoura
   
        else:
            bons_sorties = BonRetourComptoir.objects.filter(bon_comptoir_associe__store=selected_store, user=myuser)       
            bons_retour = BonRetour.objects.filter(
                Q(store=selected_store, bonL__entrepot=myuser.entrepots_responsible) |
                Q(store=selected_store, user=myuser)
            )
            bons_retoura = BonRetourAncien.objects.filter(
                Q(store=selected_store, entrepot=myuser.entrepots_responsible) |
                Q(store=selected_store, user=myuser)
            )
            
            context["bons_retour"] = bons_retour
            context["bons_sorties"] =bons_sorties
            context["bons_retoura"] = bons_retoura
        entrepots = Entrepot.objects.filter(store=selected_store)
        context["entrepots"] = entrepots
        users_bills = CustomUser.objects.filter(EmployeeAt=selected_store)
        context["users"]=users_bills
        return context  

class StockSellMagView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/invoice_bill_mag54.html"  
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bonlivraison' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        if(myuser.role =='manager'):
         clients_list = Client.objects.filter(store=CurrentStore, valide= True)
         clients=[]
         for cl in clients_list:
            cl_dict={
               "client_name" :cl.name,
               "client_address":cl.adresse,
               "client_phone" : cl.phone,                      
              }
            clients.append(cl_dict)
         context["clients"]=clients    
         context["selected_store"] = selected_store
        else:
          clientsList = Client.objects.filter(user=Currentuser, valide= True)
          clients=[]
          for cl in clientsList:
            cl_dict={
               "client_name" :cl.name,
               "client_address":cl.adresse,
               "client_phone" : cl.phone,                      
              }
            clients.append(cl_dict)
          selected_store = get_object_or_404(store, pk=self.request.session["store"])
          context["selected_store"] = selected_store
          context["clients"]=clients         
        entrepots = Entrepot.objects.filter(store= selected_store)
        context["entrepots"]=entrepots    
        modeReg = ModeReglement.objects.filter(store= selected_store) 
        context["modeReg"]=modeReg  
        echeances = EcheanceReglement.objects.filter(store= selected_store)
        context["echeances"] = echeances 
        banques= Banque.objects.filter(store= selected_store)
        context["banques"] = banques
        categories= Category.objects.filter(store= selected_store)
        print(categories)
        context["categories"] = categories
        current_year = timezone.now().year

        # Filter BonComptoir instances created in the current year
        boncomptoirs_this_year = models.BonSortie.objects.filter(dateBon__year=current_year)

        # Get the count of BonComptoir instances in the current year
        sequential_number = boncomptoirs_this_year.count() + 1

        boncomptoire_code = f'BL{str(current_year)[-2:]}/{str(sequential_number).zfill(5)}'
        context["code"] = boncomptoire_code
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):     
      data = json.loads(request.body)
      dataInvoice = data.get('formData', '')
      Currentuser = request.user
      myuser  = CustomUser.objects.get(username=Currentuser.username)
      store_id = self.request.session["store"]
      CurrentStore = store.objects.get(pk=store_id)
      with transaction.atomic():
        idBon = dataInvoice["IdBon"]
        dateBon = dataInvoice["dateBp"]
        total = dataInvoice['total']
        remise =0
        if dataInvoice['remise'] :
            remise = dataInvoice['remise']
        fraisLivraison = 0
        if dataInvoice['fraislivraison'] :
            fraisLivraison = dataInvoice['fraislivraison']
        client_info = dataInvoice['clientInfo']
        agenceLivraison = dataInvoice["agencelivraison"]
        print("this agelv",agenceLivraison)
        # Create or get the client
        client_name = client_info['name']
        client= Client.objects.filter(name=client_name).first()
        client.solde += total
        client.save()
        currentEntrepot = Entrepot.objects.get(name=dataInvoice["entrepotBon"]) 
        
                               
        for product in dataInvoice["produits"]:            
            p = Stock.objects.select_for_update().get( Q(product__reference=product["ref"]) & Q(entrepot__name=currentEntrepot))
            new_quantity = p.quantity - int(product["qty"]) ## la quantité dans l'entrepot qui convient
            print(p, int(product["qty"]))
            if new_quantity < 0:
                # If any product has insufficient quantity, return a response to inform the user
                return JsonResponse({'error': f"Insufficient stock for product: {product['ref']}", 'prompt_user': True})            
            p.quantity = new_quantity
            p.save()

        bon_sortie = models.BonSortie.objects.create(idBon=idBon, dateBon=dateBon, totalPrice=total, agenceLivraison=agenceLivraison, num_cheque_reglement = fraisLivraison , Remise = remise, entrepot=currentEntrepot, client=client, user=myuser, store=CurrentStore)
        for product in dataInvoice["produits"]:
                p = Product.objects.get(reference=product["ref"], store = CurrentStore)
                p.TotalQte -= int(product["qty"])
                p.save()
                prod_total_price = p.prix_vente * int(product["qty"])
                entrepot_inst = currentEntrepot
                models.ProduitsEnBonSortie.objects.create(
                    BonNo=bon_sortie,
                    stock=p,
                    entrepot=entrepot_inst,
                    quantity=int(product["qty"]),
                    unitprice=p.prix_vente,
                    totalprice=prod_total_price
                )
        return JsonResponse({'message': "Product Added successfully."})
    
class StockSellDIVAView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/invoice_billd.html"  
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bonlivraison' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        if (myuser.role =='manager') or (myuser.role =='Finance'):
         clients_list = Client.objects.filter(store=CurrentStore, valide= True)
         clients=[]
         for cl in clients_list:
            cl_dict={
               "client_name" :cl.name,
               "client_address":cl.adresse,
               "client_phone" : cl.phone,    
               "client_type": cl.categorie_client.id,     
               "client_solde":float(cl.remaining_amount),
               "registreCommerce" : cl.registreCommerce,
               "Nif":cl.Nif,
               "Nis": cl.Nis,
               "num_article": cl.num_article,
            }
            clients.append(cl_dict)
         context["clients"]=clients    
         context["selected_store"] = selected_store
        else:
          clientsList = Client.objects.filter(user=Currentuser, valide= True)
          clients=[]
          for cl in clientsList:
            cl_dict={
               "client_name" :cl.name,
               "client_address":cl.adresse,
               "client_phone" : cl.phone,    
               "client_type": cl.categorie_client.id,     
               "client_solde":float(cl.remaining_amount),
               "registreCommerce" : cl.registreCommerce,
               "Nif":cl.Nif,
               "Nis": cl.Nis,
               "num_article": cl.num_article,
              }
            clients.append(cl_dict)
          selected_store = get_object_or_404(store, pk=self.request.session["store"])
          context["selected_store"] = selected_store
          context["clients"]=clients         
        entrepots = Entrepot.objects.filter(store= selected_store)
        context["entrepots"]=entrepots    
        modeReg = ModeReglement.objects.filter(store= selected_store) 
        context["modeReg"]=modeReg  
        echeances = EcheanceReglement.objects.filter(store= selected_store)
        context["echeances"] = echeances 
        banques= Banque.objects.filter(store= selected_store)
        context["banques"] = banques
        categories= Category.objects.filter(store= selected_store)
        context["categories"] = categories
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):     
      data = json.loads(request.body)
      dataInvoice = data.get('formData', '')
      Currentuser = request.user
      myuser  = CustomUser.objects.get(username=Currentuser.username)
      store_id = self.request.session["store"]
      CurrentStore = store.objects.get(pk=store_id)
      with transaction.atomic():
        idBon = dataInvoice["IdBon"]
        dateBon = dataInvoice["dateBp"]
        total = float(dataInvoice['total'])
        remise =0
        if dataInvoice['remise'] :
            remise = dataInvoice['remise']
        fraisLivraison = 0
        if dataInvoice['fraislivraison'] :
            fraisLivraison = dataInvoice['fraislivraison']
            
        modereg = None
        if dataInvoice['ModeReglement'] :
            modereg = ModeReglement.objects.get(id = dataInvoice['ModeReglement'])
            
        banque = None
        if dataInvoice['banque'] :
            banque = Banque.objects.get(id = dataInvoice['banque'])
            
        num_cheque = ''
        if dataInvoice['numCheque'] :
            num_cheque = dataInvoice['numCheque']
        
        fraislivraisonext = 0
        if dataInvoice.get('fraislivraisonext') :
            fraislivraisonext = dataInvoice['fraislivraisonext']

        client_info = dataInvoice['clientInfo']
        agenceLivraison = dataInvoice.get("agencelivraison", "divatech")

        # Create or get the client
        client_name = client_info['name']
        client= Client.objects.filter(name=client_name).first()
        currentEntrepot = Entrepot.objects.get(name=dataInvoice["entrepotBon"]) 
        
        List_data_transfert = []                  
        if dataInvoice["creationAutomatique"]:
              bon_trans_dict = {}
              for produit in dataInvoice["produits"]:
                if produit["ent"] != dataInvoice["entrepotBon"]:
                    stock_dep =Stock.objects.get(product__reference=produit["ref"], entrepot__name=produit["ent"])
                    List_data_transfert.append({'stock_dep':stock_dep, 'quantity':produit["qty"]})
                    
              for data in List_data_transfert:
                 stock = data.get("stock_dep")
                 entrepot_depart = stock.entrepot
                 new_quantity_in_source = stock.quantity - int(data["quantity"])

                 if new_quantity_in_source < 0:
                     return JsonResponse({
                         'error': f"Insufficient stock for product: {stock.product.reference} In {entrepot_depart.name}",
                         'prompt_user': True
                     })

                 # Check if a BonTransfert object already exists for the given stock_dep and entrepot_depart
                 key = (entrepot_depart.id)
                 if key in bon_trans_dict:
                     bon_trans = bon_trans_dict[key]
                 else:
                     # Create a new BonTransfert if one does not exist
                     current_year = datetime.now().strftime('%y')
                     current_month = datetime.now().strftime('%m')
                     last_bon = BonTransfert.objects.order_by('-id').first()
                     if last_bon:
                         last_id = last_bon.idBon.split('-')[-1]
                         if last_id.isnumeric():
                             sequence_number = int(last_id) + 1
                         else:
                             sequence_number = 1
                     else:
                         sequence_number = 1

                     codeBon = f'BT{current_year}{current_month}-{sequence_number}'
                     bon_trans = BonTransfert.objects.create(
                         idBon=codeBon,
                         dateBon=dataInvoice["dateBp"],
                         entrepot_depart=entrepot_depart,
                         entrepot_arrive=currentEntrepot,
                         store=CurrentStore,
                         automatiquement=True,
                         valide=False,
                         user=myuser
                     )
                     responsable_entrepot = CustomUser.objects.filter(entrepots_responsible=stock.entrepot).first()
                     if responsable_entrepot:
                        notify.send(
                            sender=myuser,
                            recipient=responsable_entrepot,
                            verb=f'Bon de transfert numero {codeBon} a été créer automatiquement par {myuser} , Veuillez valider',
                            description=f'/stock/Edit-bontransfert/{bon_trans.id}',
                            level=1,
                        )
                     # Store the BonTransfert object in the dictionary
                     bon_trans_dict[key] = bon_trans



                 # Create or get the stock_dest
                 stock_dest, created = Stock.objects.get_or_create(
                     product=stock.product,
                     entrepot=currentEntrepot,
                     defaults={'quantity': 0}
                 )

                 # Create a new ProduitsEnBonTransfert entry
                 ProduitsEnBonTransfert.objects.create(
                     BonNo=bon_trans,
                     stock_dep=stock,
                     stock_arr=stock_dest,
                     quantity=int(data["quantity"]),
                 )

        for product in dataInvoice["produits"]:      
            entrepot_inst = currentEntrepot
            if product["ent"] != entrepot_inst.name:
                entrepot_inst = Entrepot.objects.get(name = product["ent"], store = CurrentStore)      
            p = Stock.objects.select_for_update().get( Q(product__reference=product["ref"]) & Q(entrepot__name=entrepot_inst))
            stock_exists = False
            for item in List_data_transfert:
                if item['stock_dep'] == p:
                    stock_exists = True
                    break
            if not stock_exists:    
                new_quantity = p.quantity - int(product["qty"]) ## la quantité dans l'entrepot qui convient
                if new_quantity < 0:
                    # If any product has insufficient quantity, return a response to inform the user
                    return JsonResponse({'error': f"Insufficient1 stock for product: {product['ref']}", 'prompt_user': True})            
        current_year = timezone.now().year
        current_month = datetime.now().strftime('%m')
        boncomptoirs_this_year = models.BonSortie.objects.filter(dateBon__year=current_year, store = CurrentStore )

        # Get the count of BonComptoir instances in the current year
        sequential_number = boncomptoirs_this_year.count() + 1
        while True:
            # Generate the boncomptoire_code
            if self.request.session["store"] == '1':
                boncomptoire_code = f'BL{str(current_year)[-2:]}{str(current_month)}/{str(sequential_number).zfill(5)}'
            else:
                boncomptoire_code = f'BL{str(current_year)[-2:]}{str(current_month)}-{str(sequential_number).zfill(5)}'
        
            # Check if the boncomptoire_code already exists in the database
            existing_bon = models.BonSortie.objects.filter(idBon=boncomptoire_code, store=CurrentStore).first()
        
            if existing_bon is None:
                # If the boncomptoire_code is unique, break out of the loop
                break
        
            # If the boncomptoire_code already exists, increment the sequential_number and try again
            sequential_number += 1 
        bon_sortie = models.BonSortie.objects.create(
            idBon=boncomptoire_code,
            dateBon=dateBon,
            agenceLivraison=agenceLivraison,
            fraisLivraison = fraisLivraison,
            fraisLivraisonexterne = fraislivraisonext,
            mode_reglement = modereg,
            banque_Reglement = banque,
            note = dataInvoice["obs"],
            num_cheque_reglement = num_cheque,
            typebl= "DET",
            confirmed = False,
            Remise = remise,
            entrepot=currentEntrepot, 
            client=client, user=myuser, store=CurrentStore)
        
        if dataInvoice["creationAutomatique"]:
            models.DemandeTransfert.objects.create(
                BonSNo = bon_sortie,
                BonTransfert = bon_trans,
                etat='False'
            )

        for product in dataInvoice["produits"]:
                
                entrepot_inst = currentEntrepot
                pr = Product.objects.get(reference=product["ref"], store = CurrentStore)
                if product["ent"] == currentEntrepot.name:
                    s = Stock.objects.get(product = pr, entrepot = currentEntrepot )
                    new_quantity = s.quantity - int(product["qty"]) ## la quantité dans l'entrepot qui convient
                    s.quantity = new_quantity
                    s.save()
                prod_total_price = float(product["rateLiv"]) * int(product["qty"])    
                if product["ent"] != entrepot_inst.name:
                    entrepot_inst = Entrepot.objects.get(name = product["ent"], store = CurrentStore)
                models.ProduitsEnBonSortie.objects.create(
                    BonNo=bon_sortie,
                    stock=pr,
                    entrepot=entrepot_inst,                   
                    quantity=int(product["qty"]),
                    unitprice= float(product["rateLiv"]),
                    totalprice=prod_total_price
                )
                
        if not dataInvoice["creationAutomatique"]:        
            responsable_entrepot = CustomUser.objects.filter(role ="manager")
            if responsable_entrepot:
                for resp in responsable_entrepot : 
                        notify.send(
                            sender=myuser,
                            recipient=resp,
                            verb=f'Bon de Livraison numero {idBon} a été créer  par {myuser} , Veuillez valider',
                            description=f'/ventes/edit-bill-diva/{bon_sortie.id}',
                            level=1,
                        )
        # Filter BonComptoir instances created in the current year
        
                        
        return JsonResponse({'message': "Bill Added successfully.", 'code': boncomptoire_code})
    
class StockSellCartonView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/invoice_billd_carton.html"  
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bonlivraison' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
        # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        if (myuser.role =='manager') or (myuser.role =='Finance'):
         clients_list = Client.objects.filter(store=CurrentStore, valide= True)
         clients=[]
         for cl in clients_list:
            cl_dict={
               "client_name" :cl.name,
               "client_address":cl.adresse,
               "client_phone" : cl.phone,    
               "client_type": cl.categorie_client.id,     
               "client_solde":float(cl.remaining_amount),
               "registreCommerce" : cl.registreCommerce,
               "Nif":cl.Nif,
               "Nis": cl.Nis,
               "num_article": cl.num_article,
            }
            clients.append(cl_dict)
         
         context["clients"]=clients    
         context["selected_store"] = selected_store
        else:
          clientsList = Client.objects.filter(user=Currentuser, valide= True)
          clients=[]
          for cl in clientsList:
            cl_dict={
               "client_name" :cl.name,
               "client_address":cl.adresse,
               "client_phone" : cl.phone,    
               "client_type": cl.categorie_client.id,     
               "client_solde":float(cl.remaining_amount),
               "registreCommerce" : cl.registreCommerce,
               "Nif":cl.Nif,
               "Nis": cl.Nis,
               "num_article": cl.num_article,
              }
            clients.append(cl_dict)
          selected_store = get_object_or_404(store, pk=self.request.session["store"])
          context["selected_store"] = selected_store
          context["clients"]=clients         
        entrepots = Entrepot.objects.filter(store= selected_store)
        context["entrepots"]=entrepots    
        modeReg = ModeReglement.objects.filter(store= selected_store) 
        context["modeReg"]=modeReg  
        echeances = EcheanceReglement.objects.filter(store= selected_store)
        context["echeances"] = echeances 
        banques= Banque.objects.filter(store= selected_store)
        context["banques"] = banques
        categories= Category.objects.filter(store= selected_store)
        context["categories"] = categories
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):     
      data = json.loads(request.body)
      dataInvoice = data.get('formData', '')
      Currentuser = request.user
      myuser  = CustomUser.objects.get(username=Currentuser.username)
      store_id = self.request.session["store"]
      CurrentStore = store.objects.get(pk=store_id)
      with transaction.atomic():
        idBon = dataInvoice["IdBon"]
        dateBon = dataInvoice["dateBp"]
        total = float(dataInvoice['total'])
        remise =0
        if dataInvoice['remise'] :
            remise = dataInvoice['remise']
        fraisLivraison = 0
        if dataInvoice['fraislivraison'] :
            fraisLivraison = dataInvoice['fraislivraison']
            
        modereg = None
        if dataInvoice['ModeReglement'] :
            modereg = ModeReglement.objects.get(id = dataInvoice['ModeReglement'])
            
        banque = None
        if dataInvoice['banque'] :
            banque = Banque.objects.get(id = dataInvoice['banque'])
            
        num_cheque = ''
        if dataInvoice['numCheque'] :
            num_cheque = dataInvoice['numCheque']
        
        fraislivraisonext = 0
        if dataInvoice.get('fraislivraisonext') :
            fraislivraisonext = dataInvoice['fraislivraisonext']

        client_info = dataInvoice['clientInfo']
        agenceLivraison = dataInvoice.get("agencelivraison", "divatech")

        # Create or get the client
        client_name = client_info['name']
        client= Client.objects.filter(name=client_name).first()
        currentEntrepot = Entrepot.objects.get(name=dataInvoice["entrepotBon"]) 
        
        List_data_transfert = []                  
        if dataInvoice["creationAutomatique"]:
              bon_trans_dict = {}
              for produit in dataInvoice["produits"]:
                if produit["ent"] != dataInvoice["entrepotBon"]:
                    stock_dep =Stock.objects.get(product__reference=produit["ref"], entrepot__name=produit["ent"])
                    List_data_transfert.append({'stock_dep':stock_dep, 'quantity':produit["qty"]})
                    
              for data in List_data_transfert:
                 stock = data.get("stock_dep")
                 entrepot_depart = stock.entrepot
                 new_quantity_in_source = stock.quantity - int(data["quantity"])

                 if new_quantity_in_source < 0:
                     return JsonResponse({
                         'error': f"Insufficient stock for product: {stock.product.reference} In {entrepot_depart.name}",
                         'prompt_user': True
                     })

                 # Check if a BonTransfert object already exists for the given stock_dep and entrepot_depart
                 key = (entrepot_depart.id)
                 if key in bon_trans_dict:
                     bon_trans = bon_trans_dict[key]
                 else:
                     # Create a new BonTransfert if one does not exist
                     current_year = datetime.now().strftime('%y')
                     current_month = datetime.now().strftime('%m')
                     last_bon = BonTransfert.objects.order_by('-id').first()
                     if last_bon:
                         last_id = last_bon.idBon.split('-')[-1]
                         if last_id.isnumeric():
                             sequence_number = int(last_id) + 1
                         else:
                             sequence_number = 1
                     else:
                         sequence_number = 1

                     codeBon = f'BT{current_year}{current_month}-{sequence_number}'
                     bon_trans = BonTransfert.objects.create(
                         idBon=codeBon,
                         dateBon=dataInvoice["dateBp"],
                         entrepot_depart=entrepot_depart,
                         entrepot_arrive=currentEntrepot,
                         store=CurrentStore,
                         automatiquement=True,
                         valide=False,
                         user=myuser
                     )
                     responsable_entrepot = CustomUser.objects.filter(entrepots_responsible=stock.entrepot).first()
                     if responsable_entrepot:
                        notify.send(
                            sender=myuser,
                            recipient=responsable_entrepot,
                            verb=f'Bon de transfert numero {codeBon} a été créer automatiquement par {myuser} , Veuillez valider',
                            description=f'/stock/Edit-bontransfert/{bon_trans.id}',
                            level=1,
                        )
                     # Store the BonTransfert object in the dictionary
                     bon_trans_dict[key] = bon_trans



                 # Create or get the stock_dest
                 stock_dest, created = Stock.objects.get_or_create(
                     product=stock.product,
                     entrepot=currentEntrepot,
                     defaults={'quantity': 0}
                 )

                 # Create a new ProduitsEnBonTransfert entry
                 ProduitsEnBonTransfert.objects.create(
                     BonNo=bon_trans,
                     stock_dep=stock,
                     stock_arr=stock_dest,
                     quantity=int(data["quantity"]),
                 )

        for product in dataInvoice["produits"]:      
            entrepot_inst = currentEntrepot
            if product["ent"] != entrepot_inst.name:
                entrepot_inst = Entrepot.objects.get(name = product["ent"], store = CurrentStore)      
            p = Stock.objects.select_for_update().get( Q(product__reference=product["ref"]) & Q(entrepot__name=entrepot_inst))
            stock_exists = False
            for item in List_data_transfert:
                if item['stock_dep'] == p:
                    stock_exists = True
                    break
            if not stock_exists:    
                new_quantity = p.quantity - int(product["qty"]) ## la quantité dans l'entrepot qui convient
                if new_quantity < 0:
                    # If any product has insufficient quantity, return a response to inform the user
                    return JsonResponse({'error': f"Insufficient1 stock for product: {product['ref']}", 'prompt_user': True})            
        current_year = timezone.now().year
        current_month = datetime.now().strftime('%m')
        boncomptoirs_this_year = models.BonSortie.objects.filter(dateBon__year=current_year, store = CurrentStore )

        # Get the count of BonComptoir instances in the current year
        sequential_number = boncomptoirs_this_year.count() + 1
        while True:
            # Generate the boncomptoire_code
            if self.request.session["store"] == '1':
                boncomptoire_code = f'BL{str(current_year)[-2:]}{str(current_month)}/{str(sequential_number).zfill(5)}'
            else:
                boncomptoire_code = f'BL{str(current_year)[-2:]}{str(current_month)}-{str(sequential_number).zfill(5)}'
        
            # Check if the boncomptoire_code already exists in the database
            existing_bon = models.BonSortie.objects.filter(idBon=boncomptoire_code, store=CurrentStore).first()
        
            if existing_bon is None:
                # If the boncomptoire_code is unique, break out of the loop
                break
        
            # If the boncomptoire_code already exists, increment the sequential_number and try again
            sequential_number += 1 
        bon_sortie = models.BonSortie.objects.create(
            idBon=boncomptoire_code,
            dateBon=dateBon,
            agenceLivraison=agenceLivraison,
            fraisLivraison = fraisLivraison,
            fraisLivraisonexterne = fraislivraisonext,
            mode_reglement = modereg,
            banque_Reglement = banque,
            note = dataInvoice["obs"],
            num_cheque_reglement = num_cheque,
            typebl= "carton",
            confirmed = False,
            Remise = remise,
            entrepot=currentEntrepot, 
            client=client, user=myuser, store=CurrentStore)
        
        if dataInvoice["creationAutomatique"]:
            models.DemandeTransfert.objects.create(
                BonSNo = bon_sortie,
                BonTransfert = bon_trans,
                etat='False'
            )
                  
        for product in dataInvoice["produits"]:
                
                entrepot_inst = currentEntrepot
                pr = Product.objects.get(reference=product["ref"], store = CurrentStore)
                if product["ent"] == currentEntrepot.name:
                    s = Stock.objects.get(product = pr, entrepot = currentEntrepot )
                    new_quantity = s.quantity - int(product["qty"]) ## la quantité dans l'entrepot qui convient
                    s.quantity = new_quantity
                    s.save()
                prod_total_price = float(product["rateLiv"]) * int(product["qty"])    
                if product["ent"] != entrepot_inst.name:
                    entrepot_inst = Entrepot.objects.get(name = product["ent"], store = CurrentStore)
                models.ProduitsEnBonSortie.objects.create(
                    BonNo=bon_sortie,
                    stock=pr,
                    entrepot=entrepot_inst,                   
                    quantity=int(product["qty"]),
                    unitprice= float(product["rateLiv"]),
                    totalprice=prod_total_price
                )
                
        if not dataInvoice["creationAutomatique"]:        
            responsable_entrepot = CustomUser.objects.filter(role ="manager")
            if responsable_entrepot:
                for resp in responsable_entrepot : 
                        notify.send(
                            sender=myuser,
                            recipient=resp,
                            verb=f'Bon de Livraison numero {idBon} a été créer  par {myuser} , Veuillez valider',
                            description=f'/ventes/edit-bill-diva/{bon_sortie.id}',
                            level=1,
                        )
        # Filter BonComptoir instances created in the current year
        
                        
        return JsonResponse({'message': "Bill Added successfully.", 'code': boncomptoire_code})

class StockSellComptoirView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/comptoire_bill.html"  
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bonlivraison' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        if(myuser.role =='manager'):
         clients_list = Client.objects.filter(store=CurrentStore, valide= True)
         clients=[]
         for cl in clients_list:
            cl_dict={
                "client_id":cl.id,
               "client_name" :cl.name,
               "client_address":cl.adresse,
               "client_phone" : cl.phone,                      
              }
            clients.append(cl_dict)
         context["clients"]=clients    
         context["selected_store"] = selected_store
        else:
          clientsList = Client.objects.filter(user=Currentuser, valide= True)
          clients=[]
          for cl in clientsList:
            cl_dict={
                "client_id":cl.id,
               "client_name" :cl.name,
               "client_address":cl.adresse,
               "client_phone" : cl.phone,                      
              }
            clients.append(cl_dict)
          selected_store = get_object_or_404(store, pk=self.request.session["store"])
          context["selected_store"] = selected_store
          context["clients"]=clients         
        entrepots = Entrepot.objects.filter(store= selected_store)
        context["entrepots"]=entrepots    
        modeReg = ModeReglement.objects.filter(store= selected_store) 
        context["modeReg"]=modeReg  
        echeances = EcheanceReglement.objects.filter(store= selected_store)
        context["echeances"] = echeances 
        banques= Banque.objects.filter(store= selected_store)
        context["banques"] = banques
        categories= Category.objects.filter(store= selected_store)
        context["categories"] = categories
        current_year = timezone.now().year
        bons_compt = BonComptoire.objects.all()
        sequential_number = bons_compt.count() + 1
        boncomptoire_code = f'VC{str(current_year)[-2:]}/{str(sequential_number).zfill(3)}'
        context["code"] =boncomptoire_code
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):     
      data = json.loads(request.body)
      dataInvoice = data.get('formData', '')
      Currentuser = request.user
      myuser  = CustomUser.objects.get(username=Currentuser.username)
      store_id = self.request.session["store"]
      CurrentStore = store.objects.get(pk=store_id)
      with transaction.atomic():
        idBon = dataInvoice["IdBon"]
        dateBon = dataInvoice["dateBp"]
        total = dataInvoice['total']
     
        client_info = dataInvoice['clientInfo']
        # Create or get the client
        client_name = client_info['name']
        client= Client.objects.get(id=client_name)
        client.solde += total
        client.save()
        currentEntrepot = Entrepot.objects.get(name=dataInvoice["entrepotBon"]) 

        for product in dataInvoice["produits"]:            
            p = Stock.objects.select_for_update().get( Q(product__reference=product["ref"]) & Q(entrepot__name=currentEntrepot))
            new_quantity = p.quantity - int(product["qty"]) ## la quantité dans l'entrepot qui convient
            print(p, int(product["qty"]))
            if new_quantity < 0:
                # If any product has insufficient quantity, return a response to inform the user
                return JsonResponse({'error': f"Insufficient stock for product: {product['ref']}", 'prompt_user': True})            
            p.quantity = new_quantity
            p.save()

        bon_sortie = BonComptoire.objects.create(idBon=idBon, dateBon=dateBon,  client=client, user=myuser, store=CurrentStore)
        for product in dataInvoice["produits"]:
                p = Product.objects.get(reference=product["ref"], store = CurrentStore)
                p.TotalQte -= int(product["qty"])
                p.save()
                prod_total_price = p.prix_vente * int(product["qty"])
                entrepot_inst = currentEntrepot
                ProduitsEnBonComptoir.objects.create(
                    BonNo=bon_sortie,
                    stock=p,
                    entrepot=entrepot_inst,
                    quantity=int(product["qty"]),
                    unitprice=p.prix_vente,
                    totalprice=prod_total_price
                )
        return JsonResponse({'message': "Product Added successfully."})
    
class StockSellView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/invoice_bill.html"  
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bonlivraison' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        if (myuser.role =='manager') or (myuser.role =='Finance'):
         clients_list = Client.objects.filter(store=CurrentStore, valide= True)
         clients=[]
         for cl in clients_list:
            cl_dict={
               "client_name" :cl.name,
               "client_address":cl.adresse,
               "client_phone" : cl.phone,    
               "client_type": cl.categorie_client.id,     
               "client_solde":float(cl.remaining_amount),
               "registreCommerce" : cl.registreCommerce,
               "Nif":cl.Nif,
               "Nis": cl.Nis,
               "num_article": cl.num_article,
            }
            clients.append(cl_dict)
         context["clients"]=clients    
         context["selected_store"] = selected_store
        else:
          clientsList = Client.objects.filter(user=Currentuser, valide= True)
          clients=[]
          for cl in clientsList:
            cl_dict={
                "client_id":cl.id,
               "client_name" :cl.name,
               "client_address":cl.adresse,
               "client_phone" : cl.phone,    
               "client_type": cl.categorie_client.id,     
               "client_solde":float(cl.remaining_amount),
               "registreCommerce" : cl.registreCommerce,
               "Nif":cl.Nif,
               "Nis": cl.Nis,
               "num_article": cl.num_article,
              }
            clients.append(cl_dict)
          selected_store = get_object_or_404(store, pk=self.request.session["store"])
          context["selected_store"] = selected_store
          context["clients"]=clients         
        entrepots = Entrepot.objects.filter(store= selected_store)
        context["entrepots"]=entrepots    
        modeReg = ModeReglement.objects.filter(store= selected_store) 
        context["modeReg"]=modeReg  
        echeances = EcheanceReglement.objects.filter(store= selected_store)
        context["echeances"] = echeances 
        banques= Banque.objects.filter(store= selected_store)
        context["banques"] = banques
        categories= Category.objects.filter(store= selected_store)

        context["categories"] = categories

        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):     
      data = json.loads(request.body)
      dataInvoice = data.get('formData', '')
      Currentuser = request.user
      myuser  = CustomUser.objects.get(username=Currentuser.username)
      store_id = self.request.session["store"]
      CurrentStore = store.objects.get(pk=store_id)
      with transaction.atomic():
        idBon = dataInvoice["IdBon"]
        dateBon = dataInvoice["dateBp"]
        total = dataInvoice['total']
     
        client_info = dataInvoice['clientInfo']
        # Create or get the client
        client_name = client_info['name']
        client= Client.objects.get(name=client_name, store = CurrentStore)
        
        modereg = None
        if dataInvoice['ModeReglement'] :
            modereg = ModeReglement.objects.get(id = dataInvoice['ModeReglement'])
            
        banque = None
        if dataInvoice['banque'] :
            banque = Banque.objects.get(id = dataInvoice['banque'])
            
        num_cheque = ''
        if dataInvoice['numCheque'] :
            num_cheque = dataInvoice['numCheque']
        
        currentEntrepot = Entrepot.objects.get(name=dataInvoice["entrepotBon"]) 
        List_data_transfert = []                  
        if dataInvoice["creationAutomatique"]:
              bon_trans_dict = {}
              for produit in dataInvoice["produits"]:
                if produit["ent"] != dataInvoice["entrepotBon"]:
                    produit_ins = Product.objects.get(reference = produit['ref'], store = CurrentStore )
                    stock_dep =Stock.objects.get(product = produit_ins, entrepot__name=produit["ent"])
                    List_data_transfert.append({'stock_dep':stock_dep, 'quantity':produit["qty"]})
                    
              for data in List_data_transfert:
                 stock = data.get("stock_dep")
                 entrepot_depart = stock.entrepot
                 new_quantity_in_source = stock.quantity - int(data["quantity"])

                 if new_quantity_in_source < 0:
                     return JsonResponse({
                         'error': f"Insufficient stock for product: {stock.product.reference} In {entrepot_depart.name}",
                         'prompt_user': True
                     })

                 # Check if a BonTransfert object already exists for the given stock_dep and entrepot_depart
                 key = (entrepot_depart.id)
                 if key in bon_trans_dict:
                     bon_trans = bon_trans_dict[key]
                 else:
                     # Create a new BonTransfert if one does not exist
                     current_year = datetime.now().strftime('%y')
                     current_month = datetime.now().strftime('%m')
                     last_bon = BonTransfert.objects.order_by('-id').first()
                     if last_bon:
                         last_id = last_bon.idBon.split('-')[-1]
                         if last_id.isnumeric():
                             sequence_number = int(last_id) + 1
                         else:
                             sequence_number = 1
                     else:
                         sequence_number = 1

                     codeBon = f'BT{current_year}{current_month}-{sequence_number}'
                     bon_trans = BonTransfert.objects.create(
                         idBon=codeBon,
                         dateBon=dataInvoice["dateBp"],
                         entrepot_depart=entrepot_depart,
                         entrepot_arrive=currentEntrepot,
                         store=CurrentStore,
                         automatiquement=True,
                         valide=False,
                         user=myuser
                     )
                     responsable_entrepot = CustomUser.objects.filter(entrepots_responsible=stock.entrepot).first()
                     if responsable_entrepot:
                        notify.send(
                            sender=myuser,
                            recipient=responsable_entrepot,
                            verb=f'Bon de transfert numero {codeBon} a été créer automatiquement par {myuser} , Veuillez valider',
                            description=f'/stock/Edit-bontransfert/{bon_trans.id}',
                            level=1,
                        )
                     # Store the BonTransfert object in the dictionary
                     bon_trans_dict[key] = bon_trans



                 # Create or get the stock_dest
                 stock_dest, created = Stock.objects.get_or_create(
                     product=stock.product,
                     entrepot=currentEntrepot,
                     defaults={'quantity': 0}
                 )

                 # Create a new ProduitsEnBonTransfert entry
                 ProduitsEnBonTransfert.objects.create(
                     BonNo=bon_trans,
                     stock_dep=stock,
                     stock_arr=stock_dest,
                     quantity=int(data["quantity"]),
                 )
                 
               
        for product in dataInvoice["produits"]:   
          if "ref" in product:               
            p = Stock.objects.select_for_update().get( Q(product__reference=product["ref"]) & Q(entrepot__name=currentEntrepot))
            new_quantity = p.quantity - int(product["qty"]) ## la quantité dans l'entrepot qui convient
            if new_quantity < 0:
                # If any product has insufficient quantity, return a response to inform the user
                return JsonResponse({'error': f"Insufficient stock for product: {product['ref']}", 'prompt_user': True})            

        current_year = timezone.now().year
        current_month = datetime.now().strftime('%m')
        boncomptoirs_this_year = models.BonSortie.objects.filter(dateBon__year = current_year, store= CurrentStore)


        # Get the count of BonComptoir instances in the current year
        sequential_number = boncomptoirs_this_year.count() + 1
        if self.request.session["store"] == 1:
            boncomptoire_code = f'BL{str(current_year)[-2:]}{str(current_month)}/{str(sequential_number).zfill(5)}'
        else: 
            boncomptoire_code = f'BL{str(current_year)[-2:]}{str(current_month)}-{str(sequential_number).zfill(5)}'
        bon_sortie = models.BonSortie.objects.create(
            idBon=boncomptoire_code,
            dateBon=dateBon,
            entrepot=currentEntrepot, 
            reference_pc = dataInvoice["reference_pc"], 
            name_pc = dataInvoice["designation_pc"], 
            Remise = dataInvoice["remise"],
            mode_reglement = modereg,
            banque_Reglement = banque,
            typebl= "PC",
            confirmed = False,
            num_cheque_reglement = num_cheque,
            client=client, 
            user=myuser, 
            store=CurrentStore)
                     
        if dataInvoice["creationAutomatique"]:
            models.DemandeTransfert.objects.create(
                BonSNo = bon_sortie,
                BonTransfert = bon_trans,
                etat='False'
            )    
            
        for product in dataInvoice["produits"]:
            if "ref" in product:
                p = Product.objects.get(reference=product["ref"], store = CurrentStore)
                s = Stock.objects.get(product = p, entrepot = currentEntrepot )
                print("------------------------------------------------------------------------------------------")
                print(p.ref)
                print(p.name)
                print("------------------------------------------------------------------------------------------")
                
                new_quantity = s.quantity - int(product["qty"]) ## la quantité dans l'entrepot qui convient
                s.quantity = new_quantity
                s.save()
                p.TotalQte -= int(product["qty"])
                p.save()
                product_rate = float(product['rateLiv'])
                prod_total_price = float(product['rateLiv']) * int(product["qty"])
                entrepot_inst = currentEntrepot
                models.ProduitsEnBonSortie.objects.create(
                    BonNo=bon_sortie,
                    stock=p,
                    entrepot=entrepot_inst,
                    quantity=int(product["qty"]),
                    unitprice=product_rate,
                    totalprice=prod_total_price
                )
        return JsonResponse({'message': "Product Added successfully."})
        
class InvoiceKitListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/invoice_page_kit.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bonlivraison' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)       
        # store_id = self.kwargs.get('store_id')
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        if(myuser.role =='manager') or (myuser.role == 'Finance') or (myuser.role=='DIRECTEUR EXECUTIF') :
          bons_sorties = models.BonSortie.objects.filter(store=selected_store, typebl='KIT').order_by('-id')
          context["bons_sorties"] =bons_sorties
        elif myuser.role=='gestion-stock':
            bons_sorties = models.BonSortie.objects.filter(
                store=selected_store,
                valide = True,
                typebl = 'KIT',
                entrepot__name ="Depot principal Reghaia"
            ).exclude(client__name="Annulé --- Annulé").filter(Q(bon_garantie__isnull=True)).order_by('-id')  # Sort by date in descending order
            context["bons_sorties"] = bons_sorties
            
        else:
          bons_sorties = models.BonSortie.objects.filter(store=selected_store, user=myuser, typebl='KIT').order_by('-id')       
          context["bons_sorties"] =bons_sorties
        entrepots = Entrepot.objects.filter(store=selected_store)
        context["entrepots"] = entrepots
        users_bills = CustomUser.objects.filter(EmployeeAt=selected_store)
        context["users"]=users_bills
        categories= Category.objects.filter(store= selected_store, kit = True)
        context["categories"] = categories
        return context 
        
class StockSellKitView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/invoice_billd_kit.html"  
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bonlivraison' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        if (myuser.role =='manager') or (myuser.role =='Finance'):
         clients_list = Client.objects.filter(store=CurrentStore, valide= True)
         clients=[]
         for cl in clients_list:
            cl_dict={
               "client_name" :cl.name,
               "client_address":cl.adresse,
               "client_phone" : cl.phone,    
               "client_type": cl.categorie_client.id,     
               "client_solde":float(cl.remaining_amount),
            }
            clients.append(cl_dict)
         context["clients"]=clients    
         context["selected_store"] = selected_store
        else:
          clientsList = Client.objects.filter(user=Currentuser, valide= True)
          clients=[]
          for cl in clientsList:
            cl_dict={
               "client_name" :cl.name,
               "client_address":cl.adresse,
               "client_phone" : cl.phone, 
               "client_type": cl.categorie_client.id,  
               "client_solde":float(cl.remaining_amount),
              }
            clients.append(cl_dict)
          selected_store = get_object_or_404(store, pk=self.request.session["store"])
          context["selected_store"] = selected_store
          context["clients"]=clients         
        entrepots = Entrepot.objects.filter(store= selected_store)
        context["entrepots"]=entrepots    
        modeReg = ModeReglement.objects.filter(store= selected_store) 
        context["modeReg"]=modeReg  
        echeances = EcheanceReglement.objects.filter(store= selected_store)
        context["echeances"] = echeances 
        banques= Banque.objects.filter(store= selected_store)
        context["banques"] = banques
        categories= Category.objects.filter(store= selected_store, kit = True)
        context["categories"] = categories
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):     
      data = json.loads(request.body)
      dataInvoice = data.get('formData', '')
      Currentuser = request.user
      myuser  = CustomUser.objects.get(username=Currentuser.username)
      store_id = self.request.session["store"]
      CurrentStore = store.objects.get(pk=store_id)
      with transaction.atomic():
        idBon = dataInvoice["IdBon"]
        dateBon = dataInvoice["dateBp"]
        total = float(dataInvoice['total'])
        remise =0
        if dataInvoice['remise'] :
            remise = dataInvoice['remise']
        fraisLivraison = 0
        if dataInvoice['fraislivraison'] :
            fraisLivraison = dataInvoice['fraislivraison']
            
        modereg = None
        if dataInvoice['ModeReglement'] :
            modereg = ModeReglement.objects.get(id = dataInvoice['ModeReglement'])
            
        banque = None
        if dataInvoice['banque'] :
            banque = Banque.objects.get(id = dataInvoice['banque'])
            
        num_cheque = ''
        if dataInvoice['numCheque'] :
            num_cheque = dataInvoice['numCheque']
        
        fraislivraisonext = 0
        if dataInvoice.get('fraislivraisonext') :
            fraislivraisonext = dataInvoice['fraislivraisonext']

        client_info = dataInvoice['clientInfo']
        agenceLivraison = dataInvoice.get("agencelivraison", "divatech")

        # Create or get the client
        client_name = client_info['name']
        client= Client.objects.filter(name=client_name).first()
        currentEntrepot = Entrepot.objects.get(name=dataInvoice["entrepotBon"]) 
        
        List_data_transfert = []                  
        if dataInvoice["creationAutomatique"]:
              bon_trans_dict = {}
              for produit in dataInvoice["produits"]:
                if produit["ent"] != dataInvoice["entrepotBon"]:
                    stock_dep =Stock.objects.get(product__reference=produit["ref"], entrepot__name=produit["ent"])
                    List_data_transfert.append({'stock_dep':stock_dep, 'quantity':produit["qty"]})
                    
              for data in List_data_transfert:
                 stock = data.get("stock_dep")
                 entrepot_depart = stock.entrepot
                 new_quantity_in_source = stock.quantity - int(data["quantity"])

                 if new_quantity_in_source < 0:
                     return JsonResponse({
                         'error': f"Insufficient stock for product: {stock.product.reference} In {entrepot_depart.name}",
                         'prompt_user': True
                     })

                 # Check if a BonTransfert object already exists for the given stock_dep and entrepot_depart
                 key = (entrepot_depart.id)
                 if key in bon_trans_dict:
                     bon_trans = bon_trans_dict[key]
                 else:
                     # Create a new BonTransfert if one does not exist
                     current_year = datetime.now().strftime('%y')
                     current_month = datetime.now().strftime('%m')
                     last_bon = BonTransfert.objects.order_by('-id').first()
                     if last_bon:
                         last_id = last_bon.idBon.split('-')[-1]
                         if last_id.isnumeric():
                             sequence_number = int(last_id) + 1
                         else:
                             sequence_number = 1
                     else:
                         sequence_number = 1

                     codeBon = f'BT{current_year}{current_month}-{sequence_number}'
                     bon_trans = BonTransfert.objects.create(
                         idBon=codeBon,
                         dateBon=dataInvoice["dateBp"],
                         entrepot_depart=entrepot_depart,
                         entrepot_arrive=currentEntrepot,
                         store=CurrentStore,
                         automatiquement=True,
                         valide=False,
                         user=myuser
                     )
                     responsable_entrepot = CustomUser.objects.filter(entrepots_responsible=stock.entrepot).first()
                     if responsable_entrepot:
                        notify.send(
                            sender=myuser,
                            recipient=responsable_entrepot,
                            verb=f'Bon de transfert numero {codeBon} a été créer automatiquement par {myuser} , Veuillez valider',
                            description=f'/stock/Edit-bontransfert/{bon_trans.id}',
                            level=1,
                        )
                     # Store the BonTransfert object in the dictionary
                     bon_trans_dict[key] = bon_trans



                 # Create or get the stock_dest
                 stock_dest, created = Stock.objects.get_or_create(
                     product=stock.product,
                     entrepot=currentEntrepot,
                     defaults={'quantity': 0}
                 )

                 # Create a new ProduitsEnBonTransfert entry
                 ProduitsEnBonTransfert.objects.create(
                     BonNo=bon_trans,
                     stock_dep=stock,
                     stock_arr=stock_dest,
                     quantity=int(data["quantity"]),
                 )
                 
                               
        for product in dataInvoice["produits"]:      
            entrepot_inst = currentEntrepot
            if product["ent"] != entrepot_inst.name:
                entrepot_inst = Entrepot.objects.get(name = product["ent"], store = CurrentStore)      
            p = Stock.objects.select_for_update().get( Q(product__reference=product["ref"]) & Q(entrepot__name=entrepot_inst))
            stock_exists = False
            for item in List_data_transfert:
                if item['stock_dep'] == p:
                    stock_exists = True
                    break
            if not stock_exists:    
                new_quantity = p.quantity - int(product["qty"]) ## la quantité dans l'entrepot qui convient
                if new_quantity < 0:
                    # If any product has insufficient quantity, return a response to inform the user
                    return JsonResponse({'error': f"Insufficient1 stock for product: {product['ref']}", 'prompt_user': True})            
        current_year = timezone.now().year
        current_month = datetime.now().strftime('%m')
        boncomptoirs_this_year = models.BonSortie.objects.filter(dateBon__year=current_year, store = CurrentStore )

        # Get the count of BonComptoir instances in the current year
        sequential_number = boncomptoirs_this_year.count() + 1
        while True:
            # Generate the boncomptoire_code
            if self.request.session["store"] == '1':
                boncomptoire_code = f'BL{str(current_year)[-2:]}{str(current_month)}/{str(sequential_number).zfill(5)}'
            else:
                boncomptoire_code = f'BL{str(current_year)[-2:]}{str(current_month)}-{str(sequential_number).zfill(5)}'
        
            # Check if the boncomptoire_code already exists in the database
            existing_bon = models.BonSortie.objects.filter(idBon=boncomptoire_code, store=CurrentStore).first()
        
            if existing_bon is None:
                # If the boncomptoire_code is unique, break out of the loop
                break
        
            # If the boncomptoire_code already exists, increment the sequential_number and try again
            sequential_number += 1 
        bon_sortie = models.BonSortie.objects.create(
            idBon=boncomptoire_code,
            dateBon=dateBon,
            agenceLivraison=agenceLivraison,
            fraisLivraison = fraisLivraison,
            fraisLivraisonexterne = fraislivraisonext,
            mode_reglement = modereg,
            banque_Reglement = banque,
            num_cheque_reglement = num_cheque,
            typebl= "KIT",
            confirmed = False,
            Remise = remise,
            entrepot=currentEntrepot, 
            client=client, user=myuser, store=CurrentStore)
        
        if dataInvoice["creationAutomatique"]:
            models.DemandeTransfert.objects.create(
                BonSNo = bon_sortie,
                BonTransfert = bon_trans,
                etat='False'
            )
                  
        for product in dataInvoice["produits"]:
                entrepot_inst = currentEntrepot
                pr = Product.objects.get(reference=product["ref"], store = CurrentStore)
                if product["ent"] == currentEntrepot.name:
                    s = Stock.objects.get(product = pr, entrepot = currentEntrepot )
                    new_quantity = s.quantity - int(product["qty"]) ## la quantité dans l'entrepot qui convient
                    s.quantity = new_quantity
                    s.save()
                prod_total_price = float(product["rateLiv"]) * int(product["qty"])    
                if product["ent"] != entrepot_inst.name:
                    entrepot_inst = Entrepot.objects.get(name = product["ent"], store = CurrentStore)
                models.ProduitsEnBonSortie.objects.create(
                    BonNo=bon_sortie,
                    stock=pr,
                    entrepot=entrepot_inst, 
                    kit = product["kit"],                 
                    quantity=int(product["qty"]),
                    unitprice= float(product["rateLiv"]),
                    totalprice=prod_total_price
                )
                
        if not dataInvoice["creationAutomatique"]:        
            responsable_entrepot = CustomUser.objects.filter(role ="manager")
            if responsable_entrepot:
                for resp in responsable_entrepot : 
                        notify.send(
                            sender=myuser,
                            recipient=resp,
                            verb=f'Bon de Livraison numero {idBon} a été créer  par {myuser} , Veuillez valider',
                            description=f'/ventes/edit-bill-diva/{bon_sortie.id}',
                            level=1,
                        )
                
        return JsonResponse({'message': "Bill Added successfully.", 'code': boncomptoire_code})

class StockSellDIVAKitUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/invoice_billd_kit_edit.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bonlivraison' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        bill_id = self.kwargs.get('bill_id')
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        try:
            bill_id = kwargs['bill_id']
            invoice = models.BonSortie.objects.get(id=bill_id)
            # rest of your code
        except models.BonSortie.DoesNotExist:
            raise Http404(f"Bon {bill_id} n'existe Pas")
        except ValueError as e:
            # Log the error along with additional information like user details
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in get_context_data: {e}, User: {self.request.user}, Bill ID: {bill_id}")
            # re-raise the error to maintain the normal flow
            raise
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        if myuser.role != 'manager' and myuser.role != 'DIRECTEUR EXECUTIF' and myuser.username != 'younes_facturation' and not invoice.modifiable:
            raise PermissionDenied("Vous avez pas la permission d'accéder au.")
       
        idBon = invoice.idBon
        dateBon = invoice.dateBon.strftime('%d/%m/%Y')
        client_name = invoice.client.name
        client_address = invoice.client.adresse
        client_phone = invoice.client.phone
        client_solde = float(invoice.client.remaining_amount),
        clients = Client.objects.filter(store=CurrentStore, valide= True)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        
        context["clients"]=clients    
        products_enBon = invoice.produits_en_bon_sorties.all()
        entrepots = Entrepot.objects.filter(store= CurrentStore)
        context["entrepots"]=entrepots    
        modeReg = ModeReglement.objects.filter(store= CurrentStore) 
        context["modeReg"]=modeReg  
        echeances = EcheanceReglement.objects.filter(store= CurrentStore)
        context["echeances"] = echeances 
        banques= Banque.objects.filter(store= CurrentStore)
        context["banques"] = banques
        items=[]
        for product in products_enBon:
             produit_dict={
               "produit_ref" :product.stock.reference,
               "produit_name" :product.stock.name,
               "kit": product.kit,
               "produit_qty":product.quantity,
               "produit_tva": float(product.stock.tva),
               "produit_tax": float(product.stock.tva_douan),
               "produit_livraison": float(product.stock.prix_livraison),
               "produit_unitprice": float(product.unitprice) if product.unitprice is not None else None,                    
               "produit_freeprice": float(product.unitprice) - float(product.stock.prix_livraison),                    
              }
             items.append(produit_dict)
          
        context["bill"] = invoice

        context["items"]=items
        if(myuser.role =='manager'):
          bons_retour = BonRetour.objects.filter(store=CurrentStore)
        else:    
          bons_retour = BonRetour.objects.filter(store=CurrentStore, user = myuser)
        context["bons_commandes"]= bons_retour
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        context["selected_store"] = selected_store    
        store_id = self.request.session["store"]
        my_store = store.objects.get(pk=store_id)
     
        entrepots = Entrepot.objects.filter(store=my_store)
          # Step 3: Get all the stocks associated with each Entrepot
        all_stocks = []
        for entrepot in entrepots:
            stocks_for_entrepot = entrepot.get_stocks()
            all_stocks.extend(stocks_for_entrepot)
        my_entrepot = invoice.entrepot
        stocks = my_entrepot.get_stocks()
        stock_data=[]
        type_client = invoice.client.categorie_client.id
        for stock in stocks:
                product_name = stock.product.name
                entrepot_name = stock.entrepot.name
                
                if myuser.role == 'manager':
                    quantity = stock.get_quantity
                else:
                    quantity = stock.get_quantity
                price = stock.product.get_price_per_type(type_client, 'kit')
                reference = stock.product.reference
                entrepot= stock.entrepot.name
                categorie=stock.product.category.pc_component if stock.product.category is not None else ""
                if price != 0 :
                    stock_info = {
                        "product_name": product_name,
                        "entrepot_name": entrepot_name,
                        "quantity": quantity,
                        "reference": reference,
                        "entrepot":entrepot,
                        "categorie":categorie,
                        "price": float(price),
                        "prix_livraison": float(stock.product.prix_livraison),
                        "tax": float(stock.product.tva_douan),
                    }
                    stock_data.append(stock_info)
        types_client = typeClient.objects.filter(store = CurrentStore)      
        typescl_info = []
        for t in types_client:
            typescl_info.append({
                'label': t.type_desc,
                'percent': t.percent
            })  
        context["typespercents"] = typescl_info      
        context["stocks"] = stock_data
        categories= Category.objects.filter(store= selected_store, kit = True)
        context["categories"] = categories
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        data = data.get('formData', '')
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        try:
             with transaction.atomic():
                # Get the existing BonComptoir instance
                idbon = data["IdBon"]
                bon_comptoir = models.BonSortie.objects.select_for_update().get(id=data["id"])
                # Handle stock updates for deleted entries
                for produit in bon_comptoir.produits_en_bon_sorties.all():
                    myentrepot = Entrepot.objects.get(name = data["entrepotBon"], store = CurrentStore)
                    try:
                        stock_entry = Stock.objects.get(product=produit.stock, entrepot=myentrepot)
                        # If it exists, update the quantity
                        stock_entry.quantity += produit.quantity
                        
                    except Stock.DoesNotExist:
                        # If it doesn't exist, create a new stock entry
                        stock_entry = Stock.objects.create(product=produit.stock, entrepot=myentrepot, quantity=produit.quantity)
                    stock_entry.save()
                    produit.delete()
                
                fraisLivraison = bon_comptoir.fraisLivraison,                  
                fraisLivraison = 0
                if data['fraislivraison'] :
                    fraisLivraison = data['fraislivraison']
                if self.request.session["store"] == '6' :    
                    if bon_comptoir.dateBon != data["dateBp"]:
                        bon_comptoir.dateBon = data["dateBp"]
                        bon_comptoir.save()    
  
                bon_comptoir.idBon = idbon
                bon_comptoir.fraisLivraison = fraisLivraison 

                client_name = data["clientInfo"]["name"]
                client_instance = Client.objects.filter(name=client_name, store = CurrentStore).first()
                bon_comptoir.client = client_instance
                bon_comptoir.Remise = float(data.get('remise', bon_comptoir.Remise))
                myentrepot = Entrepot.objects.get(name = data["entrepotBon"], store = CurrentStore)
                bon_comptoir.entrepot= myentrepot
                # Save the updated BonComptoir
                for product in data["produits"]:            
                    p = Stock.objects.get( Q(product__reference=product["ref"]) & Q(entrepot=myentrepot))
                    new_quantity = p.quantity - int(product["qty"]) ## la quantité dans l'entrepot qui convient
                    if new_quantity < 0:
                         # If any product has insufficient quantity, return a response to inform the user
                        return JsonResponse({'error': f"Stock Insuffisant pour  : {product['name']}", 'prompt_user': True})            
                bon_comptoir.etat_reglement = data["obs"]    
                bon_comptoir.modifiable=False    
                bon_comptoir.valide=False    
                bon_comptoir.save()
                    
                for produit in data["produits"]:
                    p = Stock.objects.get( Q(product__reference=produit["ref"]) & Q(entrepot=myentrepot))
                    new_quantity = p.quantity - int(produit["qty"]) ## la quantité dans l'entrepot qui convient
                    p.quantity = new_quantity
                    p.save() 
                    produit_inst = Product.objects.get(reference=produit["ref"], store = CurrentStore)
                    qty = int(produit['qty'])
                    rate = float(produit['rateLiv'])
                    total = int(qty) * float(rate)
                    models.ProduitsEnBonSortie.objects.create(
                        BonNo = bon_comptoir,
                        stock = produit_inst,
                        quantity = qty,
                        unitprice = rate,
                        totalprice =total
                    )
                myuser=CustomUser.objects.get(username=self.request.user.username)
                responsable_entrepot = CustomUser.objects.filter(role ="manager")
                if responsable_entrepot:
                 for resp in responsable_entrepot : 
                        notify.send(
                            sender=myuser,
                            recipient=resp,
                            verb=f'Bon de Livraison numero {bon_comptoir.idBon} a été Modifié  par {myuser} , Veuillez valider',
                            description=f'/ventes/edit-bill-diva/{bon_comptoir.id}',
                            level=1,
                        )        
        except models.BonSortie.DoesNotExist:
            return JsonResponse({'error': "Bon Livraison not found.", 'prompt_user': False})    
        
        return JsonResponse({'success': "Bon Livraison modifié.", 'prompt_user': False})
        
class StockSellUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "ventes/invoice_bill_update.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bonlivraison' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  
        
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        bill_id=self.kwargs.get('bill_id')
    
        invoice = models.BonSortie.objects.get(id=bill_id)
        idBon = invoice.idBon
        dateBon = invoice.dateBon
        totalPrice=invoice.totalPrice
        client_name= invoice.client.name
        client_address = invoice.client.adresse
        client_phone= invoice.client.phone
        products_enBon = invoice.get_produits()
        items=[]
        for product in products_enBon:
            produit_dict={
               "produit_ref" :product.stock.reference,
               "produit_name" :product.stock.name,
               "produit_category" :product.stock.category.Libellé,
               "produit_qty":int(product.quantity),
               "produit_unitPrice" : float(product.unitprice),
               "prdouit_totalPrice":float(product.totalprice)            
              }
            items.append(produit_dict)
          
        context["idBon"] = idBon
        context["dateBon"] = dateBon
        context["totalPrice"] = totalPrice
        context["client_name"]= client_name
        context["client_address"]= client_address
        context["client_phone"] = client_phone
        context["bill"]=invoice
        context["items"]=items

        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        context["selected_store"] = selected_store    
        store_id = self.request.session["store"]
        my_store = store.objects.get(pk=store_id)
     
        entrepots = Entrepot.objects.filter(store=my_store)
          # Step 3: Get all the stocks associated with each Entrepot
        all_stocks = []
        for entrepot in entrepots:
            stocks_for_entrepot = entrepot.get_stocks()
            all_stocks.extend(stocks_for_entrepot)
        context["entrepots"] = entrepots
        context["stock"] = all_stocks
        
        entrepots = Entrepot.objects.filter(store= selected_store)
        context["entrepots"]=entrepots    
        modeReg = ModeReglement.objects.filter(store= selected_store) 
        context["modeReg"]=modeReg  
        echeances = EcheanceReglement.objects.filter(store= selected_store)
        context["echeances"] = echeances 
        banques= Banque.objects.filter(store= selected_store)
        context["banques"] = banques
        categories= Category.objects.filter(store= selected_store)
        context["categories"] = categories
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
      
      data = json.loads(request.body)
      dataInvoice = data.get('formData', '')
      Currentuser = request.user
      myuser  = CustomUser.objects.get(username=Currentuser.username)
      if dataInvoice:
         try:
            id_bon = dataInvoice["IdBon"]
            date_bon = dataInvoice["dateBp"]
            total = dataInvoice['total']

            client_info = dataInvoice['clientInfo']
            client_name = client_info['name']
            client_address = client_info['address']
            client_phone = client_info['phone']

            # Assuming you have a model named 'BonSortie' to represent sell bills
            from .models import BonSortie, Client, Stock, ProduitsEnBonSortie

            try:
                # Get the existing sell bill from the database based on ID (IdBon)
                bon_sortie = BonSortie.objects.get(idBon=id_bon)

                # Update the sell bill fields
                bon_sortie.dateBon = date_bon
                bon_sortie.totalPrice = total

                # Get or create the client
                client, _ = Client.objects.get_or_create(name=client_name, adresse=client_address, phone=client_phone, user=myuser)
                bon_sortie.client = client

                # Process and update the products
                products_to_update = []

                for product in dataInvoice["produits"]:
                    stock = Stock.objects.select_for_update().get(product__reference=product["ref"])
                    new_quantity = stock.quantity - int(product["qty"])
                    if new_quantity < 0:
                        return JsonResponse({'error': f"Insufficient stock for product: {product['ref']}", 'prompt_user': True})

                    products_to_update.append((stock, new_quantity))

                with transaction.atomic():
                    for stock, new_quantity in products_to_update:
                        stock.quantity = new_quantity
                        stock.save()

                    # Delete existing products from the sell bill
                    ProduitsEnBonSortie.objects.filter(BonNo=bon_sortie).delete()

                    # Create new products for the updated sell bill
                    for product in dataInvoice["produits"]:
                        stock = Stock.objects.get(product__reference=product["ref"])
                        prod_total_price = stock.product.prix_vente * int(product["qty"])
                        ProduitsEnBonSortie.objects.create(
                            BonNo=bon_sortie,
                            stock=stock.product,
                            quantity=int(product["qty"]),
                            unitprice=stock.product.prix_vente,
                            totalprice=prod_total_price
                        )

                return JsonResponse({'message': 'Sell bill updated successfully.'}, status=200)

            except BonSortie.DoesNotExist:
                return JsonResponse({'error': 'Sell bill not found.'})

         except Exception as e:
            return JsonResponse({'error': str(e)})
      return JsonResponse({'message': "Product Added successfully."})
import requests
# class BonLivrison_gamingzone(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
#         template_name = "ventes/bonlivrison_gamingzone.html"
#     login_url = 'home' 
#     raise_exception = True  # Set to True to raise a PermissionDenied exception

#     def test_func(self):
#         # Define the custom test function
#         myuser=CustomUser.objects.get(username=self.request.user.username)
#         return 'ventes.can_see_bonlivraison' in self.request.session.get('permissions', [])

#     def handle_no_permission(self):
#          # Redirect users without permission to the "noaccess" page
#         return HttpResponseRedirect(reverse_lazy('noaccess'))  
        
#     def get_context_data(self, *args, **kwargs):
#         context = super().get_context_data(**kwargs)       
#         # store_id = self.kwargs.get('store_id')
#         selected_store = get_object_or_404(store, pk=self.request.session["store"])
        
#         Currentuser = self.request.user
#         myuser  = CustomUser.objects.get(username=Currentuser.username)
#         current_month = datetime.now().month
#         if(myuser.role =='manager') or (myuser.role == 'Finance') or (myuser.role=='DIRECTEUR EXECUTIF') :
#             today = datetime.today()
#             first_day_current_month = today.replace(day=1)
#             # Get the first day of the past month
#             first_day_past_month = (first_day_current_month - timedelta(days=1)).replace(day=1)
            
#             # Filter objects with dateBon greater than or equal to the first day of the past month
#             bons_sorties = models.BonSortie.objects.filter(
#                 store=selected_store
#             ).exclude(
#                 Q(typebl="KIT") | Q(typebl="carton")
#             ).order_by('-id')
            
#             context["bons_sorties"] = bons_sorties
#         elif myuser.role=='gestion-stock':
#             bons_sorties = models.BonSortie.objects.filter(
#                 store=selected_store,
#                 valide = True,
#                 reference_pc__exact='',
#                 entrepot__name ="Depot principal Reghaia"
#             ).exclude(client__name="Annulé --- Annulé").filter(Q(bon_garantie__isnull=True)).exclude(Q(typebl="KIT") | Q(typebl="carton")).order_by('-id')  # Sort by date in descending order
#             context["bons_sorties"] = bons_sorties
            
#         else:
#           bons_sorties = models.BonSortie.objects.filter(store=selected_store, user=myuser).exclude(Q(typebl="KIT") | Q(typebl="carton")).order_by('-id')     
#           context["bons_sorties"] =bons_sorties
#         entrepots = Entrepot.objects.filter(store=selected_store)
#         context["entrepots"] = entrepots
#         users_bills = CustomUser.objects.filter(EmployeeAt=selected_store)
#         context["users"]=users_bills
#         modeReg = ModeReglement.objects.filter(store= selected_store) 
#         context["modeReg"]=modeReg  
#         echeances = EcheanceReglement.objects.filter(store= selected_store)
#         context["echeances"] = echeances 
#         banques= Banque.objects.filter(store= selected_store)
#         context["banques"] = banques
#         return context 
    

    
    