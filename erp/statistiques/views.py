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
from clientInfo.models import store, CompteEntreprise
from tiers.models import Client, Banque, Fournisseur
from ventes.models import BonSortie, Facture, ProduitsEnBonSortie
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from produits.models import ProduitsCustomPermission, Category
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from notifications.signals import notify
from users.models import MyLogEntry
from achats.models import BonAchat
from target.models import TargetCustomPermission
from django.template import defaultfilters
from inventory.models import Entrepot
from django.db.models import Sum
# Create your views here.

class statsClients(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "statistiques/clients_regstats.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'reglements.can_see_etatregbl' in self.request.session.get('permissions', []) or myuser.role == 'DIRECTEUR EXECUTIF'

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
       
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)

        if(myuser.role =='manager' or myuser.role == 'DIRECTEUR EXECUTIF'):
         clients_list = Client.objects.filter(store=CurrentStore)
          # Filter clients whose client_Bons is not empty using list comprehension
         filtered_clients = [client for client in clients_list if client.client_bonS.exists()]


         context["bons"] = filtered_clients

         return context   

class statsClientsSold(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "statistiques/clients_sold.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return  self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF" or self.request.session["role"] == "commercial"

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)

        if(myuser.role =='manager' or myuser.role == 'DIRECTEUR EXECUTIF'):
            clients_list = Client.objects.filter(store=CurrentStore)
        else:
            clients_list = Client.objects.filter(store=CurrentStore, user =  myuser)
        clients_stat = []    
        for client in clients_list:
            cl_dict={
                "client_id":client.pk,
                "client_name" :client.name,
                "client_user":client.user.username,
                "client_region":client.adresse,
                "productssoldStat": client.myproductssold,     
                "chiffre_affaire":client.get_chiffre_affaire,    
            }
            clients_stat.append(cl_dict)

        context["bons"] = clients_stat
        users_bills = CustomUser.objects.filter(EmployeeAt=CurrentStore)
        context["users"]=users_bills
        return context   
    
class statsClients104(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "statistiques/clients_104.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return  self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF" or self.request.session["role"] == "commercial"

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)

        if(myuser.role =='manager' or myuser.role == 'DIRECTEUR EXECUTIF'):
            clients_list = Client.objects.filter(store=CurrentStore)
        else:
            clients_list = Client.objects.filter(store=CurrentStore, user =  myuser)
        clients_stat = []    
        for client in clients_list:
            cl_dict={
                "client_id":client.pk,
                "client_name" :client.name,
                "client_registreCommerce" :client.registreCommerce,
                "client_Nif" :client.Nif,
                "client_Nis" :client.Nis,
                "client_num_article" :client.num_article,    
                "chiffre_affaire":client.get_chiffre_affaire,    
            }
            clients_stat.append(cl_dict)

        context["bons"] = clients_stat

        return context   

class StastCaMa(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "statistiques/clients_ca.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'tiers.can_see_clients' in self.request.session.get('permissions', []) or myuser.role == 'DIRECTEUR EXECUTIF'

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
        clients_list = Client.objects.filter(store=CurrentStore)
        # Filter clients whose client_Bons is not empty using list comprehension
        filtered_clients = [client for client in clients_list if client.client_bonS.exists()]
        clients = []
        for cl in filtered_clients:
            client_bons = cl.client_bonS.all()
            total_CA= 0
            for bon in client_bons:
                total_CA += bon.totalPrice                
            cl_dict={
                "client_id":cl.pk,
                "client_name" :cl.name,
                "user": cl.user.username,
                "margin":cl.margin_total,    
                "chiffre_affaire":cl.get_chiffre_affaire,           
            }
            clients.append(cl_dict)
            context["clients"]=clients

       
        users_bills = CustomUser.objects.filter(EmployeeAt=CurrentStore)
        context["users"]=users_bills
        entrepots = Entrepot.objects.filter(store=CurrentStore)
        context["entrepots"] = entrepots
        return context
        
class statsFournisseur(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "statistiques/fournisseurs_regstats.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'reglements.can_see_etatregbl' in self.request.session.get('permissions', []) or myuser.role == 'DIRECTEUR EXECUTIF'

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
       
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        clients_list = Fournisseur.objects.filter(store=CurrentStore)
        context["bons"] =clients_list
        return context   