
from django.shortcuts import render
from django.views.generic.base import TemplateView
from django.http import Http404, JsonResponse
from . import models
from django.db import transaction
import json
from django.contrib.auth.decorators import login_required
from django.db import transaction,  IntegrityError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import render, get_object_or_404
from users.models import CustomUser, Equipe
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
from clientInfo.models import store, CompteEntreprise
from tiers.models import Client, Banque, Fournisseur, Region
from ventes.models import BonSortie, Facture
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from notifications.signals import notify
from users.models import MyLogEntry, Equipe
from produits.models import Product
import ast

@transaction.atomic
def createEquipe(request):
    data = json.loads(request.body)
    dataInvoice = data
    if dataInvoice:
        label = dataInvoice.get('labeleq')
        dateeq = dataInvoice.get('date')
        store_id = request.session["store"]
        my_store = store.objects.get(pk=store_id)
        # Create Equipe instance
        equipe_instance = Equipe.objects.create(label=label, date_created=dateeq, store=my_store)

        # Create CustomUser instances and associate them with the Equipe
        users_data = dataInvoice["users"]
        for username in users_data:
            user_instance = CustomUser.objects.get(username=username)
            user_instance.equipe_affiliated = equipe_instance
            user_instance.save()
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False})

@transaction.atomic
def editEquipe(request):
    data = json.loads(request.body)
    dataInvoice = data
    if dataInvoice:
        equipe_id = dataInvoice.get('equipe_id')
        label = dataInvoice.get('labeleq')
        dateeq = dataInvoice.get('date')
        store_id = request.session["store"]
        my_store = store.objects.get(pk=store_id)

        # Get the Equipe instance
        equipe_instance = Equipe.objects.get(id=equipe_id, store=my_store)

        # Update Equipe properties
        equipe_instance.label = label
        equipe_instance.date_created = dateeq
        equipe_instance.save()

        # Update equipe_affiliated field for associated CustomUser instances
        users_data = dataInvoice["users"]
        CustomUser.objects.filter(equipe_affiliated=equipe_instance).update(equipe_affiliated=None)

        for username in users_data:
            user_instance = CustomUser.objects.get(username=username)
            user_instance.equipe_affiliated = equipe_instance
            user_instance.save()

        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False})
    
@transaction.atomic    
def deleteEquipe(request):
    data = json.loads(request.body)
    dataInvoice = data
    if dataInvoice:
        equipe_id = dataInvoice.get('equipe_id')
        store_id = request.session["store"]
        my_store = store.objects.get(pk=store_id)

        # Get the Equipe instance
        equipe_instance = Equipe.objects.get(id=equipe_id, store=my_store)

        # Set equipe_affiliated to NULL for associated CustomUser instances
        CustomUser.objects.filter(equipe_affiliated=equipe_instance).update(equipe_affiliated=None)

        # Delete the Equipe instance
        equipe_instance.delete()

        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False})
    
@transaction.atomic
def editRegion(request):
    data = json.loads(request.body)
    dataInvoice = data
    if dataInvoice:
        equipe_id = dataInvoice.get('equipe_id')
        label = dataInvoice.get('labeleq')
        dateeq = dataInvoice.get('date')
        store_id = request.session["store"]
        my_store = store.objects.get(pk=store_id)

        # Get the Equipe instance
        equipe_instance = Region.objects.get(id=equipe_id, store=my_store)

        # Update Equipe properties
        equipe_instance.label = label
        equipe_instance.date_created = dateeq
        equipe_instance.save()

        # Update equipe_affiliated field for associated CustomUser instances
        users_data = dataInvoice["users"]
        Client.objects.filter(region=equipe_instance).update(region=None)

        for name in users_data:
            user_instance = Client.objects.get(name=name)
            user_instance.region = equipe_instance
            user_instance.save()
            
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False})
    
@transaction.atomic    
def deleteRegion(request):
    data = json.loads(request.body)
    dataInvoice = data
    if dataInvoice:
        equipe_id = dataInvoice.get('equipe_id')
        store_id = request.session["store"]
        my_store = store.objects.get(pk=store_id)

        equipe_instance = Region.objects.get(id=equipe_id, store=my_store)

        # # Set equipe_affiliated to NULL for associated CustomUser instances
        # Client.objects.filter(region=equipe_instance).update(region=None)

        # Delete the Equipe instance
        equipe_instance.delete()

        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False})
        
@transaction.atomic    
def deletePrevisionGlobale(request):
    data = json.loads(request.body)
    dataInvoice = data
    if dataInvoice:
        equipe_id = dataInvoice.get('equipe_id')
        store_id = request.session["store"]
        my_store = store.objects.get(pk=store_id)

        equipe_instance = models.PrevisionGlobal.objects.get(id=equipe_id, store=my_store)

        equipe_instance.delete()

        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False})
    
@transaction.atomic    
def deleteTarget(request):
    data = json.loads(request.body)
    dataInvoice = data
    if dataInvoice:
        target_ids = dataInvoice['liste_ids']  # Assuming you're using POST and receiving a list of target IDs
        models.Target.objects.filter(id__in=target_ids).delete()

        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False})
        
@transaction.atomic    
def deletePrevision(request):
    data = json.loads(request.body)
    dataInvoice = data
    if dataInvoice:
        target_ids = dataInvoice['liste_ids']  # Assuming you're using POST and receiving a list of target IDs
        
        models.SalesPrediction.objects.all().delete()

        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False})
 
class targetstat(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "target/target_stats.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return self.request.session["role"] == "commercial" or self.request.session["role"] == "commercial-vente" or self.request.session["role"] == "manager" or self.request.session["role"] == "DIRECTEUR EXECUTIF"

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore =store.objects.get(pk=store_id)
        target_id=self.kwargs.get('target_id')

        mytarget = models.Target.objects.get(id=target_id)
        context["target"]=mytarget
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        if(myuser.role == 'manager' or myuser.role == 'DIRECTEUR EXECUTIF'):
            context["users"] = mytarget.get_taux_completion_per_member
            context["users_ca"] = mytarget.get_taux_cacompletion_per_member
        else: 
           completion_rates = mytarget.get_taux_completion_per_member
           completion_carates = mytarget.get_taux_cacompletion_per_member
           context["users"] = next((member["percent"] for member in completion_rates if member["name"] == myuser.username), 0)    
           context["users_ca"] = next((float(member["percent"]) for member in completion_carates if member["name"] == myuser.username), 0)      
           context["ca"] = next((float(member["quantity_sold"]) for member in completion_carates if member["name"] == myuser.username), 0)      
        return context 
    
class targetView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "target/target_page.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'target.can_create_target' in self.request.session.get('permissions', []) or self.request.session["role"] == "manager"  or self.request.session["role"] == "DIRECTEUR EXECUTIF"
    
    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
       
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore =store.objects.get(pk=store_id)
        products_objs = Product.objects.filter(store=CurrentStore)
        liste_products =[]
        for p in products_objs:
            liste_products.append({'reference':p.reference, 'name':p.name, 'qty':p.total_quantity_in_stock})
        context["produits"] = liste_products
        my_users  = CustomUser.objects.filter(EmployeeAt=CurrentStore)   
        liste_users =[]
        for user in my_users:
            liste_users.append(user.username)
        context['users'] = liste_users
        
        equipes  = Equipe.objects.filter(store=CurrentStore)   
        liste_equipes =[]
        for eq in equipes:
            liste_equipes.append(eq.label)
        context['equipes'] = liste_equipes  
            
        return context
    
    @method_decorator(login_required)
    @transaction.atomic
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):      
         data = json.loads(request.body)
         dataInvoice = data
         if dataInvoice:
            print(dataInvoice)
            label = dataInvoice.get('label')
            datedeb = dataInvoice.get('datedeb')
            datefin = dataInvoice.get('datefin')
            isUser = dataInvoice.get('isUser')
            concerned = dataInvoice.get('concerned')
            produits = dataInvoice.get('produits')
            store_id = self.request.session["store"]
            CurrentStore =store.objects.get(pk=store_id)
            Currentuser = self.request.user
            myuser  = CustomUser.objects.get(username=Currentuser.username)
            # Determine user or team based on isUser
            if isUser:
                concerned_instance = CustomUser.objects.get(username=concerned)
            else:
                concerned_instance = Equipe.objects.get(label=concerned)

            # Create Target instance
            target_instance = models.Target.objects.create(
                name=label,
                start_date=datedeb,
                end_date=datefin,
                user=concerned_instance if isUser else None,
                team=concerned_instance if not isUser else None,
                seuil_prime=  dataInvoice.get('percent'),
                prime =  dataInvoice.get('prime')
            )

            # Assuming produits is a list of product data, associate them with the Target
            for product_data in produits:
                product_instance = Product.objects.filter(reference=product_data.get('reference'), store = CurrentStore).first()  # Assuming you have a unique identifier for products
                if product_instance is not None:
                    quantity = product_data.get('quantity')
                    models.TargetProduct.objects.create(target=target_instance, product=product_instance, quantity=quantity, chiffreAffaire = product_data.get('ca'))   
                     
            current_timestamp = datetime.now()
            users_to_notify = []
            if isUser:
                users_to_notify.append(target_instance.user)
            else:
                team_targeted = target_instance.team
                for member in team_targeted.mes_membres.all():
                    users_to_notify.append(member)
                    
            for user_notify in users_to_notify:
                            notify.send(
                                sender=myuser,
                                recipient=user_notify,
                                verb=f'Un nouveau Target Vous a été affecté! cliquez pour le consulter!',  
                                description='/users/userHome',                     
                                level=1,
            )
            return JsonResponse({'success': True})
         else:
            return JsonResponse({'success': False})
        
class targetEditView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "target/target_page_edit.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'target.can_create_target' in self.request.session.get('permissions', []) or self.request.session["role"] == "manager"  or self.request.session["role"] == "DIRECTEUR EXECUTIF"
    
    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
       
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore =store.objects.get(pk=store_id)
        bill_id = self.kwargs.get('bill_id')
        target = models.Target.objects.get(id=bill_id)
        context['target'] = target
        # rest of your code
        products_objs = Product.objects.filter(store=CurrentStore)
        liste_products =[]
        for p in products_objs:
            liste_products.append({'reference':p.reference, 'name':p.name, 'qty':p.total_quantity_in_stock})
        context["produits"] = liste_products
        my_users  = CustomUser.objects.filter(EmployeeAt=CurrentStore)   
        liste_users =[]
        for user in my_users:
            liste_users.append(user.username)
        context['users'] = liste_users
        
        equipes  = Equipe.objects.filter(store=CurrentStore)   
        liste_equipes =[]
        for eq in equipes:
            liste_equipes.append(eq.label)
        context['equipes'] = liste_equipes  
            
        return context
    
    @method_decorator(login_required)
    @transaction.atomic
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):      
         data = json.loads(request.body)
         dataInvoice = data
         store_id = self.request.session["store"]
         CurrentStore =store.objects.get(pk=store_id)
         if dataInvoice:
            target_cible = models.Target.objects.get(id = dataInvoice["id"])    
            target_cible.seuil_prime = dataInvoice.get('percent')
            target_cible.prime = dataInvoice.get('prime')
            produits = dataInvoice.get('produits')
            target_cible.target_products.all().delete()
            for product_data in produits:
                product_instance = Product.objects.filter(reference=product_data.get('reference'), store = CurrentStore).first()  # Assuming you have a unique identifier for products
                if product_instance is not None:
                    quantity = product_data.get('quantity')
                    models.TargetProduct.objects.create(target= target_cible, product=product_instance, quantity=quantity, chiffreAffaire = product_data.get('ca'))   
                    
            return JsonResponse({'success': True})
         else:
            return JsonResponse({'success': False})
    
class PrevisionView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "target/prevision_page.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    
    def test_func(self):
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'target.can_create_target' in self.request.session.get('permissions', []) or self.request.session["role"] == "manager" or self.request.session["role"] == "DIRECTEUR EXECUTIF"
    
    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess'))
       
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore =store.objects.get(pk=store_id)
        products_objs = Product.objects.filter(store=CurrentStore)
        liste_products =[]
        for p in products_objs:
            liste_products.append({'reference':p.reference, 'name':p.name, 'qty':p.total_quantity_in_stock})
        context["produits"] = liste_products
        my_users  = Client.objects.filter(store=CurrentStore, categorie_client__type_desc = 'Revendeur')   
        liste_users =[]
        for user in my_users:
            liste_users.append(user.name)
        context['users'] = liste_users
        
        equipes  = Region.objects.filter(store=CurrentStore)   
        liste_equipes =[]
        for eq in equipes:
            wilayas_list = ast.literal_eval(eq.wilayas)
            equipe_dict ={
                "label":eq.label,
                "clients": wilayas_list  
            }
            liste_equipes.append(equipe_dict)
        context['equipes'] = liste_equipes  
            
        return context
    
    @method_decorator(login_required)
    @transaction.atomic
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):      
         data = json.loads(request.body)
         dataInvoice = data
         store_id = self.request.session["store"]
         CurrentStore =store.objects.get(pk=store_id)
         if dataInvoice:
           if 'products' in dataInvoice :
              products_data = dataInvoice["products"] 
              for productData in products_data: 
                clientObject = Client.objects.filter(name = productData["client"], store = CurrentStore).first()
                if clientObject is not None:
                    prevision_client = models.SalesPrediction.objects.create(
                        client = clientObject,
                        date_start = dataInvoice["datedeb"],
                        date_end = dataInvoice["datefin"],
                        store=CurrentStore  # You may want to update this based on your requirements
                    )
                    if 'components' in productData:
                        for componentData in productData["components"]:
                            models.ComponentsInPrediction.objects.create(
                                prevision = prevision_client,
                                component = componentData["name"],
                                predicted_quantity = componentData["quantity"]
                            )
              return JsonResponse({'success': True})
           else:
               return JsonResponse({'success': False, 'message': 'No products found.'}) 
         else:
            return JsonResponse({'success': False})
 
class EquipesView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "target/equipes_page.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'target.can_see_equipe' in self.request.session.get('permissions', []) or self.request.session["role"] == "manager" or self.request.session["role"] == "DIRECTEUR EXECUTIF"

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
       
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore =store.objects.get(pk=store_id)
        equipes = Equipe.objects.filter(store=CurrentStore)
        equipes_list=[]
        for equipe in equipes:
            membres=[]
            for mem in equipe.mes_membres.all():
               membres.append(mem.username)  
            equipe_inf={
                'id':equipe.id,
                'label':equipe.label,
                'date_creation':equipe.date_created.strftime('%Y-%m-%d'),
                'membres':membres
            } 
            equipes_list.append(equipe_inf)
             
        context["equipes"]=equipes_list 
        my_users  = CustomUser.objects.filter(EmployeeAt=CurrentStore)   
        liste_users =[]
        for user in my_users:
            liste_users.append(user.username)
        context['users'] = liste_users             
        return context       
    
class RegionsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "target/regions_page.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'target.can_see_equipe' in self.request.session.get('permissions', []) or self.request.session["role"] == "manager" or self.request.session["role"] == "DIRECTEUR EXECUTIF"

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
       
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore =store.objects.get(pk=store_id)
        equipes = Region.objects.filter(store=CurrentStore)
        equipes_list=[]
        for equipe in equipes:
            membres=[]
            try:
                wilayas_list = ast.literal_eval(equipe.wilayas)
            except (SyntaxError, ValueError):
                # Handle the case where wilayas_string is not a valid Python literal
                wilayas_list = []
                print("Invalid wilayas format.")
            for mem in wilayas_list:
               membres.append(mem)  
            equipe_inf={
                'id':equipe.id,
                'label':equipe.label,
                'date_creation':equipe.date_created.strftime('%Y-%m-%d'),
                'membres':membres
            } 
            equipes_list.append(equipe_inf)
             
        context["equipes"]=equipes_list 
        my_users  = Client.objects.filter(store=CurrentStore)   
        liste_users =[]
        for user in my_users:
            liste_users.append(user.name)
        context['users'] = liste_users         
        return context    
       
    @method_decorator(login_required)
    @transaction.atomic
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs): 
        data = json.loads(request.body)
        dataInvoice = data
        if dataInvoice:
            label = dataInvoice.get('labeleq')
            dateeq = dataInvoice.get('date')
            store_id = request.session["store"]
            my_store = store.objects.get(pk=store_id)
            # Create Equipe instance
            equipe_instance = Region.objects.create(label=label, date_created=dateeq, store=my_store)

            # Create CustomUser instances and associate them with the Equipe
            users_data = dataInvoice["users"]
            name_list = []

            # Loop through each name in users_data
            for name in users_data:
                # Add the name to the name_list
                name_list.append(name)

            # Assign the name_list to equipe_instance.wilaya
            equipe_instance.wilayas = name_list
            equipe_instance.save()
                
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False})

class PrevisionGlobaleView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "target/prevision_globale.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'target.can_see_equipe' in self.request.session.get('permissions', []) or self.request.session["role"] == "manager" or self.request.session["role"] == "DIRECTEUR EXECUTIF"

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
       
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore =store.objects.get(pk=store_id)
        equipes = models.PrevisionGlobal.objects.filter(store=CurrentStore)
        equipes_list=[]
        for equipe in equipes:
            equipe_inf={
                'id': equipe.id,
                'label': equipe.designation,
                'qte': equipe.qty_prevu,
                'ca': float(equipe.ca_prevu),
                'date_creation': equipe.date_creation.strftime('%Y-%m-%d'),
                'period': equipe.period,
            } 
            equipes_list.append(equipe_inf)
             
        context["equipes"]=equipes_list 
        my_users  = Client.objects.filter(store=CurrentStore)   
        liste_users =[]
        for user in my_users:
            liste_users.append(user.name)
        context['users'] = liste_users         
        return context    
       
    @method_decorator(login_required)
    @transaction.atomic
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs): 
        data = json.loads(request.body)
        dataInvoice = data
        if dataInvoice:
            label = dataInvoice.get('labeleq')
            qte = dataInvoice.get('qteprevu')
            ca = dataInvoice.get('caprevu')
            dateeq = dataInvoice.get('date')
            period = dataInvoice.get('period')
            store_id = request.session["store"]
            my_store = store.objects.get(pk=store_id)
            # Create Equipe instance
            equipe_instance = models.PrevisionGlobal.objects.create(designation=label, qty_prevu = qte, ca_prevu = ca, date_creation=dateeq,period=period, store=my_store)
        
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False})

class targetStateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "target/target_state_page.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return self.request.session["role"] == "commercial" or self.request.session["role"] == "commercial-vente" or self.request.session["role"] == "manager" or self.request.session["role"] == "DIRECTEUR EXECUTIF"

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
       
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore =store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        if (myuser.role == 'manager') or (myuser.role == 'DIRECTEUR EXECUTIF'):
            targets = models.Target.objects.all()  # Fetch all records
        else: 
            targets = models.Target.objects.filter(team = myuser.equipe_affiliated) # Fetch all records  
            
        filtered_targets = [target for target in targets if target.target_store == CurrentStore]
        target_list=[]
        for target in filtered_targets:
          user_targeted = []
          if target.user :
              user_targeted.append(target.user.username)
          else:
              for user in target.team.mes_membres.all():
                  user_targeted.append(user.username)
          target_info={
              'id': target.id,
              'label': target.name,
              'target_createddate': target.start_date.strftime('%Y-%m-%d'),  # Format as needed
              'target_duedate': target.end_date.strftime('%Y-%m-%d'),  # Format as needed   
              'users':user_targeted,   
              'completion_rate': target.get_taux_completion
          } 
          target_list.append(target_info) 
        context["targets"] = target_list    
        return context   
    
class PrevisionState(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "target/prevision_state_page.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'target.can_see_targetstats' in self.request.session.get('permissions', []) or self.request.session["role"] == "manager" or self.request.session["role"] == "DIRECTEUR EXECUTIF"

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        target_id = self.kwargs.get('target_id')

        mytarget = models.PrevisionClient.objects.get(id=target_id)
        context["target"] = mytarget
        total_sold_qte = sum([item["quantity"] for item in mytarget.get_product_sold])
        context["qte_sold"] = total_sold_qte
        context["total_qte"] = sum([item["quantity"] for item in mytarget.get_product_category])
        context["users"]= mytarget.get_completion_per_region
            
        return context 
    
class PrevisionWilayaState(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "target/prevision_wilaya_state_page.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'target.can_see_targetstats' in self.request.session.get('permissions', []) or self.request.session["role"] == "manager" or self.request.session["role"] == "DIRECTEUR EXECUTIF"

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        target_id = self.kwargs.get('prevision_id')
        wilaya = self.kwargs.get('wilaya')
        mytarget = models.PrevisionClient.objects.get(id=target_id)
        context["wilaya"] = wilaya
        context["target"] = mytarget
 
        total_sold_qte = mytarget.get_statistiques_wilaya(wilaya)["total_quantity_sold"]
        print(mytarget.get_statistiques_wilaya(wilaya))
        context["qte_sold"] = total_sold_qte
        context["total_qte"] = mytarget.get_statistiques_wilaya(wilaya)["initial_quantity"]
        context["users"]= mytarget.get_statistiques_wilaya(wilaya)["quantities_sold_per_category"]
        
        context["clients_rep"] = mytarget.get_statistiques_wilaya(wilaya)["client_statistics"]
        return context 
       
       
class PrevisionStateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "target/previsions_page.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'target.can_see_targetstats' in self.request.session.get('permissions', []) or self.request.session["role"] == "manager" or self.request.session["role"] == "DIRECTEUR EXECUTIF"

    def handle_no_permission(self):
        # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
       
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore =store.objects.get(pk=store_id)
        filtered_targets = models.SalesPrediction.objects.filter(store= CurrentStore)  # Fetch all records
        target_list=[]
        unique_usernames= []
        for target in filtered_targets:
            target_stard_date = target.date_start          
            target_end_date = target.date_end        
            target_info = {
                'id': target.id,
                'user': target.client.user.username,
                'client': target.client.name,
                'startDate': target.date_start.strftime('%Y-%m-%d'),  # Format as needed
                'endDate': target.date_end.strftime('%Y-%m-%d'),  # Format as needed    
                'tauxCompletion': 0,  
                'components': [comp.prediction_stats for comp in target.quantity_previsions.all()],
            } 
            if target.client.user.username not in unique_usernames:
                unique_usernames.append(target.client.user.username)
            target_list.append(target_info)  
              
        active_previsions = models.PrevisionGlobal.get_active_prevision(target_stard_date, target_end_date)
        previsions_data = []
        for prevision in active_previsions:
            prevision_data = {
                'composant': prevision.designation,
                'qty_prevu': prevision.qty_prevu,
                'ca_prevu': float(prevision.ca_prevu) if prevision.ca_prevu is not None else 0,  # Default to 0 if ca_prevu is None
            }
            previsions_data.append(prevision_data)
        context["active_previsions"] = previsions_data                  
        context["targets"] = target_list    

        # Convert the set of unique usernames to a list of dictionaries
        users_bills = [{'username': username} for username in unique_usernames]

        context["users"]=users_bills
        return context   