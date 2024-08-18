from django.shortcuts import render
from django.views.generic.base import TemplateView
from django.http import Http404, JsonResponse
import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from . import models
from clientInfo.models import store
from users.models import CustomUser
import plotly.express as px
import plotly.graph_objs as go
import plotly
import numpy as np
import plotly.graph_objs as go
import plotly.express as px
from plotly.subplots import make_subplots
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime
from django.shortcuts import redirect
from inventory.models import Entrepot
from tiers.models import Fournisseur,typeClient
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from .models import ProduitsCustomPermission
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from decimal import Decimal
from inventory.models import Stock
from django.db import transaction
from ventes.models import ProduitsEnBonSortie
from django.db.models import Count
from achats.models import ProduitsEnBonAchat, BonAchat
from inventory.models import ProduitsEnBonReintegration, ProduitsEnBonEntry, ProduitsEnBonRetour
from django.db.models import Sum
from django.db.models.functions import Lower

def FilltheProductHistory(request):
    with open('jsonHistoryP.json', 'r') as f:
        dataList = json.load(f) 
    for product in dataList:
        if product["id"] :
            productIns = models.Product.objects.get(id = product["id"])
            achats = product["achats"]  
            for achat_pr in achats:
                prix_achat_calcule = ((achat_pr["priceAchatAct"] * achat_pr["qtyActual"]) + (achat_pr["priceachat"] * achat_pr["quantityachat"])) / (achat_pr["quantityachat"] + achat_pr["qtyActual"])
                models.HistoriqueAchatProduit.objects.create(
                    produit=productIns,  
                    qty_qctuelle=achat_pr["qtyActual"],
                    prix_achat_actuelle=achat_pr["priceAchatAct"],
                    qty_achete=achat_pr["quantityachat"],
                    prix_achat=achat_pr["priceachat"],
                    prix_achat_calcule=prix_achat_calcule, 
                    dateAchat=achat_pr["dateAchat"],
                )        
    return JsonResponse({'message':'Historique Produits Importé!'}) 
    
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
        stock_info = {
            "product_name": product_name,
            "entrepot_name": entrepot_name,
            "quantity": quantity,
            "reference": reference,
            "entrepot":entrepot,
            "price": price,
        }
        stock_data.append(stock_info)
   return JsonResponse({'stocks':stock_data})
   
def GetProductHistorique(request):
    store_id = request.session["store"]
    current_store = store.objects.get(pk=store_id)
    products = models.Product.objects.filter(store = current_store)  # Get all products from the database
    stock_data = []
    for product in products:
        bill_data = []
        previousAchat = None
        previous_priceAchat = product.prix_achat
        initialQty = product.Totalquantity_initial
        for bon_achat in BonAchat.objects.filter(produits_en_bon_achat__produit=product):
            if previousAchat is None: 
                purchased_product = bon_achat.produits_en_bon_achat.get(produit=product)

                # Calculate remaining quantity for each purchase
                bons_achat_before = BonAchat.objects.filter(dateBon__lt=bon_achat.dateBon)
                purchased_quantity = bons_achat_before.filter(produits_en_bon_achat__produit=product).aggregate(
                    total_purchased=Sum('produits_en_bon_achat__quantity'))['total_purchased'] or 0

                bons_sortie = ProduitsEnBonSortie.objects.filter(stock=product, BonNo__dateBon__lt=bon_achat.dateBon)
                sold_quantity_before = bons_sortie.aggregate(total_sold=Sum('quantity'))['total_sold'] or 0
                
                bons_sortie = ProduitsEnBonSortie.objects.filter(stock=product, BonNo__dateBon__lt=bon_achat.dateBon)
                sold_quantity_before = bons_sortie.aggregate(total_sold=Sum('quantity'))['total_sold'] or 0

                bons_reintegration = ProduitsEnBonRetour.objects.filter(produit=product, reintegrated = True, BonNo__dateBon__lt=bon_achat.dateBon)
                returned_quantity_before = bons_reintegration.aggregate(total_returned=Sum('quantity'))['total_returned'] or 0
                
                bon_entries = ProduitsEnBonEntry.objects.filter(stock=product, BonNo__dateBon__lt=bon_achat.dateBon)
                entered_quantity_before = bon_entries.aggregate(total_entered=Sum('quantity'))['total_entered'] or 0
                remaining_quantity = initialQty + returned_quantity_before + entered_quantity_before - sold_quantity_before
                

                bill_data.append({
                    'dateAchat': bon_achat.dateBon.strftime('%Y-%m-%d'),
                    'qutyentered': entered_quantity_before,
                    'soldqTY': sold_quantity_before,
                    'returned': returned_quantity_before,
                    'qtyActual': remaining_quantity,
                    'initialQty': initialQty,
                    'priceAchatAct': float(previous_priceAchat),
                    'quantityachat': purchased_product.quantity,
                    'priceachat': float(purchased_product.prixUnitaire),
                })
                previousAchat = bon_achat
                previous_priceAchat = float(purchased_product.prixUnitaire)
                initialQty = remaining_quantity
            else:
                purchased_product = bon_achat.produits_en_bon_achat.get(produit=product)

                # Calculate remaining quantity for each purchase
                bons_achat_before = BonAchat.objects.filter(
                    dateBon__gt=previousAchat.dateBon,
                    dateBon__lt=bon_achat.dateBon
                )
                purchased_quantity = bons_achat_before.filter(produits_en_bon_achat__produit=product).aggregate(
                    total_purchased=Sum('produits_en_bon_achat__quantity'))['total_purchased'] or 0

                bons_sortie = ProduitsEnBonSortie.objects.filter(
                    stock=product,
                    BonNo__dateBon__gt=previousAchat.dateBon,
                    BonNo__dateBon__lt=bon_achat.dateBon                
                )
                
                sold_quantity_before = bons_sortie.aggregate(total_sold=Sum('quantity'))['total_sold'] or 0                
                bons_sortie = ProduitsEnBonSortie.objects.filter(stock=product, BonNo__dateBon__gte=previousAchat.dateBon, BonNo__dateBon__lt=bon_achat.dateBon)
                sold_quantity_before = bons_sortie.aggregate(total_sold=Sum('quantity'))['total_sold'] or 0

                bons_reintegration = ProduitsEnBonRetour.objects.filter(produit=product, reintegrated = True, BonNo__dateBon__gte=previousAchat.dateBon, BonNo__dateBon__lt=bon_achat.dateBon)
                returned_quantity_before = bons_reintegration.aggregate(total_returned=Sum('quantity'))['total_returned'] or 0
                
                bon_entries = ProduitsEnBonEntry.objects.filter(stock=product, BonNo__dateBon__gte=previousAchat.dateBon, BonNo__dateBon__lt=bon_achat.dateBon)
                entered_quantity_before = bon_entries.aggregate(total_entered=Sum('quantity'))['total_entered'] or 0
                remaining_quantity = initialQty + returned_quantity_before + entered_quantity_before - sold_quantity_before
                
                bill_data.append({
                    'dateAchat': bon_achat.dateBon.strftime('%Y-%m-%d'),
                    'qutyentered': entered_quantity_before,
                    'soldqTY': sold_quantity_before,
                    'returned': returned_quantity_before,
                    'qtyActual': remaining_quantity,
                    'initialQty': initialQty,
                    'priceAchatAct': float(previous_priceAchat),
                    'quantityachat': purchased_product.quantity,
                    'priceachat': float(purchased_product.prixUnitaire),
                })
                previousAchat = bon_achat
                previous_priceAchat = float(purchased_product.prixUnitaire)
                initialQty = remaining_quantity
        stock_data.append({
            'id': product.pk,
            'name': product.name,
            'reference': product.reference,
            'achats': bill_data,
            'firstPrice': float(product.prix_achat)
        })

    with open('jsonHistoryP.json', 'w') as f:
        json.dump(stock_data, f, indent=4)  # Write data to JSON file with indentation
    return JsonResponse({'message':'Historique Produits Importé!'})     

class EtatStockWeekly(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "produits/etat_stock_week.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'produits.can_see_produits' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
        # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('inventory'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        store_id = self.kwargs.get('store_id')
        selected_store = store.objects.get(pk=self.request.session["store"])
        products = models.Product.objects.filter(
            store=selected_store,
            parent_product__isnull=True,
            name__icontains='msi'
        ).annotate(
            name_lower=Lower('name')
        ).filter(
            name_lower__icontains='msi'
        )
        products_stock = []
        # Loop through each product and generate the weekly report
        for product in products:
            weekly_report = product.weekly_stock_report()
            products_stock.extend(weekly_report)
        context["stock"] = products_stock
        return context
        
class QuantiteFactureView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "produits/qtys_facture.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'produits.can_see_produits' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('inventory'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        store_id = self.kwargs.get('store_id')
        selected_store = store.objects.get(pk=self.request.session["store"])
        if self.request.session["store"] == '2' :
            products = models.Product.objects.filter(store=selected_store, parent_product__isnull= True)
        else:
            products = models.Product.objects.filter(store=selected_store, parent_product__isnull= True)[:150]
        product_families = models.Category.objects.filter(store=selected_store)
        context["product_families"]=product_families
        fournisseurs = Fournisseur.objects.filter(store=selected_store)
        context["product_fournisseur"] = fournisseurs
       
        # Extract specific fields from the queryset and create a list of dictionaries
        entrepots = Entrepot.objects.filter(store=selected_store)
        context["entrepots"]=entrepots
        context["stock"] = products
        return context
        
def ProductBlockView(request):
    data = json.loads(request.body)
    my_product = models.Product.objects.get(id=data['id'])
    store_id = request.session["store"]
    current_store = store.objects.get(pk=store_id)
    print(data)
    if data['qty'] == 0:
       my_product.reforme = False
    else:
       my_product.reforme = True
    entrepot_ins = Entrepot.objects.get(name = data['entrepot'], store = current_store )
    stock = Stock.objects.get(product = my_product, entrepot = entrepot_ins)
    stock.quantity_blocked = data['qty']
    stock.save()
    my_product.save()
    return JsonResponse({'message':'Produit Blocké!'})

def ImportProducts(request):
   data = json.loads(request.body)
   products_list = data["products"]
   store_id = request.session["store"]
   current_store = store.objects.get(pk=store_id)
   for prod_data in products_list:
      category = models.Category.objects.filter(Libellé = prod_data["family"], store = current_store).first()
      product_ins = models.Product.objects.filter(reference = prod_data['reference'], store = current_store).first()
      if product_ins is None :
          product = models.Product.objects.create(
                reference=prod_data['reference'],
                name=prod_data['name'],
                prix_vente=prod_data['prixVente'],
                prix_achat=prod_data['PrixAchat'],
                prix_livraison= prod_data['livraison'],
                category = category,
                initial_qte=0,  # You can set this value
                TotalQte=0,     # You can set this value
                tva= 19,
                tva_douan= prod_data['tax'],
                store= current_store
            ) 
          if "prixVente" in prod_data:
            type_client= typeClient.objects.get(type_desc='Client Final', store=current_store)
            variant_price_client = models.variantsPrixClient.objects.create(
                type_client=type_client,
                produit=product,
                prix_vente=prod_data["prixVente"]
            )
          if "prixVenteR" in prod_data:  
            type_client= typeClient.objects.get(type_desc='Revendeur', store=current_store)
            variant_price_client = models.variantsPrixClient.objects.create(
                type_client=type_client,
                produit=product,
                prix_vente=prod_data["prixVenteR"]
            )
          if "prixVenteRB" in prod_data:
            type_client= typeClient.objects.get(type_desc='Grossiste', store=current_store)
            variant_price_client = models.variantsPrixClient.objects.create(
                type_client=type_client,
                produit=product,
                prix_vente=prod_data["prixVenteRB"]
            )
          

   return JsonResponse({'message':'Produits Importé!'})
   
def UpdateRepartition(request):
    store_id = request.session["store"]
    current_store = store.objects.get(pk=store_id)  # Assuming 'store' is your Store model
    data = json.loads(request.body)
    dataInvoice = data.get('formData', '')
    if dataInvoice:       
        product_id = dataInvoice.get('id')
        if product_id:
            try:
                product_obj = models.Product.objects.get(pk=int(product_id), store=current_store)
                entrepot_name = dataInvoice.get('entrepot_rep')
                if entrepot_name :
                    entrepot_rep = Entrepot.objects.get(name = entrepot_name, store = current_store)
                    mon_stock = Stock.objects.get(entrepot = entrepot_rep, product = product_obj)
                    quantity_kit = dataInvoice.get('quantity_kit')
                    quantity_pc = dataInvoice.get('quantity_pc')
                    quantity_det = dataInvoice.get('quantity_det')
                    newquantity = int(mon_stock.quantity) - int(quantity_pc) - int(quantity_kit)
                    if newquantity < 0 :
                        return JsonResponse({'error': 'Répartitionnement Invalid! Quantité Insuffisante.'})
                    else:
                        mon_stock.quantity_kit = quantity_kit
                        mon_stock.quantity_pc = quantity_pc
                        mon_stock.save()
                return JsonResponse({'message': 'Produit repartitioner successfully.'})
            except models.Product.DoesNotExist:
                return JsonResponse({'error': 'Produit not found.'})
        else:
            return JsonResponse({'error': 'Produit not provided.'})
    else:
        return JsonResponse({'error': 'Invalid request data.'})

def LaunchPromotion(request):
    store_id = request.session["store"]
    current_store = store.objects.get(pk=store_id)  # Assuming 'store' is your Store model
    data = json.loads(request.body)
    dataInvoice = data.get('formData', '')
    if dataInvoice:       
        product_id = dataInvoice.get('id')
        if product_id:
            try:
                
                product_obj = models.Product.objects.get(pk=int(product_id), store=current_store)
                promoListe = dataInvoice.get('promoList')
                datedebut = dataInvoice["datedebPromo"]              
                datefin = dataInvoice["datefinPromo"]  
                if promoListe :
                    for typecl in promoListe:
                        print(typecl)
                        typeClientObj = typeClient.objects.filter(type_desc=typecl["nom"]).first()
                        if typeClientObj :        
                            models.Promotion.objects.create(
                                type_client = typeClientObj,
                                product = product_obj,
                                prix_vente = typecl["prixHt"], 
                                prix_vente_pc = typecl["prixHtPC"], 
                                prix_vente_kit = typecl["prixHtKIT"], 
                                prix_vente_carton = typecl["prixHtCarton"], 
                                start_date = datedebut,
                                end_date = datefin
                            )   
                return JsonResponse({'message': 'Promotion Créé.'})
            except models.Product.DoesNotExist:
                return JsonResponse({'error': 'Produit not found.'})
        else:
            return JsonResponse({'error': 'Produit not provided.'})
    else:
        return JsonResponse({'error': 'Invalid request data.'})
        
def loadallProducts(request):
    print(request)
    data = json.loads(request.body)
    last_id = data['lastId']  
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    products = models.Product.objects.filter(store = CurrentStore,  parent_product__isnull= True, id__gte = last_id)
    products_data = []
    for prod in products:
        product_data = {
            'id': prod.id,
            'reference': prod.reference,
            'reforme': True if prod.reforme else False,
            'name': prod.name,
            'prix_a': prod.prix_achat,
            'prix_mag': prod.prix_vente,
            'price': round(((float(prod.clientfinal_price) + float(prod.prix_livraison) + float(prod.tva_douan)) * 1.19), 2),
            'priceachat': float(prod.prix_vente) + float(prod.prix_livraison),
            'prixRevendeur': round(((float(prod.revendeur_price) + float(prod.prix_livraison) + float(prod.tva_douan)) * 1.19), 2),
            'fournisseur': prod.fournisseur,
            'qty_diva': prod.qty_in_store if prod.qty_in_store != '' else '',  # You'll need to define quantity_total
            'frais_livraison': prod.prix_livraison,
            'tax': prod.tva_douan,
            'entrepot_quantities': prod.quantities_per_entrepot,
            'entrepot_blockedquantities': prod.quantitiesblocked_per_entrepot,
            'family': prod.category.Libellé if prod.category else '',
            'motherfamily': prod.ancestor_categories,
            'showVariants': False,
            'price_variants': prod.get_price_variants,
            'variants': [],  # You can populate this later if needed
        }
        products_data.append(product_data)
    return JsonResponse({'stock': products_data})
    
def ImportProductsPrice(request):
   data = json.loads(request.body)
   products_list = data["products"]
   store_id = request.session["store"]
   current_store = store.objects.get(pk=store_id)
   for prod_data in products_list:
      product_ins = models.Product.objects.filter(reference = prod_data['reference'], store = current_store).first()
      if product_ins is None :
          return JsonResponse({'message':'Produit Not existant!'})
      else:
          if "livraison" in prod_data:
              product_ins.prix_livraison = prod_data["livraison"]
          if "PrixAchat" in prod_data:
              product_ins.prix_achat = prod_data["PrixAchat"]
          if "tax" in prod_data:
              product_ins.tva_douan = prod_data["tax"]
          if "prixVente" in prod_data:
            type_client= typeClient.objects.get(type_desc='Client Final', store=current_store)
            variant_price_client = models.variantsPrixClient.objects.create(
                type_client=type_client,
                produit=product_ins,
                prix_vente=prod_data["prixVente"]
            )
          if "prixVenteR" in prod_data:  
            type_client= typeClient.objects.get(type_desc='Revendeur', store=current_store)
            variant_price_client = models.variantsPrixClient.objects.create(
                type_client=type_client,
                produit=product_ins,
                prix_vente=prod_data["prixVenteR"]
            )
          if "prixVenteG" in prod_data:
            type_client= typeClient.objects.get(type_desc='Grossiste', store=current_store)
            variant_price_client = models.variantsPrixClient.objects.create(
                type_client=type_client,
                produit=product_ins,
                prix_vente=prod_data["prixVenteG"]
            )
          product_ins.save()
   return JsonResponse({'message':'Produits Importé!'})

def importProductPriceCarton(request):
   data = json.loads(request.body)
   products_list = data["products"]
   store_id = request.session["store"]
   current_store = store.objects.get(pk=store_id)
   for prod_data in products_list:
      product_ins = models.Product.objects.filter(reference = prod_data['reference'], store = current_store).first()
      if product_ins is None :
          return JsonResponse({'message':'Produit Not existant!'})
      else:
          if "QteParCarton" in prod_data:
              product_ins.QuantityPerCarton = prod_data["QteParCarton"]
              product_ins.save()
          if "PrixCFCarton" in prod_data:
            type_client= typeClient.objects.get(type_desc='Client Final', store=current_store)
            variant_price_client = models.variantsPrixClient.objects.create(
                type_client=type_client,
                produit=product_ins,
                prix_vente_carton=prod_data["PrixCFCarton"]
            )
          if "PrixRVCarton" in prod_data:  
            type_client= typeClient.objects.get(type_desc='Revendeur', store=current_store)
            variant_price_client = models.variantsPrixClient.objects.create(
                type_client=type_client,
                produit=product_ins,
                prix_vente_carton=prod_data["PrixRVCarton"]
            )
          if "PrixGCarton" in prod_data:
            type_client= typeClient.objects.get(type_desc='Grossiste', store=current_store)
            variant_price_client = models.variantsPrixClient.objects.create(
                type_client=type_client,
                produit=product_ins,
                prix_vente_carton=prod_data["PrixGCarton"]
            )
          product_ins.save()
   return JsonResponse({'message':'Produits Importé!'})
   
class PrixListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "produits/liste_prix.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'produits.can_see_produits' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('inventory'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        store_id = self.kwargs.get('store_id')
        selected_store = store.objects.get(pk=self.request.session["store"])
        products = models.Product.objects.filter(store=selected_store, parent_product__isnull= True) 
        product_families = models.Category.objects.filter(store=selected_store)
        context["product_families"]=product_families
        fournisseurs = Fournisseur.objects.filter(store=selected_store)
        context["product_fournisseur"] = fournisseurs
        # Extract specific fields from the queryset and create a list of dictionaries
        entrepots = Entrepot.objects.filter(store=selected_store)
        context["entrepots"]=entrepots
        
        context["stock"] = products
        return context
        
def getArchiveProducts(request):
   data = json.loads(request.body)
   my_archive = models.VerificationArchive.objects.get(id=data["id"])
   store_id = request.session["store"]
   current_store = store.objects.get(pk=store_id)
   stocks = my_archive.produits_verification.all()
   produits_archives = []
   for stock in stocks:
        product_obj = models.Product.objects.get(reference = stock.product_reference, store =current_store)
        prod_dict = {
            "reference": stock.product_reference,
            "name": product_obj.name,
            "realQuantity" : stock.realQuantity,
            "quantity": stock.quantity
        }
        produits_archives.append(prod_dict)

   return JsonResponse({'stocks':produits_archives})
   
def editCategory(request):
    store_id = request.session["store"]
    current_store = store.objects.get(pk=store_id)  # Assuming 'store' is your Store model
    data = json.loads(request.body)
    dataInvoice = data.get('formData', '')
    if dataInvoice:      
        category_id = dataInvoice.get('id')
        print(dataInvoice)
        if category_id:
            try:
                category = models.Category.objects.get(pk=int(category_id), store=current_store)
                # Update the fields based on the data from the request
                mother_category_id = dataInvoice.get('categorieP')
                if mother_category_id and mother_category_id != 'null':
                    mother_category = models.Category.objects.get(pk=int(mother_category_id))
                    category.MotherCategory = mother_category
                else:
                    category.MotherCategory = None

                category.Libellé = dataInvoice.get('libFamille')
                category.pc_component = dataInvoice.get('component')
                kit = False
                components = ''
                if dataInvoice.get('kit') == True or dataInvoice.get('kit') == 'true' :
                    category.kit = True
                    category.kitcomponents = dataInvoice.get('list2')

                # Save the changes
                category.save()

                return JsonResponse({'message': 'Category updated successfully.', 'category_id': category.id})
            except models.Category.DoesNotExist:
                return JsonResponse({'error': 'Category not found.'})
        else:
            return JsonResponse({'error': 'categoryId not provided.'})
    else:
        return JsonResponse({'error': 'Invalid request data.'})  
 
def supprimerCategorie(request):
    data = json.loads(request.body)
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    liste_id = data["liste_ids"]
    for id_bon in liste_id:
        category = models.Category.objects.get(id=id_bon, store=CurrentStore)
        with transaction.atomic():
              category.products.all().update(category=None)
               # Delete the Category instance
              category.delete()
    return JsonResponse({'message': "Eléments Supprimé !"})
    
def DeleteProductView(request):
    try:
        # Find the product by reference
        data = json.loads(request.body)
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        liste_ids = data["liste_ids"]
        for ref_produit in liste_ids:
            product = models.Product.objects.get(reference=ref_produit, store=CurrentStore)
            if not product.is_integrated():
                for product_variante in product.myvariants.all():
                    if not product_variante.is_integrated():
                        product_variante.delete()
                    else:
                        return JsonResponse({'success': False, 'message': 'Variante de Produit Ne peut pas être Supprimé! Il est intégré dans des bons.'})
                product.delete()
                     # If the product is not integrated, you can delete it                   
            else:
                return JsonResponse({'success': False, 'message': 'Produit Ne peut pas être Supprimé! Il est intégré dans des bons.'})
        return JsonResponse({'success': True , 'message': 'Produits Supprimés!'} )
    except models.Product.DoesNotExist:
        return JsonResponse({'success': False, 'error_message': 'ERREUR! Produit Non-trouvé.'})

def supprimerArchive(request):
    data = json.loads(request.body)
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    archive_id = data["archive_id"]
    category = models.VerificationArchive.objects.get(id=archive_id, store=CurrentStore)
    with transaction.atomic():
            for product in category.produits_verification.all() :
                product.delete()    
                        
            category.delete()
    return JsonResponse({'message': "Archive Supprimé !"})  
    
class ProductUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "produits/update_product.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'produits.can_see_produits' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('inventory'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) 
        ref = self.kwargs.get('product_ref')
        
        my_product = models.Product.objects.get(id=ref)
        if my_product:   
          context["id_produit"] = my_product.id  
          context["reference_produit"] = my_product.reference
          context["nom_product"]= my_product.name
          context["category_product"]=my_product.category.Libellé if my_product.category is not None else ""
          context["prix_product"]=my_product.prix_vente
          context["tva_product"]=my_product.tva     
          context["prix_livraison"]= my_product.prix_livraison
          context["tax_produit"] = my_product.tva_douan
          context["fournisseur"] = my_product.fournisseur
          context["qtyperCarton"] = my_product.QuantityPerCarton
          store = self.request.session["store"]
          CurrentStore = models.store.objects.get(pk=store)
          Currentuser = self.request.user
          myuser  = CustomUser.objects.get(username=Currentuser.username)
          categories = models.Category.objects.filter(store=CurrentStore)
          fournisseurs_list = Fournisseur.objects.filter(store=CurrentStore)
          fournisseurs=[]
          for f in fournisseurs_list :                       
            fr_dict={
                "acronym": f.acronym,
                "adresse": f.adresse,
                "phone": f.phone,
                "email": f.email,
                "raison_Social": f.raison_Social,
                "typefournisseur": f.typefournisseur,
                "fournisseurClient": f.fournisseurClient,
                "fournisseurEtrange": f.fournisseurEtrange,                 
            }
            fournisseurs.append(fr_dict)
          context["fournisseurs"]=fournisseurs
          context["categories"]= categories
          if my_product.myvariants.all() :
            variants_list =[]
            for variant in  my_product.myvariants.all():
              variant_dict={
                    "reference_produit" : variant.reference,
                    "nom_product": variant.name,
                    "category_product":variant.category.Libellé,
                    "prix_product":float(variant.prix_vente),
                    "prix_achat": float(variant.prix_achat),
                    "fournisseur" : variant.fournisseur,
              }
              variants_list.append(variant_dict)
            context["variants_products"] = variants_list
          historique_prix = my_product.monHIstoriqueAchat.all()         
          historique_prix_list = []
          # Parcours des instances et ajout des valeurs à la liste
          prix_achatlast = my_product.prix_achat
          for prix_instance in historique_prix:
            prix_achatlast = prix_instance.prix_achat_calcule
            historique_prix_list.append({
                "date": prix_instance.dateAchat,
                "qty_qctuelle": prix_instance.qty_qctuelle,
                "prix_achat_actuelle":prix_instance.prix_achat_actuelle,
                "qty_achete":prix_instance.qty_achete,
                "prix_achat":prix_instance.prix_achat,
                "prix_achat_calcule":prix_instance.prix_achat_calcule,
            })
          context["historiqueAchat"] = historique_prix_list
          context["prix_achat"]= prix_achatlast
          clients = models.typeClient.objects.filter(store=my_product.store)
          # Create a dictionary to quickly find existing variantsPrixClient instances
          existing_variants = {vp.type_client.id: vp for vp in my_product.produit_var.all()}
          # List to store the results for each client type
          variants_prix_data = []

          # Iterate over all possible client types
          for cl in clients:
            # Initialize a dictionary for each typeClient
            variant_data = {
                "type_client": cl.type_desc,
                "prix_vente": 0,  # Default value
                "prix_vente_pc": 0,  # Default value
                "prix_vente_kit": 0,  # Default value
                "prix_vente_carton": 0,  # Default value
            }
            # Check if there's a corresponding variantsPrixClient instance
            variant = existing_variants.get(cl.id)

            if variant:
                # If variant exists, use its values
                if self.request.session["store"] != '2' and self.request.session["store"] != '8':
                    variant_data["prix_vente"] = float(variant.prix_vente)
                else:
                    variant_data["prix_vente"] = float(my_product.prix_vente)
                variant_data["prix_vente_pc"] = float(variant.prix_vente_pc)
                variant_data["prix_vente_kit"] = float(variant.prix_vente_kit)
                variant_data["prix_vente_carton"] = float(variant.prix_vente_carton)
            else:
                # If there's no corresponding variant, keep the default (e.g., 0 or other logic)
                if self.request.session["store"] == '2' or self.request.session["store"] == '8':
                    variant_data["prix_vente"] = float(my_product.prix_vente)

            # Add the data to the list
            variants_prix_data.append(variant_data)

          # Update the context with the collected data
          context["type_clients"] = [{"nom": cl.type_desc} for cl in clients]
          context["variants_prix_data"] = variants_prix_data
          mes_stocks = my_product.mon_stock.all()
          stockList=[]
          for stock in mes_stocks:            
             stock_dict={
                "entrepot": stock.entrepot.name,
                "quantity": stock.quantity,
                "quantity_detailed": stock.quantity_detailed,
                "quantity_pc": stock.quantity_pc,
                "quantity_kit": stock.quantity_kit
             }
             stockList.append(stock_dict)
          context["stocks"]=stockList
          entrepots = Entrepot.objects.filter(store=CurrentStore)
          context["entrepots"]=entrepots
          promoListe = []
          for p in my_product.promotions.all():
            promoListe.append({
                "DateDEb": p.start_date.strftime('%d/%m/%Y'),
                "DateFin": p.end_date.strftime('%d/%m/%Y'),
                "actif": 'true' if p.end_date.strftime('%d/%m/%Y') < datetime.today().strftime('%d/%m/%Y') else 'false'
            })
          context["promotions"] = promoListe
          return context
        
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
          return super().dispatch(*args, **kwargs)
      
    def post(self, request, *args, **kwargs):
          data = json.loads(request.body)
          dataInvoice = data.get('formData')
          if dataInvoice:
            store_id = self.request.session["store"]
            currentStore = store.objects.get(id=store_id)
            product_id_to_update = dataInvoice["id"] # Set this to the ID of the product you want to update
            # Retrieve the product you want to update
            try:
                product = models.Product.objects.get(id=product_id_to_update, store=currentStore)
            except models.Product.DoesNotExist:
                # Handle the case where the product with the specified ID does not exist
                return JsonResponse({'Message':"Product not found"})
            category =models.Category.objects.get(Libellé = dataInvoice['category'], store = currentStore)
            # Update the product fields based on your data
            product.reference = dataInvoice['reference']
            product.name = dataInvoice['designation']
            product.fournisseur = dataInvoice['fournisseur']
            product.prix_vente = dataInvoice['prixVenteHt']
            product.prix_achat = dataInvoice['prixAchatHt']
            product.prix_livraison= dataInvoice['prix_livraison']
            product.tva = dataInvoice['tva']
            product.tva_douan = dataInvoice['taxProduit']
            product.category = category
            product.marge = max(float(dataInvoice['marge']), 0)
            if 'qtypercart' in dataInvoice :
                product.QuantityPerCarton = dataInvoice['qtypercart']
            product.save()
            new_references=[]
            if dataInvoice['product_variantes']:
              for variant_data in dataInvoice['product_variantes']:
                  for value in variant_data['value']:
                      # Construct the reference for the product variant
                      new_product_id = dataInvoice["reference"]
                      reference = f'{new_product_id}{variant_data["variante"]}{value}'
                      new_references.append(reference)
                      products_variants = product.myvariants.all()
              for product_varian in products_variants:
                  if product_varian.reference not in new_references:
                        product_varian.delete()
            if dataInvoice['product_variantes']:
              for variant_data in dataInvoice['product_variantes']:
                  for value in variant_data['value']:
                      # Construct the reference for the product variant
                      new_product_id = dataInvoice["reference"]
                      reference = f'{new_product_id}{variant_data["variante"]}{value}'

                      # Try to get an existing product variant by reference
                      product_variant, created = models.Product.objects.get_or_create(
                          reference=reference,
                          defaults={
                              'name': dataInvoice['designation'] +' '+ variant_data['variante'] +' '+ value,
                              'fournisseur': dataInvoice['fournisseur'],
                              'parent_product': product,
                              'prix_vente': dataInvoice['prixVenteHt'],
                              'prix_achat': dataInvoice['prixAchatHt'],
                              'tva': dataInvoice['tva'],
                              'category': category,
                              'marge': max(float(dataInvoice['marge']), 0),
                              'initial_qte': 0,
                              'TotalQte': 0,
                              'store': currentStore
                          }
                      )
                      if not created:
                          # Update the fields of the product variant
                          product_variant.name = dataInvoice['designation'] + variant_data['variante'] + value
                          product_variant.fournisseur = dataInvoice['fournisseur']
                          product_variant.prix_vente = dataInvoice['prixVenteHt']
                          product_variant.prix_achat = dataInvoice['prixAchatHt']
                          product_variant.tva = dataInvoice['tva']
                          product_variant.category = category
                          product_variant.marge = max(float(dataInvoice['marge']), 0)

                      # If you want to update other fields, do so here

                      # Save the changes to the product variant
                      product_variant.save()
            if dataInvoice['clients_price']:
              for client_price in dataInvoice['clients_price']:
                  type_client_name = client_price['nom']
                  prix_vente = client_price['prixHt']
                  prix_vente_pc = client_price['prixHtPC']
                  prix_vente_kit = client_price['prixHtKIT']
                  prix_vente_carton = client_price['prixHtCarton']
                  typeClient = models.typeClient.objects.get(type_desc= type_client_name, store = currentStore)                
                   # Create or update the client price
                  client_price = models.variantsPrixClient.objects.filter(
                      type_client=typeClient,
                      produit=product,  # Make sure to set the correct product                               
                  ).first()
                  if client_price is not None:
                      client_price.prix_vente = prix_vente
                      client_price.prix_vente_pc = prix_vente_pc
                      client_price.prix_vente_kit = prix_vente_kit
                      client_price.prix_vente_carton = prix_vente_carton
                      client_price.save()
                  else:
                    models.variantsPrixClient.objects.create(
                        type_client=typeClient,
                        produit=product,  
                        prix_vente=prix_vente,
                        prix_vente_pc=prix_vente_pc,
                        prix_vente_carton = prix_vente_carton
                    )  
            return JsonResponse({'message': 'Product updated !.'})

class stockState(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "produits/edit_stocks.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'produits.can_see_produits' in self.request.session.get('permissions', []) or self.request.session["role"] == "DIRECTEUR EXECUTIF"

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('inventory'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        selected_store = store.objects.get(pk=self.request.session["store"])
        products = models.Product.objects.filter(store=selected_store, parent_product__isnull=True)
        product_families = models.Category.objects.filter(store=selected_store)
        fournisseurs = Fournisseur.objects.filter(store=selected_store)
        entrepots = Entrepot.objects.filter(store=selected_store)
        stocks_all = Stock.objects.filter(product__store=selected_store, entrepot__name = "Depot principal Reghaia")
        stock_list = []

        for stock in stocks_all:
            stock_dict = {
                "reference": stock.product.reference,
                "name": stock.product.name,
                "entrepot": stock.entrepot.name,
                "quantity_entered": stock.historical_entered_quantity,
                "quantity_received": stock.historical_received_quantity,
                "quantity_transfered":stock.historical_transfered_quantity,
                "quantity_sold": stock.product_sold_quantity,
                "quantity_returned":stock.product_returned_quantity,
                "quantity_inreal":stock.quantity,
                "quantity_expected": stock.quantity_expected
            }
            stock_list.append(stock_dict)
        context["entrepots"] = entrepots
        context["product_families"] = product_families
        context["product_fournisseur"] = fournisseurs
        context["stock"] = stock_list
        
        return context
        
    @method_decorator(transaction.atomic)    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        dataJson = json.loads(request.body)
        data = dataJson.get('formData', '')
        store_id = self.request.session["store"]
        currentStore = store.objects.get(id=store_id)
        liste_products =data['liste_products']
        for product_data in liste_products:
            entrepot_name = product_data['entrepot']
            product_name = product_data['product']
            quantity_expected = int(product_data['quantity_expected'])
            if quantity_expected >= 0:
                # Fetch the Stock instance based on entrepot and product
                try:
                  entrepot_name = product_data['entrepot']
                  product_name = product_data['product']  
                  stock = Stock.objects.get(entrepot__name=entrepot_name, product__reference=product_name)
                  stock.quantity = quantity_expected
                  stock.save()
                except Stock.DoesNotExist:
                    return JsonResponse({'message': 'Erreur!'})
            else:
                try:
                  entrepot_name = product_data['entrepot']
                  product_name = product_data['product']  
                  stock = Stock.objects.get(entrepot__name=entrepot_name, product__reference=product_name)
                  stock.quantity = 0
                  stock.save()
                except Stock.DoesNotExist:
                    return JsonResponse({'message': 'Erreur!'})
        return JsonResponse({'message': 'Stock modifié!.'})
        
class ProductDetailsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "produits/product_details.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'produits.can_see_produits' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('inventory'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) 
        ref = self.kwargs.get('product_ref')
        my_product = models.Product.objects.get(id=ref)
        if my_product:  
          quantity_total = 0
          if my_product.myvariants.all() :
            for variant in  my_product.myvariants.all():
                quantity_total += variant.total_quantity_in_stock
          else:
             quantity_total = my_product.total_quantity_in_stock
          context["reference_produit"] = my_product.reference
          context["id"] = my_product.id
          context["tva_produit"] = my_product.tva
          context["nom_product"]= my_product.name
          context["category_product"]=my_product.category.Libellé if my_product.category is not None else ""
          context["prix_product"]=my_product.prix_vente
          context["prix_achat"]= my_product.prix_achat
          context["prix_livraison"]= my_product.prix_livraison
          context["tax_produit"] = my_product.tva_douan
          context["fournisseur"] = my_product.fournisseur
          context["qteTotale"] = quantity_total
          context["qteReforme"] = my_product.reforme_quantity
          context["qteintacte"] = int(quantity_total) - int(my_product.reforme_quantity)
          
          if my_product.myvariants.all() :
            variants_list =[]
            for variant in  my_product.myvariants.all():
              variant_dict={
                    "id":variant.id,
                    "reference_produit" : variant.reference,
                    "nom_product": variant.name,
                    "category_product":variant.category.Libellé,
                    "prix_product":float(variant.prix_vente),
                    "prix_achat": float(variant.prix_achat),
                    "fournisseur" : variant.fournisseur,
                    "qteTotale" : variant.TotalQte,
                    "qteReforme" : variant.reforme_quantity,
                    "qteintacte" : variant.available_quantity,
              }
              variants_list.append(variant_dict)
            context["variants_products"] = variants_list
            
          mes_stocks = my_product.mon_stock.all()
          stockList=[]
          for stock in mes_stocks:            
             stock_dict={
                "entrepot": stock.entrepot.name,
                "quantity": stock.quantity
             }
             stockList.append(stock_dict)
          context["stocks"]=stockList

          historique_prix = ProduitsEnBonAchat.objects.filter(produit=my_product)

          historique_prix_list = []
          # Parcours des instances et ajout des valeurs à la liste
          for prix_instance in historique_prix:
            historique_prix_list.append({
             "date": prix_instance.BonNo.dateBon,
             "prix_achat": prix_instance.prixUnitaire,
             "quantity": prix_instance.quantity,
            })
          context["historiqueAchat"] = historique_prix_list

          clients = models.typeClient.objects.filter(store=my_product.store)

          # Create a dictionary to quickly find existing variantsPrixClient instances
          existing_variants = {vp.type_client.id: vp for vp in my_product.produit_var.all()}

          # List to store the results for each client type
          variants_prix_data = []

          # Iterate over all possible client types
          for cl in clients:
            # Initialize a dictionary for each typeClient
            variant_data = {
                "type_client": cl.type_desc,
                "prix_vente": 0,  # Default value
                "prix_vente_pc": 0,  # Default value
            }

            # Check if there's a corresponding variantsPrixClient instance
            variant = existing_variants.get(cl.id)

            if variant:
                # If variant exists, use its values
                if self.request.session["store"] != '2' and self.request.session["store"] != '8':
                    variant_data["prix_vente"] = float(variant.prix_vente)
                else:
                    variant_data["prix_vente"] = float(my_product.prix_vente)
                variant_data["prix_vente_pc"] = float(variant.prix_vente_pc)
            else:
                # If there's no corresponding variant, keep the default (e.g., 0 or other logic)
                if self.request.session["store"] == '2' or self.request.session["store"] == '8':
                    variant_data["prix_vente"] = float(my_product.prix_vente)

            # Add the data to the list
            variants_prix_data.append(variant_data)

        # Update the context with the collected data
        context["type_clients"] = [{"nom": cl.type_desc} for cl in clients]
        context["variants_prix_data"] = variants_prix_data
        return context

class ProduitsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "produits/products_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'produits.can_see_produits' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('inventory'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        store_id = self.kwargs.get('store_id')
        selected_store = store.objects.get(pk=self.request.session["store"])
        if self.request.session["store"] == '2' :
            products = models.Product.objects.filter(store=selected_store, parent_product__isnull= True)
        else:
            products = models.Product.objects.filter(store=selected_store, parent_product__isnull= True)[:150]
        product_families = models.Category.objects.filter(store=selected_store)
        context["product_families"]=product_families
        fournisseurs = Fournisseur.objects.filter(store=selected_store)
        context["product_fournisseur"] = fournisseurs
       
        # Extract specific fields from the queryset and create a list of dictionaries
        entrepots = Entrepot.objects.filter(store=selected_store)
        context["entrepots"]=entrepots
        context["stock"] = products
        return context

class ProduitsVerifMagView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "produits/verificationProductQteMag.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'produits.can_see_archives' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('inventory'))
   
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        entrepots = Entrepot.objects.filter(store=CurrentStore)
        context["entrepots"]= entrepots
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        if dataInvoice:  
           store_id = self.request.session["store"]
           CurrentStore = store.objects.get(pk=store_id)
           entrepot =Entrepot.objects.get(name= dataInvoice["entrepot"], store=CurrentStore)
           dateVerification = datetime.now()
           store_id = self.request.session["store"]
           CurrentStore = store.objects.get(pk=store_id)
           current_year = datetime.now().strftime('%y')
           current_month = datetime.now().strftime('%m')
           last_number = models.VerificationArchive.objects.order_by('-id').first()
           if last_number:
                last_number = last_number.id
           else:
                last_number = 0
           codeArchive= f'AR{current_year}{current_month}-{last_number + 1:04d}'
           verification = models.VerificationArchive.objects.create(
            codeArchive=codeArchive,
            store=CurrentStore,
            entrepot=entrepot,
            date_verification=dateVerification 
            )
           products = dataInvoice["products"]
           for produit in products:
              reference = produit["productReference"]
              quantity = produit["quantity"]
              verificationResult = produit["verificationResult"]
              realQuantity = produit["realQuantity"]
              models.ListProductVerificationArchive.objects.create(
                verification=verification,
                product_reference=reference,
                quantity=quantity,
                realQuantity=realQuantity,
                verification_result=verificationResult
            )
           return JsonResponse({'message': 'Verification data saved successfully'})
 
class UpdateArchiveMagView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "produits/update_verificationProductQteMag.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'produits.can_see_archives' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('inventory'))
   
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        entrepots = Entrepot.objects.filter(store=CurrentStore)
        context["entrepots"]= entrepots
        id_archive = self.kwargs.get('archive_id')
        context["id_archive"] = id_archive
        archive = models.VerificationArchive.objects.get(id=id_archive)
        entrepot = archive.entrepot
        context["entrepot"]= entrepot
        
        produits_archives = []
        stocks = entrepot.get_stocks()
        stock_data=[]
        for stock in stocks:
                product_name = stock.product.name
                entrepot_name = stock.entrepot.name
                quantity = stock.quantity
                price = stock.product.prix_vente
                reference = stock.product.reference
                entrepot=stock.entrepot.name
                stock_info = {
                    "product_name": product_name,
                    "entrepot_name": entrepot_name,
                    "quantity": quantity,
                    "reference": reference,
                }
                stock_data.append(stock_info)
        context['stocks'] = stock_data
        for prodduit in  archive.produits_verification.all():
            product_obj = models.Product.objects.get(reference = prodduit.product_reference, store = CurrentStore)
            prod_dict = {
              "reference": prodduit.product_reference,
              "name": product_obj.name,
              "realQuantity" : prodduit.realQuantity,
              "quantity": prodduit.quantity
            }
            produits_archives.append(prod_dict)
            
        context["produits_archives"]=produits_archives
        return context
    
    @method_decorator(login_required)
    @transaction.atomic
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        if dataInvoice: 
           store_id = self.request.session["store"]
           CurrentStore = store.objects.get(pk=store_id)
           store_id = self.request.session["store"]
           CurrentStore = store.objects.get(pk=store_id)
           verification = models.VerificationArchive.objects.get(id= dataInvoice["archive_id"])
           for product in verification.produits_verification.all():
               product.delete()
               
           products = dataInvoice["products"]
           for produit in products:
              reference = produit["productReference"]
              quantity = produit["quantity"]
              verificationResult = produit["verificationResult"]
              realQuantity = produit["realQuantity"]
              models.ListProductVerificationArchive.objects.create(
                verification=verification,
                product_reference=reference,
                quantity=quantity,
                realQuantity=realQuantity,
                verification_result=verificationResult
            )
           return JsonResponse({'message': 'Verification data saved successfully'})
           
class ProduitsVerifView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "produits/verificationProductQte.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'produits.can_see_archives' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('inventory'))
   
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        entrepots = Entrepot.objects.filter(store=CurrentStore)
        context["entrepots"]= entrepots
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        if dataInvoice:  
           store_id = self.request.session["store"]
           CurrentStore = store.objects.get(pk=store_id)
           entrepot =Entrepot.objects.get(name= dataInvoice["entrepot"], store=CurrentStore)
           dateVerification = datetime.now()
           store_id = self.request.session["store"]
           CurrentStore = store.objects.get(pk=store_id)
           current_year = datetime.now().strftime('%y')
           current_month = datetime.now().strftime('%m')
           last_number = models.VerificationArchive.objects.order_by('-id').first()
           if last_number:
                last_number = last_number.id
           else:
                last_number = 0
           codeArchive= f'AR{current_year}{current_month}-{last_number + 1:04d}'
           verification = models.VerificationArchive.objects.create(
            codeArchive=codeArchive,
            store=CurrentStore,
            entrepot=entrepot,
            date_verification=dateVerification 
            )
           products = dataInvoice["products"]
           for produit in products:
              reference = produit["productReference"]
              quantity = produit["quantity"]
              verificationResult = produit["verificationResult"]
              realQuantity = produit["realQuantity"]
              models.ListProductVerificationArchive.objects.create(
                verification=verification,
                product_reference=reference,
                quantity=quantity,
                realQuantity=realQuantity,
                verification_result=verificationResult
            )
           return JsonResponse({'message': 'Verification data saved successfully'})

class AddProductView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name="produits/add_product.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'produits.can_see_produits' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('inventory'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        store = self.request.session["store"]
        CurrentStore = models.store.objects.get(pk=store)
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        categories = models.Category.objects.filter(store=CurrentStore)
        fournisseurs_list = Fournisseur.objects.filter(store=CurrentStore)
        fournisseurs=[]
        latest_product = models.Product.objects.latest('id')
        # Obtenir son id
        latest_id = latest_product.id if latest_product else 0

        #Calculer la nouvelle référence
        new_reference = str(latest_id + 1).zfill(5)
      
        context["mareference"] = new_reference
        for f in fournisseurs_list :                       
            fr_dict={
                "acronym": f.acronym,
                "adresse": f.adresse,
                "phone": f.phone,
                "email": f.email,
                "raison_Social": f.raison_Social,
                "typefournisseur": f.typefournisseur,
                "fournisseurClient": f.fournisseurClient,
                "fournisseurEtrange": f.fournisseurEtrange,                 
            }
            fournisseurs.append(fr_dict)
        clients = models.typeClient.objects.filter(store=CurrentStore)
        types_clients =[]
        for cl in clients:
           cl_dict ={
              "nom":cl.type_desc
           }
           types_clients.append(cl_dict)
        context["type_clients"]=types_clients
        context["fournisseurs"]=fournisseurs
        context["categories"]= categories
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        dataJson = json.loads(request.body)
        data = dataJson.get('formData', '')
        store_id = self.request.session["store"]
        currentStore = store.objects.get(id=store_id)
        category= None
        if models.Category.objects.get(id = data['category'], store = currentStore) :
          category =models.Category.objects.get(id = data['category'], store = currentStore)
          
        existing_product = models.Product.objects.filter(reference=data['reference'], store=currentStore).first()
        if existing_product:
            return JsonResponse({'error': 'Il existe déja un produit avec cette Référence !.'})
        QuantityPerCarton =0
        if 'qtypercart' in data :
            QuantityPerCarton = data['qtypercart'] 
                
        product = models.Product.objects.create(
            reference=data['reference'],
            name=data['designation'],
            fournisseur=data['fournisseur'],
            prix_vente=data['prixVenteHt'],
            prix_achat=data['prixAchatHt'],
            prix_livraison= data['frais_livraison'],
            category = category,
            marge= max(float(data['marge']), 0),
            initial_qte=0,  # You can set this value
            TotalQte=0,     # You can set this value
            tva= data['tva'],
            tva_douan= data['taxProduit'],
            QuantityPerCarton= QuantityPerCarton,
            store= currentStore
        )
        
        if data['product_variantes'] != "":
         for variant_data in data['product_variantes']:
          for value in variant_data['value']:
              previous_product = models.Product.objects.latest('id')    
              new_product_id = data['reference']
              reference = f'{new_product_id}{variant_data["variante"]}{value}'
              product_variants = models.Product.objects.create(
                reference=reference,
                name=data['designation']+' '+ variant_data['variante']+' ' + value,
                parent_product= product,
                fournisseur=data['fournisseur'],
                prix_vente=data['prixVenteHt'],
                prix_achat=data['prixAchatHt'],
                category = category,
                marge= max(float(data['marge']), 0),
                initial_qte=0,  # You can set this value
                TotalQte=0,     # You can set this value
                store= currentStore
            )
        
        if data['clients_price']:
         for client_price in data['clients_price']:
           type_client_name = client_price['nom']
           prix_vente = client_price['prixHt']  
           prix_vente_pc = client_price['prixHtPC']  
           type_client, created = typeClient.objects.get_or_create(type_desc=type_client_name, store=currentStore)
           variant_price_client = models.variantsPrixClient.objects.create(
             type_client=type_client,
             produit=product,
             prix_vente=prix_vente,
             prix_vente_pc = prix_vente_pc
           )
        
        return JsonResponse({'success': 'Produit Ajouté !.'})

class FamilleView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "produits/categories_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'produits.can_see_produits_familles' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('inventory'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        Currentuser = self.request.user
        categories  = models.Category.objects.filter(store=CurrentStore)
        context["categories"]= categories
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
          mother_category_id = dataInvoice.get('categorieP')
          if mother_category_id != '':
                mother_category = models.Category.objects.get(pk=int(mother_category_id))
          else:
            mother_category = None

          libFamille = dataInvoice.get('libFamille')
          kit = False
          components = ''
          if dataInvoice.get('kit') == 'true':
            kit = True
            components = dataInvoice.get('list2')
          category = models.Category.objects.create(
            MotherCategory=mother_category,
            Libellé=libFamille,
            kit = kit,
            kitcomponents = components,
            pc_component = dataInvoice.get('component'),
            store=CurrentStore,
          )
        return JsonResponse({'message': 'Category created successfully.', 'category_id': category.id})
        
class ArchiveListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "produits/listeArchive.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'produits.can_see_archives' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('inventory'))

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        archives = models.VerificationArchive.objects.filter(store=CurrentStore)
        
        context["archives"]=archives
        return context