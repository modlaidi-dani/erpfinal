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
from ventes.models import BonSortie, Facture
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from .models import ReglementsCustomPermission
from produits.models import ProduitsCustomPermission
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from notifications.signals import notify
from users.models import MyLogEntry
from achats.models import BonAchat
from target.models import TargetCustomPermission
from django.template import defaultfilters
from django.db.models import Sum, Case, When, IntegerField
from inventory.models import BonRetour, InventoryCustomPermission
# Create your views here.
from datetime import datetime, timedelta
from comptoire.models import BonComptoire


def getMotifs(request):
    data = json.loads(request.body)
    type_objects = models.TypeDepense.objects.filter(type=data["type_depense"])
    stock_data=[]
    for type_dep in type_objects:
        if type_dep.type == "salaire":
            stock_data.append({
                "id":type_dep.id,
                "label": type_dep.nom_salarie,
            })
        elif type_dep.type == "loyers - entretien":
            stock_data.append({
                "id":type_dep.id,
                "label": f'{type_dep.numero_local} -  {type_dep.adresse_local}',
            })
        elif type_dep.type == "loyers - location":
            stock_data.append({
                "id":type_dep.id,
                "label": f'{type_dep.numero_local} -  {type_dep.adresse_local}',
            })
        elif type_dep.type == "divers":
            stock_data.append({
                "id":type_dep.id,
                "label": type_dep.designation,
            })
    return JsonResponse({'stocks':stock_data})

def supprimerRegs(request):
    data = json.loads(request.body)
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    liste_id = data["liste_ids"]
    for id_bon in liste_id:
        bon_c = models.Reglement.objects.get(id=id_bon, store=CurrentStore)
        with transaction.atomic():             
                bon_c.delete()
    return JsonResponse({'message': "Eléments Supprimé !"})
    
def verifyPassword(request):
        data = json.loads(request.body)
        print(data)
        user = request.user
        # Verify if the provided password matches the current user's password
        if user.check_password(data["password"]):
            print('true')
            reglement = models.Reglement.objects.filter(codeReglement=data["reglementCode"]).first()
            reglement.collected=True
            reglement.save()
            store_id = request.session["store"]
            CurrentStore = store.objects.get(pk=store_id)
            myuser= CustomUser.objects.get(username=user.username)
            current_timestamp = datetime.now()
            logs_saving = MyLogEntry.objects.create(
                author= myuser,
                description= f' A collecté le règlement n°=  {data["reglementCode"]} ',
                timestamp = current_timestamp.strftime("%d/%m/%Y at %H:%Mh"),
                store  = CurrentStore
            )
            return JsonResponse({'success': True})
        else:
            print('false')
            return JsonResponse({'success': False})
        
def verifyPasswordCloture(request):
        data = json.loads(request.body)
        user = request.user
        # Verify if the provided password matches the current user's password
        if user.check_password(data["password"]):
            if  data["cloture_id"] != 0 :
                reglement = models.ClotureReglements.objects.filter(id=data["reglementCode"]).first()
                reglement.collected=True
                reglement.montant_collected = data["montant_collected"]
                reglement.save()      
            else:
                store_id = request.session["store"]
                CurrentStore = store.objects.get(pk=store_id)
                myuser= CustomUser.objects.get(username=user.username)
                current_timestamp = datetime.now()
                caisse = CompteEntreprise.objects.get(id=data['caisse'])	
                montc = models.montantCollected.objects.create(montant =data["montant_collected"], date = current_timestamp.date(), store = CurrentStore, utilisateur = myuser, caisse = caisse)    
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False})

def supprimerMouvement(request):
    try:
        data = json.loads(request.body)
        print(data)
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        user = models.mouvementCaisse.objects.get(id=data["user_id"])
        user.delete()
        return JsonResponse({'message': 'Mouvement Supprimé !'})
    except models.CustomUser.DoesNotExist:
        return JsonResponse({'error': 'Mouvement Non-trouvé.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché, car cette Affectation est lié aux autres composants - {}'.format(str(e))})  
   
def editMouvement(request):
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
                existing_mouvement_caisse = models.mouvementCaisse.objects.get(id=cloture_id)
                existing_mouvement_caisse.CompteEntreprise = CompteEntreprise.objects.get(id=data['caisse'])
                existing_mouvement_caisse.debit = data["debit"]
                existing_mouvement_caisse.credit = data["credit"]
                existing_mouvement_caisse.motif = data["motif"]
                existing_mouvement_caisse.date = data.get('date')
                existing_mouvement_caisse.user = CustomUser.objects.get(username=request.user.username)
                existing_mouvement_caisse.store = CurrentStore
                existing_mouvement_caisse.save()
                return JsonResponse({'message': 'Mouvement a été Modifié.'})
          except models.AffectationCaisse.DoesNotExist:
            return JsonResponse({'error': 'Mouvement Ne peut pas être modifié.'})
        return JsonResponse({'error': 'Re-essayer S il vous plait.'})
    
def editDepense(request):
         # Find the product by reference
        data = json.loads(request.body)
        Currentuser = request.user
        myuser = CustomUser.objects.get(username=Currentuser.username)
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)   
        cloture_id = data.get('user_id')  
        if  cloture_id:
          try:
            with transaction.atomic():  
                existing_mouvement_caisse = models.depense.objects.get(id=cloture_id)
                existing_mouvement_caisse.CompteEntreprise = CompteEntreprise.objects.get(id=data['caisse'])
                type_dep = models.TypeDepense.objects.get(id=data["motif"])
                mode_reg = models.ModeReglement.objects.get(id=data.get('mode_reg', ''))  # Assuming you have a 'mode_reg' field in your formData
                existing_mouvement_caisse.type_depense = type_dep
                existing_mouvement_caisse.mode_reglement = mode_reg
                existing_mouvement_caisse.montant = data.get('montant')

                existing_mouvement_caisse.save()
                return JsonResponse({'message': 'Dépense a été Modifié.'})
          except models.AffectationCaisse.DoesNotExist:
            return JsonResponse({'error': 'Dépense Ne peut pas être modifié.'})
        return JsonResponse({'error': 'Re-essayer S il vous plait.'})
 
def ValiderDepense(request):
    try:
         # Find the product by reference
        data = json.loads(request.body)
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        user = request.user
        # Verify if the provided password matches the current user's password
        if user.check_password(data["password"]):
            depense = models.depense.objects.get(id=data["user_id"])
            Currentuser = request.user
            depense.user =  CustomUser.objects.get(username=Currentuser.username)
            return JsonResponse({'success': True})
    except models.CustomUser.DoesNotExist:
        return JsonResponse({'error': 'Elément Non-trouve.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La validation a été échouché - {}'.format(str(e))})
        
def supprimerTypeDepense(request):
    try:
         # Find the product by reference
        data = json.loads(request.body)

        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        user = models.TypeDepense.objects.get(id=data["user_id"])
        user.delete()
        return JsonResponse({'success': True})
    except models.CustomUser.DoesNotExist:
        return JsonResponse({'error': 'Elément Non-trouve.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché - {}'.format(str(e))})

def editType(request):
        # Find the product by reference
        data = json.loads(request.body)
        Currentuser = request.user
        myuser = CustomUser.objects.get(username=Currentuser.username)
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        type_dep = models.TypeDepense.objects.get(id=data["user_id"])
        if type_dep.type == "salaire" :
            nom_salarie = data['nom']
            fonction_salarie = data['fonction']
            adresse_salarie = data["adresse"]
            tlfn_salarie = data['phone']
            
            type_dep.nom_salarie=nom_salarie
            type_dep.fonction_salarie=fonction_salarie
            type_dep.adresse_salarie=adresse_salarie
            type_dep.tlfn_salarie=tlfn_salarie
            type_dep.save()
            
        if type_dep.type == "loayer" :
            numero_local = data['numero_local']
            adresse_local = data['adresse_local']

            type_dep.numero_local=numero_local
            type_dep.adresse_local=adresse_local

            type_dep.save()
            
        if type_dep.type == "divers" :
            designation = data['designation']

            type_dep.designation=designation

            type_dep.save()

        return JsonResponse({'message': 'Client instance updated successfully'})
    
def supprimerDepense(request):
    try:
        data = json.loads(request.body)
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        user = models.depense.objects.get(id=data["user_id"])
        user.delete()
        return JsonResponse({'message': 'Dépense Supprimé !'})
    except models.CustomUser.DoesNotExist:
        return JsonResponse({'error': 'Dépense Non-trouvé.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché, car cette Affectation est lié aux autres composants - {}'.format(str(e))})      

@csrf_exempt  # Use with caution, consider adding proper CSRF protection in production
@login_required 
def saveReglement(request):
   if request.method == 'POST':
            print("here u are")
            data_invoice = request.POST  # Assuming you are sending form data via POST            
            type_reglement = data_invoice["typeReg"]
            client = Client.objects.get(id=data_invoice["client"])
            mode_reglement = models.ModeReglement.objects.get(id=data_invoice["modeReglement"])
            dateReglement = data_invoice["date"]
            BonS = BonSortie.objects.get(idBon=data_invoice["bon"])
            montant = data_invoice["montant"]
            CompteEntreprise_data = CompteEntreprise.objects.get(id=data_invoice["compteEntreprise"])
            uploaded_file = request.FILES.get('file')
            store_id = request.session["store"]
            CurrentStore = store.objects.get(pk=store_id)
            Currentuser = request.user
            myuser  = CustomUser.objects.get(username=Currentuser.username)
            banque = Banque.objects.get(id=data_invoice["banque"])
            num_cheque = data_invoice["chequeInput"]
            
            if abs(BonS.totalPrice - float(montant)) < 0.01:  # Adjust the threshold as needed
                BonS.etat_reglement = "regle"
                BonS.totalPrice -= float(montant)
            else:
                BonS.totalPrice -= float(montant)
            BonS.save()
            
            client.solde -= Decimal(montant)
            reglement_code = data_invoice["code"]
            reglement = models.Reglement.objects.create(
                codeReglement=reglement_code,
                type_reglement=type_reglement,
                client=client,
                mode_reglement=mode_reglement,
                dateReglement=dateReglement,
                BonS=BonS,
                banque=banque,
                num_cheque=num_cheque,                
                piece_jointe=uploaded_file,
                montant=montant,
                store=CurrentStore,
                user=myuser,
                CompteEntreprise=CompteEntreprise_data
            )
            manager_user = models.CustomUser.objects.filter(role='manager').first()
            if manager_user:
                notify.send(
                    sender=myuser,
                    recipient=manager_user,
                    verb=f'a introduit une nouveau règlement, cliquer pour collecter !',
                    description='/reglements/reglements',
                    level=1,
                )

            current_timestamp = datetime.now()
            logs_saving = MyLogEntry.objects.create(
                author=request.user,
                description=f'A Introduit un nouveau règlement du bon de Livraison n°= {BonS.idBon}, '
                            f'codeRèglement : {reglement_code}, avec un montant de : {montant}  ',
                timestamp=current_timestamp.strftime("%d/%m/%Y at %H:%Mh"),
                store=CurrentStore
            )

            return redirect("reglements")    
   else:
        return JsonResponse({'error': 'Invalid request method'}, status=400)
        
class DepensesListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "reglements/liste_depenses_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        return 'reglements.can_see_depense' in self.request.session.get('permissions', []) or self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF"

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
        cloture = models.depense.objects.filter(store=CurrentStore).order_by('date')
        list_cloture =[]
        
        for clot in cloture:
            if clot.type_depense.type == 'salaire':
                motif = f'{clot.type_depense.type} - {clot.type_depense.nom_salarie}'
            elif clot.type_depense.type == 'loyers - location':
                motif = f'{clot.type_depense.type} - {clot.type_depense.numero_local}' 
            elif clot.type_depense.type == 'divers':
                motif = f'{clot.type_depense.type} - {clot.type_depense.designation}' 
            else:
                # Handle the case when the type is not recognized
                motif = ''
            cloture_dict = {
                'id': clot.id,
                'motif': motif,
                'motif_type': clot.type_depense.type,
                'motif_id': clot.type_depense.id,
                'date': str(clot.date),
                'valide': 'True' if clot.user.username == 'toufik' else 'False',
                'caisse': clot.caisse.label,
                'montant': float(clot.montant),
                'mode_reglement': clot.mode_reglement.label,
                'mode_reglement_id': clot.mode_reglement.id,
                'caisse_id':clot.caisse.id,
            }        
            list_cloture.append(cloture_dict)
            
        entrepots = CompteEntreprise.objects.filter(store=CurrentStore)
        context["entrepots"] = entrepots
        modes_regs = models.ModeReglement.objects.filter(store=CurrentStore)
        context["users"]=modes_regs
        context["clotures"]=list_cloture
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
            print(dataInvoice)  
            Currentuser = self.request.user
            myuser  = CustomUser.objects.get(username=Currentuser.username)
            Currentstore = self.request.session["store"]
            my_store= store.objects.get(pk=Currentstore)
            type_dep = models.TypeDepense.objects.get(id=dataInvoice["motif"])
            mode_reg = models.ModeReglement.objects.get(id=dataInvoice.get('mode_reg', ''))  # Assuming you have a 'mode_reg' field in your formData
            caisse = CompteEntreprise.objects.get(id=dataInvoice['caisse'])
            depense_instance = models.depense.objects.create(
                    type_depense=type_dep,
                    montant=dataInvoice.get('montant', ''),  # Assuming you have this field in your formData
                    date=dataInvoice.get('date', ''),
                    mode_reglement= mode_reg,
                    caisse=caisse,  
                    user=myuser,
                    store=my_store,
            )

                # Save the depense instance
            depense_instance.save()
        return JsonResponse({'message': "Client Added successfully."})
    
class SalariesDetailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "reglements/salaries_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        return 'reglements.can_see_salaries' in self.request.session.get('permissions', []) or self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF"

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
        clients_list = models.TypeDepense.objects.filter(store=CurrentStore, type ="salaire")
        clients=[]
        for cl in clients_list:              
            cl_dict={
                "client_id":cl.id,
                "client_name" :cl.nom_salarie,
                "client_address":cl.adresse_salarie,
                "client_phone" : cl.tlfn_salarie,      
                "client_fonction":cl.fonction_salarie,
                "client_datecreation":defaultfilters.date(cl.date_creation, 'SHORT_DATE_FORMAT'),  
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
            nom_salarie = dataInvoice['nom']
            fonction_salarie = dataInvoice['fonction']
            adresse_salarie = dataInvoice["adresse"]
            tlfn_salarie = dataInvoice['phone']
            salary_depense = models.TypeDepense.objects.create(
                type='salaire',
                nom_salarie=nom_salarie,
                fonction_salarie=fonction_salarie,
                adresse_salarie=adresse_salarie,
                tlfn_salarie=tlfn_salarie,
                date_creation=datetime.now(),
                store = my_store,
            )

            salary_depense.save()
        return JsonResponse({'message': "Client Added successfully."})
    
class LoyerDetailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "reglements/loyers_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        return 'reglements.can_see_loyers' in self.request.session.get('permissions', []) or self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF"

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
        clients_list = models.TypeDepense.objects.filter(store=CurrentStore, type ="loyers - location")
        clients=[]
        
        for cl in clients_list:             
            cl_dict={
                "client_id":cl.id,
                "client_name" :cl.numero_local,
                "client_address":cl.adresse_local,
                "client_datecreation":defaultfilters.date(cl.date_creation, 'SHORT_DATE_FORMAT'),  
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
            num_local = dataInvoice['nom']
            adresse_local = dataInvoice["adresse"]

            salary_depense = models.TypeDepense.objects.create(
                type='loyers - location',
                numero_local=num_local,
                adresse_local=adresse_local,
                date_creation=datetime.now(),
                store = my_store,
            )

            salary_depense.save()
        return JsonResponse({'message': "Client Added successfully."})
    
class LoyerEntretienView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "reglements/loyers_entretien.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        return 'reglements.can_see_loyers' in self.request.session.get('permissions', []) or self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF"

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
        clients_list = models.TypeDepense.objects.filter(store=CurrentStore, type ="loyers - entretien")
        clients=[]
        
        for cl in clients_list:             
            cl_dict={
                "client_id":cl.id,
                "client_name" :cl.numero_local,
                "client_address":cl.adresse_local,
                "client_datecreation":defaultfilters.date(cl.date_creation, 'SHORT_DATE_FORMAT'),  
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
            num_local = dataInvoice['nom']
            adresse_local = dataInvoice["adresse"]

            salary_depense = models.TypeDepense.objects.create(
                type='loyers - entretien',
                numero_local=num_local,
                adresse_local=adresse_local,
                date_creation=datetime.now(),
                store = my_store,
            )

            salary_depense.save()
        return JsonResponse({'message': "Client Added successfully."})
    
class DiversDetailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "reglements/divers_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        return 'reglements.can_see_divers' in self.request.session.get('permissions', []) or self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF"

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
        clients_list = models.TypeDepense.objects.filter(store=CurrentStore, type ="divers")
        clients=[]
        
        for cl in clients_list:             
            cl_dict={
                "client_id":cl.id,
                "client_name" :cl.designation,
                "client_datecreation":defaultfilters.date(cl.date_creation, 'SHORT_DATE_FORMAT'),  
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
            designation = dataInvoice['nom']

            salary_depense = models.TypeDepense.objects.create(
                type='divers',
                designation=designation,
                date_creation=datetime.now(),
                store = my_store,
            )
            salary_depense.save()
        return JsonResponse({'message': "Client Added successfully."})
    
class EtatTresorerieView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "reglements/etat_tresorerie.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'reglements.can_see_etattres' in self.request.session.get('permissions', []) or self.request.session["role"] == 'manager'

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)    
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        store_id = self.request.session["store"]
        my_store = store.objects.get(pk=store_id)  
        caisses = CompteEntreprise.objects.filter(store=my_store)
        list_cloture =[]
        for caisse in caisses:
            cloture_dict = {
                'id': caisse.id,
                'caisse': caisse.label,
                'credit': caisse.mon_credit,
                'debit': caisse.mon_debit,
            }        
            list_cloture.append(cloture_dict)  
        entrepots = CompteEntreprise.objects.filter(store=my_store)
        context["entrepots"] = entrepots
        users_bills = CustomUser.objects.filter(EmployeeAt=my_store)
        context["users"]=users_bills
        context["clotures"]=list_cloture
        clients = Client.objects.filter(store=my_store)
        clients_reg=[]
        for client in clients:
            client_inf= {
                'name': client.name,    
                'credits': client.mon_credit,
                'debit': client.mon_debit
            }
            clients_reg.append(client_inf)
        context["clients"]=clients_reg
        
        fournisseurs = Fournisseur.objects.filter(store = my_store)
        reg_fournisseur = []
        for fournisseur in fournisseurs:
           four_dict = {
               "fournisseur": fournisseur.acronym,
               "credit": fournisseur.credit_reglements,
           } 
           reg_fournisseur.append(four_dict)
        context["reglements_fournisseurs"] = reg_fournisseur  
        depenses_liste = models.depense.objects.filter(store= my_store)
        liste_depenses = []
        for dep in depenses_liste :
           dep_dict = {
               "dep": dep.type_depense.type,
               "date": str(dep.date),
               "caisse": dep.caisse.label,
               "credit": float(dep.montant),
           } 
           liste_depenses.append(dep_dict)   
        context["depenses"] = liste_depenses
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        print(dataInvoice)
        
class MouvementCaisseView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "reglements/mouvement_caisse.html"
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
        if self.request.session["role"] == "manager":
           cloture = models.mouvementCaisse.objects.filter(store=my_store).order_by('date')
        else:
            cloture = models.mouvementCaisse.objects.filter(user=myuser).order_by('date')
        list_cloture =[]
        for clot in cloture:
            cloture_dict = {
                'id': clot.id,
                'debit': float(clot.debit),
                'credit': float(clot.credit),
                'motif': clot.motif,
                'date': str(clot.date),
                'utilisateur': clot.user.username,
                'caisse': clot.CompteEntreprise.label,
                'caisse_id':clot.CompteEntreprise.id,
                'caissed': clot.CompteEntrepriseDestinataire.label,
                'caissed_id':clot.CompteEntrepriseDestinataire.id,
            }        
            list_cloture.append(cloture_dict)
            
        entrepots = CompteEntreprise.objects.filter(store=my_store)
        context["entrepots"] = entrepots
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
            caisse = CompteEntreprise.objects.get(id=dataInvoice['caisse'])	
            caissed = CompteEntreprise.objects.get(id=dataInvoice['caissed'])	
            cloture = models.mouvementCaisse.objects.create(
                CompteEntreprise= caisse,
                CompteEntrepriseDestinataire = caissed,
                debit=dataInvoice["debit"],
                credit=dataInvoice["credit"],
                motif=dataInvoice["motif"],
                date=dataInvoice.get('date'),
                user=myuser,
                store=my_store
            )           
        return JsonResponse({'success': True})
        
class EcheanceReglementsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "reglements/EcheancesReglements_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'reglements.can_see_echreg' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
      
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        if(myuser.role =='manager'):
          types= models.EcheanceReglement.objects.all()
          context["types"]=types
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData', '')
        actif =False
        if dataInvoice["status"] == 'true':
          actif=True
        print(dataInvoice)
        if dataInvoice:
          type_instance = models.EcheanceReglement(
            label=dataInvoice['label'],
            actif=actif,
          )
          type_instance.save()
        return JsonResponse({'message': "Echeances  Added successfully."})
    
class EtatRegBlView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "reglements/etatReglements_BL_page.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'reglements.can_see_etatregbl' in self.request.session.get('permissions', []) or  self.request.session['username'] == "younes"

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
       
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        model = ContentType.objects.get_for_model(InventoryCustomPermission)

        # # Define custom permissions
        custom_permissions = [
            {'codename': 'can_create_bon_maintenance', 'name': 'can_create_bon_maintenance'},
            {'codename': 'can_see_etat_maintenance', 'name': 'can_see_etat_maintenance'},
            {'codename': 'can_see_sav_tab', 'name': 'can_see_sav_tab'},
            {'codename': 'can_create_echange_bill', 'name': 'can_create_echange_bill'}
        ]

        # Create custom permissions
        for permission_data in custom_permissions:
          permission, created = Permission.objects.get_or_create(
            codename=permission_data['codename'],
            content_type=model,
            defaults={'name': permission_data['name']}
          )

        if created:
            print(f"Created permission: {permission.name}")
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)


        clients_list = Client.objects.filter(store=CurrentStore)
        clients=[]
    
        context["clients"]=clients_list 
        return context    

class EtatRegBlFournisseurView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "reglements/etatReglements_BL_page_fournisseur.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'reglements.can_see_etatregbl' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
       
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        # model = ContentType.objects.get_for_model(ReglementsCustomPermission)

        #  # Define custom permissions
        # custom_permissions = [
        #   {
        #     'codename': 'can_see_etatregfac_fourn',
        #     'name': 'Can see état des règlements facture client',
        #   },
        #   {
        #     'codename': 'can_see_regfacfourn',
        #     'name': 'Can see règlements facture client',
        #   },
        #  {
        #     'codename': 'can_see_etatregbl_fourn',
        #     'name': 'Can see état des règlements bon de livraison',
        #   },
        #   {
        #     'codename': 'can_see_regblfourn',
        #     'name': 'Can see règlements bon de livraison',
        #   },

        # ]

        # # Create custom permissions
        # for permission_data in custom_permissions:
        #   permission, created = Permission.objects.get_or_create(
        #     codename=permission_data['codename'],
        #     content_type=model,
        #     defaults={'name': permission_data['name']}
        #   )

        # if created:
        #     print(f"Created permission: {permission.name}")
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)

        if(myuser.role =='manager'):
         clients_list = Fournisseur.objects.filter(store=CurrentStore)
         clients=[]
        #  for cl in clients_list:
        #     print(cl.client_bonS.all())
        #     cl_dict={
        #        "client_id":cl.pk,
        #        "client_name" :cl.name,
        #        "client_address":cl.adresse,
        #        "client_phone" : cl.phone,  
        #        "total_amount ":cl.total_amount,
        #        "total_paid_amount" : cl.total_paid_amount,
        #       }
        #     clients.append(cl_dict)
         context["clients"]=clients_list 
         return context    

class EtatRegFaView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "reglements/etatReglements_FA_page.html"   
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'reglements.can_see_etatregfac' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)

        clients_list = Client.objects.filter(store=CurrentStore)
        clients=[]
        for cl in clients_list:
            print(cl.client_bonS.all())
            cl_dict={
               "client_id":cl.pk,
               "client_name" :cl.name,
               "client_address":cl.adresse,
               "client_phone" : cl.phone,  
               "total_amount ":cl.total_amount,
               "total_paid_amount" : cl.total_paid_amount,
              }
            clients.append(cl_dict)
        context["clients"]=clients_list 
        return context  
        
class EtatRegFaFournisseurView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "reglements/etatReglements_FA_page_fournisseur.html"   
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'reglements.can_see_etatregfac' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)

        clients_list = Fournisseur.objects.filter(store=CurrentStore)
        # clients = []
        # for cl in clients_list:
        #     print(cl.client_bonS.all())
        #     cl_dict={
        #        "client_id":cl.pk,
        #        "client_name" :cl.name,
        #        "client_address":cl.adresse,
        #        "client_phone" : cl.phone,  
        #        "total_amount ":cl.total_amount,
        #        "total_paid_amount" : cl.total_paid_amount,
        #     }
            # clients.append(cl_dict)
        context["clients"]=clients_list 
        return context    

class ReglementNewView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "reglements/new_reglement.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        return 'reglements.can_see_regbl' in self.request.session.get('permissions', []) or  self.request.session['username'] == "younes" or  self.request.session['username'] == "nadjemeddine"

    def handle_no_permission(self):
        # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)

        clients_list = Client.objects.filter(store=CurrentStore)
        clients=[]
        for cl in clients_list:
            bills = [{'idBon': bill.idBon, 'montantRegle':0, 'montant': float(bill.total_remaining_amount)} for bill in cl.client_bonS.exclude(idBon__startswith='BECH') if bill.total_remaining_amount > 0]
            cl_dict={
               "client_id":cl.id,
               "client_name" :cl.name,
               "client_address":cl.adresse,
               "client_phone" : cl.phone, 
               "bills": bills                     
            }
            clients.append(cl_dict)
        context["clients"] = clients    
        context["selected_store"] = CurrentStore 
        bons_sortie = BonSortie.objects.filter(store=CurrentStore)
        context["bons"] = bons_sortie   

        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)       
        comptes = CompteEntreprise.objects.filter(store=CurrentStore)
        context["comptes"] = comptes
        modeReg = models.ModeReglement.objects.filter(store=CurrentStore)
        context["modeReg"]=modeReg  
        banques= Banque.objects.filter(store=CurrentStore)
        context["banques"] = banques

        return context
    
    @method_decorator(login_required)
    @method_decorator(transaction.atomic)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
        
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData', '')          
        client = Client.objects.get(id=dataInvoice["client"])
        type_reglement = dataInvoice["typeReg"]
        dateReglement = dataInvoice["dateReg"]
        mode_reglement = models.ModeReglement.objects.get(id=dataInvoice["modeReg"])
        CompteEntreprise_data = CompteEntreprise.objects.get(id=dataInvoice["comptes"])
        banque_list = dataInvoice["banque"]
        if banque_list:  # Check if the list is not empty
            banque_id = banque_list
            banque = Banque.objects.get(id=banque_id)
            cheque_input = dataInvoice["chequeInput"]
        else:
            banque=None
            cheque_input = ""
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        BonS = None
        montantRamasse = None
        print(dataInvoice)
        if 'montantTotal' in dataInvoice :
            montantRamasse = models.HistoriqueMontantRecuperer.objects.create(
                montant = dataInvoice["montantTotal"],
                date = dateReglement,
                client = client
            )
            
        if len(dataInvoice["bills"]) > 0:
            bills = dataInvoice["bills"]
            for bill in bills :
                BonS =  None
                if bill["idBon"] != 'avance':
                    BonS = BonSortie.objects.get(idBon= bill["idBon"], store = CurrentStore)
                if float(bill["montantRegle"]) > 0 :
                    current_year = timezone.now().year
                    reglements_for_year = models.Reglement.objects.all()
                    sequential_number = reglements_for_year.count() + 1
                    reglement_code = f'REG{str(current_year)[-2:]}/{str(sequential_number).zfill(3)}' 
                    note = ''
                    if 'note' in dataInvoice:
                        note = dataInvoice["note"]
                    reglement = models.Reglement.objects.create(
                        montantSource = montantRamasse,
                        codeReglement=reglement_code,
                        type_reglement=type_reglement,
                        client=client,
                        mode_reglement=mode_reglement,
                        dateReglement=dateReglement,
                        BonS=BonS,    
                        note = note,
                        num_cheque = cheque_input,                  
                        montant=float(bill["montantRegle"]),
                        store=CurrentStore,
                        user=myuser,
                        CompteEntreprise=CompteEntreprise_data
                    )
        manager_user = models.CustomUser.objects.filter(role='manager').first()
        if manager_user:
            notify.send(
                sender=myuser,
                recipient=manager_user,
                verb=f'a introduit une nouveau règlement, cliquer pour collecter !',
                description='/reglements/reglements',
                level=1,
            )

        current_timestamp = datetime.now()
        logs_saving = MyLogEntry.objects.create(
            author=myuser,
            description=f'A Introduit un nouveau règlement, '
                        f'codeRèglement : {reglement_code}',
            timestamp=current_timestamp.strftime("%d/%m/%Y at %H:%Mh"),
            store=CurrentStore
        )

        return redirect("reglements")  

class ReglementUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "reglements/reglement_update.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'reglements.can_edit_regbl ' in self.request.session.get('permissions', []) or self.request.session["role"] == "manager"

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        clients_list = Client.objects.filter(store=CurrentStore)
        clients=[]
        for cl in clients_list:
            cl_dict={
               "client_id":cl.pk,
               "client_name" :cl.name,
               "client_address":cl.adresse,
               "client_phone" : cl.phone,                      
              }
            clients.append(cl_dict)
        context["clients"]=clients    
        context["selected_store"] = CurrentStore 
        bons_sortie = BonSortie.objects.filter(store=CurrentStore)
        context["bons"] = bons_sortie   

     
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)       
        comptes = CompteEntreprise.objects.filter(store=CurrentStore)
        context["comptes"] = comptes
        modeReg = models.ModeReglement.objects.filter(store=CurrentStore)
        context["modeReg"]=modeReg  
        banques= Banque.objects.filter(store=CurrentStore)
        context["banques"] = banques

        reg_id=self.kwargs.get('reglement_id')
        reglement = models.Reglement.objects.get(id=reg_id)
        context["reglement"] = reglement
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        print(data)
        if dataInvoice: 
           montant = dataInvoice["montant"]
           CompteEntreprise_data = CompteEntreprise.objects.get(id=dataInvoice["compteEntreprise"])
           existing_reglement = models.Reglement.objects.get(id=dataInvoice["id"])             
           existing_reglement.type_reglement = dataInvoice["typeReg"]
           existing_reglement.client = Client.objects.get(id=dataInvoice["client"])
           existing_reglement.mode_reglement = models.ModeReglement.objects.get(id=dataInvoice["modeReglement"])
           existing_reglement.dateReglement = dataInvoice["date"]
           if dataInvoice["bons"]:
            existing_reglement.BonS = BonSortie.objects.get(idBon=dataInvoice["bons"])
           existing_reglement.montant = dataInvoice["montant"]
           existing_reglement.CompteEntreprise = CompteEntreprise.objects.get(id=dataInvoice["compteEntreprise"])


            # Optionally, update other fields as needed

            # Save the updated instance
           existing_reglement.save() 
           current_timestamp = datetime.now()
           logs_saving = MyLogEntry.objects.create(
                author= myuser,
                description= f' A Modifié un règlement avec codeRèglement : {existing_reglement.codeReglement}, avec un montant de : {montant}  ',
                timestamp = current_timestamp.strftime("%d/%m/%Y at %H:%Mh"),
                store  =CurrentStore
            )

        return JsonResponse({'message': "Règlement Modifié!."})

class ClotureReglementsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "reglements/clotures_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'reglements.can_see_regbl' in self.request.session.get('permissions', []) or  self.request.session['username'] == "younes" or  self.request.session['username'] == "nadjemeddine"

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)    
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        store_id = self.request.session["store"]
        my_store = store.objects.get(pk=store_id)  
        today = datetime.now().date()

        list_clotures = []

        # Create a dictionary to organize data by caisse and date
        data_by_caisse_and_date = {}

        # Iterate over days from the beginning of the year till today
        today = datetime.now().date()

        if self.request.session["role"] == "manager":
            clotures = models.ClotureReglements.objects.filter(store=my_store).order_by('date')
        else:
            clotures = models.ClotureReglements.objects.filter(utilisateur=myuser).order_by('date')

        list_clotures = []
       
        # Iterate over each CompteEntreprise (caisse)
        Caisses = CompteEntreprise.objects.filter(store=my_store)
        for caisse in Caisses:
            current_date = datetime(today.year, 1, 1).date()
           
            while current_date < today:
                # Check if Cloture object exists for the current date
                total_reglementbc_for_date = 0
                cloture_for_date = clotures.filter(date=current_date, caisse=caisse).first()
                id = 0
                montant_introduit = 0
                # Calculate sum of Reglement.montant for the current date
                reglements_for_date = models.Reglement.objects.filter(store=my_store, dateReglement=current_date, CompteEntreprise=caisse)

                
                total_reglement_for_date = sum(Decimal(reg.montant) if reg.montant != '' else Decimal(0) for reg in reglements_for_date)

                comtpoire_for_date = BonComptoire.objects.filter(store=my_store, dateBon=current_date)
                
                for bc in comtpoire_for_date:
                    if bc.user.mon_affectation.first().CompteTres == caisse :
                        total_reglementbc_for_date += Decimal(bc.totalprice) if bc.totalprice != '' else Decimal(0) 

                # Create a dictionary for Cloture information
                cloture_dict = {
                    'id': id,
                    'date': str(current_date),
                    'montant_introduit': float(montant_introduit),
                    'total_reglement_for_date': float(total_reglement_for_date),
                    'totalComptoire': float(total_reglementbc_for_date),
                    'caisse': caisse.label,
                }

                list_clotures.append(cloture_dict)

                # Move to the next day
                current_date += timedelta(days=1)

        file_path = "file.json"
        with open(file_path, 'w') as json_file:
            json.dump(list_clotures, json_file)    
        entrepots = CompteEntreprise.objects.filter(store=my_store)
        context["entrepots"] = entrepots
        users_bills = CustomUser.objects.filter(EmployeeAt=my_store)
        context["users"]=users_bills
        context["clotures"]=list_clotures
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
            existing_cloture = models.ClotureReglements.objects.filter(date=date, utilisateur=myuser, store=my_store).first()

            if existing_cloture:
                return JsonResponse({'error': True, 'error': 'Vous avez déjà introduit une clôture.'})
            else:
                # Create a new Cloture instance
                cloture = models.ClotureReglements.objects.create(
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
                        description='/reglements/cloturesReglements',
                        level=1,
                    )
            return JsonResponse({'error': False})
            
class ReglementFournisseurNewView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "reglements/new_reglement_fournisseur.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'reglements.can_see_regbl' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        fournisseurs = Fournisseur.objects.filter(store=CurrentStore)

        context["clients"]= fournisseurs  
        context["selected_store"] = CurrentStore 
        bons_sortie = BonAchat.objects.filter(store=CurrentStore)
        context["bons"] = bons_sortie   

     
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)       
        comptes = CompteEntreprise.objects.filter(store=CurrentStore)
        context["comptes"] = comptes
        modeReg = models.ModeReglement.objects.filter(store=CurrentStore)
        context["modeReg"]=modeReg  
        banques= Banque.objects.filter(store=CurrentStore)
        context["banques"] = banques
        current_year = timezone.now().year
        reglements_for_year = models.ReglementFournisseur.objects.all()
        sequential_number = reglements_for_year.count() + 1
        reglement_code = f'REG{str(current_year)[-2:]}/{str(sequential_number).zfill(3)}'
        context["codereglement"] = reglement_code
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        if dataInvoice: 
           type_reglement = dataInvoice["typeReg"]
           client = Fournisseur.objects.get(id=dataInvoice["client"])
           mode_reglement = models.ModeReglement.objects.get(id=dataInvoice["modeReglement"])
           dateReglement = dataInvoice["date"]
           BonS = BonAchat.objects.get(idBon= dataInvoice["bl"])
           montant = dataInvoice["montant"]
           CompteEntreprise_data = CompteEntreprise.objects.get(id=dataInvoice["compteEntreprise"])

           if abs(BonS.totalPrice - float(montant)) < 0.01:  # Adjust the threshold as needed
            BonS.totalPrice -= float(montant)
           else:
            BonS.totalPrice -= float(montant)
           BonS.save()

           reglement_code =dataInvoice["code"]
           reglement = models.ReglementFournisseur.objects.create(
              codeReglement = reglement_code,
              type_reglement=type_reglement,
              fournisseur=client,
              mode_reglement=mode_reglement,
              dateReglement=dateReglement,
              BonA=BonS,
              montant=montant,
              store=CurrentStore,
              user=myuser,
              CompteEntreprise=CompteEntreprise_data
            )
           manager_user = models.CustomUser.objects.filter(role='manager').first()
           if manager_user:
                        notify.send(
                            sender=myuser,
                            recipient=manager_user,
                            verb=f'{myuser.username} a introduit une nouveau règlement, cliquer pour collecter !',  
                            description='/reglements/reglements',                     
                            level=1,
            )
           current_timestamp = datetime.now()
           logs_saving = MyLogEntry.objects.create(
                author= myuser,
                description= f' A Introduit un nouveau règlement du bon de Livraison n°= {BonS.idBon}, codeRèglement : {reglement_code}, avec un montant de : {montant}  ',
                timestamp = current_timestamp.strftime("%d/%m/%Y at %H:%Mh"),
                store  =CurrentStore
            )

        return JsonResponse({'message': "Règlement Ajouté!."})
        
class ReglementNewFactureView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "reglements/new_reglement_facture.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'reglements.can_see_regbl' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)

     
        clients_list = Client.objects.filter(store=CurrentStore)
        clients=[]
        for cl in clients_list:
            cl_dict={
               "client_id":cl.pk,
               "client_name" :cl.name,
               "client_address":cl.adresse,
               "client_phone" : cl.phone,                      
              }
            clients.append(cl_dict)
        context["clients"]=clients    
        context["selected_store"] = CurrentStore 
        bons_sortie = Facture.objects.filter(store=CurrentStore)
        context["bons"] = bons_sortie   
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)       
        comptes = CompteEntreprise.objects.filter(store=CurrentStore)
        context["comptes"] = comptes
        modeReg = models.ModeReglement.objects.filter(store=CurrentStore) 
        context["modeReg"]=modeReg  
        banques= Banque.objects.filter(store=CurrentStore)
        context["banques"] = banques
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        audit_logs = LogEntry.objects.filter(actor_id=myuser.id)
        print(data)
        if dataInvoice: 
           type_reglement = dataInvoice["typeReg"]
           client = Client.objects.get(name=dataInvoice["client"])
           mode_reglement = models.ModeReglement.objects.get(id=dataInvoice["modeReglement"])
           dateReglement = dataInvoice["date"]
           BonS = Facture.objects.get(codeFacture= dataInvoice["bl"])
           montant = dataInvoice["montant"]
           CompteEntreprise_data = CompteEntreprise.objects.get(id=dataInvoice["compteEntreprise"])

           if abs(BonS.totalPrice - float(montant)) < 0.01:  # Adjust the threshold as needed
            BonS.etat_reglement = "reglé"
            BonS.totalPrice -= float(montant)
           else:
            BonS.totalPrice -= float(montant)
           BonS.save()
           current_year = timezone.now().year
           reglements_for_year = models.Reglement.objects.all()
           sequential_number = reglements_for_year.count() + 1
           reglement_code = f'REG{str(current_year)[-2:]}/{str(sequential_number).zfill(3)}'

           reglement = models.Reglement.objects.create(
              codeReglement = reglement_code,
              type_reglement=type_reglement,
              client=client,
              mode_reglement=mode_reglement,
              dateReglement=dateReglement,
              facture=BonS,
              montant=montant,
              store=CurrentStore,
              user=myuser,
              CompteEntreprise=CompteEntreprise_data
            )
           manager_user = models.CustomUser.objects.filter(role='manager').first()
           if manager_user:
                        notify.send(
                            sender=myuser,
                            recipient=manager_user,
                            verb=f'{myuser.username} a introduit une nouveau règlement, cliquer pour collecter !',  
                            description='/reglements/reglements-facture',                     
                            level=1,
            )
           current_timestamp = datetime.now()
           logs_saving = MyLogEntry.objects.create(
                author= myuser,
                description= f' A Introduit un nouveau règlement de la facture n°= {BonS.codeFacture}, codeRèglement : {reglement_code}, avec un montant de : {montant}  ',
                timestamp = current_timestamp.strftime("%d/%m/%Y at %H:%Mh"),
                store  =CurrentStore
            )
        return redirect('reglements')
  
class TypeReglementsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "reglements/typesReglements_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'reglements.can_see_typereg' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
  
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        types= models. ModeReglement.objects.filter(store=CurrentStore)
        context["types"]=types
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
      
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData', '')
        actif =False
        if dataInvoice["status"] == 'true':
          actif=True
        print(dataInvoice)
        if dataInvoice:
          store_id = self.request.session["store"]
          CurrentStore = store.objects.get(pk=store_id)
          type_instance = models.ModeReglement(
            label=dataInvoice['label'],
            actif=actif,
            store= CurrentStore,
          )
          type_instance.save()
        return JsonResponse({'message': "Mode Règlement Added successfully."})
            
class HistoriqueMontantsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "reglements/historique_montants.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'reglements.can_see_regbl' in self.request.session.get('permissions', [])  or  self.request.session['username'] == "younes" or  self.request.session['username'] == "nadjemeddine"

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
       

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore =store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)       
      
        reglement_data = []    
        hist = models.HistoriqueMontantRecuperer.objects.filter(client__store = CurrentStore)
        for montant in hist:
            reglement_dict = {
              'id':montant.id,
              'client': str(montant.client.name),  # Assuming Client model has a __str__ method defined              
              'user': str(montant.client.user.username),  # Assuming Client model has a __str__ method defined
              'mode_reglement': str(montant.rep_reglements.first().mode_reglement.label) if len(montant.rep_reglements.all()) > 0 else '',              
              'date': montant.date.strftime('%Y-%m-%d'),
              'montant': float(montant.montant),             
              'bills': [{   'idBon': reg.BonS.idBon if reg.BonS else '/',
                            'dateBon': reg.BonS.dateBon.strftime('%Y-%m-%d') if reg.BonS else '/',
                            'montant': float(reg.BonS.get_total_soldprice) if reg.BonS else 0,
                            'montantRegle': float(reg.montant)
                        } for reg in montant.rep_reglements.all()  
                ],          
            }
            reglement_data.append(reglement_dict)
        entrepots = CompteEntreprise.objects.filter(store=CurrentStore)
        context["entrepots"] = entrepots
        users_bills = CustomUser.objects.filter(EmployeeAt=CurrentStore)
        context["users"]=users_bills
        context["reglements"] = reglement_data
        return context
    
class ReglementsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "reglements/reglements_page.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'reglements.can_see_regbl' in self.request.session.get('permissions', [])  or  self.request.session['username'] == "younes" or  self.request.session['username'] == "nadjemeddine"

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
       

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore =store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)       
      
        reglement_data = []    
          # Assuming YourModel is the name of the model containing the fields you provided
        from django.db.models import Q
        myuser  = CustomUser.objects.get(username=Currentuser.username)       
        if(myuser.role == 'manager' or myuser.role == 'DIRECTEUR EXECUTIF'):
            reglements = models.Reglement.objects.filter(
                Q(store=CurrentStore)
             ).order_by('-id')
        else :
            reglements = models.Reglement.objects.filter(
                user=myuser
             ).order_by('-id')
        for reglement in reglements:
            reglement_dict = {
              'id':reglement.id,
              'codeReglement': reglement.codeReglement,
              'type_reglement': reglement.type_reglement,
              'collected': str(reglement.collected),
              'client': str(reglement.client.name),  # Assuming Client model has a __str__ method defined
              'mode_reglement': str(reglement.mode_reglement),
              'dateReglement': reglement.dateReglement.strftime('%Y-%m-%d'),
              'BonS': str(reglement.BonS.idBon) if reglement.BonS else '',
              'facture': str(reglement.facture.codeFacture) if reglement.facture else '',
              'montant': float(reglement.montant),
              'note': f'{reglement.note}',
              'user': str(reglement.user.first_name),
              'CompteEntreprise': str(reglement.CompteEntreprise.label),          
            }
            reglement_data.append(reglement_dict)
        entrepots = CompteEntreprise.objects.filter(store=CurrentStore)
        context["entrepots"] = entrepots
        users_bills = CustomUser.objects.filter(EmployeeAt=CurrentStore)
        context["users"]=users_bills
        context["reglements"] = reglement_data
        return context
        
class ReglementsEspeceView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "reglements/reglementsespece_page.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'reglements.can_see_regbl' in self.request.session.get('permissions', [])  or  self.request.session['username'] == "younes" or  self.request.session['username'] == "nadjemeddine"

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
       

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore =store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)       
      
        reglement_data = []    
          # Assuming YourModel is the name of the model containing the fields you provided
        from django.db.models import Q
        myuser  = CustomUser.objects.get(username=Currentuser.username)       
        bonSorties = BonSortie.objects.filter(store = CurrentStore)
        for bon in bonSorties:
            reglement_dict = {
              'id':bon.id,
              'codebon': bon.idBon,
              'dateBon': bon.dateBon.strftime('%Y-%m-%d'),
              'mode_reglement': bon.mode_reglement.label if bon.mode_reglement is not None else '' ,
              'client': str(bon.client.name),
              'montantBon': round(float(bon.get_total_soldprice),0),
              'codeReglement': bon.bonS_reglements.first().codeReglement if bon.bonS_reglements.first() is not None else '',
              'dateReglement': str(bon.bonS_reglements.first().dateReglement.strftime('%Y-%m-%d')) if bon.bonS_reglements.first() is not None else '',
              'montantRegle': round(float(bon.bonS_reglements.first().montant),0) if bon.bonS_reglements.first() is not None else 0.00,          
            }
            reglement_data.append(reglement_dict)
        context["reglements"] = reglement_data
        modeReg = models.ModeReglement.objects.filter(store=CurrentStore)
        context["modeReg"]=modeReg
        return context

class ReglementsChequeView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "reglements/reglementscheque_page.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'reglements.can_see_regbl' in self.request.session.get('permissions', [])  or  self.request.session['username'] == "younes" or  self.request.session['username'] == "nadjemeddine"

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
       

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore =store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)       
      
        reglement_data = []    
          # Assuming YourModel is the name of the model containing the fields you provided
        from django.db.models import Q
        myuser  = CustomUser.objects.get(username=Currentuser.username)       
        bonSorties = BonSortie.objects.filter(store = CurrentStore, mode_reglement__id = 2)
        for bon in bonSorties:
            banque = ''
            numcheque = ''
            if bon.banque_Reglement :
               banque = bon.banque_Reglement.nom 
               numcheque = bon.num_cheque_reglement
            elif bon.bonS_reglements.first() is not None:
               banque = bon.bonS_reglements.first().CompteEntreprise.label
               numcheque = bon.bonS_reglements.first().num_cheque
            reglement_dict = {
              'id':bon.id,
              'codebon': bon.idBon,
              'dateBon': bon.dateBon.strftime('%Y-%m-%d'),
              'mode_reglement': bon.mode_reglement.label,
              'client': str(bon.client.name),
              'banque': banque,
              'NumeroCheque': numcheque,
              'montantBon': round(float(bon.get_total_soldprice),0),
              'codeReglement': bon.bonS_reglements.first().codeReglement if bon.bonS_reglements.first() is not None else '',
              'dateReglement': str(bon.bonS_reglements.first().dateReglement.strftime('%Y-%m-%d')) if bon.bonS_reglements.first() is not None else '',
              'montantRegle': round(float(bon.bonS_reglements.first().montant),0) if bon.bonS_reglements.first() is not None else 0.00,          
            }
            reglement_data.append(reglement_dict)
        context["reglements"] = reglement_data
        return context
        
class ReglementsVirementView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "reglements/reglementsvirement_page.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'reglements.can_see_regbl' in self.request.session.get('permissions', [])  or  self.request.session['username'] == "younes" or  self.request.session['username'] == "nadjemeddine"

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
       

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore =store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)       
      
        reglement_data = []    
          # Assuming YourModel is the name of the model containing the fields you provided
        from django.db.models import Q
        myuser  = CustomUser.objects.get(username=Currentuser.username)       
        bonSorties = BonSortie.objects.filter(store = CurrentStore, mode_reglement__id = 5)
        for bon in bonSorties:
            banque = ''
            if bon.banque_Reglement :
               banque = bon.banque_Reglement.nom 
            elif bon.bonS_reglements.first() is not None:
               banque = bon.bonS_reglements.first().CompteEntreprise.label
            reglement_dict = {
              'id':bon.id,
              'codebon': bon.idBon,
              'dateBon': bon.dateBon.strftime('%Y-%m-%d'),
              'mode_reglement': bon.mode_reglement.label,
              'client': str(bon.client.name),
              'banque': banque,
              'montantBon': round(float(bon.get_total_soldprice),0),
              'codeReglement': bon.bonS_reglements.first().codeReglement if bon.bonS_reglements.first() is not None else '',
              'dateReglement': str(bon.bonS_reglements.first().dateReglement.strftime('%Y-%m-%d')) if bon.bonS_reglements.first() is not None else '',
              'montantRegle': round(float(bon.bonS_reglements.first().montant),0) if bon.bonS_reglements.first() is not None else 0.00,          
            }
            reglement_data.append(reglement_dict)
        context["reglements"] = reglement_data
        return context
      
class ReglementsFournisseurView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "reglements/reglements_page_bl_fournisseur.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'reglements.can_see_regbl' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
       
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore =store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)       
        if(myuser.role =='manager'):
         reglement_data = []    
          # Assuming YourModel is the name of the model containing the fields you provided
         from django.db.models import Q
         reglements = models.ReglementFournisseur.objects.filter(
           Q(BonA__isnull=False) & Q(store=CurrentStore)
         )
         for reglement in reglements:
            reglement_dict = {
              'codeReglement': reglement.codeReglement,
              'type_reglement': reglement.type_reglement,
              'collected': str(reglement.collected),
              'fournisseur': str(reglement.fournisseur.acronym),  # Assuming Client model has a __str__ method defined
              'mode_reglement': str(reglement.mode_reglement),
              'dateReglement': reglement.dateReglement.strftime('%Y-%m-%d'),
              'BonS': str(reglement.BonA.idBon) if reglement.BonA else '',
              'facture': str(reglement.facture.codeFacture) if reglement.facture else '',
              'montant': float(reglement.montant),
              'CompteEntreprise': str(reglement.CompteEntreprise.label),          
              }
            reglement_data.append(reglement_dict)
         context["reglements"] = reglement_data
        return context

class ReglementsFactureView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "reglements/reglements_page_facture.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'reglements.can_see_regbl' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
       

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        Currentuser = self.request.user
        store_id = self.request.session["store"]
        CurrentStore =store.objects.get(pk=store_id)
        myuser  = CustomUser.objects.get(username=Currentuser.username)       
        if(myuser.role =='manager'):
         reglement_data = []    
          # Assuming YourModel is the name of the model containing the fields you provided
         from django.db.models import Q

         reglements = models.Reglement.objects.filter(
           Q(facture__isnull=False) & Q(store=CurrentStore)
         )
         for reglement in reglements:
            reglement_dict = {
              'codeReglement': reglement.codeReglement,
              'type_reglement': reglement.type_reglement,
              'collected': str(reglement.collected),
              'client': str(reglement.client.name),  # Assuming Client model has a __str__ method defined
              'mode_reglement': str(reglement.mode_reglement),
              'dateReglement': reglement.dateReglement.strftime('%Y-%m-%d'),
              'facture': str(reglement.facture.codeFacture) if reglement.facture else '',
              'montant': float(reglement.montant),
              'CompteEntreprise': str(reglement.CompteEntreprise.label),          
              }
            reglement_data.append(reglement_dict)
         context["reglements"] = reglement_data
        return context