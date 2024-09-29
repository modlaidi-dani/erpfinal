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
from inventory.models import Entrepot, Stock, BonTransfert, ProduitsEnBonTransfert, BonEntry
from clientInfo.models import store,typeClient
from tiers.models import Client, Banque
from produits.models import Product, Category, NumSeries
from reglements.models import ModeReglement, EcheanceReglement
from comptoire.models import BonComptoire, ProduitsEnBonComptoir, BonRetourComptoir, ProduitsEnBonRetourComptoir
from ventes.models import BonSortie
from django.db.models import Count, Q

import requests

        
class TrackUsersView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "logistique/users_location.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        # return 'logistique.can_create_bontransport' in self.request.session.get('permissions', []) or self.request.session["role"] == 'manager'
        return self.request.session["username"] == 'fares' or  self.request.session["username"] == 'sofian' or self.request.session["role"] == 'DIRECTEUR EXECUTIF' or self.request.session["role"] == 'manager'
   
    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        selected_store = get_object_or_404(store, pk=self.request.session["store"]) 
        active_users = CustomUser.objects.filter(role ='Chauffeur')
        user_coordinates = []
        for user in active_users:
            username = user.username
            name = user.last_name +' ' +user.first_name
            ip_address = user.adresse_ip

            latitude = ''
            longitude = ''
            # Get coordinates
            user_latitude = user.mycoordinates.last()
            if user_latitude:
                latitude = user_latitude.latitude
                longitude = user_latitude.longitude

            # Append a dictionary to the array
            user_coordinates.append({'name': name, 'latitude': latitude, 'longitude': longitude})

        context['user_coordinates'] = user_coordinates
        return context
        
def fetchBills(request):
    data = json.loads(request.body)
    print(data)
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    client = Client.objects.filter(name=data["clientName"], store=CurrentStore).first()
    bills = []
    for bill in client.client_bonS.all():
        bills.append({
            'idbon': bill.idBon,
            'datebon': bill.dateBon
        })
        
    return JsonResponse({'bills': bills})
   
        
def supprimerReglement(request):
    try:
        data = json.loads(request.body)
        print(data)
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        user = models.ReglementTransport.objects.get(id=data["user_id"])
        user.delete()
        return JsonResponse({'message': 'Reglement Supprimé !'})
    except models.CustomUser.DoesNotExist:
        return JsonResponse({'error': 'Reglement Non-trouvé.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché, car cette Affectation est lié aux autres composants - {}'.format(str(e))})  
    
def supprimerRequete(request):
    try:
        data = json.loads(request.body)
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        liste_ids = data["liste_ids"]
        for id_bon in liste_ids:
            req = models.requeteClientInfo.objects.get(id=id_bon)
            req.delete()
        return JsonResponse({'message': 'Requête Supprimé !'})
    except models.requeteClientInfo.DoesNotExist:
        return JsonResponse({'error': 'Requête Non-trouvé.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché! - {}'.format(str(e))})  
        
def supprimerMoyenTransport(request):
    try:
        data = json.loads(request.body)
        print(data)
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        user = models.MoyenTransport.objects.get(id=data["user_id"])
        user.delete()
        return JsonResponse({'message': 'Moyen Transport Supprimé !'})
    except models.CustomUser.DoesNotExist:
        return JsonResponse({'error': 'Moyen Transport Non-trouvé.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché - {}'.format(str(e))})  

def delete_transport_bill(request):
    data = json.loads(request.body)
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    liste_ids = data["liste_ids"]
    for id_bon in liste_ids:
        bon_c = models.BonTransport.objects.get(idBon=id_bon, store=CurrentStore)
        with transaction.atomic():
            bon_c.delete()
    return JsonResponse({'message': "Bons de Transport Supprimées."})
    
def editReglement(request):   
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
                cloture_obj = models.ReglementTransport.objects.get(id=cloture_id)
                old_montant =  cloture_obj.montant
                cloture_obj.montant = data.get('montant')
                cloture_obj.save()  # Save the changes
                CurrentStore = store.objects.get(pk=store_id)
                user = request.user
                myuser= CustomUser.objects.get(username=user.username)

                return JsonResponse({'message': 'Reglement a été Modifié.'})
          except models.AffectationCaisse.DoesNotExist:
            return JsonResponse({'error': 'Reglement Ne peut pas être modifié.'})
        return JsonResponse({'error': 'Re-essayer S il vous plait.'})
        
def supprimerCourses(request):
    try:
        data = json.loads(request.body)
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        liste_ids = data["liste_ids"]
        for id_bon in liste_ids:
            req = models.CourseLivraison.objects.get(id=id_bon)
            req.delete()
        return JsonResponse({'message': 'Affectation  Supprimé !'})
    except models.CourseLivraison.DoesNotExist:
        return JsonResponse({'error': 'Affectation Non-trouvé.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché! - {}'.format(str(e))})  

        
class PageCoursesLivraisonView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "logistique/livraisoncourses.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        return self.request.session["role"] == 'manager' or  self.request.session["role"] == 'DIRECTEUR EXECUTIF' or  self.request.session["role"] == 'Finance' or self.request.session["username"] == 'fares' or  self.request.session["username"] == 'sofian'

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)  
        Currentuser = self.request.user
        liste_courses = models.CourseLivraison.objects.all().order_by('-id')
        liste_user =[]
        for course in liste_courses:
            user_dict ={
                'id': course.id,
                'adresse': course.adresse,
                'dateTimeAffectation': course.dateTimeAffectation.date(),
                'dateTimeDebut': course.dateTimeDebut.strftime('%d/%m/%y - %H:%M') if course.dateTimeDebut else '',
                'dateTimeFin': course.dateTimeFin.strftime('%d/%m/%y - %H:%M') if course.dateTimeFin else '',
                'chauffeur': course.chauffeur.username if course.chauffeur else '',
                'idBon': course.bonlivraison.idBon,
                'dateBon': course.bonlivraison.dateBon.strftime('%d/%m/%y'),
                'montantBl': course.bonlivraison.get_total_soldprice,
                'solde': course.bonlivraison.client.remaining_amount,
                'note': course.note,
                'typeCourse': course.typeCourse,
                'transporteur': course.transporteur if course.typeCourse == ' trans' else course.bonlivraison.client.name,
                'bonlivraison': course.bonlivraison.idBon,
                'montant': course.montant,
                'etat': course.etat,
            }
            liste_user.append(user_dict)
        context ["courses"]= liste_user
        users_drivers = CustomUser.objects.filter(role = 'Chauffeur')
        context["utilisateurs"] = users_drivers
        return context
        
class LivraisonCourseView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "logistique/affectationlivraison.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        # return 'logistique.can_create_bontransport' in self.request.session.get('permissions', []) or self.request.session["role"] == 'manager'
        return  self.request.session["role"] == 'Finance' or self.request.session["username"] == 'fares' or self.request.session["role"] == 'DIRECTEUR EXECUTIF' or self.request.session["role"] == 'manager' or  self.request.session["username"] == 'sofian'
    
    
    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        clients = Client.objects.filter(store=selected_store)
        context["clients"] = clients
        bills = BonSortie.objects.filter(livre = False, store = selected_store)
        context["bills"] = bills        
        chauffeurs = CustomUser.objects.filter(role = 'Chauffeur')
        context["chauffeurs"] = chauffeurs
        moyens_transport = models.MoyenTransport.objects.filter(store=selected_store)
        context["moyens_transport"] = moyens_transport
        return context   
    
    @method_decorator(login_required)
    @method_decorator(transaction.atomic)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        if dataInvoice: 
            chauffeur =CustomUser.objects.get(username = dataInvoice["chaufeur"])
            date = datetime.now()
            adresse = dataInvoice["adresse"]
            moyen_transport = models.MoyenTransport.objects.get(id= dataInvoice["moyen_transport"])
            type = dataInvoice["type"]
            transporteur = dataInvoice["transporteur"]
            fraistransport = dataInvoice["fraistransport"]
            montant = dataInvoice["montant"]
            note = dataInvoice["note"]
            for bill_data in dataInvoice["bills"]:
                bill = BonSortie.objects.get(id = bill_data["id"])   
                models.CourseLivraison.objects.create(  
                        chauffeur = chauffeur,
                        bonlivraison = bill,
                        adresse = adresse,
                        note = note,
                        dateTimeAffectation = date,
                        moyen_transport = moyen_transport,
                        montant = montant,
                        fraisTransport = fraistransport,
                        typeCourse = type,
                        transporteur = transporteur,
                        etat = 'en-attente'
                )   
            return JsonResponse({'success': True})
           
class PrepareStockView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "logistique/prepare_stock.html"
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
        
        invoice = BonEntry.objects.get(id=bill_id)
        idBon = invoice.idBon
        dateBon = invoice.dateBon
        
        products_enBon = invoice.get_produits()
        items=[]
        for product in products_enBon:
             produit_dict={
               "produit_ref" :product.stock.reference,
               "produit_name" :product.stock.name,
               "produit_qty":product.quantity,                   
              }
             items.append(produit_dict)
        context["bill"] = invoice    
        context["idBon"] = idBon
        context["dateBon"] = dateBon
        
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
           products =dataInvoice["produits"]
           for product in products :
              produit_inst = Product.objects.get(reference = product["ref"], store = CurrentStore)
              for numSerie in product["numSeries"]:
                    NumSeries.objects.create(
                        produit = produit_inst,
                        numseries = numSerie,
                        used = False,
                    )   
           return JsonResponse({'Message':'bill created Succesfully'})


class NumerSeriesView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "logistique/preparation_codeseries.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        # return 'logistique.can_create_bontransport' in self.request.session.get('permissions', []) or self.request.session["role"] == 'manager'
        return self.request.session["username"] == 'fares' or self.request.session["role"] == 'DIRECTEUR EXECUTIF' or self.request.session["role"] == 'manager' or  self.request.session["username"] == 'sofian'
   
    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        products = Product.objects.filter(store=selected_store)
        products_list = []
        for product in products:
            products_list.append({
                'reference': product.reference,
                'name': product.name,
            })
        context["produits"] = products_list    
        return context   
    
    @method_decorator(login_required)
    @method_decorator(transaction.atomic)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        if dataInvoice: 
           reference_bt = dataInvoice["referenceBon"]
           date_bt = dataInvoice["date"]
           bonLivraison = BonSortie.objects.get(idBon = dataInvoice["bonlivraison"], ferme= False, store =selected_store)
           if dataInvoice["etat_livraison"] == "true":
               ferme = True
               bonLivraison.ferme = True
           else:
               bonLivraison.ferme = False
           if dataInvoice["partial"] == "true":
               etat_liv = 'Partielle'
           else:
               etat_liv = 'Complète'   
           client = Client.objects.get(id = dataInvoice["client"], store =selected_store)
           moyen_transport = models.MoyenTransport.objects.get(id = dataInvoice["moyen_transport"], store =selected_store)
           chauffeur = dataInvoice["chauffeur"]
           adresse = dataInvoice["adresse"]
           frais = dataInvoice["frais"]
           myuser=CustomUser.objects.get(username=self.request.user.username)
           bon_t= models.BonTransport.objects.create(
                idBon = reference_bt,
                bonlivraison = bonLivraison,
                moyen_transport = moyen_transport,
                chauffeur = chauffeur,
                date_depart = dataInvoice["date"],
                adresse_livraison = adresse,
                client = client,
                etat_livraison =etat_liv,
                frais_Livraison = frais,
                store = selected_store,
                user = myuser
           )
           for produit in dataInvoice["produits"]:
                    produit_inst = Product.objects.get(reference=produit["ref"])                 
                    qty = int(produit['qty'])
                    models.ProduitsEnBonTransport.objects.create(
                        BonNo = bon_t,
                        produit = produit_inst,
                        quantity = qty,
                        livre=True,
                    )
           return JsonResponse({'success': True})
         
class BonTransportView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "logistique/bon_transport.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        # return 'logistique.can_create_bontransport' in self.request.session.get('permissions', []) or self.request.session["role"] == 'manager'
        return self.request.session["username"] == 'fares' or self.request.session["role"] == 'DIRECTEUR EXECUTIF' or self.request.session["role"] == 'manager' or self.request.session["role"] == 'Finance' or  self.request.session["username"] == 'sofian'
   
    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        bonsLivraison = BonSortie.objects.filter(store=selected_store, valide=True).order_by('-id')
        context["bonsLivraison"] = bonsLivraison
        moyen_transport = models.MoyenTransport.objects.filter(store=selected_store)
        context["moyens_transport"] = moyen_transport
        clients = Client.objects.filter(store=selected_store)
        context["clients"] = clients
          
        return context   
    
    @method_decorator(login_required)
    @method_decorator(transaction.atomic)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        if dataInvoice: 
           client = Client.objects.get(id = dataInvoice["client"], store =selected_store)
           date_bt = dataInvoice["date"]
           chauffeur = dataInvoice["chaufeur"]
           adresse = dataInvoice["adresse"]
           for bill in dataInvoice["bills"]: 
                current_year = timezone.now().year
                reglements_for_year = models.BonTransport.objects.all()
                sequential_number = reglements_for_year.count() + 1
                BT_code = f'BT{str(current_year)[-2:]}/{str(sequential_number).zfill(3)}'
                reference_bt = BT_code   
                bonLivraison = BonSortie.objects.get(id = bill["id"], store =selected_store)            
                moyen_transport = models.MoyenTransport.objects.get(id = dataInvoice["moyen_transport"], store =selected_store)              
                frais = bonLivraison.fraisLivraison
                myuser= CustomUser.objects.get(username=self.request.user.username)
                bon_t= models.BonTransport.objects.create(
                        idBon = reference_bt,
                        bonlivraison = bonLivraison,
                        moyen_transport = moyen_transport,
                        chauffeur = chauffeur,
                        date_depart = dataInvoice["date"],
                        adresse_livraison = adresse,
                        client = client,
                        etat_livraison ='complète',
                        frais_Livraison = frais,
                        store = selected_store,
                        user = myuser
                )
           return JsonResponse({'success': True})
       
class RequeteView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "logistique/requete_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        # return 'logistique.can_create_bontransport' in self.request.session.get('permissions', []) or self.request.session["role"] == 'manager'
        return self.request.session["username"] == 'ziad' or self.request.session["role"] == 'DIRECTEUR EXECUTIF' or self.request.session["role"] == 'manager' or self.request.session["role"] == 'Finance' or  self.request.session["username"] == 'sofian'
   
    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        clients = Client.objects.filter(store=selected_store)
        context["clients"] = clients

        return context   
    
    @method_decorator(login_required)
    @method_decorator(transaction.atomic)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        if dataInvoice: 
 
           client = Client.objects.get(name = dataInvoice["client"], store =selected_store)
           myuser=CustomUser.objects.get(username=self.request.user.username)
           bon_t= models.requeteClientInfo.objects.create(
                client = client,
                dateReq = dataInvoice["date"],
                etat = dataInvoice["etat"],
                note = dataInvoice["note"],  
           )
           for produit in dataInvoice["bls"]:
                    bl_instance = BonSortie.objects.get(idBon=produit["idbon"], store = selected_store)                 
                    models.BlsEnRequeteClient.objects.create(
                        requete = bon_t,
                        bonlivraison = bl_instance,
                        modePaiement = produit["mode"],
                        etat_livraison = produit["etat"],
                        note = produit["note"],
                    )
           return JsonResponse({'success': True})
       
class FicheView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "logistique/fiche_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        # return 'logistique.can_create_bontransport' in self.request.session.get('permissions', []) or self.request.session["role"] == 'manager'
        return self.request.session["username"] == 'ziad' or self.request.session["username"] == 'fares' or self.request.session["role"] == 'DIRECTEUR EXECUTIF' or self.request.session["role"] == 'manager' or  self.request.session["username"] == 'sofian'
   
    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        clients = Client.objects.filter(store=selected_store)
        context["clients"] = clients

        return context   
    
    @method_decorator(login_required)
    @method_decorator(transaction.atomic)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        if dataInvoice: 
 
           client = Client.objects.get(name = dataInvoice["client"], store =selected_store)
           myuser=CustomUser.objects.get(username=self.request.user.username)
           bon_t= models.FicheLivraisonExterne.objects.create(  
                client= dataInvoice["client"],
                adresse= dataInvoice["adresse"],
                date= dataInvoice["date"],
                transporteur= dataInvoice["transporteur"],
                montant= dataInvoice["montant"],
                numeroColis= dataInvoice["numeroColis"],
                note= dataInvoice["note"],
           )
           
           return JsonResponse({'success': True})
       
class EditRequeteView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "logistique/requete_page_edit.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        # return 'logistique.can_create_bontransport' in self.request.session.get('permissions', []) or self.request.session["role"] == 'manager'
        return self.request.session["username"] == 'ziad' or self.request.session["role"] == 'DIRECTEUR EXECUTIF' or self.request.session["role"] == 'manager' or  self.request.session["username"] == 'sofian'
   
    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        bill_id=self.kwargs.get('id_bon')
        requete = models.requeteClientInfo.objects.get(id=bill_id)
        context["requete"]=requete
        items = []
        for bl in requete.bonsL_enreq.all():
            items.append({
                'idbon': bl.bonlivraison.idBon,
                'date': str(bl.bonlivraison.dateBon),
                'mode': bl.modePaiement,
                'etat': bl.etat_livraison,
                'note': bl.note
            })

        context["items"]=items    
        clients = Client.objects.filter(store=selected_store)
        context["clients"] = clients 
        return context   
    
    @method_decorator(login_required)
    @method_decorator(transaction.atomic)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        if dataInvoice: 
           requete_obj = models.requeteClientInfo.objects.get(id = dataInvoice["id"])
           requete_obj.etat = dataInvoice["etat"]
           requete_obj.note = dataInvoice["note"]    
           requete_obj.dateReq = dataInvoice["date"]      
           clientobj = Client.objects.get(name = dataInvoice["client"], store =selected_store)
           requete_obj.client = clientobj
           requete_obj.save()
           requete_obj.bonsL_enreq.all().delete()
           for produit in dataInvoice["bls"]:
                    bl_instance = BonSortie.objects.get(idBon=produit["idbon"], store = selected_store)                 
                    models.BlsEnRequeteClient.objects.create(
                        requete = requete_obj,
                        bonlivraison = bl_instance,
                        modePaiement = produit["mode"],
                        etat_livraison = produit["etat"],
                        note = produit["note"],
                    )
           return JsonResponse({'success': True})

class ReglementTransportView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "logistique/reglements_transport.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        # return 'logistique.can_see_regtransport' in self.request.session.get('permissions', []) or self.request.session["role"] == "manager"
        return self.request.session["username"] == 'fares' or self.request.session["role"] == 'DIRECTEUR EXECUTIF' or self.request.session["role"] == 'manager' or  self.request.session["username"] == 'sofian'
    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)    
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        store_id = self.request.session["store"]
        my_store = store.objects.get(pk=store_id)  
        if self.request.session["role"] == "manager":
           cloture = models.ReglementTransport.objects.filter(store=my_store).order_by('date')
        else:
            cloture = models.ReglementTransport.objects.filter(user=myuser).order_by('date')
        list_cloture =[]
        for clot in cloture:
            cloture_dict = {
                'id': clot.id,
                'montant': float(clot.montant),
                'date': str(clot.date),
                'utilisateur': clot.user.username,
                'bonvente':clot.bon_transport.idBon,
                'fraislivraison': float(clot.bon_transport.frais_Livraison),
            }        
            list_cloture.append(cloture_dict)  
        bons_transport = models.BonTransport.objects.filter(store=my_store)
        context["bons"] = bons_transport
        users_bills = CustomUser.objects.filter(EmployeeAt=my_store)
        context["users"]=users_bills
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
            # Create a new Cloture instance
            bonT = models.BonTransport.objects.get(idBon = dataInvoice["bon"], store=my_store)
            cloture = models.ReglementTransport.objects.create(
                montant=montant,
                date=date,
                user=myuser,
                bon_transport = bonT,
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
        
class MoyenTransportView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "logistique/moyens_transport.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        # return 'logistique.can_see_moyenstr' in self.request.session.get('permissions', []) or self.request.session["role"] == 'manager'
        return self.request.session["username"] == 'fares' or self.request.session["role"] == 'DIRECTEUR EXECUTIF' or self.request.session["role"] == 'manager' or  self.request.session["username"] == 'sofian'

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess')) 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Define the model for which you want to create custom permissions
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        Currentuser = self.request.user
        myuser = CustomUser.objects.get(username=Currentuser.username)
        clients_list = models.MoyenTransport.objects.filter(store=CurrentStore)
        clients=[]
        
        for cl in clients_list:             
            cl_dict={
                "client_id":cl.id,
                "client_name" :cl.designation,
                "date_created" :str(cl.date),
                "matricule": cl.immatriculation,
            }
            clients.append(cl_dict)
            
        context["clients"]=clients
        users_bills = CustomUser.objects.filter(EmployeeAt=CurrentStore)
        context["users"]=users_bills
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData', '')
        print(dataInvoice)
        with transaction.atomic():  
          if dataInvoice:
            Currentuser = self.request.user
            myuser  = CustomUser.objects.get(username=Currentuser.username)
            Currentstore = self.request.session["store"]
            my_store= store.objects.get(pk=Currentstore)
            designation = dataInvoice['name']
            matricule = dataInvoice['matricule']
            moyen_transport = models.MoyenTransport.objects.create(
                designation = designation,
                immatriculation = matricule,
                date = datetime.now(),
                store = my_store,
            )
            moyen_transport.save()
        return JsonResponse({'message': "Moyen de Transport Added successfully."})
    
class BillsNotPreparedView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "logistique/bills_notprepared_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        myuser=CustomUser.objects.get(username=self.request.user.username)
        # return 'logistique.can_see_bontransport' in self.request.session.get('permissions', []) or self.request.session["role"] == "manager"
        return self.request.session["username"] == 'fares' or self.request.session["role"] == 'DIRECTEUR EXECUTIF' or self.request.session["role"] == 'manager' or  self.request.session["username"] == 'sofian'

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess'))  
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)       
        # store_id = self.kwargs.get('store_id')
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        bills = BonSortie.objects.filter(
            store=selected_store,
            valide=True,
            entrepot__name="Depot principal Reghaia"
        ).annotate(
            num_bon_garantie=Count('bon_garantie'),
            num_mes_bon_retours=Count('MesbonRetours'),
            num_produits_en_bon_sorties=Count('produits_en_bon_sorties')
        ).filter(
            Q(num_bon_garantie=0) &
            Q(num_mes_bon_retours=0) &
            Q(num_produits_en_bon_sorties__gt=0)
        )
        context["bills"] = bills
        users_bills = CustomUser.objects.filter(EmployeeAt=selected_store)
        context["users"]=users_bills
        return context 
        
class BonTransportListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "logistique/bons_transport_page.html"
    login_url = 'home' 
    raise_exception = True  
    def test_func(self):
        myuser=CustomUser.objects.get(username=self.request.user.username)
        # return 'logistique.can_see_bontransport' in self.request.session.get('permissions', []) or self.request.session["role"] == "manager"
        return self.request.session["username"] == 'fares' or self.request.session["role"] == 'DIRECTEUR EXECUTIF' or self.request.session["role"] == 'manager' or self.request.session["role"] == 'Finance' or  self.request.session["username"] == 'sofian'

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess'))  
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)       
        # store_id = self.kwargs.get('store_id')
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        current_month = datetime.now().month
        bons_sorties = models.BonTransport.objects.filter(store=selected_store, date_depart__month = current_month).order_by('-id')
        context["bons_sorties"] =bons_sorties

        moyens_transport = models.MoyenTransport.objects.filter(store=selected_store)
        context["moyens"] = moyens_transport
        users_bills = CustomUser.objects.filter(EmployeeAt=selected_store)
        context["users"]=users_bills
        return context 
    
class FichesLivraisonView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "logistique/fichelivext_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        myuser=CustomUser.objects.get(username=self.request.user.username)
        # return 'logistique.can_see_bontransport' in self.request.session.get('permissions', []) or self.request.session["role"] == "manager"
        return self.request.session["username"] == 'ziad' or self.request.session["username"] == 'fares' or self.request.session["role"] == 'DIRECTEUR EXECUTIF' or self.request.session["role"] == 'manager' or  self.request.session["username"] == 'sofian'

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess'))  
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)       
        # store_id = self.kwargs.get('store_id')
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        bons_sorties = models.FicheLivraisonExterne.objects.all().order_by('-date')
        context["reqs"] =bons_sorties

        return context 
    
class RequetesPageView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "logistique/page_requetes.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        myuser=CustomUser.objects.get(username=self.request.user.username)
        # return 'logistique.can_see_bontransport' in self.request.session.get('permissions', []) or self.request.session["role"] == "manager"
        return self.request.session["username"] == 'ziad' or self.request.session["role"] == 'DIRECTEUR EXECUTIF' or self.request.session["role"] == 'manager' or  self.request.session["username"] == 'sofian'

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess'))  
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)       
        # store_id = self.kwargs.get('store_id')
        selected_store = get_object_or_404(store, pk=self.request.session["store"])
        
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        bons_sorties = models.requeteClientInfo.objects.filter(client__store=selected_store).order_by('-dateReq')
        context["reqs"] =bons_sorties

        return context 