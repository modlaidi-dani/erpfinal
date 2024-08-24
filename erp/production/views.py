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
from inventory.models import Entrepot, Stock, BonTransfert, ProduitsEnBonTransfert
from clientInfo.models import store,typeClient
from tiers.models import Client, Banque
from produits.models import Product, Category,variantsPrixClient
from reglements.models import ModeReglement, EcheanceReglement
from comptoire.models import BonComptoire, ProduitsEnBonComptoir, BonRetourComptoir, ProduitsEnBonRetourComptoir
from django.db.models import Count
import ast

def getStock(request):
   data = json.loads(request.body)
   my_entrepot = Entrepot.objects.get(name=data["nomEnt"])
   stocks = my_entrepot.get_stocks()
   stock_data=[]
   for stock in stocks:
        product_name = stock.product.name
        entrepot_name = stock.entrepot.name
        quantity = stock.quantity
        price = stock.product.prix_vente
        reference = stock.product.reference
        entrepot=stock.entrepot.name
        categorie=stock.product.category.pc_component if stock.product.category is not None else ''


        stock_info = {
            "product_name": product_name,
            "entrepot_name": entrepot_name,
            "quantity": quantity,
            "reference": reference,
            "entrepot":entrepot,
            "categorie":categorie,
            "price": stock.product.prix_achat,
        }
        stock_data.append(stock_info)
   return JsonResponse({'stocks':stock_data})

def deleteOrdres(request):
    data = json.loads(request.body)
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    liste_id = data["liste_ids"]
    for id_bon in liste_id:
        bon_c = models.ordreFabrication.objects.get(codeOrdre=id_bon, store=CurrentStore)
        with transaction.atomic():
                # Get the associated product transfers
                produits_transfert = models.ProduitsEnOrdreFabrication.objects.filter(BonNo=bon_c)
                my_entrepot = Entrepot.objects.get(name=bon_c.entrepot_destocker, store=CurrentStore)           
                # Iterate over the product transfers and update stock quantities
                for produit_transfert in produits_transfert:                
                    mon_stock = Stock.objects.get(entrepot=my_entrepot, product=produit_transfert.stock)
                    quantity = produit_transfert.quantity               
                    # Update the source warehouse stock quantity
                    mon_stock.quantity += quantity                
                    mon_stock.save()
                
                    produit_transfert.delete()
                bon_c.pc_created.delete()
                bon_c.delete()
    return JsonResponse({'message': "Eléments Supprimé !"})   

class OrdresFabricationPage(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "production/ordre_fabrications_page.html"
    login_url = 'home' 
    raise_exception = True  

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'ventes.can_see_bongarantie' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)       
        # store_id = self.kwargs.get('store_id')
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        bons_sorties = models.ordreFabrication.objects.filter(store=selected_store)


        context["bons_sorties"] = bons_sorties
        entrepots = Entrepot.objects.filter(store=selected_store)
        context["entrepots"] = entrepots
        users_bills = CustomUser.objects.filter(EmployeeAt=selected_store)
        context["users"]=users_bills
        return context
 
class OrdresFabricationNew(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "production/ordre_fabrication.html"  
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
               
        entrepots = Entrepot.objects.filter(store= selected_store)
        context["entrepots"]=entrepots    

        categories= Category.objects.filter(store= selected_store)

        context["categories"] = categories
        clients = typeClient.objects.filter(store=CurrentStore)
        types_clients =[]
        for cl in clients:
           cl_dict ={
              "nom":cl.type_desc
           }
           types_clients.append(cl_dict)
        context["type_clients"]=types_clients
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
        currentEntrepot = Entrepot.objects.get(name=dataInvoice["entrepot_des"])   
        stockEntrepot =  Entrepot.objects.get(name=dataInvoice["entrepot_stock"])   
        for product in dataInvoice["produits"]:            
                p = Stock.objects.select_for_update().get( Q(product__reference=product["ref"]) & Q(entrepot__name=currentEntrepot))
                new_quantity = p.quantity - int(product["qty"]) ## la quantité dans l'entrepot qui convient
                if new_quantity < 0:
                    # If any product has insufficient quantity, return a response to inform the user
                    return JsonResponse({'error': f"Insufficient stock for product: {product['ref']}", 'prompt_user': True})            
                p.quantity = new_quantity
                p.save()
                
        category= None
        if Category.objects.get(id = dataInvoice['category'], store = CurrentStore) :
          category =Category.objects.get(id = dataInvoice['category'], store = CurrentStore)
          
        existing_product = Product.objects.filter(reference=dataInvoice['reference'], store=CurrentStore).first()
        if existing_product:
            return JsonResponse({'error': 'Il existe déja un produit avec cette Référence !.'})
  
        product_instance = Product.objects.create(
            reference=dataInvoice['reference'],
            name=dataInvoice['designation'],
            fournisseur=dataInvoice['fournisseur'],
            prix_vente=dataInvoice['prixVenteHt'],
            prix_achat=dataInvoice['prixAchatHt'],
            prix_livraison= dataInvoice['frais_livraison'],
            category = category,
            marge= max(float(dataInvoice['marge']), 0),
            initial_qte=0,  # You can set this value
            TotalQte=0,     # You can set this value
            tva= dataInvoice['tva'],
            store= CurrentStore
        )
       
        if dataInvoice['clients_price']:
         for client_price in dataInvoice['clients_price']:
           type_client_name = client_price['nom']
           prix_vente = client_price['prixHt']  
           type_client, created = typeClient.objects.get_or_create(type_desc=type_client_name, store=CurrentStore)
           variant_price_client = variantsPrixClient.objects.create(
             type_client=type_client,
             produit=product_instance,
             prix_vente=prix_vente
           )
        product_stock = Stock.objects.create(
                    product=product_instance,
                    entrepot=stockEntrepot,
                    quantity = dataInvoice['quantity']
                )
        product_stock.quantity = dataInvoice['quantity']
        product_stock.save()
        
        current_year = datetime.now().strftime('%y')
        current_month = datetime.now().strftime('%m')
        last_bon = models.ordreFabrication.objects.order_by('-id').first()
        if last_bon:
            last_id = last_bon.id
            if last_id:
                sequence_number = int(last_id) + 1
            else:
                sequence_number = 1
        else:
            sequence_number = 1

        codeBon = f'OF{current_year}{current_month}-{sequence_number}' 
        ordre_fabrication_instance = models.ordreFabrication.objects.create(
            entrepot_destocker=currentEntrepot,
            entrepot_stocker=stockEntrepot,
            pc_created=product_instance,
            store=CurrentStore,
            codeOrdre=codeBon
        )
        
        for product in dataInvoice["produits"]:
                        p = Product.objects.get(reference=product["ref"], store = CurrentStore)
                        models.ProduitsEnOrdreFabrication.objects.create(
                            BonNo=ordre_fabrication_instance,
                            stock=p,
                            quantity=int(product["qty"]),
                        )

        
        return JsonResponse({'message': "Nouveau Produit Configuration a été Créer!."})   
    
class EditordreFabrication(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "production/ordre_fabrication_edit.html"  
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
        bill_id = self.kwargs.get('ordre_id')
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        invoice = models.ordreFabrication.objects.get(id=bill_id)
        context["ordre"] = invoice   
            
        entrepots = Entrepot.objects.filter(store= CurrentStore)
        context["entrepots"]=entrepots    
        
        categories= Category.objects.filter(store= CurrentStore)
        context["categories"] = categories
        
        clients = typeClient.objects.filter(store=CurrentStore)
        types_clients =[]
        for cl in clients:
            cl_dict = {
              "nom":cl.type_desc
            }
            types_clients.append(cl_dict)
        context["type_clients"]=types_clients
        
        variants_prix_data = []
        for variant in invoice.pc_created.produit_var.all():
            type_client = variant.type_client.type_desc
            prix_vente = variant.prix_vente

            variants_prix_data.append({
                "type_client": type_client,
                "prix_vente": float(prix_vente),
            }) 
        context["variants_prix_data"] = variants_prix_data
        items=[]
        for product in invoice.produits_en_ordre_fabrication.all():
             produit_dict={
               "ref" :product.stock.reference,
               "name" :product.stock.name,
               "qty":product.quantity,
               "price": float(product.stock.prix_achat) if product.stock.prix_achat is not None else 0.00,                    
              }
             items.append(produit_dict)
        context["items"]=items
        my_entrepot = invoice.entrepot_destocker
        stocks = my_entrepot.get_stocks()
        stock_data=[]
        for stock in stocks:
            product_name = stock.product.name
            entrepot_name = stock.entrepot.name
            quantity = stock.quantity
            price = stock.product.prix_vente
            reference = stock.product.reference
            entrepot=stock.entrepot.name
            categorie=stock.product.category.pc_component
            stock_info = {
                "product_name": product_name,
                "entrepot_name": entrepot_name,
                "quantity": quantity,
                "reference": reference,
                "entrepot":entrepot,
                "categorie":categorie,
                "price": float(stock.product.prix_achat),
            }
            stock_data.append(stock_info)
        context["stocks"] = stock_data    
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
        currentEntrepot = Entrepot.objects.get(name=dataInvoice["entrepot_des"])   
        stockEntrepot =  Entrepot.objects.get(name=dataInvoice["entrepot_stock"])   
        for product in dataInvoice["produits"]:            
                p = Stock.objects.select_for_update().get( Q(product__reference=product["ref"]) & Q(entrepot__name=currentEntrepot))
                new_quantity = p.quantity - int(product["qty"]) ## la quantité dans l'entrepot qui convient
                if new_quantity < 0:
                    # If any product has insufficient quantity, return a response to inform the user
                    return JsonResponse({'error': f"Insufficient stock for product: {product['ref']}", 'prompt_user': True})            
                p.quantity = new_quantity
                p.save()
                
        category= None
        if Category.objects.get(id = dataInvoice['category'], store = CurrentStore) :
          category =Category.objects.get(id = dataInvoice['category'], store = CurrentStore)
          
        existing_product = Product.objects.filter(reference=dataInvoice['reference'], store=CurrentStore).first()
        if existing_product:
            return JsonResponse({'error': 'Il existe déja un produit avec cette Référence !.'})
  
        product_instance = Product.objects.create(
            reference=dataInvoice['reference'],
            name=dataInvoice['designation'],
            fournisseur=dataInvoice['fournisseur'],
            prix_vente=dataInvoice['prixVenteHt'],
            prix_achat=dataInvoice['prixAchatHt'],
            prix_livraison= dataInvoice['frais_livraison'],
            category = category,
            marge= max(float(dataInvoice['marge']), 0),
            initial_qte=0,  # You can set this value
            TotalQte=0,     # You can set this value
            tva= dataInvoice['tva'],
            store= CurrentStore
        )
       
        if dataInvoice['clients_price']:
         for client_price in dataInvoice['clients_price']:
           type_client_name = client_price['nom']
           prix_vente = client_price['prixHt']  
           type_client, created = typeClient.objects.get_or_create(type_desc=type_client_name, store=CurrentStore)
           variant_price_client = variantsPrixClient.objects.create(
             type_client=type_client,
             produit=product_instance,
             prix_vente=prix_vente
           )
        product_stock = Stock.objects.create(
                    product=product_instance,
                    entrepot=stockEntrepot,
                    quantity = dataInvoice['quantity']
                )
        product_stock.quantity = dataInvoice['quantity']
        product_stock.save()
        
        current_year = datetime.now().strftime('%y')
        current_month = datetime.now().strftime('%m')
        last_bon = models.ordreFabrication.objects.order_by('-id').first()
        if last_bon:
            last_id = last_bon.id
            if last_id.isnumeric():
                sequence_number = int(last_id) + 1
            else:
                sequence_number = 1
        else:
            sequence_number = 1

        codeBon = f'OF{current_year}{current_month}-{sequence_number}' 
        ordre_fabrication_instance = models.ordreFabrication.objects.create(
            entrepot_destocker=currentEntrepot,
            entrepot_stocker=stockEntrepot,
            pc_created=product_instance,
            store=CurrentStore,
            codeOrdre=codeBon
        )
        
        for product in dataInvoice["produits"]:
                        p = Product.objects.get(reference=product["ref"], store = CurrentStore)
                        models.ProduitsEnOrdreFabrication.objects.create(
                            BonNo=ordre_fabrication_instance,
                            stock=p,
                            quantity=int(product["qty"]),
                        )

        
        return JsonResponse({'message': "Nouveau Produit Configuration a été Créer!."})   
