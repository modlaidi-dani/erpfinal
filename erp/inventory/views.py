from django.shortcuts import render
from django.shortcuts import render
from django.views.generic.base import TemplateView
from django.http import Http404, JsonResponse
from tiers.models import Fournisseur
import json
from django.db import transaction,  IntegrityError
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from users.models import CustomUser, cordinates
from clientInfo.models import store
from produits.models import Category, Product
from tiers.models import Fournisseur, Client
from . import models
from ventes.models import BonSortie, ProduitsEnBonSortie, AvoirVente, DemandeTransfert, validationBl
from reglements.models import ModeReglement, EcheanceReglement
from tiers.models import Banque
import json
from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist  # Import the ObjectDoesNotExist exception
from django.http import HttpResponseServerError
from django.db.models import Sum, Case, When, IntegerField
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from datetime import date
from datetime import datetime
from achats.models import BonAchat
from comptoire.models import pointVente
from comptoire.models import pointVente, ProduitsEnBonComptoir, BonRetourComptoir
from collections import defaultdict
from notifications.signals import notify
from django.db.models import Max
from django.utils import timezone
from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from gestionRH.models import RequeteSalarie

from django.core.cache import cache
from django.http import HttpResponse

def acceptRetour(request):
    store_id = request.session["store"]
    data = json.loads(request.body)
    CurrentStore = store.objects.get(pk=store_id)
    id_retour= data["idBon"]
    user = request.user
    myuser = CustomUser.objects.get(username=user.username)
    if user.check_password(data["password"]):
        bon_retour = models.BonRetour.objects.get(idBon=id_retour, store=CurrentStore)
        bon_retour.reception_valide = True
        bon_retour.save()
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False})
    return JsonResponse({'message':'Réception Accepté!'})
    
def logCordinates(request):
    store_id = request.session["store"]
    data = json.loads(request.body)
    CurrentStore = store.objects.get(pk=store_id)
    categories = Category.objects.filter(store=CurrentStore)
    dataCoordinates = data.get('formData', '')
    Currentuser = request.user
    selected_store = store.objects.get(pk=request.session["store"])  
    myuser  = CustomUser.objects.get(username=Currentuser.username)
    cordinates.objects.create(
        User = myuser,
        latitude = dataCoordinates["latitude"],
        longitude = dataCoordinates["longitude"], 
    )
    return JsonResponse({'message':'cordinates logged'})
    
def get_sales(request):
    # Simulation de données aléatoires pour les ventes
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    categories = Category.objects.filter(store=CurrentStore)
    components = ['cpu', 'mb', 'ram', 'cpuc', 'ssd', 'psu', 'gpu', 'case', 'casef' ,'moniteur', 'claviers', 'souris']
    category_totals = []  # Liste pour stocker les totaux par catégorie

    for component in components:
        total_quantity_sold = 0
        total_quantity = 0
        # Iterate through categories of the current component
        component_categories = Category.objects.filter(store=CurrentStore, pc_component=component)
        for category in component_categories:
            for product in category.products.all():
              if product.store == CurrentStore:  
                   total_quantity_sold += (product.quantity_vendu - product.quantity_retour)
                   total_quantity += product.total_quantity_in_stock
        

        # Ajouter le résultat à la liste sous forme de dictionnaire
        category_totals.append({'component': component, 'total': total_quantity_sold, 'total_qte':total_quantity})
    
    bills = BonSortie.objects.filter(store = CurrentStore, valide = True, entrepot__name ="Depot principal Reghaia")
    bills_lst =[]
    clients_list = []

    for bill in bills:
        if len(bill.bon_garantie.all()) == 0 and len(bill.MesbonRetours.all()) == 0 and len(bill.produits_en_bon_sorties.all()) > 0:
            entrepot_first_letters = ''.join([word[0] for word in bill.entrepot.name.split()])
            bill_dict = {
                'idbon': bill.idBon,
                'entrepot': entrepot_first_letters,
                'link': f'/ventes/bonGarantie/{bill.id}',
                'username': bill.user.username,
                'agence': bill.agenceLivraison if bill.agenceLivraison != '' else 'DIVATECH',
                'client': bill.client.name,
                'wilaya': bill.client.region_client,
            }
            # Recherche du client dans clients_list
            client_found = False
            for client_info in clients_list:
                if client_info["client_name"] == bill.client.name:
                    # Ajout du bon à la liste des factures du client
                    client_info["bills"].append(bill_dict)
                    client_found = True
                    break
            if not client_found:
                # Si le client n'est pas déjà dans la liste, l'ajouter avec sa facture
                clients_list.append({"client_name": bill.client.name, "client_wilaya": bill.client.region_client, "username": bill.client.user.username, "bills": [bill_dict]})

    categories = Category.objects.filter(store=CurrentStore)
    components = ['cpu', 'mb', 'ram', 'cpuc' ,'ssd', 'psu', 'gpu', 'case', 'casef' ,'moniteur', 'claviers', 'souris']
    category_qtys = []  # Liste pour stocker les totaux par catégorie

    for component in components:
        total_quantity = 0
        # Iterate through categories of the current component
        component_categories = Category.objects.filter(store=CurrentStore, pc_component=component)
        for category in component_categories:
            for product in category.products.all():
               total_quantity += product.total_quantity_in_stock    
                  
        # Ajouter le résultat à la liste sous forme de dictionnaire
        category_qtys.append({'component': component, 'total': total_quantity})
    nbr_reqs = RequeteSalarie.objects.filter(reponse='').count()   
    return JsonResponse({'sells': category_totals, 'quantities':category_qtys, 'bills':clients_list, 'nbrrq': nbr_reqs}, safe=False)
    
def updateStockQuantiy(request):
    data = json.loads(request.body)
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    reference = data["reference"]
    entrepot = data["entrepot"]
    qty_initial = data["qty"]
    print(reference, entrepot, CurrentStore)
    prod_stock = models.Stock.objects.get(entrepot__name = entrepot, product__reference = reference, entrepot__store = CurrentStore)
    prod_stock.quantity_initial = qty_initial
    prod_stock.save()
    return JsonResponse({'success': True})
    
def delete_transfer_bill(request):
    data = json.loads(request.body)
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    liste_id = data["liste_ids"]
    for id_bon in liste_id:
        bon_transfert = models.BonTransfert.objects.get(idBon=id_bon, store=CurrentStore)
        with transaction.atomic():
                # Get the associated product transfers
                produits_transfert = models.ProduitsEnBonTransfert.objects.filter(BonNo=bon_transfert)
                
                # Iterate over the product transfers and update stock quantities
                for produit_transfert in produits_transfert:
                    stock_dep = produit_transfert.stock_dep
                    stock_arr = produit_transfert.stock_arr
                    quantity = produit_transfert.quantity
                    
                    # Update the source warehouse stock quantity
                    stock_dep.quantity += quantity
                    stock_dep.save()
                    
                    if stock_arr.quantity - quantity > 0:
                        # Update the destination warehouse stock quantity
                        stock_arr.quantity -= quantity
                        stock_arr.save()
                    else:
                         stock_arr.quantity = 0
                    # Delete the product transfer record
                    produit_transfert.delete()

                # Delete the transfer bill
                bon_transfert.delete()
        return JsonResponse({'message': "Transfer bill and associated records deleted successfully."})

class StockTransfertMagUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/transfert_billmag_update.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bontransfert' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        bill_id=self.kwargs.get('id_bill')
        transfert_bill = models.BonTransfertMagasin.objects.get(id=bill_id)
        context["bill"]=transfert_bill
        items =[]
        for produit_data in transfert_bill.produits_en_bon_transfertMag.all():
            prod_dict ={
                "ref": produit_data.stock_dep.product.reference,
                "name": produit_data.stock_dep.product.name,
                "rate":float(produit_data.stock_dep.product.revendeur_price + produit_data.stock_dep.product.prix_livraison + produit_data.stock_dep.product.tva_douan),
                "qty":produit_data.quantity
            }
            items.append(prod_dict)
        
        context["items"]=items
        my_entrepot = transfert_bill.entrepot_depart
        
        stocks = my_entrepot.get_stocks()
        stock_data=[]
        for stock in stocks:
                product_name = stock.product.name
                entrepot_name = stock.entrepot.name
                quantity = stock.quantity
                price = float(stock.product.revendeur_price + stock.product.prix_livraison + stock.product.tva_douan)
                reference = stock.product.reference
                entrepot=stock.entrepot.name
                stock_info = {
                    "product_name": product_name,
                    "entrepot_name": entrepot_name,
                    "quantity": quantity,
                    "price": price,
                    "reference": reference,
                    "entrepot":entrepot,
                }
                stock_data.append(stock_info)
        context['stocks'] = stock_data
        selected_store = store.objects.get(pk=self.request.session["store"])  

        # Get the selected store using the session data
        selected_store_id = self.request.session.get("store")
        selected_store = store.objects.get(pk=selected_store_id)

        # Create a list of dictionaries to store the store-entrepot associations
        store_entrepot_info = []

        # Loop through all stores and their associated entrepots
        for store_ins in store.objects.all():
            for entrepot in store_ins.get_entrepots():
                store_entrepot_info.append({
                    'store_name': store_ins.name,
                    'entrepot_name': entrepot.name
                })

        # Add the data to the context
        context["selected_store"] = selected_store
        context["entrepots"] = store_entrepot_info        
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs): 
      data = json.loads(request.body)
      dataInvoice = data.get('formData', '')
      Currentuser = request.user
      selected_store = store.objects.get(pk=self.request.session["store"])  
      myuser  = CustomUser.objects.get(username=Currentuser.username)
      if dataInvoice:
        bon_tr = models.BonTransfertMagasin.objects.get(idBon=dataInvoice["IdBon"])
        # dateBon = dataInvoice["dateBp"]
     
        # Create or get the client
        split_values = dataInvoice['ent_dep']['name'].split('-')

            # Extract the individual components
        store_name = split_values[0]
        entrepot_name = split_values[1]
        store_dep = store.objects.get(name = store_name)
        
        entrepot_dep = models.Entrepot.objects.filter(name = entrepot_name, store=store_dep).first()
        ent_dep= dataInvoice['ent_dep']['name']
        split_values = dataInvoice['ent_arr']['name'].split('-')

            # Extract the individual components
        store_name = split_values[0]
        entrepot_name = split_values[1]
        store_arr = store.objects.get(name = store_name)
        print(entrepot_name)
        print(store_name)
        entrepot_arr = models.Entrepot.objects.get(name = entrepot_name, store=store_arr)
        bon_tr.entrepot_depart = entrepot_dep
        bon_tr.entrepot_arrive = entrepot_arr
        
        with transaction.atomic():
            for product_data in bon_tr.produits_en_bon_transfertMag.all():
                product_data.stock_dep.quantity += product_data.quantity
                if  product_data.stock_arr.quantity - product_data.quantity > 0 :
                    product_data.stock_arr.quantity -= product_data.quantity
                else:
                    product_data.stock_arr.quantity
                product_data.stock_dep.save()
                product_data.stock_arr.save()
                product_data.delete()
            for product in dataInvoice["produits"]:
             # Retrieve the stock entry for the product in the source warehouse (ent_dep)
             stock_in_source = models.Stock.objects.get(
                product__reference=product["ref"], entrepot=entrepot_dep
             )
             stock_in_source.quantity -= int(product["qty"])
             stock_in_source.save()
             product_ref = product["ref"]
             entrepot_name = entrepot_arr 
             stock_arr = models.Stock.objects.filter(product__reference=product_ref, entrepot__name=entrepot_name).first()

             if stock_arr is None:
                    # If it doesn't exist, create a new Stock object
                    stock_arr = models.Stock.objects.create(
                        product=Product.objects.get(reference=product_ref , store = selected_store),  # Replace 'Product' with your actual model
                        entrepot=models.Entrepot.objects.get(name=entrepot_name),  # Replace 'Entrepot' with your actual model
                        quantity=int(product["qty"])
                    )
             else:
                    # If it exists, update the quantity
                    stock_arr.quantity += int(product["qty"])
                    stock_arr.save()
             # Create or update a ProduitsEnBonTransfert instance
             produit_en_bon_transfert= models.ProduitsEnBonTransfertMag.objects.create(
                BonNo=bon_tr,
                stock_dep=stock_in_source,
                stock_arr=models.Stock.objects.get(product__reference=product["ref"], entrepot=entrepot_arr),
                quantity=product["qty"],
             )
            bon_tr.save()
        return JsonResponse({'message': "Products transferred successfully."})
 
 
def delete_transfer_mag_bill(request):
    data = json.loads(request.body)
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    liste_id = data["liste_ids"]
    for id_bon in liste_id:
        bon_transfert = models.BonTransfertMagasin.objects.get(idBon=id_bon, store=CurrentStore)
        with transaction.atomic():
                # Get the associated product transfers
                produits_transfert = models.ProduitsEnBonTransfertMag.objects.filter(BonNo=bon_transfert)
                
                # Iterate over the product transfers and update stock quantities
                for produit_transfert in produits_transfert:
                    stock_dep = produit_transfert.stock_dep
                    stock_arr = produit_transfert.stock_arr
                    quantity = produit_transfert.quantity
                    
                    # Update the source warehouse stock quantity
                    stock_dep.quantity += quantity
                    stock_dep.save()
                    
                    if stock_arr.quantity - quantity > 0:
                        # Update the destination warehouse stock quantity
                        stock_arr.quantity -= quantity
                        stock_arr.save()
                    else:
                         stock_arr.quantity = 0
                    # Delete the product transfer record
                    produit_transfert.delete()

                # Delete the transfer bill
                bon_transfert.delete()
        return JsonResponse({'message': "Transfer bill and associated records deleted successfully."})
        
def getStock(request):
   data = json.loads(request.body)
   my_entrepot = models.Entrepot.objects.get(name=data["nomEnt"])
   stocks = my_entrepot.get_stocks()
   stock_data=[]
   for stock in stocks:
        product_name = stock.product.name
        entrepot_name = stock.entrepot.name
        quantity = 0
        if request.session["role"] == "manager":
            quantity = stock.quantity_detailed
        else:
            quantity = stock.get_quantity
        price = stock.product.prix_vente
        prix_achat = stock.product.prix_achat
        reference = stock.product.reference
        entrepot=stock.entrepot.name
        stock_info = {
            "product_name": product_name,
            "entrepot_name": entrepot_name,
            "quantity": quantity,
            "reference": reference,
            "entrepot":entrepot,
            "price": price,
            "prix_achat": prix_achat
        }
        stock_data.append(stock_info)
   return JsonResponse({'stocks':stock_data})

def getStockMagasin(request):
   data = json.loads(request.body)
   split_values = data["nomEnt"].split('-')

    # Extract the individual components
   store_name = split_values[0]
   entrepot_name = split_values[1]
   store_obj = store.objects.get(name=store_name)
   my_entrepot = models.Entrepot.objects.get(name=entrepot_name, store=store_obj)
   stocks = my_entrepot.get_stocks()
   stock_data=[]
   for stock in stocks:
        product_name = stock.product.name
        entrepot_name = stock.entrepot.name
        quantity = 0 
        if request.session["role"] == "manager":
            quantity = stock.quantity
        else:
            quantity = stock.get_quantity
        price = stock.product.prix_vente
        prix_achat = stock.product.prix_achat
        reference = stock.product.reference
        entrepot=stock.entrepot.name
        stock_info = {
            "product_name": product_name,
            "entrepot_name": entrepot_name,
            "quantity": quantity,
            "reference": reference,
            "entrepot":entrepot,
            "price": price,
            "prix_achat": prix_achat
        }
        stock_data.append(stock_info)
   return JsonResponse({'stocks':stock_data})
   
def supprimerInventaire(request):
    try:
         # Find the product by reference
        liste_id = data["liste_ids"]
        for id_bon in liste_id:
            with transaction.atomic(): 
                data = json.loads(request.body)
                store_id = request.session["store"]
                CurrentStore = store.objects.get(pk=store_id)
                user = models.InventaireAnnuel.objects.get(id=id_bon, store=CurrentStore)
                user.delete()
                return JsonResponse({'success': 'Inventaire Supprimé !'})
    except models.CustomUser.DoesNotExist:
        return JsonResponse({'error': 'Inventaire Non-trouve.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché - {}'.format(str(e))})

def supprimerEntrepot(request):
    try:
         # Find the product by reference
        data = json.loads(request.body)
        print(data)
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        user = models.Entrepot.objects.get(id=data["user_id"], store=CurrentStore)
               
        if user.inventories.all() :
           return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché, car cet entrepôt est lié aux autres composants'})
        else :
          user.delete()
          return JsonResponse({'success': 'Entrepôt Supprimé !'})
    except models.CustomUser.DoesNotExist:
        return JsonResponse({'error': 'Entrepôt Non-trouve.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché, car cet Entrepôt est lié aux autres composants - {}'.format(str(e))})
  
def modifierEntrepot (request):
        data = json.loads(request.body)
        Currentuser = request.user
        myuser = CustomUser.objects.get(username=Currentuser.username)
        store = request.session["store"]
        CurrentStore = models.store.objects.get(pk=store)
        entrepot_instance = models.Entrepot.objects.get(id=data["id"])
        entrepot_instance.name = data['lib']
        entrepot_instance.adresse = data['adresse']
        entrepot_instance.ville = data['ville']
        entrepot_instance.codePostal = data['postal']
        entrepot_instance.phone = data['phone']

        # Save the updated entrepot_instance
        entrepot_instance.save() 
        responsables_ids = data["responsables"]  
        print(responsables_ids)    
        for responsable_id in responsables_ids:
                responsable = CustomUser.objects.get(pk=responsable_id)
                responsable.entrepots_responsible=entrepot_instance
        return JsonResponse({'message': "Entrepot Modifié !"})
        
def deleteBillentry(request):
    data = json.loads(request.body)
    liste_id = data["liste_ids"]
    for id_bon in liste_id:
        with transaction.atomic():
            data = json.loads(request.body)
            store_id = request.session["store"]
            CurrentStore = store.objects.get(pk=store_id)
            try:
                bon_entry = models.BonEntry.objects.get(idBon=id_bon, store=CurrentStore)
            except models.BonEntry.DoesNotExist:
                response_data = {'message': 'Bon entrée invalide !'}
                return JsonResponse(response_data)

            # 2. Delete the related ProduitsEnBonEntry records

            # 3. Reverse the changes in stock quantities and product data
            for product_entry in bon_entry.produits_en_bon_entry.all():
                print(product_entry)
                product = product_entry.stock
                product.TotalQte -= product_entry.quantity
                product.initial_qte -= product_entry.quantity
                product.save()
                stock = models.Stock.objects.filter(product=product, entrepot=bon_entry.entrepot).first()
                if stock is not None:
                    if stock.quantity - product_entry.quantity < 0:
                        stock.quantity = 0
                        stock.save()
                    else:
                        stock.quantity -= product_entry.quantity
                        stock.save()
            models.ProduitsEnBonEntry.objects.filter(BonNo=bon_entry).delete()
            # 4. Delete the bill entry
            bon_entry.delete()
        response_data = {'message': 'BonS entrée sélectionnés Supprimés !'}
        return JsonResponse(response_data)

def fetchProducts(request):
  data = json.loads(request.body)
  bonLivraison = BonSortie.objects.get(idBon=data["bonL"])
  produits = bonLivraison.produits_en_bon_sorties.all()
  produits_data=[]    
  for produit in produits :
      produits_dict = {
              'name': produit.stock.name,
              'reference':produit.stock.reference,
              'quantity': produit.quantity,
              'unitprice': float(produit.unitprice),
              'totalprice': float(produit.totalprice),
              'numseries': produit.getnumSeries,
              'entrepot': produit.entrepot.name if produit.entrepot else "" 
            } 
      produits_data.append(produits_dict)
  return JsonResponse({'produits':produits_data})

def fetchProductsRetour(request):
  data = json.loads(request.body)
  if data["bonL"].startswith("BRA"):
    bonLivraison = models.BonRetourAncien.objects.get(idBon=data["bonL"])
    
    produits = bonLivraison.produits_en_bon_retourancien.all()
    produits_data=[]    
    for produit in produits :
        produits_dict = {
                'name': produit.nomproduit,
                'reference':produit.referenceproduit,
                'quantity': produit.quantity,
                'unitprice': float(produit.unitprice),
                'totalprice': float(produit.totalprice),
                } 
        produits_data.append(produits_dict)
  elif data["bonL"].startswith("BR"):
    bonLivraison = models.BonRetour.objects.get(idBon=data["bonL"])
    
    produits = bonLivraison.produits_en_bon_retour.all()
    produits_data=[]    
    for produit in produits :
        produits_dict = {
                'name': produit.produit.name,
                'reference':produit.produit.reference,
                'quantity': produit.quantity,
                'unitprice': float(produit.unitprice),
                'totalprice': float(produit.totalprice),
                } 
        produits_data.append(produits_dict)
  else:
    bonLivraison = BonRetourComptoir.objects.get(idBon=data["bonL"])
    
    produits = bonLivraison.produits_en_bon_retourcomptoir.all()
    produits_data=[]    
    for produit in produits :
        produits_dict = {
                'name': produit.produit.name,
                'reference':produit.produit.reference,
                'quantity': produit.quantity,
                'unitprice': float(produit.unitprice),
                'totalprice': float(produit.totalprice),
                } 
        produits_data.append(produits_dict)        
  return JsonResponse({'produits':produits_data})

def verifyPassword(request):
        data = json.loads(request.body)
        user = request.user
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        myuser = CustomUser.objects.get(username=user.username)
        # Verify if the provided password matches the current user's password
        print(myuser.username,data["password"])
        if user.check_password(data["password"]):
            bill_type = data.get("type","")
            bill_modif = data.get("modif","")
            if bill_type == "bs":
                with transaction.atomic():
                    bonTr = BonSortie.objects.get(id=data["idBon"])
                    print(data)                
                    if  bill_modif =="True":
                        bonTr.modifiable= True
                        bonTr.valide= False
                        bonTr.save()
                        responsable_entrepot = bonTr.user
                        if responsable_entrepot:
                                    notify.send(
                                        sender=myuser,
                                        recipient=responsable_entrepot,
                                        verb=f'Votre Demande de modification de Bon Numero {data["idBon"]} a été Accepté! Veuillez Cliquer Pour Acceder au Bon !',
                                        description=f'/ventes/edit-bill-diva/{bonTr.id}',
                                        level=1,
                                    )
                    else:
                        typevalidation = data["typevalidation"]
                        typeclientvalidation = data["typeclientvalidation"]
                        percent = data["percent"]
                        montantSolde = data["montantSolde"]
                        if typevalidation == "true":
                            validationBl.objects.create(
                                type_validation = 'special',
                                percentage = percent,
                                codeBl = bonTr.idBon,
                                montantBl = bonTr.get_total_price,
                                solde_note = montantSolde,
                                user = myuser,
                                client_name = bonTr.client.name
                            )
                        bonTr.valide=True
                        bonTr.save()
                        responsable_entrepot = CustomUser.objects.filter(role ="gestion-stock")
                        if responsable_entrepot:
                            for resp in responsable_entrepot : 
                                    notify.send(
                                        sender=myuser,
                                        recipient=resp,
                                        verb=f'Bon de Livraison numero {data["idBon"]} a été Validé! Veuillez Procéder à la création de bon de garantie et la préparation de la commande !',
                                        description=f'/ventes/bonsGarantie',
                                        level=1,
                                    )
            elif bill_type == "br": 
              if data["idBon"].startswith('BRA'):
                bonTr = models.BonRetourAncien.objects.get(idBon=data["idBon"])   
                bonTr.valide=True
                bonTr.save()
              else:    
                bonTr = models.BonRetour.objects.get(idBon=data["idBon"])   
                bonTr.valide=True
                if data["creationAutomatique"] :
                    current_year = timezone.now().year
                    boncomptoirs_this_year = models.BonReintegration.objects.filter(dateBon__year=current_year)
                    sequential_number = boncomptoirs_this_year.count() + 1
            
                    boncomptoire_code = f'BR{str(current_year)[-2:]}/{str(sequential_number).zfill(5)}'
                    existing_boncomptoire = models.BonReintegration.objects.filter(idBon=boncomptoire_code).first()
                    if existing_boncomptoire is not None :
                        while existing_boncomptoire is not None:
                            sequential_number += 1
                            boncomptoire_code = f'BR{str(current_year)[-2:]}/{str(sequential_number).zfill(5)}'
                            existing_boncomptoire = models.BonReintegration.objects.filter(idBon=boncomptoire_code).first()
                        boncomptoire_code = f'BR{str(current_year)[-2:]}/{str(sequential_number).zfill(5)}'
                    bon_reintegration= models.BonReintegration(
                        idBon=boncomptoire_code,
                        dateBon=timezone.now().date(),
                        bonRetour=bonTr,
                        entrepot=bonTr.bonL.entrepot,
                        store = CurrentStore,
                        user=myuser
                    )
                    bon_reintegration.save() 
                    intact_product =[]
                    produits_items = data["items"]
                    for produit in bonTr.produits_en_bon_retour.all():
                        if produit.reintegrated:
                            inact_product  ={
                                'ref': produit.produit.reference,
                                'qty': produit.quantity,
                            }
                            intact_product.append(inact_product)
                    for produit in produits_items:
                        product_instance = bonTr.produits_en_bon_retour.get(produit__reference = produit["ref"])  
                        if not product_instance.reintegrated:  
                            product_instance.warranty = True if produit["warranty"] == 'true' else False
                        
                    for product_intactData in intact_product:
                        product = Product.objects.get(reference=product_intactData["ref"] , store = CurrentStore)
                        stock, created = models.Stock.objects.get_or_create(product=product, entrepot=bonTr.bonL.entrepot)       
                        if created:
                            stock.quantity = int(product_intactData["qty"])
                            stock.save()
                        else:
                            stock.quantity += int(product_intactData["qty"])
                            stock.save() 

                        product.TotalQte += int(product_intactData["qty"])
                        product.save()                   
                        models.ProduitsEnBonReintegration.objects.create(
                            BonNo=bon_reintegration,
                            stock=product,
                            quantity=int(product_intactData["qty"]),
                        ) 
                bonTr.save()     
            else:    
                 print('fares')
                 bonTr = models.BonTransfert.objects.get(idBon=data["idBon"])
                 for produit in bonTr.produits_en_bon_transfert.all():              
                    # Update the stock quantity in the source entrepot
                    new_quantity_in_source = produit.stock_dep.quantity - int(produit.quantity)
                    if new_quantity_in_source < 0:
                        return JsonResponse({
                            'error': f"Insufficient stock for product: {produit.stock_dep.product.reference}",
                            'prompt_user': True
                        })
                 for produit in bonTr.produits_en_bon_transfert.all():              
                    # Update the stock quantity in the source entrepot
                    new_quantity_in_source = produit.stock_dep.quantity - int(produit.quantity)
                    produit.stock_dep.quantity = new_quantity_in_source
                    produit.stock_dep.save()
               
                    demande = DemandeTransfert.objects.get(BonTransfert = bonTr )
                    demande.etat = 'True'
                    demande.save()
                    responsable_entrepot = CustomUser.objects.filter(role ="manager")
                    if responsable_entrepot:
                        for resp in responsable_entrepot : 
                                notify.send(
                                    sender=myuser,
                                    recipient=resp,
                                    verb=f'Bon de Livraison numero {demande.BonSNo.idBon} a été créer  par {demande.BonSNo.user.username} , Veuillez valider',
                                    description=f'/ventes/edit-bill-diva/{demande.BonSNo.id}',
                                    level=1,
                                )
                 bonTr.valide=True
                 bonTr.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False})

def delete_reinteg_bill(request):
    data = json.loads(request.body)
    liste_id = data["liste_ids"]
    for id_bon in liste_id:
        with transaction.atomic():
            data = json.loads(request.body)
            store_id = request.session["store"]
            CurrentStore = store.objects.get(pk=store_id)
            try:
                bon_entry = models.BonReintegration.objects.get(idBon=id_bon, store=CurrentStore)
            except models.BonEntry.DoesNotExist:
                response_data = {'message': 'Bon de Re-integration invalide !'}
                return JsonResponse(response_data)

            # 2. Delete the related ProduitsEnBonEntry records

            # 3. Reverse the changes in stock quantities and product data
            for product_entry in bon_entry.produits_en_bon_reintegration.all():
                product = product_entry.stock
                product.TotalQte -= product_entry.quantity
                product.initial_qte -= product_entry.quantity
                product.save()
                stock = models.Stock.objects.get(product=product, entrepot=bon_entry.entrepot)
                if stock.quantity - product_entry.quantity < 0:
                    return JsonResponse({'message': 'Bon Re-integration ne peut pas être supprimé !'})
                else:
                    stock.quantity -= product_entry.quantity
                    stock.save()
                if stock.quantity == 0:
                    stock.delete()

            models.ProduitsEnBonReintegration.objects.filter(BonNo=bon_entry).delete()
            # 4. Delete the bill entry
            bon_entry.delete()
        response_data = {'message': 'Bons sélectionnés Supprimés !'}
        return JsonResponse(response_data)
    
def delete_retour_bill(request):
    data = json.loads(request.body)
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    liste_ids = data["liste_ids"]
    for id_bon in liste_ids:
        bon_c = models.BonRetour.objects.get(idBon=id_bon, store=CurrentStore)
        with transaction.atomic():
            # Get the associated product transfers
            produits_transfert =  models.ProduitsEnBonRetour.objects.filter(BonNo=bon_c)
            my_entrepot = bon_c.bonL.entrepot
            
            for produit_transfert in produits_transfert:
                quantity_product = produit_transfert.quantity

                # Check if the quantity is zero

                mon_stock = models.Stock.objects.get(entrepot=my_entrepot, product=produit_transfert.produit )
                
                if mon_stock.quantity == 0:
                    return JsonResponse({'message': "Bon ne peut pas être supprimé ! Produits de bon vide"})

                # Update the source warehouse stock quantity
                mon_stock.quantity -= quantity_product
                mon_stock.save()

                produit_transfert.delete()

            bon_c.delete()
    return JsonResponse({'message': "Bons de retour Supprimes."})   
  
def delete_sorties_bill(request):
    data = json.loads(request.body)
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    liste_id = data["liste_ids"]
    for id_bon in liste_id:
        bon_Sortie= models.Bonsortiedestock.objects.get(idBon=id_bon, store=CurrentStore)
        bon_Sortie.delete()
        
    return JsonResponse({'message': "Elements Supprimés!."})    

def delete_reforme_bill(request):
    data = json.loads(request.body)
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    liste_ids = data["liste_ids"]
    for id_bon in liste_ids:
        bon_c = models.BonReforme.objects.get(idBon=id_bon, store=CurrentStore)
        with transaction.atomic():
            bon_c.delete()
    return JsonResponse({'message': "Bons de Reforme Supprimes."})        

def delete_maintenance_bill(request):
    data = json.loads(request.body)
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    liste_ids = data["liste_ids"]
    for id_bon in liste_ids:
        bon_c = models.BonMaintenance.objects.get(idBon=id_bon, store=CurrentStore)
        with transaction.atomic():
            bon_c.delete()
    return JsonResponse({'message': "Bons de Maintenance Supprimés!"})

class stockStateInventory(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/etat_stocks.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return self.request.session["username"] == "nadjemeddine" or self.request.session["role"] == "gestion-stock"

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('inventory'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        selected_store = store.objects.get(pk=self.request.session["store"])
        products = Product.objects.filter(store=selected_store, parent_product__isnull=True)
        product_families = Category.objects.filter(store=selected_store)
        fournisseurs = Fournisseur.objects.filter(store=selected_store)
        entrepots = models.Entrepot.objects.filter(store=selected_store)
        if self.request.session["role"] == "gestion-stock": 
            stocks_all = models.Stock.objects.filter(product__store=selected_store, entrepot__name ="Depot principal Reghaia")
        elif self.request.session["username"] == "nadjemeddine":
            stocks_all = models.Stock.objects.filter(product__store=selected_store, entrepot__name ="PARKMALL SETIF")
            
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

class StockAncienRetourView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/bon_retour_ancien.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonretour' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        selected_store =store.objects.get(pk=self.request.session["store"])
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        if(myuser.role =='manager' or myuser.entrepots_responsible is not None):
          bons_sorties = BonSortie.objects.filter(store=selected_store)
        else: 
          bons_sorties = BonSortie.objects.filter(store=selected_store, user = myuser)
        context["selected_store"] = selected_store    
        store_id = self.request.session["store"]
        my_store = models.store.objects.get(pk=store_id)
     
        entrepots = models.Entrepot.objects.filter(store=my_store)
          # Step 3: Get all the stocks associated with each Entrepot
        all_stocks = []
        for entrepot in entrepots:
            stocks_for_entrepot = entrepot.get_stocks()
            all_stocks.extend(stocks_for_entrepot)
        context["bons_sorties"]=bons_sorties
        context["stock"] = all_stocks
        modeReg = ModeReglement.objects.all() 
        context["modeReg"]=modeReg  
        echeances = EcheanceReglement.objects.all() 
        context["echeances"] = echeances 
        banques= Banque.objects.all()
        context["banques"] = banques
        current_year = datetime.now().strftime('%y')
        current_month = datetime.now().strftime('%m')
        last_bon = models.BonRetourAncien.objects.order_by('-id').first()
        if last_bon:
            last_id = last_bon.idBon.split('-')[-1]
            if last_id.isnumeric():
                sequence_number = int(last_id) + 1
            else:
                sequence_number = 1
        else:
            sequence_number = 1
        codeBon = f'BRA{current_year}{current_month}-{sequence_number}' 
        context["code"] = codeBon
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData', '')
        if dataInvoice:
          with transaction.atomic(): 
               idBon =dataInvoice["IdBon"]
               dateBon =dataInvoice["dateBp"]
               total = dataInvoice["Total"]
               store_id = self.request.session["store"]
               my_store = models.store.objects.get(pk=store_id)
               Currentuser = self.request.user
               myuser  = CustomUser.objects.get(username=Currentuser.username)
               client_info = dataInvoice['clientInfo']
               
               # Create or get the client
               client_name = client_info['name']
               client_address = client_info['address']
               client_phone = client_info['phone']           
               current_year = datetime.now().strftime('%y')
               current_month = datetime.now().strftime('%m')
               last_bon = models.BonRetourAncien.objects.order_by('-id').first()
               if last_bon:
                 last_id = last_bon.idBon.split('-')[-1]
                 if last_id.isnumeric():
                    sequence_number = int(last_id) + 1
                 else:
                    sequence_number = 1
               else:
                  sequence_number = 1
               codeBon = f'BRA{current_year}{current_month}-{sequence_number}'  
               entrepot_obj = models.Entrepot.objects.get(name ="Depot principal Reghaia", store = my_store)
               bon_retour = models.BonRetourAncien.objects.create(idBon=codeBon , dateBon=dateBon, bonL =dataInvoice['AssociatedBL'], entrepot = entrepot_obj, totalPrice=total, client=client_name, store=my_store, user=myuser)
               products = dataInvoice["produits"]                          
               for product in products:
                 prod_total_price = float(product["rate"]) * int(product["qty"])
                 product_instance = models.ProduitsEnBonRetourAncien.objects.create(
                  BonNo=bon_retour,
                  referenceproduit = product["ref"],
                  nomproduit = product["name"],
                  quantity=int(product["qty"]),
                  numseries = product["numserie"],
                  unitprice=float(product["rate"]),              
                  totalprice=prod_total_price
                 )          
                 if product['etat']=='Intacte':                     
                        product_instance.reintegrated = True
                        product_instance.save()
    
                # Create the codeAvoir using the year and sequential number
               responsable_entrepot = CustomUser.objects.filter(entrepots_responsible=entrepot_obj).first()
               if responsable_entrepot:
                notify.send(
                    sender=myuser,
                    recipient=responsable_entrepot,
                    verb=f' - Bon de Retour numero {bon_retour.idBon} a été créer par {myuser} , Veuillez valider',
                    description=f'/stock/edit/retour/{bon_retour.id}',
                    level=1,
                )
        return JsonResponse({'message': "Product Added successfully."})
        
class TransfertMAGListView(TemplateView):
    template_name = "inventory/transfertMag_Page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bontransfert' in self.request.session.get('permissions', [])  
    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)        
        # store_id = self.kwargs.get('store_id')
        selected_store = store.objects.get(pk=self.request.session["store"])        
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        if myuser.role == 'manager':
            bons_sorties = models.BonTransfertMagasin.objects.filter(Q(store_depart=selected_store) | Q(store_arrive=selected_store))
        else:
            stock = models.Stock.objects.filter(product__store=selected_store)
            categories = Category.objects.filter(store=selected_store)
            bons_sorties = models.BonTransfertMagasin.objects.filter(Q(store_depart=selected_store) | Q(store_arrive=selected_store))
        
        context["bons_sorties"] = bons_sorties 
          
        entrepots = models.Entrepot.objects.filter(store=selected_store)
        context["entrepots"] = entrepots
        users_bills = CustomUser.objects.filter(EmployeeAt=selected_store)
        context["users"]=users_bills
        return context

class UpdateStockMaintenanceView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/bon_maintenance_end.html"  
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'inventory.can_create_bon_maintenance' in self.request.session.get('permissions', []) or self.request.session["role"] == 'manager'

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
        bill_id=self.kwargs.get('id_bill')
        bill_sortie = models.BonMaintenance.objects.get(id=bill_id)
        liste_retour = []        
        bons_retour = models.BonRetour.objects.filter(store=CurrentStore)
        
        for bon in bons_retour:
            liste_retour.append(bon)            
            
        bons_retour_comptoir = BonRetourComptoir.objects.filter(bon_comptoir_associe__store=CurrentStore)
        for bon in bons_retour_comptoir:
            liste_retour.append(bon)   
            
        bons_retours_data = []
        for bon in liste_retour:
            bon_dict ={
                'idBon': bon.idBon,
                'clientName': bon.bonL.client.name if bon.idBon.startswith('BR') else bon.bon_comptoir_associe.client.name,
                'phone': bon.bonL.client.phone if bon.idBon.startswith('BR') else bon.bon_comptoir_associe.client.phone,
                'address': bon.bonL.client.adresse if bon.idBon.startswith('BR') else bon.bon_comptoir_associe.client.adresse,
                'category': bon.bonL.client.categorie_client.id if bon.idBon.startswith('BR') else bon.bon_comptoir_associe.client.categorie_client.id,
                'entrepot': bon.bonL.entrepot.name if bon.idBon.startswith('BR') else bon.bon_comptoir_associe.monentrepot,
            }    
            bons_retours_data.append(bon_dict)
        context["bons_commandes"]= bons_retours_data
        entrepots = models.Entrepot.objects.filter(store= selected_store)
        context["entrepots"]=entrepots   
        context["bill"] = bill_sortie
        produit_bon =[]
        for produit in bill_sortie.produits_en_bon_maintenance.all():
            produit_bon.append({
                'reference': produit.produit.reference,
                'name': produit.produit.name,
                'quantity': produit.quantity,
                'observation': eval(produit.observation) if ',' in produit.observation else produit.observation
            })
        context["items"] = produit_bon
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
        bon_id = dataInvoice['IdBon']
        bon_date = datetime.strptime(dataInvoice['dateBp'], '%Y-%m-%d').date()
        client_name = dataInvoice['clientInfo']['name']
        bon_retour_id = dataInvoice['bon_retour']
        decision_bill = dataInvoice['decisionBill']
        produits_data = dataInvoice['produits_obs']
        bonretour = None
        bonretourC = None
        entrepot = None
        # if bon_retour_id.startswith('BR'):
        #     bonretour =models.BonRetour.objects.get(idBon=bon_retour_id)
        #     entrepot = bonretour.bonL.entrepot
        # else:
        #     bonretourC = BonRetourComptoir.objects.get(idBon=bon_retour_id) 
        #     entrepot = models.Entrepot.objects.get(name = bonretourC.bon_comptoir_associe.monentrepot, store = CurrentStore)
        # # Creating BonMaintenance instance
        # with transaction.atomic():
        #     bon_maintenance = models.BonMaintenance.objects.create(
        #         idBon=bon_id,
        #         dateBon=bon_date,
        #         totalPrice=dataInvoice['fraisManoeuvre'],  # You may adjust this based on your requirements
        #         bonL=bonretour,
        #         bonLComptoir=bonretourC,
        #         valide= decision_bill,
        #         store=CurrentStore,  # Assuming you have a Store model and change the pk value
        #         user=myuser,  # You may set a user if available
        #         entrepot=entrepot,  # You may set an entrepot if available
        #         observation=dataInvoice.get('rapportBill', '')
        #     )

        #     # Creating ProduitsEnBonMaintenance instances
        #     for produit_data in produits_data:
        #         produit = models.ProduitsEnBonMaintenance.objects.create(
        #             BonNo=bon_maintenance,
        #             produit=Product.objects.get(reference=produit_data['ref'], store = CurrentStore),  # Assuming you have a Product model and change the field used for reference
        #             quantity=int(produit_data['qty']),
        #             observation=produit_data.get('observation', '')
        #         )
        # if dataInvoice["decisionBill"]:
        #     idBon = dataInvoice["IdBon"]
        #     dateBon = dataInvoice["dateBp"]
        #     client_info = dataInvoice['clientInfo']
        #     agenceLivraison = dataInvoice.get("agencelivraison", "divatech")

        #     # Create or get the client
        #     client_name = client_info['name']
        #     client= Client.objects.filter(name=client_name).first()
        #     currentEntrepot = entrepot
        #     for product in dataInvoice["produits"]:            
        #         p = models.Stock.objects.select_for_update().get( Q(product__reference=product["ref"]) & Q(entrepot__name=currentEntrepot))
        #         new_quantity = p.quantity - int(product["qty"])
        #         if new_quantity < 0:
        #             # If any product has insufficient quantity, return a response to inform the user
        #             return JsonResponse({'error': f"Insufficient stock for product: {product['ref']}", 'prompt_user': True})            
        #         p.quantity = new_quantity
        #         p.save()
                
        #     current_year = timezone.now().year
        #     current_month = datetime.now().strftime('%m')
            
        #     # Filter BonComptoir instances created in the current year
        #     boncomptoirs_this_year = BonSortie.objects.filter(dateBon__year=current_year, idBon__startswith='BECH',dateBon__month= current_month, store__id =1)

        #     # Get the count of BonComptoir instances in the current year
        #     sequential_number = boncomptoirs_this_year.count() + 1

        #     boncomptoire_code = f'BECH{str(current_year)[-2:]}{str(current_month)}/{str(sequential_number).zfill(5)}'  
        #     bon_sortie = BonSortie.objects.create(
        #         idBon = boncomptoire_code,
        #         dateBon = dateBon,
        #         totalPrice = 0,
        #         num_cheque_reglement = bon_maintenance.idBon,
        #         entrepot = currentEntrepot, 
        #         client = client, user = myuser, store = CurrentStore
        #     )
        #     totalprice_bons = 0
        #     for product in dataInvoice["produits"]:
        #             p = Product.objects.get(reference=product["ref"], store = CurrentStore)
        #             p.TotalQte -= int(product["qty"])
        #             p.save()
        #             prod_total_price = float(product["rateLiv"]) * int(product["qty"])
        #             entrepot_inst = currentEntrepot
        #             models.ProduitsEnBonSortie.objects.create(
        #                 BonNo=bon_sortie,
        #                 stock=p,
        #                 entrepot=entrepot_inst,
        #                 quantity=int(product["qty"]),
        #                 unitprice= float(product["rateLiv"]),
        #                 totalprice=prod_total_price
        #             )
        #             totalprice_bons += prod_total_price
        #     bon_sortie.totalPrice = totalprice_bons
        #     bon_sortie.save()        
        #     responsable_entrepot = CustomUser.objects.filter(role ="manager")
        #     if responsable_entrepot:
        #         for resp in responsable_entrepot : 
        #                 notify.send(
        #                     sender=myuser,
        #                     recipient=resp,
        #                     verb=f'Bon d\'échange numero {idBon} a été créer Automatiquement lors de création de bon de Maintenance par {myuser} , Veuillez valider',
        #                     description=f'/ventes/edit-bill-diva/{bon_sortie.id}',
        #                     level=1,
        #                 )
        
        return JsonResponse({'message': "Bill Added successfully."})
        
class StockTransfertStore(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/transfert_bill_magasins.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bontransfert' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        # Get the selected store using the session data
        selected_store_id = self.request.session.get("store")
        selected_store = store.objects.get(pk=selected_store_id)

        # Create a list of dictionaries to store the store-entrepot associations
        store_entrepot_info = []

        # Loop through all stores and their associated entrepots
        for store_ins in store.objects.all():
            for entrepot in store_ins.get_entrepots():
                store_entrepot_info.append({
                    'store_name': store_ins.name,
                    'entrepot_name': entrepot.name
                })

        # Add the data to the context
        context["selected_store"] = selected_store
        context["entrepots"] = store_entrepot_info

        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, *args, **kwargs): 
      data = json.loads(request.body)
      dataInvoice = data.get('formData', '')
      Currentuser = request.user
      selected_store = store.objects.get(pk=self.request.session["store"])  
      myuser  = CustomUser.objects.get(username=Currentuser.username)
      if dataInvoice:
        idBon = dataInvoice["IdBon"]
        dateBon = dataInvoice["dateBp"]

        # Create or get the client
        split_values = dataInvoice['ent_dep']['name'].split('-')

            # Extract the individual components
        store_name = split_values[0]
        entrepot_name = split_values[1]
        store_dep = store.objects.get(name = store_name)
        
        entrepot_dep = models.Entrepot.objects.get(name = entrepot_name, store=store_dep)
        ent_dep= dataInvoice['ent_dep']['name']
        split_values = dataInvoice['ent_arr']['name'].split('-')

            # Extract the individual components
        store_name = split_values[0]
        entrepot_name = split_values[1]
        store_arr = store.objects.get(name = store_name)
        
        entrepot_arr = models.Entrepot.objects.get(name = entrepot_name, store=store_arr)
        products_to_update = []
        with transaction.atomic():
            for product in dataInvoice["produits"]:
                # Retrieve the stock entry for the product in the source warehouse (ent_dep)
                product_inst = Product.objects.get(reference = product["ref"], store = store_dep)
                stock_in_source = models.Stock.objects.select_for_update().get(
                    product=product_inst, entrepot=entrepot_dep
                )
                new_quantity_in_source = stock_in_source.quantity - int(product["qty"])

                # Check if the source warehouse has enough quantity
                if new_quantity_in_source < 0:
                    return JsonResponse({
                        'error': f"Insufficient stock for product: {product['ref']}",
                        'prompt_user': True
                    })

                products_to_update.append((stock_in_source, new_quantity_in_source))
                print(product['ref'])
                product_inst_arr = Product.objects.get(reference = product['ref'], store= store_arr)
                try:
                    stock_in_destination = models.Stock.objects.get(
                        product=product_inst_arr,
                        entrepot=entrepot_arr,
                        entrepot__store = store_arr,
                    )
                except models.Stock.DoesNotExist:
                    # If the stock entry doesn't exist, create it
                    stock_in_destination = models.Stock.objects.create(
                        product=product_inst_arr,
                        entrepot=entrepot_arr,
                        quantity=int(product["qty"])  # Initialize with the transferred quantity
                    )
                else:
                    # If the stock entry exists, update the quantity
                    stock_in_destination.quantity += int(product["qty"])
                    stock_in_destination.save()
            print('entrepot dep', entrepot_dep)
            print('store_depart', store_dep)
            print('store_arrive', store_arr)
            print('entrepot_arrive', entrepot_arr)

            # Update source warehouse quantities and create transfer bill
            bon_trans = models.BonTransfertMagasin.objects.create(
                idBon=dataInvoice["IdBon"],
                dateBon=dataInvoice["dateBp"],
                entrepot_depart=entrepot_dep,
                store_depart = store_dep,
                store_arrive = store_arr,
                entrepot_arrive = entrepot_arr,
                store= selected_store , 
                user=myuser
            )
            for product in dataInvoice["produits"]:
                quantite = int(product['qty'])
                # Retrieve the stock entry for the product in the source warehouse (ent_dep)
                product_inst = Product.objects.get(reference = product["ref"], store = store_dep)
                stock_in_source = models.Stock.objects.select_for_update().get(
                    product=product_inst, entrepot = entrepot_dep
                )            
                product_inst_arr = Product.objects.get(reference = product["ref"], store = store_arr)
                # Retrieve or create the stock entry in the destination warehouse (ent_arr)
                stock_in_destination = models.Stock.objects.get(
                    product=product_inst_arr,
                    entrepot=entrepot_arr,
                )

                models.ProduitsEnBonTransfertMag.objects.create(
                    BonNo=bon_trans,
                    stock_dep=stock_in_source,
                    stock_arr= stock_in_destination,
                    quantity= quantite,                 
                )
            for stock, new_quantity in products_to_update:
                stock.quantity = new_quantity
                stock.save()

                # Create a record in ProduitsEnBonSortie for the transfer

            return JsonResponse({'message': "Products transferred successfully."})
            
class MaintenanceListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/maintenance_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_create_bon_maintenance' in self.request.session.get('permissions', []) or self.request.session["role"] == 'manager' or self.request.session["role"] == 'DIRECTEUR EXECUTIF'

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        Currentuser = self.request.user
        currentStore= store.objects.get(pk=self.request.session["store"])
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        bons_sorties = models.BonMaintenance.objects.filter(store=currentStore)
        context["bons"]=bons_sorties
        
        entrepots = models.Entrepot.objects.filter(store=currentStore)
        context["entrepots"] = entrepots
        users_bills = Fournisseur.objects.filter(store=currentStore)
        context["users"]=users_bills
        return context
        
class StockMaintenanceView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/bon_maintenance.html"  
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'inventory.can_create_bon_maintenance' in self.request.session.get('permissions', []) or self.request.session["role"] == 'manager' or self.request.session["role"] == 'DIRECTEUR EXECUTIF'

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
         clients_list = Client.objects.filter(store=CurrentStore)
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
          clientsList = Client.objects.filter(user=Currentuser)
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

        liste_retour = []        
        bons_retour = models.BonRetour.objects.filter(store=CurrentStore)
        
        for bon in bons_retour:
            liste_retour.append(bon)            
            
        bons_retour_comptoir = BonRetourComptoir.objects.filter(bon_comptoir_associe__store=CurrentStore)
        for bon in bons_retour_comptoir:
            liste_retour.append(bon)   
            
        bons_retour_anciens = models.BonRetourAncien.objects.filter(store=CurrentStore)
        for bon in bons_retour_anciens:
            liste_retour.append(bon)   
            
        bons_retours_data = []
        for bon in liste_retour:
            if not bon.idBon.startswith('BRA'):
                bon_dict ={
                    'idBon': bon.idBon,
                    'clientName': bon.bonL.client.name if bon.idBon.startswith('BR') else bon.bon_comptoir_associe.client.name,
                    'phone': bon.bonL.client.phone if bon.idBon.startswith('BR') else bon.bon_comptoir_associe.client.phone,
                    'address': bon.bonL.client.adresse if bon.idBon.startswith('BR') else bon.bon_comptoir_associe.client.adresse,
                    'category': bon.bonL.client.categorie_client.id if bon.idBon.startswith('BR') else bon.bon_comptoir_associe.client.categorie_client.id,
                    'entrepot': bon.bonL.entrepot.name if bon.idBon.startswith('BR') else bon.bon_comptoir_associe.monentrepot,
                }    
            else:
                bon_dict ={
                    'idBon': bon.idBon,
                    'clientName': bon.client,
                    'entrepot': bon.entrepot.name,
                }  
            bons_retours_data.append(bon_dict)
        context["bons_commandes"]= bons_retours_data
        entrepots = models.Entrepot.objects.filter(store= selected_store)
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
        current_month = datetime.now().strftime('%m')
        
        # Filter BonComptoir instances created in the current year
        boncomptoirs_this_year = models.BonMaintenance.objects.filter(dateBon__year=current_year,dateBon__month= current_month, store__id =1)

        # Get the count of BonComptoir instances in the current year
        sequential_number = boncomptoirs_this_year.count() + 1

        boncomptoire_code = f'BM{str(current_year)[-2:]}{str(current_month)}/{str(sequential_number).zfill(5)}'
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
        bon_id = dataInvoice['IdBon']
        bon_date = datetime.strptime(dataInvoice['dateBp'], '%Y-%m-%d').date()
        client_name = dataInvoice['clientInfo']['name']
        bon_retour_id = dataInvoice['bon_retour']
        decision_bill = dataInvoice['decisionBill']
        produits_data = dataInvoice['produits_obs']
        bonretour = None
        bonretourC = None
        entrepot = None
        if not bon_retour_id.startswith('BRA'):
            if bon_retour_id.startswith('BR'):
                bonretour =models.BonRetour.objects.get(idBon=bon_retour_id)
                entrepot = bonretour.bonL.entrepot
            elif bon_retour_id.startswith('RCOMPT') :
                bonretourC = BonRetourComptoir.objects.get(idBon=bon_retour_id) 
                entrepot = models.Entrepot.objects.get(name = bonretourC.bon_comptoir_associe.monentrepot, store = CurrentStore)
        else:
            bonretour = None
        # Creating BonMaintenance instance
        with transaction.atomic():
            bon_maintenance = models.BonMaintenance.objects.create(
                idBon=bon_id,
                dateBon=bon_date,
                totalPrice=dataInvoice['fraisManoeuvre'],  # You may adjust this based on your requirements
                bonL=bonretour,
                bonLComptoir=bonretourC,
                decision = decision_bill,
                store=CurrentStore,  # Assuming you have a Store model and change the pk value
                user=myuser,  # You may set a user if available
                entrepot=entrepot,  # You may set an entrepot if available
                observation=dataInvoice.get('rapportBill', '')
            )

            # Creating ProduitsEnBonMaintenance instances
            for produit_data in produits_data:
                
                produit_inst = Product.objects.filter(reference=produit_data["ref"], store=CurrentStore).first()
                if produit_inst is None:
                    # Create the product if it doesn't exist
                    produit_inst = Product.objects.create(
                        reference=produit_data["ref"],
                        name = produit_data["ref"],
                        prix_vente = 0,
                        initial_qte = 1,
                        store=CurrentStore,
                    )
                produit = models.ProduitsEnBonMaintenance.objects.create(
                    BonNo=bon_maintenance,
                    produit=produit_inst,  # Assuming you have a Product model and change the field used for reference
                    quantity=int(produit_data['qty']),
                    observation=produit_data.get('observation', '')
                )
            if dataInvoice["decisionBill"] == 'Echange':
                idBon = dataInvoice["IdBon"]
                dateBon = dataInvoice["dateBp"]
                client_info = dataInvoice['clientInfo']
                agenceLivraison = dataInvoice.get("agencelivraison", "divatech")

                # Create or get the client
                client_name = client_info['name']
                client= Client.objects.filter(name=client_name).first()
                currentEntrepot = entrepot
                for product in dataInvoice["produits"]:     
                    print(product)
                    p = models.Stock.objects.select_for_update().get( Q(product__reference=product["ref"]) & Q(entrepot__name=currentEntrepot))
                    new_quantity = p.quantity - int(product["qty"])
                    if new_quantity < 0:
                        # If any product has insufficient quantity, return a response to inform the user
                        return JsonResponse({'error': f"Insufficient stock for product: {product['ref']}", 'prompt_user': True})            
                    
                current_year = timezone.now().year
                current_month = datetime.now().strftime('%m')
                
                # Filter BonComptoir instances created in the current year
                boncomptoirs_this_year = BonSortie.objects.filter(dateBon__year=current_year, idBon__startswith='BECH',dateBon__month= current_month, store__id =1)

                # Get the count of BonComptoir instances in the current year
                sequential_number = boncomptoirs_this_year.count() + 1

                boncomptoire_code = f'BECH{str(current_year)[-2:]}{str(current_month)}/{str(sequential_number).zfill(5)}'  
                bon_sortie = BonSortie.objects.create(
                    idBon = boncomptoire_code,
                    dateBon = dateBon,
                    totalPrice = 0,
                    num_cheque_reglement = bon_maintenance.idBon,
                    entrepot = currentEntrepot, 
                    client = client, user = myuser, store = CurrentStore
                )
                totalprice_bons = 0
                for product in dataInvoice["produits"]:
                        p = Product.objects.get(reference=product["ref"], store = CurrentStore)
                        p.TotalQte -= int(product["qty"])
                        p.save()
                        prod_total_price = float(product["rateLiv"]) * int(product["qty"])
                        entrepot_inst = currentEntrepot
                        models.ProduitsEnBonSortie.objects.create(
                            BonNo=bon_sortie,
                            stock=p,
                            entrepot=entrepot_inst,
                            quantity=int(product["qty"]),
                            unitprice= float(product["rateLiv"]),
                            totalprice=prod_total_price
                        )
                        totalprice_bons += prod_total_price
                bon_sortie.totalPrice = totalprice_bons
                bon_sortie.save()        
                responsable_entrepot = CustomUser.objects.filter(
                    Q(role="manager") | Q(username="fares")
                )
                if responsable_entrepot:
                    for resp in responsable_entrepot : 
                            notify.send(
                                sender=myuser,
                                recipient=resp,
                                verb=f'Bon d\'échange numero {idBon} a été créer Automatiquement lors de création de bon de Maintenance par {myuser} , Veuillez valider',
                                description=f'/ventes/edit-bill-diva/{bon_sortie.id}',
                                level=1,
                            )
        return JsonResponse({'message': "Bill Added successfully."})
        
class AnnuelInv(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/inventaires_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonentres' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        AnnuelsInv = models.InventaireAnnuel.objects.filter(store=CurrentStore)
        entrepots = models.Entrepot.objects.filter(store=CurrentStore)
        context["entrepots"] = entrepots
        context["inventaires"] = AnnuelsInv
        return context

class EchangeListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/echange_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_create_echange_bill' in self.request.session.get('permissions', []) or self.request.session["role"] == 'manager'

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        Currentuser = self.request.user
        currentStore= store.objects.get(pk=self.request.session["store"])
        myuser  = CustomUser.objects.get(username=Currentuser.username)

        if myuser.role == 'manager':
            bons_sorties = BonSortie.objects.filter(store=currentStore, idBon__startswith='BECH')
        else:
            bons_sorties = BonSortie.objects.filter(store=currentStore, user=myuser, idBon__startswith='BECH')

        context["bons"]=bons_sorties
        
        entrepots = models.Entrepot.objects.filter(store=currentStore)
        context["entrepots"] = entrepots
        users_bills = Fournisseur.objects.filter(store=currentStore)
        context["users"]=users_bills
        return context
        
class StockEchangeView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/bon_echange.html"  
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_create_echange_bill' in self.request.session.get('permissions', []) or self.request.session["role"] == 'manager'

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
        if(myuser.role =='manager' or myuser.username == "fares"):
         clients_list = Client.objects.filter(store=CurrentStore)
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
          clientsList = Client.objects.filter(user=Currentuser)
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
        if(myuser.role =='manager' or myuser.username == "fares"):
            liste_retour = []        
            bons_retour = models.BonRetour.objects.filter(store=CurrentStore)
            
            for bon in bons_retour:
                liste_retour.append(bon)            
                
            bons_retour_anciens = models.BonRetourAncien.objects.filter(store=CurrentStore)
            for bon in bons_retour_anciens:
                liste_retour.append(bon)  
        else:    
            liste_retour = []        
            bons_retour = models.BonRetour.objects.filter(store=CurrentStore, user = myuser)
            
            for bon in bons_retour:
                liste_retour.append(bon)            
                
            bons_retour_anciens = models.BonRetourAncien.objects.filter(store=CurrentStore, user = myuser)
            for bon in bons_retour_anciens:
                liste_retour.append(bon)  
                
        context["bons_commandes"]= liste_retour
        entrepots = models.Entrepot.objects.filter(store= selected_store)
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
        current_month = datetime.now().strftime('%m')
        
        # Filter BonComptoir instances created in the current year
        boncomptoirs_this_year = BonSortie.objects.filter(dateBon__year=current_year, idBon__startswith='BECH',dateBon__month= current_month, store__id =1)

        # Get the count of BonComptoir instances in the current year
        sequential_number = boncomptoirs_this_year.count() + 1

        boncomptoire_code = f'BECH{str(current_year)[-2:]}{str(current_month)}/{str(sequential_number).zfill(5)}'
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
        fraislivraisonext = 0
        if dataInvoice.get('fraislivraisonext') :
            fraislivraisonext = dataInvoice['fraislivraisonext']

        client_info = dataInvoice['clientInfo']
        agenceLivraison = dataInvoice.get("agencelivraison", "divatech")

        # Create or get the client
        client_name = client_info['name']
        client= Client.objects.filter(name=client_name).first()
        currentEntrepot = models.Entrepot.objects.get(name=dataInvoice["entrepotBon"]) 
        
        
        for product in dataInvoice["produits"]:            
            p = models.Stock.objects.select_for_update().get( Q(product__reference=product["ref"]) & Q(entrepot__name=currentEntrepot))
            new_quantity = p.quantity - int(product["qty"]) ## la quantité dans l'entrepot qui convient
            if new_quantity < 0:
                # If any product has insufficient quantity, return a response to inform the user
                return JsonResponse({'error': f"Insufficient stock for product: {product['ref']}", 'prompt_user': True})            
            p.quantity = new_quantity
            p.save()
            
        bon_retour = ""
        if dataInvoice.get('bon_retour','') != '':
           bon_retour = dataInvoice["bon_retour"]
           
        bon_sortie = BonSortie.objects.create(
            idBon=idBon,
            dateBon=dateBon,
            totalPrice=total,
            agenceLivraison=agenceLivraison,
            fraisLivraison = fraisLivraison,
            fraisLivraisonexterne = fraislivraisonext,
            mode_reglement = modereg,
            num_cheque_reglement = bon_retour,
            Remise = remise,
            entrepot=currentEntrepot, 
            client=client, user=myuser, store=CurrentStore
        )
        
        
                 
        for product in dataInvoice["produits"]:
                p = Product.objects.get(reference=product["ref"], store = CurrentStore)
                p.TotalQte -= int(product["qty"])
                p.save()
                prod_total_price = float(product["rateLiv"]) * int(product["qty"])
                entrepot_inst = currentEntrepot
                models.ProduitsEnBonSortie.objects.create(
                    BonNo=bon_sortie,
                    stock=p,
                    entrepot=entrepot_inst,
                    quantity=int(product["qty"]),
                    unitprice= float(product["rateLiv"]),
                    totalprice=prod_total_price
        )
                
        responsable_entrepot = CustomUser.objects.filter(role ="manager")
        if responsable_entrepot:
           for resp in responsable_entrepot : 
                notify.send(
                    sender=myuser,
                    recipient=resp,
                    verb=f'Bon d\'échange numero {idBon} a été créer  par {myuser} , Veuillez valider',
                    description=f'/ventes/edit-bill-diva/{bon_sortie.id}',
                    level=1,
                )
        return JsonResponse({'message': "Bill Added successfully."})
        
class AnnuelInvView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/inventaireann_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonentres' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        stock = Product.objects.filter(store=CurrentStore)
        entrepots = models.Entrepot.objects.filter(store=CurrentStore)
        fournisseurs = Fournisseur.objects.filter(store=CurrentStore)
        context["entrepots"] = entrepots
        context["fournisseurs"] = fournisseurs  
        stock_rendered =[]
        for stock_proodcut in stock : 
           stock_info = {
               "id":stock_proodcut.id,
            "name": stock_proodcut.name,
            "reference":stock_proodcut.reference,
          }
           stock_rendered.append(stock_info)   
        users = CustomUser.objects.filter(EmployeeAt = CurrentStore)
        context["users"] = users
        context["stock"] = stock_rendered
        return context
    
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData', '')
        if dataInvoice:
            store_id = self.request.session["store"]
            CurrentStore = store.objects.get(pk=store_id)
            equipe1 = dataInvoice.get('equipe1')
            equipe2 = dataInvoice.get('equipe2')
            invoiceDate = dataInvoice.get('invoiceDate')
            invoiceDueDate = dataInvoice.get('invoiceDueDate')
            Inventrepot = dataInvoice.get('Inventrepot')
            products1 = dataInvoice.get('products1')
            products2 = dataInvoice.get('products2')
            products_real = dataInvoice.get('products_real')
            current_year = timezone.now().year % 100  # Get the last two digits of the current year
            latest_id = models.InventaireAnnuel.objects.latest('id').id if models.InventaireAnnuel.objects.exists() else 0
            new_id = latest_id + 1
            code_inv = f'INV{current_year:02d}-{new_id:03d}'
            print(Inventrepot)
            with transaction.atomic():
                Invannuel_instance = models.InventaireAnnuel.objects.create(
                    codeInv = code_inv,
                    dateInv = invoiceDate,
                    datecloture = invoiceDueDate,
                    note = "",
                    entrepot = models.Entrepot.objects.get(name=Inventrepot, store= CurrentStore ), 
                    store= CurrentStore
                )
            # Start a transaction to ensure atomicity
            
                # Create equipeInventaire instances
                equipe1_instance = models.equipeInventaire.objects.create(
                    inv_annuel=Invannuel_instance,
                    label_equipe=equipe1
                )
                equipe2_instance = models.equipeInventaire.objects.create(
                    inv_annuel=Invannuel_instance,
                    label_equipe=equipe2
                )

                # Create produitEnInventaireAnnuel instances for products1
                for product_data in products1:
                    product_instance = models.produitEnInventaireAnnuel.objects.create(
                        Equipe= equipe1_instance,
                        product= Product.objects.get(reference=product_data['reference'], store = CurrentStore),
                        quantity= product_data['quantity']
                    )

                # Create produitEnInventaireAnnuel instances for products2
                for product_data in products2:
                    product_instance = models.produitEnInventaireAnnuel.objects.create(
                        Equipe= equipe2_instance,
                        product= Product.objects.get(reference=product_data['reference'], store = CurrentStore),
                        quantity= product_data['quantity']
                    )



        return JsonResponse({'message': "Product Added successfully."})  
 
class InventaireInitial(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/inventaire_initial.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_invinitial' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        stocks = models.Stock.objects.filter(entrepot__store = CurrentStore)
        stocks_list =[]
        for stock in stocks:
            stock_dict = {
                "reference": stock.product.reference,
                "name": stock.product.name,
                "entrepot": stock.entrepot.name,
                "quantity_initial": stock.quantity_initial
            }
            stocks_list.append(stock_dict)
        context["stocks"] = stocks_list
        entrepots = models.Entrepot.objects.filter(store = CurrentStore)
        context["entrepots"] = entrepots
        return context
       
class InvInitial(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/inventaireinitial_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonentres' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)

        return context
    
    def post(self, request, *args, **kwargs):
        dataJson = json.loads(request.body)
        data = dataJson.get('formData', '')
        store_id = self.request.session["store"]
        currentStore = store.objects.get(id=store_id)
        liste_products =data['liste_products']
        with transaction.atomic():
            for product_data in liste_products:
                entrepot_name = product_data['entrepot']
                product_name = product_data['reference']
                quantity = int(product_data['quantity'])

                # Fetch the Stock instance based on entrepot and product
                
                entrepot_name = product_data['entrepot']
                product_name = product_data['reference']  
                
                # Get or create the Product instance
                product_instance = Product.objects.filter(reference=product_name, store=currentStore).first()
                if product_instance is not None :
                    product_instance.initial_qte = quantity
                    product_instance.save() 
                    stock_inst = models.Stock.objects.filter(entrepot__name=entrepot_name, product=product_instance).first()

                    if stock_inst is None:
                        # Create the Stock instance if it doesn't exist
                        entrepot_in = models.Entrepot.objects.get(name=entrepot_name, store= currentStore)
                        stock_inst = models.Stock.objects.create(entrepot=entrepot_in, product=product_instance)

                    # Update the quantity and save the Stock instance
                    stock_inst.quantity_initial = quantity
                    stock_inst.save()
                    print("done"+product_instance.reference)

        return JsonResponse({'message': 'Stock modifié!.'})
    
class AnnuelInvViewEdit(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/inventaireann_page_edit.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonentres' in self.request.session.get('permissions', []) 
    
    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        context = super().get_context_data(**kwargs)       
        
        bill_id=self.kwargs.get('id_inv')
        bill_sortie = models.InventaireAnnuel.objects.get(id=bill_id)
        context["bill"]= bill_sortie

       
        users = CustomUser.objects.filter(EmployeeAt = CurrentStore)
        context["users"] = users

        return context
    
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData', '')
        if dataInvoice:
            store_id = self.request.session["store"]
            CurrentStore = store.objects.get(pk=store_id)
            equipe1 = dataInvoice.get('equipe1')
            equipe2 = dataInvoice.get('equipe2')
            invoiceDate = dataInvoice.get('invoiceDate')
            invoiceDueDate = dataInvoice.get('invoiceDueDate')
            Inventrepot = dataInvoice.get('Inventrepot')
            products1 = dataInvoice.get('products1')
            products2 = dataInvoice.get('products2')
            products_real = dataInvoice.get('products_real')
            current_year = timezone.now().year % 100  # Get the last two digits of the current year
            latest_id = models.InventaireAnnuel.objects.latest('id').id if models.InventaireAnnuel.objects.exists() else 0
            new_id = latest_id + 1
            code_inv = f'INV{current_year:02d}-{new_id:03d}'
            print(Inventrepot)
            with transaction.atomic():
                Invannuel_instance = models.InventaireAnnuel.objects.create(
                    codeInv = code_inv,
                    dateInv = invoiceDate,
                    datecloture = invoiceDueDate,
                    note = "",
                    entrepot = models.Entrepot.objects.get(name=Inventrepot, store= CurrentStore ), 
                    store= CurrentStore
                )
            # Start a transaction to ensure atomicity
            
                # Create equipeInventaire instances
                equipe1_instance = models.equipeInventaire.objects.create(
                    inv_annuel=Invannuel_instance,
                    label_equipe=equipe1
                )
                equipe2_instance = models.equipeInventaire.objects.create(
                    inv_annuel=Invannuel_instance,
                    label_equipe=equipe2
                )

                # Create produitEnInventaireAnnuel instances for products1
                for product_data in products1:
                    product_instance = models.produitEnInventaireAnnuel.objects.create(
                        Equipe= equipe1_instance,
                        product= Product.objects.get(reference=product_data['reference'], store = CurrentStore),
                        quantity= product_data['quantity']
                    )

                # Create produitEnInventaireAnnuel instances for products2
                for product_data in products2:
                    product_instance = models.produitEnInventaireAnnuel.objects.create(
                        Equipe= equipe2_instance,
                        product= Product.objects.get(reference=product_data['reference'], store = CurrentStore),
                        quantity= product_data['quantity']
                    )



        return JsonResponse({'message': "Product Added successfully."})  



class SotckView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/stock_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        if 'inventory.can_see_stocktab' in self.request.session.get('permissions', []):      
         return 'inventory.can_see_stocktab' in self.request.session.get('permissions', []) 

    # def handle_no_permission(self):
    #      # Redirect users without permission to the "inventory" page
    #     return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)    
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        if(myuser.role =='manager'):
          if self.request.user.is_authenticated:
            if  self.kwargs.get('magasin_id') :  
             store_id = self.kwargs.get('magasin_id')
             store_obj=store.objects.get(pk=store_id)
             self.request.session["nomStore"]=store_obj.name
             self.request.session["store"]=store_id   
            else:
               store_id =1   
          else:
            if  self.kwargs.get('magasin_id') :  
             store_id=self.kwargs.get('magasin_id')
             store_obj=store.objects.get(pk=store_id)
             self.request.session["nomStore"]=store_obj.name
             self.request.session["store"]=store_id
            else:
              self.request.session["store"]=1       
          my_store = store.objects.get(pk=self.request.session["store"])    
          entrepots = my_store.get_entrepots()
          # Step 3: Get all the stocks associated with each Entrepot
          all_stocks = []
          for entrepot in entrepots:
            stocks_for_entrepot = entrepot.get_stocks()
            all_stocks.extend(stocks_for_entrepot)

          context["stock"] = all_stocks
          categories = Category.objects.all()
         
          context["categories"]=categories
        else:
          store_id = self.request.session["store"]
          my_store = store.objects.get(pk=store_id)
          self.request.session["nomStore"]=my_store.name
          entrepots = my_store.get_entrepots()
          # Step 3: Get all the stocks associated with each Entrepot
          all_stocks = []
          for entrepot in entrepots:
            stocks_for_entrepot = entrepot.get_stocks()
            all_stocks.extend(stocks_for_entrepot)
          categories = Category.objects.all()
          context["categories"]=categories
          context["stock"] = all_stocks

        return context

class BonReformeView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/bon_reforme.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonreforme' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, *args,**kwargs):
        context = super().get_context_data(*args, **kwargs)
        selected_store =store.objects.get(pk=self.request.session["store"])
        bons_retour = models.BonRetour.objects.filter(store=selected_store)
        context["selected_store"] = selected_store    
        store_id = self.request.session["store"]
        my_store = models.store.objects.get(pk=store_id)
     
        entrepots = models.Entrepot.objects.filter(store=selected_store)
          # Step 3: Get all the stocks associated with each Entrepot
        all_stocks = []
        for entrepot in entrepots:
            stocks_for_entrepot = entrepot.get_stocks()
            all_stocks.extend(stocks_for_entrepot)
        context["entrepots"]=entrepots
        context["bons_sorties"]=bons_retour
        context["stock"] = all_stocks
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        try:
           latest_bon = models.BonReforme.objects.latest('id')
           new_codeBon = latest_bon.id + 1
        except models.BonReforme.DoesNotExist:
             new_codeBon = 1
        currentUser = CustomUser.objects.get(id=self.request.user.id)
        dateBon = dataInvoice["dateBp"]
        entrepot_id=dataInvoice["entrepot"]
        entrepot = models.Entrepot.objects.get(id=entrepot_id)
        currentStore= store.objects.get(pk=self.request.session["store"])
        bon_retour = models.BonRetour.objects.get(idBon=dataInvoice["AssociatedBL"])
        bon_reforme = models.BonReforme.objects.create(
                idBon=new_codeBon,
                dateBon=dateBon,
                entrepot=entrepot,
                bonretour = bon_retour,
                store=currentStore,
                user=currentUser
         )   
        for product_data in dataInvoice['produits']:
          product_id = product_data['ref']
          quantity = int(product_data['qty'])  # Assuming 'qty' is a string and needs to be converted to an integer
          observation = product_data['observation']
          product = Product.objects.get(reference=product_id, store = currentStore)
          stock = models.Stock.objects.get(product=product, entrepot=entrepot)
          if stock :
             stock.quantity = stock.quantity - int(product_data['qty'])
             stock.save()
            # Create a ProduitsEnBonReforme object
          produit_en_bon_reforme = models.ProduitsEnBonReforme.objects.create(
            BonNo=bon_reforme,  # Assuming you have 'bon_reforme' defined and represents the BonReforme object
            produit=product,
            quantity=quantity, 
            observation=observation
         ) 
        response_data = {'message': 'Bon de reforme created successfully'}
        return JsonResponse(response_data)
    
class BonReformeUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/bon_reforme_update.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonreforme' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            bill_id=self.kwargs.get('id_bill')
            bon_reforme = models.BonReforme.objects.get(id=bill_id)
            context["bill"]=bon_reforme
            items =[]
            for produit in bon_reforme.produits_en_bon_reforme.all():
                produit_dict ={
                    'ref' : produit.produit.reference,
                    'name': produit.produit.name,
                    'categorie': produit.produit.category.Libellé,
                    'qty':produit.quantity,
                    'observation':produit.observation
                }
                items.append(produit_dict)
            context["items"]=items
            selected_store = store.objects.get(pk=self.request.session["store"])
            context["selected_store"] = selected_store   
            entrepots = models.Entrepot.objects.filter(store=selected_store)
            context["entrepots"]=entrepots
            all_stocks = []
            for entrepot in entrepots:
                stocks_for_entrepot = entrepot.get_stocks()
                all_stocks.extend(stocks_for_entrepot)        
            context["stock"] = Product.objects.filter(store=selected_store)
            return context
   
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        print(dataInvoice)
        existing_bon_reforme = models.BonReforme.objects.get(idBon=dataInvoice["idBon"])
        existing_bon_reforme.entrepot = models.Entrepot.objects.get(name=dataInvoice["entrepot"])
        existing_bon_reforme.save()
        entrepot_bill = models.Entrepot.objects.get(name=dataInvoice["entrepot"])
        selected_store = store.objects.get(pk=self.request.session["store"])
        produits_en_bon_reforme = models.ProduitsEnBonReforme.objects.filter(BonNo=existing_bon_reforme)
        for produit_inst in produits_en_bon_reforme :
          stock = models.Stock.objects.get(product=produit_inst.produit, entrepot=existing_bon_reforme.entrepot )
          if stock :
             stock.quantity = int(stock.quantity) + int(produit_inst.quantity)
             stock.save() 
        existing_bon_reforme.produits_en_bon_reforme.all().delete()
        for product_data in dataInvoice['produits']:
          product_id = product_data['ref']
          quantity = int(product_data['qty'])  
          product = Product.objects.get(reference=product_id, store = selected_store)
          stock = models.Stock.objects.get(product=product, entrepot= entrepot_bill )
          if stock :
             stock.quantity = stock.quantity - int(product_data['qty'])
             stock.save()
            # Create a ProduitsEnBonReforme object
          produit_en_bon_reforme = models.ProduitsEnBonReforme.objects.create(
            BonNo=existing_bon_reforme,  
            produit=product,
            quantity=quantity
          ) 
        response_data = {'message': 'Bon de reforme created successfully'}
        return JsonResponse(response_data)
    
class ListReformeView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/liste_bon_reforme.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonreforme' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store = self.request.session["store"]
        CurrentStore = models.store.objects.get(pk=store)

        bons = models.BonReforme.objects.filter(store=CurrentStore)      
        context["bons"] = bons
        return context 
        
class BonSortieView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/bon_sortie.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonsorties' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
      
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)       
        if self.kwargs.get('id_bon') :
            bill_id=self.kwargs.get('id_bon')
            invoice = models.BonSortie.objects.get(idBon=bill_id)
            idBon = invoice.idBon
            dateBon = invoice.dateBon
            
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
                }
                items.append(produit_dict)         
            context["idBon"] = idBon
            context["dateBon"] = dateBon
            context["client_name"]= client_name
            context["client_address"]= client_address
            context["client_phone"] = client_phone
            context["items"]=items
        else:
            selected_store = store.objects.get(pk=self.request.session["store"])
            context["selected_store"] = selected_store   
            bons_Livraison = BonSortie.objects.filter(store=selected_store)
            context["bons_Livraison"]=bons_Livraison
            clients_list = Client.objects.filter(store=selected_store)
            clients=[]
            for cl in clients_list:
                cl_dict={
                "client_name" :cl.name,
                "client_address":cl.adresse,
                "client_phone" : cl.phone,                      
                }
                clients.append(cl_dict)
            context["clients"]=clients   
     
        entrepots = models.Entrepot.objects.filter(store=selected_store)
        context["entrepots"]=entrepots
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
        dataInvoice = data.get('formData')
        bon_Liv = BonSortie.objects.get(idBon=dataInvoice["AssociatedBL"])
        selected_store = store.objects.get(pk=self.request.session["store"])
        print('im here')
        bon_sortie = models.Bonsortiedestock.objects.create(
             idBon = dataInvoice ["IdBon"],
             dateBon = dataInvoice["dateBp"],
             user = CustomUser.objects.get(id=self.request.user.id),
             bonL = bon_Liv,
             entrepot= models.Entrepot.objects.get(name=dataInvoice["entrepotBon"]),
             store= store.objects.get(pk=self.request.session["store"]),
             Client= Client.objects.get(name=dataInvoice["clientInfo"]["name"]),
        )
        produits = dataInvoice.get('produits')
        for produit in produits:
            product_id = produit['ref']
            quantity = int(produit['qty'])  # Assuming 'qty' is a string and needs to be converted to an integer
            product = Product.objects.get(reference=product_id, store =selected_store)
            produit_en_bon_sortie = models.ProduitsEnBonSortieStock.objects.create(
                stock =product,
                quantity=quantity,
                BonNo=bon_sortie
            )
        return JsonResponse({"Message": "BonSortie Créer"})

class BonSortieUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/bon_sortie_update.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonsorties' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
        # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)       
        
        bill_id=self.kwargs.get('id_bon')
        bill_sortie = models.Bonsortiedestock.objects.get(id=bill_id)
        context["bill"]= bill_sortie
        items =[]
        for product_data in bill_sortie.produits_en_bon_sortie_stock.all():
            prod_dict ={
                "ref": product_data.stock.reference,
                "name":product_data.stock.name,
                "qty":product_data.quantity
            }
            items.append(prod_dict)
        context['items']=items     
        selected_store = store.objects.get(pk=self.request.session["store"])
        context["selected_store"] = selected_store   
        bons_Livraison = BonSortie.objects.filter(store=selected_store)
        context["bons_Livraison"]=bons_Livraison
        entrepots = models.Entrepot.objects.filter(store=selected_store)
        context["entrepots"]=entrepots
        all_stocks = []
        for entrepot in entrepots:
            stocks_for_entrepot = entrepot.get_stocks()
            all_stocks.extend(stocks_for_entrepot)
        context["stock"] = all_stocks
        clients_list = Client.objects.filter(store=selected_store)
        clients=[]
        for cl in clients_list:
                cl_dict={
                "client_name" :cl.name,
                "client_address":cl.adresse,
                "client_phone" : cl.phone,                      
                }
                clients.append(cl_dict)
        context["clients"]=clients 
        return context  
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        if dataInvoice :
            # Fetch or create the Bonsortiedestock instance based on IdBon
            bonsortie, created = models.Bonsortiedestock.objects.get_or_create(idBon=dataInvoice['IdBon'])
            selected_store = store.objects.get(pk=self.request.session["store"])
            # Update Bonsortiedestock fields

            bonsortie.Client = Client.objects.get(name=dataInvoice['clientInfo']["name"])
            bonsortie.entrepot = models.Entrepot.objects.get(id=dataInvoice['entrepotBon'])
            bonsortie.bonL = BonSortie.objects.get(idBon=dataInvoice['AssociatedBL'])
            bonsortie.num_doc = dataInvoice['numDoc']
            bonsortie.Date_doc_Sortie = dataInvoice['dateDoc']
            bonsortie.num_constat = dataInvoice['numConst']
            bonsortie.Date_constat = dataInvoice['dateConst']

            #Save the Bonsortiedestock instance
            bonsortie.save()

            # Clear existing related ProduitsEnBonSortie instances
            bonsortie.produits_en_bon_sortie.all().delete()

            # Create new ProduitsEnBonSortie instances based on the produits data
            for produit_data in dataInvoice['produits']:
                produit_en_bon_sortie = models.ProduitsEnBonSortie(
                    BonNo=bonsortie,
                    stock=models.Product.objects.get(reference=produit_data["ref"], store =selected_store),
                    quantity=produit_data["quantity"],
                )
                produit_en_bon_sortie.save() 
        return JsonResponse({'message': "Product Added successfully."}) 

class BonSortieBlView(TemplateView):
    template_name = "inventory/bon_sortieBL.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonsorties' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
      
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)  
        selected_store = store.objects.get(pk=self.request.session["store"])     
        if self.kwargs.get('bill_id') :
            bill_id=self.kwargs.get('bill_id')
            print(bill_id)
            invoice = BonSortie.objects.get(id=bill_id)            
            idBon = invoice.idBon
            dateBon = invoice.dateBon
            entrepot=invoice.entrepot.name
            client_name= invoice.client.name
            client_address = invoice.client.adresse
            client_phone= invoice.client.phone
            products_enBon = invoice.get_produits()
            print(idBon)
            items=[]
            for product in products_enBon:
                produit_dict={
                 "produit_ref" :product.stock.reference,
                 "produit_name" :product.stock.name,
                 "produit_qty":product.quantity,          
                }
                items.append(produit_dict)         
            context["idBon"] = idBon
            context["dateBon"] = dateBon
            context["entrepot"] = entrepot
            context["client_name"]= client_name
            context["client_address"]= client_address
            context["client_phone"] = client_phone
            print(items)
            context["items"]=items    
        entrepots = models.Entrepot.objects.filter(store=selected_store)
        context["entrepots"]=entrepots
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
      dataInvoice = data.get('formData')
      if dataInvoice :
        selected_store = store.objects.get(pk=self.request.session["store"])    
        bon_Liv = BonSortie.objects.get(idBon=dataInvoice["AssociatedBL"])
        print('im here')
        bon_sortie = models.Bonsortiedestock.objects.create(
             idBon = dataInvoice ["IdBon"],
             dateBon = dataInvoice["dateBp"],
             user = CustomUser.objects.get(id=self.request.user.id),
             bonL = bon_Liv,
             entrepot= models.Entrepot.objects.get(name=dataInvoice["entrepotBon"]),
             store= store.objects.get(pk=self.request.session["store"]),
             Client= Client.objects.get(name=dataInvoice["clientInfo"]["name"]),
        )
        produits = dataInvoice.get('produits')
        for produit in produits:
            product_id = produit['ref']
            quantity = int(produit['qty'])  # Assuming 'qty' is a string and needs to be converted to an integer
            product = Product.objects.get(reference=product_id, store =selected_store)
            produit_en_bon_sortie = models.ProduitsEnBonSortieStock.objects.create(
                stock =product,
                quantity=quantity,
                BonNo=bon_sortie
            )
        return JsonResponse({"Message": "BonSortie Créer"}) 
    
class BonEntryBAView(TemplateView):
    template_name = "inventory/Entry_bill_generated.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonsorties' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
      
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)  
        selected_store = store.objects.get(pk=self.request.session["store"])     
        if self.kwargs.get('bill_id') :
            bill_id=self.kwargs.get('bill_id')
            print(bill_id)
            invoice = BonAchat.objects.get(id=bill_id)            
            idBon = invoice.idBon
            dateBon = invoice.dateBon
            entrepot =None
            if invoice.entrepot:
                entrepot=invoice.entrepot.name  
            fournisseur =None
            if invoice.fournisseur :  
                fournisseur = invoice.fournisseur.id
                   
            products_enBon = invoice.get_produits()
            print(idBon)
            items=[]
            for product in products_enBon:
                produit_dict={
                 "produit_ref" :product.produit.reference,
                 "produit_name" :product.produit.name,
                 "produit_qty":product.quantity,          
                }
                items.append(produit_dict)         
            context["idBon"] = idBon
            context["dateBon"] = dateBon
            context["entrepot"] = entrepot
            context["fournisseur"] = fournisseur
            print(items)
            context["items"]=items  
        bons_achat = BonAchat.objects.filter(store=selected_store )
        context["bons_achat"] =bons_achat     
        entrepots = models.Entrepot.objects.filter(store=selected_store)
        context["entrepots"]=entrepots
        fournisseurs = Fournisseur.objects.filter(store=selected_store)
        context["fournisseurs"]=fournisseurs
        all_produits = []
        all_stocks =[]
        for entrepot in entrepots:
            stocks_for_entrepot = entrepot.get_stocks()
            all_stocks.extend(stocks_for_entrepot)
        stock_data = []
        for produit in all_stocks:
                stock_data.append({
                    'name': produit.product.name,
                    'reference': produit.product.reference,
                })
        context["stock"] = stock_data
        return context
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
      data = json.loads(request.body)
      dataInvoice = data.get('formData')
      if dataInvoice :
          with transaction.atomic(): 
           selected_store = store.objects.get(pk=self.request.session["store"]) 
           dateBon =dataInvoice["dateBp"]
           entrepot_name =dataInvoice["clientInfo"]["name"]
           fournisseur = Fournisseur.objects.get(id=dataInvoice["FournisseurInfo"] , store=selected_store)
           entrepot = models.Entrepot.objects.get(name=entrepot_name)
           Currentuser = request.user
           myuser  = CustomUser.objects.get(username=Currentuser.username)
           store_id = self.request.session["store"]
           CurrentStore = store.objects.get(pk=store_id)
           now = datetime.now()
           year = str(now.year)[-2:]  # Take the last two digits of the year
           month = str(now.month).zfill(2)  # Ensure the month is zero-padded to two digits

           # Determine the next available ID for the BonEntry
           last_entry = models.BonEntry.objects.order_by('-id').first()
           if last_entry:
               next_id = last_entry.id + 1
           else:
               next_id = 1

           # Create the idBon in the desired format
           idBon = f"BE{year}{month}-{str(next_id).zfill(3)}"
           bon_entry = models.BonEntry(
            idBon=idBon,
            dateBon=dateBon,
            fournisseur=fournisseur,
            entrepot=entrepot,
            store = CurrentStore,
            user=myuser
           )
           bon_entry.save()     
           print(dataInvoice)
           products = dataInvoice["produits"]
           for product_data in dataInvoice['produits']:
                product = Product.objects.get(reference=product_data["ref"], store = CurrentStore)
                stock, created = models.Stock.objects.get_or_create(product=product, entrepot=entrepot)       
                if created:
                    stock.quantity = int(product_data["qty"])
                    stock.save()
                else:
                    stock.quantity += int(product_data["qty"])
                    stock.save() 
                product.TotalQte += int(product_data  ["qty"])
                product.initial_qte += int(product_data  ["qty"])
                product.save()                   
                models.ProduitsEnBonEntry.objects.create(
                    BonNo=bon_entry,
                    stock=product,
                    quantity=int(product_data["qty"]),
                )          
      return JsonResponse({'message': "Product Added successfully."})  
    
class EntryListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/liste_bon_entres.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonentres' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        Currentuser = self.request.user
        currentStore= store.objects.get(pk=self.request.session["store"])
        myuser  = CustomUser.objects.get(username=Currentuser.username)

        bons= models.BonEntry.objects.filter(store =currentStore)
        context["bons"]=bons
        entrepots = models.Entrepot.objects.filter(store=currentStore)
        context["entrepots"] = entrepots
        users_bills = Fournisseur.objects.filter(store=currentStore)
        context["users"]=users_bills
        return context

class EntrepotView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/Entrepots_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'produits.can_see_produits' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)       
        currentStore= store.objects.get(pk=self.request.session["store"])
        if self.request.session["role"] == 'manager':
            entrepots = models.Entrepot.objects.filter(store=currentStore)
        else:
             myuser=CustomUser.objects.get(username=self.request.user.username)
             ent_ins = myuser.mon_affectation.first()
             if ent_ins:
                point_vente_label = ent_ins.emplacement.label
                point_vente = pointVente.objects.filter(label=point_vente_label).first()
                entrepots = point_vente.entrepot
                entrepots = [entrepots]
        context["entrepots"]= entrepots 
        return context    

class TransfertListView(TemplateView):
    template_name = "inventory/transfert_Page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bontransfert' in self.request.session.get('permissions', [])  
    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)        
        # store_id = self.kwargs.get('store_id')
        selected_store = store.objects.get(pk=self.request.session["store"])        
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        if(myuser.role =='manager'):
          bons_sorties = models.BonTransfert.objects.filter(store=selected_store)
          context["bons_sorties"] =bons_sorties  
          print(context["bons_sorties"])      
        else:
          stock = models.Stock.objects.filter(product__store = selected_store)
          categories = Category.objects.filter(store=selected_store)
        
          bons_sorties = models.BonTransfert.objects.filter(store=selected_store)
          context["bons_sorties"] =bons_sorties   
          
        entrepots = models.Entrepot.objects.filter(store=selected_store)
        context["entrepots"] = entrepots
        users_bills = CustomUser.objects.filter(EmployeeAt=selected_store)
        context["users"]=users_bills
        return context
    
class EntrepotListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/entrepotsList_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_entrepots' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        currentStore= models.store.objects.get(pk=self.request.session["store"])  
        if(myuser.role =='manager'):
          users = CustomUser.objects.filter(EmployeeAt=currentStore)
          ents= models.Entrepot.objects.filter(store=currentStore)
          context["users"]=users
          context["entrepots"]=ents
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        print(dataInvoice)
        if dataInvoice:  
            currentStore= models.store.objects.get(pk=self.request.session["store"])    
            lib = dataInvoice['lib']
            adresse = dataInvoice['adresse']
            ville = dataInvoice['ville']
            postal = dataInvoice['postal']
            phone = dataInvoice['phone']
            responsables_ids = dataInvoice["responsables"]           
            entrepot_instance = models.Entrepot(
              store = currentStore,
              name=lib,
              adresse=adresse,
              ville =ville,
              codePostal =postal,
              phone=phone
            )
            entrepot_instance.save()
            
            for responsable_id in responsables_ids:
                responsable = CustomUser.objects.get(pk=responsable_id)
                responsable.entrepots_responsible=entrepot_instance
        return JsonResponse({'message': "Entrepot Added successfully."})
    
def ValidateReceiving(request):
        data = json.loads(request.body)
        user = request.user
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        myuser = CustomUser.objects.get(username=user.username)
        if user.check_password(data["password"]):
            if data['decision'] == 'valide':
                bonTr = models.BonTransfert.objects.get(idBon=data["idBon"])

                for produit in bonTr.produits_en_bon_transfert.all():              
                    # Update the stock quantity in the source entrepot
                    new_quantity_in_source = produit.stock_arr.quantity + int(produit.quantity)
                    stock_in_destination, created = models.Stock.objects.get_or_create(
                        product=produit.stock_dep.product,
                        entrepot=bonTr.entrepot_arrive,
                        defaults={'quantity': 0}  # Initialize with zero quantity if creating
                    )
                    # Update the quantity in the destination warehouse
                    stock_in_destination.quantity += int(produit.quantity)
                    stock_in_destination.save()
                bonTr.validation_recu = True
                bonTr.save()
            elif data['decision'] == 'annule':
                bonTr = models.BonTransfert.objects.get(idBon=data["idBon"])
                for produit in bonTr.produits_en_bon_transfert.all():              
                    # Update the stock quantity in the source entrepot
                    new_quantity_in_source = produit.stock_dep.quantity + int(produit.quantity)
                    produit.stock_dep.quantity = new_quantity_in_source
                    produit.stock_dep.save()
                bonTr.validation_recu = False
                bonTr.annule = True
                bonTr.save()    
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False})
        
class StockTransfertView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/transfert_bill.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bontransfert' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        selected_store = store.objects.get(pk=self.request.session["store"])  
        
        allentrepots = models.Entrepot.objects.filter(store=selected_store)
        if self.request.session["role"] == "gestion-stock": 
            entrepots = models.Entrepot.objects.filter(store=selected_store, name ="Depot principal Reghaia")
        elif self.request.session["username"] == "nadjemeddine" or self.request.session["username"] == "yasmine" or self.request.session["username"] == "aimen":
            entrepots = models.Entrepot.objects.filter(store=selected_store, name ="PARKMALL SETIF")
        else:
            entrepots = models.Entrepot.objects.filter(store=selected_store)
        context["entrepots"] = entrepots   
        context["entrepotsdep"] = allentrepots   
        
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs): 
      data = json.loads(request.body)
      dataInvoice = data.get('formData', '')
      Currentuser = request.user
      selected_store = store.objects.get(pk=self.request.session["store"])  
      myuser  = CustomUser.objects.get(username=Currentuser.username)
      if dataInvoice:
        idBon = dataInvoice["IdBon"]
        dateBon = dataInvoice["dateBp"]
        
        # Create or get the client
        ent_dep = dataInvoice['ent_dep']['name']
        ent_arr = dataInvoice['ent_arr']['name']
        for product in dataInvoice["produits"]:
                # Retrieve the stock entry for the product in the source warehouse (ent_dep)
                stock_in_source = models.Stock.objects.select_for_update().get(
                    product__reference=product["ref"], entrepot__name=ent_dep
                )
                new_quantity_in_source = stock_in_source.quantity - int(product["qty"])
                
                # Check if the source warehouse has enough quantity
                if new_quantity_in_source < 0:
                    return JsonResponse({
                        'error': f"Insufficient stock for product: {product['ref']}",
                        'prompt_user': True
                    })
                
        with transaction.atomic():
            for product in dataInvoice["produits"]:
                # Retrieve the stock entry for the product in the source warehouse (ent_dep)
                stock_in_source = models.Stock.objects.select_for_update().get(
                    product__reference=product["ref"], entrepot__name=ent_dep
                )
                new_quantity_in_source = stock_in_source.quantity - int(product["qty"])
                
                # Check if the source warehouse has enough quantity
                if new_quantity_in_source < 0:
                    return JsonResponse({
                        'error': f"Insufficient stock for product: {product['ref']}",
                        'prompt_user': True
                    })
                
                # Update the source warehouse stock
                stock_in_source.quantity = new_quantity_in_source
                stock_in_source.save()

            ent_depart = models.Entrepot.objects.get(name=ent_dep)
            ent_arriv = models.Entrepot.objects.get(name=ent_arr)

            # Create transfer bill
            bon_trans = models.BonTransfert.objects.create(
                idBon=idBon,
                dateBon=dateBon,
                entrepot_depart=ent_depart,
                entrepot_arrive=ent_arriv,
                store=selected_store, 
                validation_recu = False,
                user=myuser
            )

            for product in dataInvoice["produits"]:
                quantite = int(product['qty'])
                stock_in_source = models.Stock.objects.select_for_update().get(
                    product__reference=product["ref"], entrepot__name=ent_dep
                )

                stock_in_destination, created = models.Stock.objects.get_or_create(
                    product=stock_in_source.product,
                    entrepot=ent_arriv,
                    defaults={'quantity': 0}  # Set default quantity to 0 if it does not exist
                )
                
                if request.session['store'] != '1':
                    stock_in_destination.quantity += quantite
                    stock_in_destination.save()

                models.ProduitsEnBonTransfert.objects.create(
                    BonNo=bon_trans,
                    stock_dep=stock_in_source,
                    stock_arr=stock_in_destination,
                    quantity=quantite,
                )
                
        return JsonResponse({'message': "Products transferred successfully."})
        
class StockTransfertUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/transfert_bill_update.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bontransfert' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        bill_id=self.kwargs.get('id_bill')
        transfert_bill = models.BonTransfert.objects.get(id=bill_id)
        context["bill"]=transfert_bill
        items =[]
        for produit_data in transfert_bill.produits_en_bon_transfert.all():
            prod_dict ={
                "ref": produit_data.stock_dep.product.reference,
                "name": produit_data.stock_dep.product.name,
                "rate":float(produit_data.stock_dep.product.revendeur_price + produit_data.stock_dep.product.prix_livraison + produit_data.stock_dep.product.tva_douan),
                "qty":produit_data.quantity
            }
            items.append(prod_dict)
        
        context["items"]=items
        my_entrepot = transfert_bill.entrepot_depart
        stocks = my_entrepot.get_stocks()
        stock_data=[]
        for stock in stocks:
                product_name = stock.product.name
                entrepot_name = stock.entrepot.name
                quantity = stock.quantity
                price = float(stock.product.revendeur_price + stock.product.prix_livraison + stock.product.tva_douan)
                reference = stock.product.reference
                entrepot=stock.entrepot.name
                stock_info = {
                    "product_name": product_name,
                    "entrepot_name": entrepot_name,
                    "quantity": quantity,
                    "price": price,
                    "reference": reference,
                    "entrepot":entrepot,
                }
                stock_data.append(stock_info)
        context['stocks'] = stock_data
        selected_store = store.objects.get(pk=self.request.session["store"])  
        entrepots = models.Entrepot.objects.filter(store=selected_store)       
        context["entrepots"]=entrepots     
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs): 
      data = json.loads(request.body)
      dataInvoice = data.get('formData', '')
      Currentuser = request.user
      selected_store = store.objects.get(pk=self.request.session["store"])  
      myuser  = CustomUser.objects.get(username=Currentuser.username)
      if dataInvoice:
        bon_tr = models.BonTransfert.objects.get(idBon=dataInvoice["IdBon"])
        # dateBon = dataInvoice["dateBp"]
     
        # Create or get the client
        ent_dep= models.Entrepot.objects.get(name= dataInvoice['ent_dep']['name'])
        ent_arr = models.Entrepot.objects.get(name= dataInvoice['ent_arr']['name'])
        bon_tr.entrepot_depart = ent_dep
        bon_tr.entrepot_arrive = ent_arr
        
        with transaction.atomic():
            for product_data in bon_tr.produits_en_bon_transfert.all():
                product_data.stock_dep.quantity += product_data.quantity
                if  product_data.stock_arr.quantity - product_data.quantity > 0 :
                    product_data.stock_arr.quantity -= product_data.quantity
                else:
                    product_data.stock_arr.quantity
                product_data.stock_dep.save()
                product_data.stock_arr.save()
                product_data.delete()
            for product in dataInvoice["produits"]:
             # Retrieve the stock entry for the product in the source warehouse (ent_dep)
             stock_in_source = models.Stock.objects.get(
                product__reference=product["ref"], entrepot=ent_dep
             )
             stock_in_source.quantity -= int(product["qty"])
             stock_in_source.save()
             product_ref = product["ref"]
             entrepot_name = ent_arr 
             stock_arr = models.Stock.objects.filter(product__reference=product_ref, entrepot__name=entrepot_name).first()

             if stock_arr is None:
                    # If it doesn't exist, create a new Stock object
                    stock_arr = models.Stock.objects.create(
                        product=Product.objects.get(reference=product_ref , store = selected_store),  # Replace 'Product' with your actual model
                        entrepot=models.Entrepot.objects.get(name=entrepot_name),  # Replace 'Entrepot' with your actual model
                        quantity=int(product["qty"])
                    )
             else:
                    # If it exists, update the quantity
                    stock_arr.quantity += int(product["qty"])
                    stock_arr.save()
             # Create or update a ProduitsEnBonTransfert instance
             produit_en_bon_transfert= models.ProduitsEnBonTransfert.objects.create(
                BonNo=bon_tr,
                stock_dep=stock_in_source,
                stock_arr=models.Stock.objects.get(product__reference=product["ref"], entrepot=ent_arr),
                quantity=product["qty"],
             )
            bon_tr.save()
        return JsonResponse({'message': "Products transferred successfully."})
 
class StockReintegrationView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/bon_reintegration.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonsreintegration' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  
    

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        selected_store =store.objects.get(pk=self.request.session["store"])
        bons_retour = models.BonRetour.objects.filter(store=selected_store)
        context["selected_store"] = selected_store    
        store_id = self.request.session["store"]
        my_store = models.store.objects.get(pk=store_id)
     
        entrepots = models.Entrepot.objects.filter(store=selected_store)
          # Step 3: Get all the stocks associated with each Entrepot
        all_stocks = []
        for entrepot in entrepots:
            stocks_for_entrepot = entrepot.get_stocks()
            all_stocks.extend(stocks_for_entrepot)
        context["entrepots"]=entrepots
        context["bons_sorties"]=bons_retour
        context["stock"] = all_stocks
        print(context)
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData', '')
        if dataInvoice:
           idBon =dataInvoice["IdBon"]
           dateBon =dataInvoice["dateBp"]
           entrepot_name =dataInvoice["clientInfo"]["name"]
           bonR= models.BonRetour.objects.get(idBon=dataInvoice["AssociatedBL"])
           entrepot = models.Entrepot.objects.get(id=dataInvoice["entrepotDest"])
           Currentuser = request.user
           myuser  = CustomUser.objects.get(username=Currentuser.username)
           store_id = self.request.session["store"]
           CurrentStore = store.objects.get(pk=store_id)

           bon_reintegration= models.BonReintegration(
            idBon=idBon,
            dateBon=dateBon,
            bonRetour=bonR,
            entrepot=entrepot,
            store = CurrentStore,
            user=myuser
           )
           bon_reintegration.save()     
           print(dataInvoice)
           products = dataInvoice["produits"]
           for product_data in dataInvoice['produits']:
                product = Product.objects.get(reference=product_data["ref"], store = CurrentStore)
                stock, created = models.Stock.objects.get_or_create(product=product, entrepot=entrepot)       
                if created:
                    stock.quantity = int(product_data["qty"])
                    stock.save()
                else:
                    stock.quantity += int(product_data["qty"])
                    stock.save() 

                product.TotalQte += int(product_data  ["qty"])
                product.save()                   
                models.ProduitsEnBonReintegration.objects.create(
                    BonNo=bon_reintegration,
                    stock=product,
                    quantity=int(product_data["qty"]),
                )          
        return JsonResponse({'message': "Product Added successfully."})
  
class StockReintegrationUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/bon_reintegration_update.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonsreintegration' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  
    

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        selected_store =store.objects.get(pk=self.request.session["store"])
        bons_retour = models.BonRetour.objects.filter(store=selected_store)
        context["selected_store"] = selected_store    
        store_id = self.request.session["store"]
        my_store = models.store.objects.get(pk=store_id)
        bill_id=self.kwargs.get('id_bill')
        bon_r = models.BonReintegration.objects.get(id=bill_id)
        context["bill"]=bon_r
        items =[]
        for produit in bon_r.produits_en_bon_reintegration.all():
            produit_dict ={
                'ref' : produit.stock.reference,
                'name': produit.stock.name,
                'categorie': produit.stock.category.Libellé,
                'qty':produit.quantity
            }
            items.append(produit_dict)
        context["items"]=items
        entrepots = models.Entrepot.objects.filter(store=selected_store)
          # Step 3: Get all the stocks associated with each Entrepot
        all_stocks = []
        for entrepot in entrepots:
            stocks_for_entrepot = entrepot.get_stocks()
            all_stocks.extend(stocks_for_entrepot)
        context["entrepots"]=entrepots
        context["bons_sorties"]=bons_retour
        context["stock"] = all_stocks
        print(context)
        return context
      
class StockRetourView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/bon_retour.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonretour' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        selected_store =store.objects.get(pk=self.request.session["store"])
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        if(myuser.role =='manager' or myuser.entrepots_responsible is not None):
          bons_sorties = BonSortie.objects.filter(store=selected_store)
        else: 
          bons_sorties = BonSortie.objects.filter(store=selected_store, user = myuser)
        context["selected_store"] = selected_store    
        store_id = self.request.session["store"]
        my_store = models.store.objects.get(pk=store_id)
     
        entrepots = models.Entrepot.objects.filter(store=my_store)
          # Step 3: Get all the stocks associated with each Entrepot
        all_stocks = []
        for entrepot in entrepots:
            stocks_for_entrepot = entrepot.get_stocks()
            all_stocks.extend(stocks_for_entrepot)
        context["bons_sorties"]=bons_sorties
        context["stock"] = all_stocks
        modeReg = ModeReglement.objects.all() 
        context["modeReg"]=modeReg  
        echeances = EcheanceReglement.objects.all() 
        context["echeances"] = echeances 
        banques= Banque.objects.all()
        context["banques"] = banques
        current_year = datetime.now().strftime('%y')
        current_month = datetime.now().strftime('%m')
        last_bon = models.BonRetour.objects.order_by('-id').first()
        if last_bon:
            last_id = last_bon.idBon.split('-')[-1]
            if last_id.isnumeric():
                sequence_number = int(last_id) + 1
            else:
                sequence_number = 1
        else:
            sequence_number = 1
        codeBon = f'BR{current_year}{current_month}-{sequence_number}' 
        context["code"] = codeBon
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData', '')
        if dataInvoice:
          with transaction.atomic(): 
               idBon =dataInvoice["IdBon"]
               dateBon =dataInvoice["dateBp"]
               total = dataInvoice["Total"]
               store_id = self.request.session["store"]
               my_store = models.store.objects.get(pk=store_id)
               Currentuser = self.request.user
               myuser  = CustomUser.objects.get(username=Currentuser.username)
               client_info = dataInvoice['clientInfo']
               
               # Create or get the client
               client_name = client_info['name']
               client_address = client_info['address']
               client_phone = client_info['phone']
               client, _ = models.Client.objects.get_or_create(name=client_name, adresse=client_address, phone=client_phone)
               bonL = BonSortie.objects.filter(idBon=dataInvoice["AssociatedBL"]).first()
               current_year = datetime.now().strftime('%y')
               current_month = datetime.now().strftime('%m')
               last_bon = models.BonRetour.objects.order_by('-id').first()
               if last_bon:
                 last_id = last_bon.idBon.split('-')[-1]
                 if last_id.isnumeric():
                    sequence_number = int(last_id) + 1
                 else:
                    sequence_number = 1
               else:
                  sequence_number = 1
               codeBon = f'BR{current_year}{current_month}-{sequence_number}'  
               bon_retour = models.BonRetour.objects.create(idBon=codeBon , dateBon=dateBon, bonL =bonL, totalPrice=total, client=client, store=my_store, user=myuser)
               # getting the products dans le bon 
               entrepot_bons =bonL.entrepot
               products = dataInvoice["produits"]            
               
                   
               for product in products:
                 note = ''
                 if 'note' in product:
                    note = product["note"] 
                 p=Product.objects.filter(reference=product["ref"]).first()
                 prod_total_price = p.prix_vente * int(product["qty"])
                 product_instance = models.ProduitsEnBonRetour.objects.create(
                  BonNo=bon_retour,
                  produit=p,
                  quantity=int(product["qty"]),
                  numseries = product["numserie"],
                  unitprice=float(product["rate"]),  
                  direction = note,
                  totalprice=prod_total_price
                 )          
                 if product['etat']=='Intacte':                     
                        product_instance.reintegrated = True
                        product_instance.save()

               bonLivraison = bonL
               client_obj = bonL.client
               date= dateBon
               motif= "remboursement"
               montant= total
    
               year = '24'
    
               # Find the last AvoirVente object
               last_avoir = AvoirVente.objects.last()
    
               # Determine the next sequential number
               if last_avoir:
                    last_code = last_avoir.codeAvoir
                    last_sequence = int(last_code.split('-')[1])
                    next_sequence = last_sequence + 1
               else:
                    next_sequence = 1
    
                # Create the codeAvoir using the year and sequential number
               responsable_entrepot = CustomUser.objects.filter(entrepots_responsible=bonL.entrepot).first()
               if responsable_entrepot:
                notify.send(
                    sender=myuser,
                    recipient=responsable_entrepot,
                    verb=f' - Bon de Retour numero {bon_retour.idBon} a été créer par {myuser} , Veuillez valider',
                    description=f'/stock/edit/retour/{bon_retour.id}',
                    level=1,
                )
        return JsonResponse({'message': "Product Added successfully."})

class StockRetourUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/bon_retour_update.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonretour' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        bill_id=self.kwargs.get('id_bill')
        bon_retour = models.BonRetour.objects.get(id=bill_id)
        context["bill"]=bon_retour
        items=[]
        for produit in bon_retour.produits_en_bon_retour.all():
            produit_dict = {
                'ref' : produit.produit.reference,
                'name': produit.produit.name,
                'numseries': produit.numseries if produit.numseries is not None else '' ,
                'etat': 'Défectueux' if not produit.reintegrated else 'Intacte',
                'warranty': 'false' if not produit.warranty else 'true',
                'unitprice' : float(produit.unitprice),
                'totalprice': float(produit.totalprice),
                'note': produit.direction if produit.direction is not None else '',
                'qty':produit.quantity
            }
            items.append(produit_dict)
        context["items"]=items
        selected_store =store.objects.get(pk=self.request.session["store"])
        bons_sorties = BonSortie.objects.filter(store=selected_store)
        context["selected_store"] = selected_store    
        store_id = self.request.session["store"]
        my_store = models.store.objects.get(pk=store_id)

        bonLivraison = bon_retour.bonL
        produits = bonLivraison.produits_en_bon_sorties.all()
        produits_data=[]    
        for produit in produits :
            produits_dict = {
                    'name': produit.stock.name,
                    'reference':produit.stock.reference,
                    'quantity': produit.quantity,
                    'unitprice': float(produit.unitprice),
                    'totalprice': float(produit.totalprice),
                    'entrepot': produit.entrepot.name if produit.entrepot else "" 
                    } 
            produits_data.append(produits_dict)

        context["bons_sorties"]=bons_sorties
        context["produits"] = produits_data
        modeReg = ModeReglement.objects.all() 
        context["modeReg"]=modeReg  
        echeances = EcheanceReglement.objects.all() 
        context["echeances"] = echeances 
        banques= Banque.objects.all()
        context["banques"] = banques

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
                bon_retour = models.BonRetour.objects.get(idBon=data["IdBon"])
                # Get the existing products in the database
                existing_products = bon_retour.produits_en_bon_retour.all()
                my_entrepotname = bon_retour.bonL.entrepot.name
                my_entrepot = models.Entrepot.objects.get(name=my_entrepotname, store = CurrentStore)
                produits_transfert = models.ProduitsEnBonRetour.objects.filter(BonNo=bon_retour)
                produits_edited = data.get('produits', [])
                for produit_transfert in produits_transfert:
                    quantity_product = produit_transfert.quantity
                    reference_to_check = produit_transfert.produit.reference
                    # Check if the reference exists in produits_edited list
                    matching_produit = next((produit for produit in produits_edited if produit['ref'] == reference_to_check), None)
                    # Check if the quantity is zero
                    mon_stock = models.Stock.objects.get(entrepot=my_entrepot, product=produit_transfert.produit)                    
                    if matching_produit :
                        if matching_produit['qty'] == produit_transfert.quantity :
                                continue
                    else:
                        if mon_stock.quantity == 0:
                            return JsonResponse({'message': f"Bon ne peut pas être modifié ! Stock de Produit {produit_transfert.produit.reference} f est Vide!",'prompt_user': True})

                        # Update the source warehouse stock quantity
                        mon_stock.quantity -= quantity_product
                        mon_stock.save()
                        produit_transfert.delete()
                       
                # Handle stock updates and deletions
                for product_data in data.get('produits', []):
                    produit_inst = Product.objects.get(reference=product_data["ref"] , store = CurrentStore)
                    matching_produit = models.ProduitsEnBonRetour.objects.filter(BonNo=bon_retour, produit=produit_inst).first()
                    if not matching_produit:
                        qty = int(product_data['qty'])
                        rate = float(product_data['rate'])
                        total = int(qty) * rate  
                        note = ''
                        if 'note' in product_data:
                            note = product_data["note"]                  
                        produit_en_bon_retour = models.ProduitsEnBonRetour.objects.create(
                            BonNo=bon_retour,
                            produit=produit_inst,
                            quantity=qty,
                            reintegrated = False if product_data['etat'] == 'Défectueux' else True,
                            numseries = product_data['numserie'],
                            warranty= False if product_data['warranty'] == 'false' else True,
                            unitprice=rate,
                            direction =  note,
                            totalprice=total
                        )
                        p = models.Stock.objects.get(Q(product__reference=product_data["ref"]) & Q(entrepot__name=my_entrepot) )
                        p.quantity += int(product_data["qty"])
                        p.save()
                    else :
                        continue
        except models.BonRetour.DoesNotExist:
            return JsonResponse({'message': "BonRetour not found.", 'prompt_user': False})

        return JsonResponse({'message': "BonRetour Moidifé.", 'prompt_user': False})
    
class StockRetourAncienUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/bon_retoura_update.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonretour' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        bill_id=self.kwargs.get('id_bill')
        bon_retour = models.BonRetourAncien.objects.get(id=bill_id)
        context["bill"]=bon_retour
        items=[]
        for produit in bon_retour.produits_en_bon_retourancien.all():
            produit_dict = {
                'ref' : produit.referenceproduit,
                'name': produit.nomproduit,
                'numseries': produit.numseries,
                'etat': 'Défectueux' if not produit.reintegrated else 'Intacte',
                'warranty': 'false' if not produit.warranty else 'true',
                'unitprice' : float(produit.unitprice),
                'totalprice': float(produit.totalprice),
                'qty':produit.quantity
            }
            items.append(produit_dict)
        context["items"]=items
        selected_store =store.objects.get(pk=self.request.session["store"])
        
        context["selected_store"] = selected_store    
        store_id = self.request.session["store"]
        my_store = models.store.objects.get(pk=store_id)

        bonLivraison = bon_retour.bonL

        modeReg = ModeReglement.objects.all() 
        context["modeReg"]=modeReg  
        echeances = EcheanceReglement.objects.all() 
        context["echeances"] = echeances 
        banques= Banque.objects.all()
        context["banques"] = banques

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
                bon_retour = models.BonRetourAncien.objects.get(idBon=data["IdBon"])
                # Get the existing products in the database
                existing_products = bon_retour.produits_en_bon_retourancien.all()
                my_entrepotname = bon_retour.entrepot.name
                my_entrepot = models.Entrepot.objects.get(name=my_entrepotname, store = CurrentStore)
                produits_transfert = models.ProduitsEnBonRetourAncien.objects.filter(BonNo=bon_retour)
                produits_edited = data.get('produits', [])
                for produit_transfert in produits_transfert:
                    produit_transfert.delete()
                       
                # Handle stock updates and deletions
                for product_data in data.get('produits', []):
                    prod_total_price = float(product_data["rate"]) * int(product_data["qty"])
                    product_data_instance = models.ProduitsEnBonRetourAncien.objects.create(
                        BonNo=bon_retour,
                        referenceproduit = product_data["ref"],
                        nomproduit = product_data["name"],
                        quantity=int(product_data["qty"]),
                        numseries = product_data["numserie"],
                        unitprice=float(product_data["rate"]),              
                        totalprice=prod_total_price
                    )          
                    if product_data['etat']=='Intacte':                     
                            product_data_instance.reintegrated = True
                            product_data_instance.save()
        except models.BonRetourAncien.DoesNotExist:
            return JsonResponse({'message': "BonRetour not found.", 'prompt_user': False})

        return JsonResponse({'message': "BonRetour Moidifé.", 'prompt_user': False})

class ListRetourView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/liste_bon_retour.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonretour' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store = self.request.session["store"]
        CurrentStore = models.store.objects.get(pk=store)
        myuser=CustomUser.objects.get(username=self.request.user.username)
        if myuser.role == 'manager' or myuser.role == 'gestion-stock' or myuser.username == 'nadjemeddine' or myuser.role == 'Maintenance' :
            bons_retour = models.BonRetour.objects.filter(store=CurrentStore, valide=True)
            bons_retoura = models.BonRetourAncien.objects.filter(store=CurrentStore, valide=True)
            context["bons"] = bons_retour
            context["bons_retoura"] = bons_retoura
        else: 
            bons = models.BonRetour.objects.filter(user = myuser, valide=True) 
            context["bons"] = bons
        return context 
    
class ListReintegrationView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/liste_bon_reintegration.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonsreintegration' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))  

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store = self.request.session["store"]
        CurrentStore = models.store.objects.get(pk=store)

        bons = models.BonReintegration.objects.filter(store=CurrentStore)      
        context["bons"] = bons
        return context 
    
class ListSortiesView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/liste_bons_sorties.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonsorties' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = models.store.objects.get(pk=store_id)
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        if(myuser.role =='manager'):
            bons = models.Bonsortiedestock.objects.filter(store=CurrentStore)  
        else:
            bons = models.Bonsortiedestock.objects.filter(store=CurrentStore, user=Currentuser)      
        context["bons"] = bons
        return context 
  
class StockEntryView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/Entry_bill.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonentres' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        stock = Product.objects.filter(store=CurrentStore)
        entrepots = models.Entrepot.objects.filter(store=CurrentStore)
        fournisseurs = Fournisseur.objects.filter(store=CurrentStore)
        context["entrepots"] = entrepots
        context["fournisseurs"] = fournisseurs  
        stock_rendered =[]
        for stock_proodcut in stock : 
           stock_info = {
               "id":stock_proodcut.id,
            "name": stock_proodcut.name,
            "reference":stock_proodcut.reference,
          }
           stock_rendered.append(stock_info)   
        context["stock"] = stock_rendered
        return context
    
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData', '')
        if dataInvoice:
          with transaction.atomic(): 
           
           dateBon =dataInvoice["dateBp"]
           entrepot_name =dataInvoice["clientInfo"]["name"]
           fournisseur = Fournisseur.objects.get(id=dataInvoice["FournisseurInfo"])
           entrepot = models.Entrepot.objects.get(name=entrepot_name)
           Currentuser = request.user
           myuser  = CustomUser.objects.get(username=Currentuser.username)
           store_id = self.request.session["store"]
           CurrentStore = store.objects.get(pk=store_id)
           now = datetime.now()
           year = str(now.year)[-2:]  # Take the last two digits of the year
           month = str(now.month).zfill(2)  # Ensure the month is zero-padded to two digits

           # Determine the next available ID for the BonEntry
           last_entry = models.BonEntry.objects.order_by('-id').first()
           if last_entry:
               next_id = last_entry.id + 1
           else:
               next_id = 1

           # Create the idBon in the desired format
           idBon = f"BE{year}{month}-{str(next_id).zfill(3)}"
           bon_entry = models.BonEntry(
            idBon=idBon,
            dateBon=dateBon,
            fournisseur=fournisseur,
            entrepot=entrepot,
            store = CurrentStore,
            user=myuser
           )
           bon_entry.save()     
           print(dataInvoice)
           products = dataInvoice["produits"]
           for product_data in dataInvoice['produits']:
                product = Product.objects.get(reference=product_data["ref"], store = CurrentStore)
                stock, created = models.Stock.objects.get_or_create(product=product, entrepot=entrepot)       
                if created:
                    stock.quantity = int(product_data["qty"])
                    stock.save()
                else:
                    stock.quantity += int(product_data["qty"])
                    stock.save() 
                product.TotalQte += int(product_data  ["qty"])
                product.initial_qte += int(product_data  ["qty"])
                product.save()                   
                models.ProduitsEnBonEntry.objects.create(
                    BonNo=bon_entry,
                    stock=product,
                    quantity=int(product_data["qty"]),
                )          
        return JsonResponse({'message': "Product Added successfully."})  

class StockEntryUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/Entry_bill_update.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonentres' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        bill_id=self.kwargs.get('id_bill')
        entry_bill = models.BonEntry.objects.get(id=bill_id)
        context["bill"]=entry_bill
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        stock = Product.objects.filter(store=CurrentStore)
        entrepots = models.Entrepot.objects.filter(store=CurrentStore)
        fournisseurs = Fournisseur.objects.filter(store=CurrentStore)
        context["entrepots"] = entrepots
        context["fournisseurs"] = fournisseurs      
        stock_data = []
        for produit in stock:
                stock_data.append({
                    'name': produit.name,
                    'reference': produit.reference,
                    'prix_achat': float(produit.prix_achat),
                })
        context["stock"] = stock_data
        items =[]
        for produit in entry_bill.produits_en_bon_entry.all():
            produit_dict ={
                'ref' : produit.stock.reference,
                'name': produit.stock.name,
                'qty':produit.quantity
            }
            items.append(produit_dict)
        context["items"]=items
        return context
    
    def post(self, request, *args, **kwargs):
      data = json.loads(request.body)
      dataInvoice = data.get('formData', '')
      if dataInvoice:
        with transaction.atomic():   
            bon_entry = models.BonEntry.objects.get(idBon=dataInvoice['IdBon'])
            # bon_entry.dateBon = dataInvoice['dateBp']
            fournisseur_name = dataInvoice['FournisseurInfo']
            bon_entry.fournisseur = Fournisseur.objects.filter(acronym=fournisseur_name).first()
            bon_entry.entrepot = models.Entrepot.objects.filter(name=dataInvoice["clientInfo"]).first()
            bon_entry.save()

            # product = Product.objects.get(reference=product_data["ref"])
            entrepot_bill = models.Entrepot.objects.filter(name=dataInvoice["clientInfo"]).first()
            # stock= models.Stock.objects.get(product=product, entrepot=entrepot_bill)
            store_id = self.request.session["store"]
            CurrentStore = store.objects.get(pk=store_id)
            # previous_products = models.ProduitsEnBonEntry.objects(stock)
            for prev_product in bon_entry.produits_en_bon_entry.all():
                product = Product.objects.get(reference=prev_product.stock.reference , store = CurrentStore)
                stock= models.Stock.objects.filter(product=product, entrepot=entrepot_bill).first()
                if stock is not None:
                    new_quantity = stock.quantity - prev_product.quantity
                    # Check if the new_quantity meets your CHECK constraint conditions.
                    print(new_quantity)
                    if new_quantity >= 0:
                        stock.quantity = new_quantity
                        stock.save()
                    product.TotalQte -= prev_product.quantity
                    product.initial_qte -= prev_product.quantity
                    product.save()
            bon_entry.produits_en_bon_entry.all().delete()
            for product_data in dataInvoice['produits']:     
                product = Product.objects.get(reference=product_data["ref"], store = CurrentStore)
                stock, created = models.Stock.objects.get_or_create(product=product, entrepot=entrepot_bill)       
                if created:
                    stock.quantity = int(product_data["qty"])
                    stock.save()
                else:
                    stock.quantity += int(product_data["qty"])
                    stock.save() 
                product.TotalQte += int(product_data  ["qty"])
                product.initial_qte += int(product_data  ["qty"])
                product.save()                   
                models.ProduitsEnBonEntry.objects.create(
                    BonNo=bon_entry,
                    stock=product,
                    quantity=int(product_data["qty"]),
                )     
            return JsonResponse({'message': "Product Added successfully."})  
        
class ListEntryStockView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/stock_entry.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_etatentres' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)    
        product_summary = models.ProduitsEnBonEntry.objects.filter(BonNo__store=CurrentStore)
        bilan_data = {}
        for entry in product_summary:
            key = entry.stock.id
            bilan_info = {
                "id": entry.id,
                "product_name": entry.stock.name,
                "product_reference": entry.stock.reference,
                "codeean": entry.stock.get_codeEA,
                # "product_category":entry.stock.category.pc_component,
                "category":entry.stock.ancestor_categories,
                "bill": entry.BonNo.idBon,
                "date": entry.BonNo.dateBon.strftime("%Y-%m-%d"),
                "entrepot": entry.BonNo.entrepot,
                "quantity": entry.quantity,
                "prix_achat":entry.stock.prix_achat,
                "fournisseur":entry.BonNo.fournisseur.acronym,
                
              
            }
            if key in bilan_data:
                bilan_data[key].append(bilan_info)
            else:
                bilan_data[key] = [bilan_info]
        context["product_summary"]=[item for sublist in bilan_data.values() for item in sublist]
        
        entrepots = models.Entrepot.objects.filter(store = CurrentStore )
        context["entrepots"] = entrepots
        
        familles = Category.objects.filter(store = CurrentStore)
        context["familles"] = familles
        fonrnisseurs=Fournisseur.objects.filter(store=CurrentStore)
        context["fonrnisseurs"]=fonrnisseurs
       
        
        return context
 
class ListSortieStockView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/stock_sortie.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_etatsorties' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)    
        current_month = datetime.now().month
        produits_en_bon_comptoir_entries = ProduitsEnBonComptoir.objects.filter(BonNo__store=CurrentStore)
        produits_en_bon_sortie_entries = ProduitsEnBonSortie.objects.filter(BonNo__store=CurrentStore)

        bilan_data = {}

        # Process produits_en_bon_comptoir_entries
        for entry in produits_en_bon_comptoir_entries:
            key = entry.stock.id
            bilan_info = {
                "id": entry.id,
                "product_name": entry.stock.name,
                "product_reference": entry.stock.reference,
                "codeean": entry.stock.get_codeEA,
                "product_category":entry.stock.category.pc_component,
                "category":entry.stock.ancestor_categories,
                "bill": entry.BonNo.idBon,
                "client": entry.BonNo.client.name if entry.BonNo.client is not None else '',
                "date": entry.BonNo.dateBon.strftime("%Y-%m-%d"),
                "entrepot": entry.BonNo.monentrepot,
                "quantity": entry.quantity,
                "prix_vente": float(entry.totalprice),
   
                
            }

            # Check if key is already in bilan_data
            if key in bilan_data:
                bilan_data[key].append(bilan_info)
            else:
                bilan_data[key] = [bilan_info]

        # Process produits_en_bon_sortie_entries
        for entry in produits_en_bon_sortie_entries:
            key = entry.stock.id
            bilan_info = {
                "id": entry.id,
                "product_name": entry.stock.name,
                "product_reference": entry.stock.reference,
                "codeean": entry.stock.get_codeEA,
                "product_category":entry.stock.category.pc_component if entry.stock.category is not None else '',
                "category":entry.stock.ancestor_categories,
                "bill": entry.BonNo.idBon,
                "client": entry.BonNo.client.name,
                "date": entry.BonNo.dateBon.strftime("%Y-%m-%d"),
                "entrepot": entry.BonNo.entrepot.name,
                "quantity": entry.quantity,
                "prix_vente": float(entry.totalprice),
                "NumSeries":entry.getnumSeries,
                
            }

            # Check if key is already in bilan_data
            if key in bilan_data:
                bilan_data[key].append(bilan_info)
            else:
                bilan_data[key] = [bilan_info]
        fonrnisseurs=Fournisseur.objects.filter(store=CurrentStore)
        context["fonrnisseurs"]=fonrnisseurs
        entrepots = models.Entrepot.objects.filter(store = CurrentStore )
        context["entrepots"] = entrepots
        
        familles = Category.objects.filter(store = CurrentStore)
        context["familles"] = familles
        # Convert dictionary values to a flat list
        context["products"] = [item for sublist in bilan_data.values() for item in sublist]
      
        return context
   

   
class ListReformeStockView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/stock_reforme.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonreforme' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        product_summary = models.ProduitsEnBonReforme.objects.filter(BonNo__store=CurrentStore ).values('produit__name','produit__reference','produit__TotalQte').annotate(
        total_quantity=Sum('quantity'),
        quantity_in_bonReforme=Sum(
            Case(
                When(BonNo__isnull=False, then='quantity'),
                default=0,
                output_field=IntegerField()
            )
        )
        )
        context["product_summary"]=product_summary
        print(context["product_summary"])
        return context   
     
class ListReintegreStockView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/stock_reintegration.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonreforme' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        products_info = []
        produits_en_bon_entries = models.ProduitsEnBonReintegration.objects.select_related('BonNo__bonRetour')
        for entry in produits_en_bon_entries:
         if entry.stock.store == CurrentStore:
           product_info = {
            'product_name': entry.stock.name,
            'product_reference': entry.stock.reference,
            'quantity_reintegrated': entry.quantity,
            'bon_reintegration_id': entry.BonNo.idBon,
            'date_bon': entry.BonNo.dateBon,
            'bon_retour_id': entry.BonNo.bonRetour.idBon if entry.BonNo.bonRetour else None,
            'user': entry.BonNo.user.username,
           }
           products_info.append(product_info)
        context["products"] = products_info
        return context 

class ListMaintenanceStockView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/stock_maintenance.html"
    login_url = 'home' 
    raise_exception = True 
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonreforme' in self.request.session.get('permissions', [])  or myuser.username == "nadjemeddine"

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        products_info = []
        produits_en_bon_retour_entries = models.ProduitsEnBonMaintenance.objects.select_related('BonNo__bonL')

        for entry in produits_en_bon_retour_entries:
          bon_retour = None
          if entry.BonNo.bonL is not None:
              bon_retour = entry.BonNo.bonL
          elif entry.BonNo.bonLComptoir is not None:  
              bon_retour = entry.BonNo.bonLComptoir
          else:
              bon_retour = entry.BonNo.bonR    
          if entry.produit.store == CurrentStore:
            product_info = {
                'product_name': entry.produit.name,
                'product_reference': entry.produit.reference,
                'decision': entry.BonNo.decision,
                'bon_id':entry.BonNo.idBon,
                'bonL_id':bon_retour.idBon if bon_retour is not None else '',
                'client':bon_retour.client.name if bon_retour is not None else '',
                'bonretour_date':bon_retour.dateBon if bon_retour is not None else '',
                'date_maint': entry.BonNo.dateBon,
            }
            products_info.append(product_info)
        context["products"] = products_info
        return context 

class ListEchangeStockView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/stock_echange.html"
    login_url = 'home' 
    raise_exception = True 
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonreforme' in self.request.session.get('permissions', [])  or myuser.username == "nadjemeddine"

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        products_info = []
        produits_en_bons_echange = ProduitsEnBonSortie.objects.filter(BonNo__idBon__startswith='BECH')

        for entry in produits_en_bons_echange:
          bon_retour = None
          id_bon = entry.BonNo.num_cheque_reglement
          if id_bon != '' and id_bon.startswith('BR'):             
              bon_retour = models.BonRetour.objects.filter(idBon = id_bon).first()  
          if entry.stock.store == CurrentStore:
                product_info = {
                    'product_name': entry.stock.name,
                    'product_reference': entry.stock.reference,
                    'qte': entry.quantity,
                    'bon_id': entry.BonNo.idBon,
                    'bonL_id': bon_retour.idBon if bon_retour is not None else '',
                    'client': entry.BonNo.client.name,
                    'bonretour_date':bon_retour.dateBon if bon_retour is not None else '',
                    'date_echange': entry.BonNo.dateBon,
                }
                products_info.append(product_info)
        context["products"] = products_info
        return context 
        
class ListRetourStockView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory/stock_retour.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'inventory.can_see_bonreforme' in self.request.session.get('permissions', [])  or myuser.username == "nadjemeddine"

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        products_info = []
        produits_en_bon_retour_entries = models.ProduitsEnBonRetour.objects.select_related('BonNo__bonL')

        for entry in produits_en_bon_retour_entries:
          if entry.produit.store == CurrentStore:
            product_info = {
                'product_name': entry.produit.name,
                'product_reference': entry.produit.reference,
                'delivered_quantity': entry.quantity,
                'reintegration_quantity': entry.quantity if entry.reintegrated == True else 0,
                'reintegration_decision': entry.reintegrated,
                'bonretour_id':entry.BonNo.idBon,
                'client':entry.BonNo.client.name,
                'bonretour_date':entry.BonNo.dateBon,
                'delivery_receipt_id': entry.BonNo.bonL.idBon if entry.BonNo.bonL else None
            }
            products_info.append(product_info)
        produits_en_bon_retour_entries = models.ProduitsEnBonRetourComptoir.objects.select_related('BonNo__bon_comptoir_associe')

        for entry in produits_en_bon_retour_entries:
          if entry.produit.store == CurrentStore:
            product_info = {
                'product_name': entry.produit.name,
                'product_reference': entry.produit.reference,
                'delivered_quantity': entry.quantity,
                'reintegration_quantity': entry.quantity,
                'reintegration_decision': True,
                'bonretour_id':entry.BonNo.idBon,
                'client':entry.BonNo.client.name,
                'bonretour_date':entry.BonNo.dateBon,
                'delivery_receipt_id': entry.BonNo.bon_comptoir_associe.idBon if entry.BonNo.bon_comptoir_associe else None
            }
            products_info.append(product_info)
        context["products"] = products_info
        return context 