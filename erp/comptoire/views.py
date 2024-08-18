from django.shortcuts import render
from django.views.generic.base import TemplateView
from django.http import Http404, JsonResponse
import json
from django.db import transaction,  IntegrityError
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from users.models import CustomUser
from clientInfo.models import store, CompteEntreprise, typeClient
from produits.models import Category, Product
from tiers.models import Fournisseur, Client
from . import models
from ventes.models import BonSortie
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
from inventory.models import Entrepot, Stock
from reglements.models import ModeReglement
from django.utils import timezone
from notifications.signals import notify
from django.db.models import Q
from decimal import Decimal
from users.models import MyLogEntry
from django.db.models import Count
from datetime import datetime, timedelta
from itertools import chain

def verifyPassword(request):
        data = json.loads(request.body)
        user = request.user
        # Verify if the provided password matches the current user's password
        if user.check_password(data["password"]):
            cloture = models.Cloture.objects.get(id=data["cloture_id"])
            cloture.collected=True
            cloture.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False})

def deletePointSell(request):
    try:
        data = json.loads(request.body)
        print(data)
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        user = models.pointVente.objects.get(id=data["user_id"])
        user.delete()
        return JsonResponse({'message': 'Point de vente Supprimé !'})
    except models.pointVente.DoesNotExist:
        return JsonResponse({'error': 'Point de vente Non-trouve.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché, car cet point de vente est lié aux autres composants - {}'.format(str(e))})
   
def supprimerCloture(request):
    try:
        data = json.loads(request.body)
        print(data)
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        user = models.Cloture.objects.get(id=data["user_id"])
        user.delete()
        return JsonResponse({'message': 'Cloture Supprimé !'})
    except models.Cloture.DoesNotExist:
        return JsonResponse({'error': 'Cloture Non-trouvé.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché, car cette Affectation est lié aux autres composants - {}'.format(str(e))})  
   
def editCloture(request):   
         # Find the product by reference
        data = json.loads(request.body)
        Currentuser = request.user
        myuser = CustomUser.objects.get(username=Currentuser.username)
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)   
        cloture_id = data.get('user_id')  # Assuming you have a field for the AffectationCaisse's ID in dataInvoice
        if  cloture_id:
          try:
            with transaction.atomic():  
                cloture_obj = models.Cloture.objects.get(id=cloture_id)
                old_montant =  cloture_obj.montant
                cloture_obj.montant = data.get('montant')
                cloture_obj.save()  # Save the changes
                CurrentStore = store.objects.get(pk=store_id)
                user = request.user
                myuser= CustomUser.objects.get(username=user.username)
                current_timestamp = datetime.now()
                logs_saving = MyLogEntry.objects.create(
                    author= myuser,
                    description= f' A modifié la clôture n°=  {cloture_id}, de la date {cloture_obj.date} : de {old_montant} -> {cloture_obj.montant}',
                    timestamp = current_timestamp.strftime("%d/%m/%Y at %H:%Mh"),
                    store  = CurrentStore
                )
                return JsonResponse({'message': 'Cloture a été Modifié.'})
          except models.AffectationCaisse.DoesNotExist:
            return JsonResponse({'error': 'Cloture Ne peut pas être modifié.'})
        return JsonResponse({'error': 'Re-essayer S il vous plait.'})
        
def editPointVente(request):   
         # Find the product by reference
        data = json.loads(request.body)
        Currentuser = request.user
        myuser = CustomUser.objects.get(username=Currentuser.username)
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        print(data) 
        pointvente_id = data.get('pointvente_id')  # Assuming you have a field for the pointVente's ID in data
        if pointvente_id:
         try:
            pointvente_obj = models.pointVente.objects.get(id=pointvente_id)
            pointvente_obj.label = data.get('label')
            pointvente_obj.entrepot = Entrepot.objects.get(id=data['entrepot'])
            pointvente_obj.type_reglement = data['type_reg']
            pointvente_obj.mode_payment = ModeReglement.objects.get(id=data['mode_paiement'])
            pointvente_obj.adresse = data['adresse']
            pointvente_obj.Téléphone = data['tlf']
            pointvente_obj.fidelite = data['fidelite'].lower() == 'true'
            pointvente_obj.store = CurrentStore
            pointvente_obj.save()  # Save the changes
         except models.pointVente.DoesNotExist:
            return JsonResponse({'message': 'Point de vente Ne peut pas être modifié.'})
        
        return JsonResponse({'message': 'Point de vente instance updated successfully.'})
 
def supprimerAffectation(request):
    try:
        data = json.loads(request.body)
        print(data)
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        user = models.AffectationCaisse.objects.get(id=data["user_id"])
        user.delete()
        return JsonResponse({'message': 'Affectation Supprimé !'})
    except models.AffectationCaisse.DoesNotExist:
        return JsonResponse({'error': 'Affectation Non-trouve.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché, car cette Affectation est lié aux autres composants - {}'.format(str(e))})  
   
def editAffectation(request):   
         # Find the product by reference
        data = json.loads(request.body)
        Currentuser = request.user
        myuser = CustomUser.objects.get(username=Currentuser.username)
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)   
        affectation_id = data.get('affectation_id')  # Assuming you have a field for the AffectationCaisse's ID in dataInvoice
        if affectation_id:
          try:
            affectation_obj = models.AffectationCaisse.objects.get(id=affectation_id)
            affectation_obj.emplacement = models.pointVente.objects.get(id=data['emplacement'])
            affectation_obj.CompteTres = CompteEntreprise.objects.get(id=data['caisse'])
            affectation_obj.utilisateur = CustomUser.objects.get(id=data['utilisateur'])
            affectation_obj.store = CurrentStore
            affectation_obj.save()  # Save the changes
            return JsonResponse({'message': 'Point de vente instance updated successfully.'})
          except models.AffectationCaisse.DoesNotExist:
            return JsonResponse({'message': 'Point de vente Ne peut pas être modifié.'})
        return JsonResponse({'message': 'Re-essayer S il vous plait.'})
        
def addClient(request):
    data = json.loads(request.body)
    print(data)
    dataInvoice = data
    if dataInvoice:
        nom_client = dataInvoice["nomClient"] 
        adresse_client = dataInvoice["adresse"]
        phone_client = dataInvoice["phone"]
        categorie = dataInvoice["catclient"]
        Currentuser = request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        store_id = request.session["store"]
        my_store = store.objects.get(pk=store_id)
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
    else:
        return JsonResponse({'success': False})

def fetchProductCompt(request):
  data = json.loads(request.body)
  print(data)
  bonLivraison = models.BonComptoire.objects.get(id=data["bonL"])
  produits = bonLivraison.produits_en_bon_comptoir.all()
  produits_data=[]    
  for produit in produits :
      produits_dict = {
              'name': produit.stock.name,
              'reference':produit.stock.reference,
              'quantity': produit.quantity,
              'unitprice': float(produit.unitprice),
              'totalprice': float(produit.totalprice),
            } 
      produits_data.append(produits_dict)
  return JsonResponse({'produits':produits_data})

class ComtpoirRetourView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "comptoire/comptoir_retour_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'comptoire.can_see_comptoir' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)    
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        store_id = self.request.session["store"]
        my_store = store.objects.get(pk=store_id)
        clients_list = Client.objects.filter(store=my_store)
        clients=[]
        for cl in clients_list:
                cl_dict={
                "client_name" :cl.name,
                "client_address":cl.adresse,
                "client_phone" : cl.phone,                      
                }
                clients.append(cl_dict)
        context["clients"]=clients
        entrepots = Entrepot.objects.filter(store=my_store)
        context["entrepots"]=entrepots
        bons = models.BonComptoire.objects.filter(store=my_store)
        context["bons_compt"]=bons
        types_clients = typeClient.objects.filter(store=my_store)
        context["types_clients"]=types_clients
        myuser=CustomUser.objects.get(username=self.request.user.username)
        ent_ins = myuser.mon_affectation.first()
        context["caisse"]=ent_ins.CompteTres
        if ent_ins:
         point_vente_label = ent_ins.emplacement.label
         point_vente = models.pointVente.objects.filter(label=point_vente_label).first()
         my_entrepot = point_vente.entrepot
         stocks = my_entrepot.get_stocks()
         stock_data=[]
         for stock in stocks:
            product_name = stock.product.name
            entrepot_name = stock.entrepot.name
            quantity = stock.quantity
            price = stock.product.prix_vente
            reference = stock.product.reference
            entrepot=stock.entrepot.name
            categorie=stock.product.category.Libellé if stock.product.category is not None else ''
            stock_info = {
            "product_name": product_name,
            "entrepot_name": entrepot_name,
            "quantity": quantity,
            "reference": reference,
            "entrepot":entrepot,
            "categorie":categorie,
            "price": float(price),
            }
            stock_data.append(stock_info)
         context["stock"]=stock_data
        else:
          my_entrepot = None  

        current_year = timezone.now().year

        # Filter BonComptoir instances created in the current year
        boncomptoirs_this_year = models.BonRetourComptoir.objects.filter(dateBon__year=current_year)

        # Get the count of BonComptoir instances in the current year
        sequential_number = boncomptoirs_this_year.count() + 1

        boncomptoire_code = f'RCOMPT{str(current_year)[-2:]}/{str(sequential_number).zfill(5)}'
        context["code"] = boncomptoire_code
        return context
    
    @method_decorator(login_required)
    @transaction.atomic
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        print(dataInvoice)
        if dataInvoice: 
            print(dataInvoice)
            IdBon = dataInvoice["IdBon"]
            dateBon = dataInvoice["dateBp"]
            store_id = self.request.session["store"]
            my_store = store.objects.get(pk=store_id)
            clientObj = Client.objects.get(id=dataInvoice["clientId"])
            boncomptoir = models.BonComptoire.objects.get(id=dataInvoice["boncomptoir"])
            decision = dataInvoice["decision"]
            if decision == 'refund':
                refundAmount = dataInvoice["refundAmount"]
                print('refundampunt is ',refundAmount)
            for product_data in dataInvoice["produits"]:
                 myuser=CustomUser.objects.get(username=self.request.user.username)
                 ent_ins = myuser.mon_affectation.first()
                 point_vente_label = ent_ins.emplacement.label
                 point_vente = models.pointVente.objects.filter(label=point_vente_label).first()
                 my_entrepot = point_vente.entrepot
                 p = Stock.objects.select_for_update().get( Q(product__name=product_data["name"]) & Q(entrepot__name=my_entrepot))
                 p.quantity += int(product_data["qty"])
                 p.save()
                 produit_inst = Product.objects.filter(name=product_data["name"], store=my_store ).first()
                 produit_inst.TotalQte += int(product_data["qty"])
                 produit_inst.save()
                 if dataInvoice["refundAmount"] :
                  refundAmount = dataInvoice["refundAmount"]
                  clientObj.solde -= Decimal(refundAmount)
            bonretourcompt = models.BonRetourComptoir.objects.create(
                     idBon =IdBon,
                     dateBon = dateBon,
                     client = clientObj,
                     user= myuser,
                     bon_comptoir_associe = boncomptoir,
                     decision =decision
                 )
            for product_data in dataInvoice["produits"]:
                produit_inst = Product.objects.filter(name=product_data["name"], store=my_store ).first()
                qty = int(product_data['qty'])
                rate = float(product_data['rate'])
                total = int(qty) * float(rate)
                models.ProduitsEnBonRetourComptoir.objects.create(
                    BonNo = bonretourcompt,
                    produit = produit_inst,
                    quantity = qty,
                    unitprice = rate,
                    totalprice =total
                )
            return JsonResponse({'success':True})   

class ComtpoirRetourViewFull(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "comptoire/comptoir_retour_pagefull.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'comptoire.can_see_comptoir' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)    
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        store_id = self.request.session["store"]
        my_store = store.objects.get(pk=store_id)
        clients_list = Client.objects.filter(store=my_store)
        clients=[]
        for cl in clients_list:
                cl_dict={
                "client_name" :cl.name,
                "client_address":cl.adresse,
                "client_phone" : cl.phone,                      
                }
                clients.append(cl_dict)
        context["clients"]=clients
        entrepots = Entrepot.objects.filter(store=my_store)
        context["entrepots"]=entrepots
        bons = models.BonComptoire.objects.filter(store=my_store)
        context["bons_compt"]=bons
        types_clients = typeClient.objects.filter(store=my_store)
        context["types_clients"]=types_clients
        myuser=CustomUser.objects.get(username=self.request.user.username)
        ent_ins = myuser.mon_affectation.first()
        context["caisse"]=ent_ins.CompteTres
        if ent_ins:
         point_vente_label = ent_ins.emplacement.label
         point_vente = models.pointVente.objects.filter(label=point_vente_label).first()
         my_entrepot = point_vente.entrepot
         stocks = my_entrepot.get_stocks()
         stock_data=[]
         for stock in stocks:
            product_name = stock.product.name
            entrepot_name = stock.entrepot.name
            quantity = stock.quantity
            price = stock.product.prix_vente
            reference = stock.product.reference
            entrepot=stock.entrepot.name
            categorie=stock.product.category.Libellé
            stock_info = {
            "product_name": product_name,
            "entrepot_name": entrepot_name,
            "quantity": quantity,
            "reference": reference,
            "entrepot":entrepot,
            "categorie":categorie,
            "price": float(price),
            }
            stock_data.append(stock_info)
         context["stock"]=stock_data
        else:
          my_entrepot = None  
        current_year = timezone.now().year
        last_bon = models.BonRetourComptoir.objects.order_by('-id').first()
        if last_bon:
            sequential_number = last_bon.id + 1
        else:
            sequential_number = 1
        boncomptoire_code = f'RCOMPT{str(current_year)[-2:]}/{str(sequential_number).zfill(5)}'
        context["code"] =boncomptoire_code
        return context
    
    @method_decorator(login_required)
    @transaction.atomic
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        print(dataInvoice)
        if dataInvoice: 
            print(dataInvoice)
            IdBon = dataInvoice["IdBon"]
            dateBon = dataInvoice["dateBp"]
            store_id = self.request.session["store"]
            my_store = store.objects.get(pk=store_id)
            clientObj = Client.objects.get(id=dataInvoice["clientId"])
            boncomptoir = models.BonComptoire.objects.get(id=dataInvoice["boncomptoir"])
            decision = dataInvoice["decision"]
            if decision == 'refund':
                refundAmount = dataInvoice["refundAmount"]
                print('refundampunt is ',refundAmount)
            for product_data in dataInvoice["produits"]:
                 myuser=CustomUser.objects.get(username=self.request.user.username)
                 ent_ins = myuser.mon_affectation.first()
                 point_vente_label = ent_ins.emplacement.label
                 point_vente = models.pointVente.objects.filter(label=point_vente_label).first()
                 my_entrepot = point_vente.entrepot
                 p = Stock.objects.select_for_update().get( Q(product__name=product_data["name"]) & Q(entrepot__name=my_entrepot))
                 p.quantity += int(product_data["qty"])
                 p.save()
                 produit_inst = Product.objects.get(name=product_data["name"], store = my_store)
                 produit_inst.TotalQte += int(product_data["qty"])
                 produit_inst.save()
                 if dataInvoice["refundAmount"] :
                  refundAmount = dataInvoice["refundAmount"]
                  clientObj.solde -= Decimal(refundAmount)
            bonretourcompt = models.BonRetourComptoir.objects.create(
                     idBon =IdBon,
                     dateBon = dateBon,
                     client = clientObj,
                     user= myuser,
                     bon_comptoir_associe = boncomptoir,
                     decision =decision
                 )
            for product_data in dataInvoice["produits"]:
                produit_inst = Product.objects.get(name=product_data["name"], store =my_store)
                qty = int(product_data['qty'])
                rate = float(product_data['rate'])
                total = int(qty) * float(rate)
                models.ProduitsEnBonRetourComptoir.objects.create(
                    BonNo = bonretourcompt,
                    produit = produit_inst,
                    quantity = qty,
                    unitprice = rate,
                    totalprice =total
                )
            return JsonResponse({'success':True})   

class ComtpoirView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "comptoire/comptoir_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'comptoire.can_see_comptoir' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)    
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        store_id = self.request.session["store"]
        my_store = store.objects.get(pk=store_id)
        clients_list = Client.objects.filter(store=my_store)
        clients=[]
        for cl in clients_list:
                cl_dict={
                "client_name" :cl.name,
                "client_address":cl.adresse,
                "client_phone" : cl.phone,                      
                }
                clients.append(cl_dict)
        context["clients"]=clients
        entrepots = Entrepot.objects.filter(store=my_store)
        context["entrepots"]=entrepots
        bons = models.BonComptoire.objects.filter(store=my_store)
        context["bons"]=bons
        types_clients = typeClient.objects.filter(store=my_store)
        context["types_clients"]=types_clients
        myuser=CustomUser.objects.get(username=self.request.user.username)
        ent_ins = myuser.mon_affectation.first()
        if ent_ins:
         context["caisse"]=ent_ins.CompteTres
         point_vente_label = ent_ins.emplacement.label
         point_vente = models.pointVente.objects.filter(label=point_vente_label).first()
         my_entrepot = point_vente.entrepot
         stocks = my_entrepot.get_stocks()
         stock_data=[]
         for stock in stocks:
            product_name = stock.product.name
            entrepot_name = stock.entrepot.name
            quantity = stock.quantity
            
            if store_id == '1':
                prix_vente = stock.product.prix_vente
                prix_livraison = stock.product.prix_livraison 
                tva = stock.product.tva_douan
                # Convert the float to Decimal before multiplication
                price = round((prix_vente + prix_livraison + tva)* Decimal('1.19'),0)
            else:
                price = stock.product.prix_vente 
               
            reference = stock.product.reference
            entrepot=stock.entrepot.name
            categorie=stock.product.category.Libellé if stock.product.category is not None else ''
            stock_info = {
            "product_id": stock.product.id,    
            "product_name": product_name,
            "entrepot_name": entrepot_name,
            "quantity": quantity,
            "reference": reference,
            "entrepot":entrepot,
            "categorie":categorie,
            "price": float(price),
            }
            stock_data.append(stock_info)
         context["stock"]=stock_data
        else:
          my_entrepot = None  
        
        return context
    
    @method_decorator(login_required)
    @transaction.atomic
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        print(dataInvoice)
        if dataInvoice: 
            print(dataInvoice)
            idBon = dataInvoice["IdBon"]
            dateBon = dataInvoice["dateBp"]
            client_name = dataInvoice["clientInfo"]["name"]
            client_instance =Client.objects.filter(name=client_name).first()
            Currentuser = request.user
            myuser  = CustomUser.objects.get(username=Currentuser.username)
            store_id = request.session["store"]
            my_store = store.objects.get(pk=store_id)
            ent_ins = myuser.mon_affectation.first()
            TotalPay =0
            if dataInvoice.get("verssement"):
                TotalPay = 0               
            else:
                TotalPay = dataInvoice.get("TotalPay", None)  # Use None as a default value if "TotalPay" is not present

            TotalRemise =dataInvoice["TotalRemise"]
            if ent_ins :
                caisse = ent_ins.CompteTres
            else :
                caisse=None           
            if ent_ins:
                point_vente_label = ent_ins.emplacement.label
                point_vente = models.pointVente.objects.filter(label=point_vente_label).first()
                my_entrepot = point_vente.entrepot
            if my_entrepot:
             for product in dataInvoice["produits"]:            
                p = Stock.objects.select_for_update().get( Q(product__name=product["name"]) & Q(entrepot__name=my_entrepot))
                new_quantity = p.quantity - int(product["qty"]) ## la quantité dans l'entrepot qui convient
                print(p, int(product["qty"]))
                if new_quantity < 0:
                  # If any product has insufficient quantity, return a response to inform the user
                  return JsonResponse({'error': f"Stock Insuffisant pour  : {product['name']}", 'prompt_user': True})            
                p.quantity = new_quantity
                p.save()  
             current_year = timezone.now().year

             # Filter BonComptoir instances created in the current year
             boncomptoirs_this_year = models.BonComptoire.objects.filter(dateBon__year=current_year)
    
             # Get the count of BonComptoir instances in the current year
             sequential_number = boncomptoirs_this_year.count() + 1
             boncomptoire_code = f'VC{str(current_year)[-2:]}/{str(sequential_number).zfill(5)}'
             existing_boncomptoire = models.BonComptoire.objects.filter(idBon=boncomptoire_code).first()
             if existing_boncomptoire is not None :
                while existing_boncomptoire is not None:
                    sequential_number += 1
                    boncomptoire_code = f'VC{str(current_year)[-2:]}/{str(sequential_number).zfill(5)}'
                    existing_boncomptoire = models.BonComptoire.objects.filter(idBon=boncomptoire_code).first()
                boncomptoire_code = f'VC{str(current_year)[-2:]}/{str(sequential_number).zfill(5)}'
             bonComptoir = models.BonComptoire.objects.create(
                idBon=boncomptoire_code,
                dateBon =dateBon,
                client = client_instance,
                store=my_store,
                pointVente =point_vente,
                observation = dataInvoice["obs"],
                user= myuser,
                caisse = caisse,
                totalprice =TotalPay,
                totalremise = TotalRemise
             )
             current_date = timezone.now()
             if dataInvoice.get("verssement"):
                verssement_instance = models.verssement(
                montant=dataInvoice["TotalPay"],
                date=current_date,
                utilisateur=myuser,  # Assuming you have a logged-in user
                bon_comptoir_associe=bonComptoir,
                store=my_store,
                ) 
                verssement_instance.save()  
             for produit in dataInvoice["produits"]:
                print(produit)
                produit_inst = Product.objects.get(reference=produit["ref"], store =my_store)
                produit_inst.TotalQte -= int(produit["qty"])
                produit_inst.save()
                qty = int(produit['qty'])
                rate = float(produit['rate'])
                total = int(qty) * float(rate)
                models.ProduitsEnBonComptoir.objects.create(
                    BonNo = bonComptoir,
                    stock = produit_inst,
                    quantity = qty,
                    unitprice = rate,
                    totalprice =total
                )
             return JsonResponse({'success':True, 'code': boncomptoire_code})
            else :
                return JsonResponse({"error":"Aucun Entrepot n'est selectioné"})
            
class ComtpoirRectificationView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "comptoire/comptoir_rectif_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'comptoire.can_see_comptoir' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)    
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        store_id = self.request.session["store"]
        my_store = store.objects.get(pk=store_id)
        clients_list = Client.objects.filter(store=my_store)
        clients=[]
        for cl in clients_list:
                cl_dict={
                "client_name" :cl.name,
                "client_address":cl.adresse,
                "client_phone" : cl.phone,                      
                }
                clients.append(cl_dict)
        context["clients"]=clients
        entrepots = Entrepot.objects.filter(store=my_store)
        context["entrepots"]=entrepots
        bons = models.BonComptoire.objects.filter(store=my_store)
        context["bons"]=bons
        types_clients = typeClient.objects.filter(store=my_store)
        context["types_clients"]=types_clients
        myuser=CustomUser.objects.get(username=self.request.user.username)
        ent_ins = myuser.mon_affectation.first()
        if ent_ins:
         context["caisse"]=ent_ins.CompteTres
         point_vente_label = ent_ins.emplacement.label
         point_vente = models.pointVente.objects.filter(label=point_vente_label).first()
         my_entrepot = point_vente.entrepot
         stocks = my_entrepot.get_stocks()
         stock_data=[]
         for stock in stocks:
            product_name = stock.product.name
            entrepot_name = stock.entrepot.name
            quantity = stock.quantity
            
            if store_id == '1':
                prix_vente = stock.product.prix_vente
                prix_livraison = stock.product.prix_livraison 
                tva = stock.product.tva_douan
                # Convert the float to Decimal before multiplication
                price = round((prix_vente + prix_livraison + tva)* Decimal('1.19'),0)
            else:
                price = stock.product.prix_vente 
               
            reference = stock.product.reference
            entrepot=stock.entrepot.name
            categorie=stock.product.category.Libellé if stock.product.category is not None else ''
            stock_info = {
                "product_id": stock.product.id,    
                "product_name": product_name,
                "entrepot_name": entrepot_name,
                "quantity": quantity,
                "reference": reference,
                "entrepot":entrepot,
                "categorie":categorie,
                "price": float(price),
            }
            stock_data.append(stock_info)
         context["stock"]=stock_data
        else:
          my_entrepot = None  
        
        return context
    
    @method_decorator(login_required)
    @transaction.atomic
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        print(dataInvoice)
        if dataInvoice: 
            print(dataInvoice)
            idBon = dataInvoice["IdBon"]
            dateBon = dataInvoice["dateBp"]
            client_name = dataInvoice["clientInfo"]["name"]
            client_instance =Client.objects.filter(name=client_name).first()
            Currentuser = request.user
            myuser  = CustomUser.objects.get(username=Currentuser.username)
            store_id = request.session["store"]
            my_store = store.objects.get(pk=store_id)
            ent_ins = myuser.mon_affectation.first()
            TotalPay =0
            if dataInvoice.get("verssement"):
                TotalPay = 0               
            else:
                TotalPay = dataInvoice.get("TotalPay", None)  # Use None as a default value if "TotalPay" is not present

            TotalRemise =dataInvoice["TotalRemise"]
            if ent_ins :
                caisse = ent_ins.CompteTres
            else :
                caisse=None           
            if ent_ins:
                point_vente_label = ent_ins.emplacement.label
                point_vente = models.pointVente.objects.filter(label=point_vente_label).first()
                my_entrepot = point_vente.entrepot
            if my_entrepot:
             current_year = timezone.now().year

             # Filter BonComptoir instances created in the current year
             boncomptoirs_this_year = models.BonRectification.objects.filter(dateBon__year=current_year)
    
             # Get the count of BonComptoir instances in the current year
             sequential_number = boncomptoirs_this_year.count() + 1
             boncomptoire_code = f'VCR{str(current_year)[-2:]}/{str(sequential_number).zfill(5)}'
             existing_boncomptoire = models.BonRectification.objects.filter(idBon=boncomptoire_code).first()
             if existing_boncomptoire is not None :
                while existing_boncomptoire is not None:
                    sequential_number += 1
                    boncomptoire_code = f'VC{str(current_year)[-2:]}/{str(sequential_number).zfill(5)}'
                    existing_boncomptoire = models.BonRectification.objects.filter(idBon=boncomptoire_code).first()
                boncomptoire_code = f'VC{str(current_year)[-2:]}/{str(sequential_number).zfill(5)}'
             bonComptoir = models.BonRectification.objects.create(
                idBon=boncomptoire_code,
                dateBon =dateBon,
                client = client_instance,
                store=my_store,
                pointVente =point_vente,
                observation = dataInvoice["obs"],
                user= myuser,
                caisse = caisse,
                totalprice =TotalPay,
                totalremise = TotalRemise
             )
             current_date = timezone.now()
             if dataInvoice.get("verssement"):
                verssement_instance = models.verssement(
                    montant=dataInvoice["TotalPay"],
                    date=current_date,
                    utilisateur=myuser,  # Assuming you have a logged-in user
                    bon_rectification_associe=bonComptoir,
                    store=my_store,
                ) 
                verssement_instance.save()  
             for produit in dataInvoice["produits"]:
                produit_inst = Product.objects.filter(reference=produit["ref"], store=my_store).first()

                if produit_inst is None:
                    # Create the product if it doesn't exist
                    produit_inst = Product.objects.create(
                        reference=produit["ref"],
                        name = produit["ref"],
                        prix_vente = produit["rate"],
                        initial_qte = 1,
                        store=my_store,
                    )
                qty = int(produit['qty'])
                rate = float(produit['rate'])
                total = int(qty) * float(rate)
                models.ProduitsEnBonRectif.objects.create(
                    BonNo = bonComptoir,
                    stock = produit_inst,
                    quantity = qty,
                    unitprice = rate,
                    totalprice =total
                )
             return JsonResponse({'success':True, 'code': boncomptoire_code})
            else :
                return JsonResponse({"error":"Aucun Entrepot n'est selectioné"})
 
class ComtpoirViewFull(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "comptoire/comptoir_pagefull.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'comptoire.can_see_comptoir' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)    
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        store_id = self.request.session["store"]
        my_store = store.objects.get(pk=store_id)
        clients_list = Client.objects.filter(store=my_store)
        clients=[]
        for cl in clients_list:
                cl_dict={
                "client_name" :cl.name,
                "client_address":cl.adresse,
                "client_phone" : cl.phone,                      
                }
                clients.append(cl_dict)
        context["clients"]=clients
        entrepots = Entrepot.objects.filter(store=my_store)
        context["entrepots"]=entrepots
        bons = models.BonComptoire.objects.filter(store=my_store)
        context["bons"]=bons
        types_clients = typeClient.objects.filter(store=my_store)
        context["types_clients"]=types_clients
        myuser=CustomUser.objects.get(username=self.request.user.username)
        ent_ins = myuser.mon_affectation.first()
        if ent_ins:
         context["caisse"]=ent_ins.CompteTres
         point_vente_label = ent_ins.emplacement.label
         point_vente = models.pointVente.objects.filter(label=point_vente_label).first()
         my_entrepot = point_vente.entrepot
         stocks = my_entrepot.get_stocks()
         stock_data=[]
         for stock in stocks:
            product_name = stock.product.name
            entrepot_name = stock.entrepot.name
            quantity = stock.quantity
            price = stock.product.prix_vente
            reference = stock.product.reference
            entrepot=stock.entrepot.name
            categorie=stock.product.category.Libellé
            stock_info = {
            "product_name": product_name,
            "entrepot_name": entrepot_name,
            "quantity": quantity,
            "reference": reference,
            "entrepot":entrepot,
            "categorie":categorie,
            "price": float(price),
            }
            stock_data.append(stock_info)
         context["stock"]=stock_data
        else:
          my_entrepot = None  
        current_year = timezone.now().year

        # Filter BonComptoir instances created in the current year
        boncomptoirs_this_year = models.BonComptoire.objects.filter(dateBon__year=current_year)

        # Get the count of BonComptoir instances in the current year
        sequential_number = boncomptoirs_this_year.count() + 1

        boncomptoire_code = f'VC{str(current_year)[-2:]}/{str(sequential_number).zfill(5)}'
        context["code"] =boncomptoire_code
        return context
    
    @method_decorator(login_required)
    @transaction.atomic
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        print(dataInvoice)
        if dataInvoice: 
            print(dataInvoice)
            idBon = dataInvoice["IdBon"]
            dateBon = dataInvoice["dateBp"]
            client_name = dataInvoice["clientInfo"]["name"]
            client_instance =Client.objects.filter(name=client_name).first()
            Currentuser = request.user
            myuser  = CustomUser.objects.get(username=Currentuser.username)
            store_id = request.session["store"]
            my_store = store.objects.get(pk=store_id)
            ent_ins = myuser.mon_affectation.first()
            TotalPay =0
            if dataInvoice.get("verssement"):
                TotalPay = 0               
            else:
                TotalPay = dataInvoice.get("TotalPay", None)  # Use None as a default value if "TotalPay" is not present
            TotalRemise =dataInvoice["TotalRemise"]
            if ent_ins :
                caisse = ent_ins.CompteTres
            else :
                caisse=None           
            if ent_ins:
                point_vente_label = ent_ins.emplacement.label
                point_vente = models.pointVente.objects.filter(label=point_vente_label).first()
                my_entrepot = point_vente.entrepot
            if my_entrepot:
             for product in dataInvoice["produits"]:            
                p = Stock.objects.select_for_update().get( Q(product__name=product["name"]) & Q(entrepot__name=my_entrepot))
                new_quantity = p.quantity - int(product["qty"]) ## la quantité dans l'entrepot qui convient
                print(p, int(product["qty"]))
                if new_quantity < 0:
                  # If any product has insufficient quantity, return a response to inform the user
                  return JsonResponse({'error': f"Stock Insuffisant pour  : {product['name']}", 'prompt_user': True})            
                p.quantity = new_quantity
                p.save()    
             bonComptoir = models.BonComptoire.objects.create(
                idBon=idBon,
                dateBon =dateBon,
                client = client_instance,
                store=my_store,
                user= myuser,
                pointVente =point_vente,
                caisse = caisse,
                totalprice =TotalPay,
                totalremise = TotalRemise
             )
             current_date = timezone.now()
             if dataInvoice.get("verssement"):
                verssement_instance = models.verssement(
                montant=dataInvoice["TotalPay"],
                date=current_date,
                utilisateur=myuser,  # Assuming you have a logged-in user
                bon_comptoir_associe=bonComptoir,
                store=my_store,
                ) 
                verssement_instance.save()  
             for produit in dataInvoice["produits"]:
                print(produit)
                produit_inst = Product.objects.get(reference=produit["ref"], store = my_store)
                produit_inst.TotalQte -= int(produit["qty"])
                produit_inst.save()
                qty = int(produit['qty'])
                rate = float(produit['rate'])
                total = int(qty) * float(rate)
                models.ProduitsEnBonComptoir.objects.create(
                    BonNo = bonComptoir,
                    stock = produit_inst,
                    quantity = qty,
                    unitprice = rate,
                    totalprice =total
                )
             return JsonResponse({'success':True})
            else :
                return JsonResponse({"error":"Aucun Entrepot n'est selectioné"})
 
class ClientFideliteView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "comptoire/fidelite_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'comptoire.can_see_comptoir' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)    
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        store_id = self.request.session["store"]
        my_store = store.objects.get(pk=store_id)
        clients = Client.objects.filter(store=my_store)
        context["clients"] = clients
        return context
         
class SellPointsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "comptoire/points_sells.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'comptoire.can_see_comptoir' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)    
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        store_id = self.request.session["store"]
        my_store = store.objects.get(pk=store_id)
        points_ventes = models.pointVente.objects.filter(store=my_store)
        context["points_ventes"] = points_ventes
        entrepots = Entrepot.objects.filter(store=my_store)
        context["entrepots"] = entrepots
        emplacements = Entrepot.objects.filter(store=my_store) 
        context["emplacements"] =emplacements
        mode_paiment = ModeReglement.objects.filter(store=my_store)
        context["mode_paiement"] = mode_paiment
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        print(dataInvoice)
        if dataInvoice: 
            label = dataInvoice.get('label')
            entrepot = Entrepot.objects.get(id=dataInvoice["entrepot"])
            mode_paiement = ModeReglement.objects.get(id=dataInvoice["mode_paiement"])
            type_reg=dataInvoice["type_reg"]
            adresse= dataInvoice["adresse"]
            tlf=dataInvoice["tlf"]
            fidelite= dataInvoice["fidelite"].lower() == 'true'
			
            pointvente_obj = models.pointVente.objects.create(
                label =label,
                entrepot=entrepot,
                type_reglement=type_reg,
                mode_payment = mode_paiement,
                adresse = adresse,
                Téléphone = tlf,
                fidelite = fidelite,
                store = store.objects.get(pk=self.request.session["store"])  
            )
        return JsonResponse({'success': True})
    
class AffectationsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "comptoire/affectation_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'comptoire.can_see_comptoir' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)    
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        store_id = self.request.session["store"]
        my_store = store.objects.get(pk=store_id)
        comptes = CompteEntreprise.objects.filter(store=my_store)
        context["comptes"] = comptes
        users = CustomUser.objects.filter(EmployeeAt=my_store)
        context["users"] = users
        emplacements = models.pointVente.objects.filter(store=my_store) 
        context["emplacements"] =emplacements
        affectations = models.AffectationCaisse.objects.filter(store=my_store)
        context["affectations"] = affectations
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        if dataInvoice: 
            emplacement = models.pointVente.objects.get(id=dataInvoice["emplacement"])
            caisse = CompteEntreprise.objects.get(id=dataInvoice["caisse"])
            utilisateur= CustomUser.objects.get(id=dataInvoice["utilisateur"])
            store_id = self.request.session["store"]
            my_store = store.objects.get(pk=store_id)
            affect = models.AffectationCaisse.objects.create(
                emplacement=emplacement, 
                CompteTres=caisse,
                utilisateur=utilisateur,
                store= my_store
            )
        return JsonResponse({'success': True})
        
class EmplacementView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "comptoire/emplacement.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'comptoire.can_see_comptoir' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)    
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        store_id = self.request.session["store"]
        my_store = store.objects.get(pk=store_id)  
        emplacements = models.Emplacement.objects.filter(store=my_store)
        context["emplacements"] =emplacements
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        print(dataInvoice)
        if dataInvoice: 
            label =dataInvoice.get('label')
            lieu=dataInvoice.get('lieu')
            store_id = self.request.session["store"]
            my_store = store.objects.get(pk=store_id)  
            emp = models.Emplacement.objects.create(
                Label=label,
                lieu=lieu,
                store=my_store
            )
        return JsonResponse({'success': True})
    
class ClotureView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "comptoire/cloture_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'comptoire.can_see_comptoir' in self.request.session.get('permissions', []) or  self.request.session["role"] == "DIRECTEUR EXECUTIF"

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)    
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        store_id = self.request.session["store"]
        my_store = store.objects.get(pk=store_id)  
        if self.request.session["role"] == "manager" or  self.request.session["role"] == "DIRECTEUR EXECUTIF":
           clotures = models.Cloture.objects.filter(store=my_store).order_by('date')
        else:
            clotures = models.Cloture.objects.filter(utilisateur=myuser).order_by('date')
        list_cloture =[]
        all_caisses = CompteEntreprise.objects.filter(store=my_store)
        today = datetime.now().date()
        current_date = datetime(today.year, 1, 1).date()
        affectations = models.pointVente.objects.filter(store= my_store)
        for affectation in affectations:
            user = affectation.pos_affectation.first().utilisateur
            while user.group is None:
                # Get the next user in the affectation
                affectation = models.AffectationCaisse.objects.filter(store=my_store, utilisateur__gt=user).first()
                # If no more users, break out of the loop
                if affectation is None:
                    break

                user = affectation.utilisateur


            current_date = datetime(2024, 1, 1).date()  # Set the starting date

            while current_date < today:
                cloture = models.Cloture.objects.filter(utilisateur=user, date=current_date, store=my_store).first()
                if cloture is None:
                    # If the cloture entry doesn't exist, create one with montant set to 0
                    cloture_obj = models.Cloture.objects.create(
                        utilisateur=user,
                        date=current_date,
                        store=my_store,
                        montant=Decimal(0),
                        # Add any other necessary fields
                    )
                current_date += timedelta(days=1)

                       
        for clot in clotures:
                total_price_sum = 0
                total_remise_sum = 0
                prix_encaisse_sum = 0
                prix_rembourse_sum = 0
                bonComptoir_objects = models.BonComptoire.objects.filter(store=my_store, user=clot.utilisateur, dateBon=clot.date)
                BonRetourComptoir_objects = models.BonRetourComptoir.objects.filter(bon_comptoir_associe__store=my_store, user=clot.utilisateur, dateBon=clot.date)
            
                prix_to_pay_list = [bon.totalprice for bon in bonComptoir_objects]
                total_price_sum = sum(prix_to_pay_list)
                total_price_sum = total_price_sum or Decimal(0)  # Convert to Decimal
                
                total_remise_sum = bonComptoir_objects.aggregate(Sum('totalremise'))['totalremise__sum'] or 0
                prix_rembourse_sum = sum(bon.myTotalPrice for bon in BonRetourComptoir_objects)
                prix_encaisse_sum = sum(bon.prix_encaisse for bon in bonComptoir_objects) - prix_rembourse_sum
                verssements = models.verssement.objects.filter(store=my_store, utilisateur=clot.utilisateur, date=clot.date)
                total_verssements = sum(Decimal(v.montant) if v.montant != '' else Decimal(0) for v in verssements)
                prix_encaisse_sum += total_verssements
                user_affectation = clot.utilisateur.mon_affectation.first()
                caisse = user_affectation.CompteTres.label
                cloture_dict = {
                    'id': clot.id,
                    'montant': clot.montant,
                    'date': str(clot.date),
                    'utilisateur': clot.utilisateur.username,
                    'caisse': caisse,
                    'collected': str(clot.collected),
                    'totalprice_sum': float(total_price_sum),
                    'totalprix_encaisse': float(prix_encaisse_sum),
                    'totalremise': float(total_remise_sum),
                    'total_verssement':float(total_verssements),
                    'totalRembourse': float(prix_rembourse_sum),
                }        
                list_cloture.append(cloture_dict)
            
        entrepots = CompteEntreprise.objects.filter(store=my_store)
        context["entrepots"] = entrepots
        users_bills = CustomUser.objects.filter(EmployeeAt=my_store)
        context["users"]=users_bills
        context["clotures"]=list_cloture
        context["clotures"]=list_cloture
       
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        print(dataInvoice)
        if dataInvoice: 
            montant = dataInvoice.get('montant')
            date = dataInvoice.get('date')
            myuser=CustomUser.objects.get(username=self.request.user.username)
            store_id = self.request.session["store"]
            my_store = store.objects.get(pk=store_id)  
            existing_cloture = models.Cloture.objects.filter(date=date, utilisateur=myuser, store=my_store).first()

            if existing_cloture:
                # Return an error response if a Cloture already exists for the given date
                return JsonResponse({'error': True, 'error': 'Vous avez déjà introduit une clôture.'})
            else:
                # Create a new Cloture instance
                cloture = models.Cloture.objects.create(
                    montant=montant,
                    date=date,
                    utilisateur=myuser,
                    collected=False,
                    store=my_store
                )

                manager_users = CustomUser.objects.filter(role='manager')
                for manager_user in manager_users:
                    notify.send(
                        sender=myuser,
                        recipient=manager_user,
                        verb=f'{myuser.username} a introduit une nouvelle clôture, cliquer pour collecter !',
                        description='/comptoire/clotures',
                        level=1,
                    )
            return JsonResponse({'error': False})

class ReglementComptoir(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "comptoire/reglements_comptoire.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser = CustomUser.objects.get(username=self.request.user.username)
        return 'comptoire.can_see_comptoir' in self.request.session.get('permissions', []) or  self.request.session["role"] == "DIRECTEUR EXECUTIF"

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)    
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)

        if(myuser.role =='manager') or (myuser.role == 'DIRECTEUR EXECUTIF'):
            comptoire_list = models.BonComptoire.objects.filter(store=CurrentStore)
            rectification_list = models.BonRectification.objects.filter(store=CurrentStore)
            combined_list = list(chain(comptoire_list, rectification_list))
        else:
            comptoire_list = models.BonComptoire.objects.filter(store=CurrentStore, user=myuser)
            rectification_list = models.BonRectification.objects.filter(store=CurrentStore, user=myuser)
            combined_list = list(chain(comptoire_list, rectification_list))
            
        context["bons"]=combined_list     
        entrepots = CompteEntreprise.objects.filter(store=CurrentStore)
        context["entrepots"] = entrepots
        users_bills = CustomUser.objects.filter(EmployeeAt=CurrentStore)
        context["users"]=users_bills     
        return context
    
    @method_decorator(login_required)
    @transaction.atomic
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        user = request.user    
        if dataInvoice :
            print(dataInvoice)
            bonc = dataInvoice["bonComptoir"]
            store_id = request.session["store"]
            my_store = store.objects.get(pk=store_id)
            boncomptoir = models.BonComptoire.objects.get(idBon=bonc, store=my_store)
            montant_introduit = dataInvoice["monantintroduit"]
            current_date = timezone.now()
            myuser= CustomUser.objects.get(username=user.username)
            # Create an instance of the verssement model
            verssement_instance = models.verssement(
                montant=montant_introduit,
                date=current_date,
                utilisateur=myuser,  # Assuming you have a logged-in user
                bon_comptoir_associe=boncomptoir,
                store=my_store,
            )
            # Save the instance to the database
            verssement_instance.save()           
            current_timestamp = datetime.now()
            logs_saving = MyLogEntry.objects.create(
                author= myuser,
                description= f' A introduit un règlement de {montant_introduit} DA , du bon comptoir n°= {bonc} ',
                timestamp = current_timestamp.strftime("%d/%m/%Y at %H:%Mh"),
                store  = my_store
            )
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False})        