from django.shortcuts import render
from django.views.generic.base import TemplateView
from django.http import Http404, JsonResponse
import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from . import models
from tiers.models import Banque, Agence
from users.models import CustomUser
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from clientInfo.models import store
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from .models import ClientInfoCustomPermission
from django.views.generic import DetailView
from django.shortcuts import get_object_or_404
from comptoire.models import BonRetourComptoir
from inventory.models import BonRetour
from django.db import transaction

def DeleteComptes(request):
    data = json.loads(request.body)
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    data = data.get('formData', '')
    compte_id = data["id"]
    compte = models.CompteEntreprise.objects.get(id=compte_id, store=CurrentStore)
    with transaction.atomic():   
      if len(compte.caisse_affectation.all()) > 0  or len(compte.fournisseurs_reglements.all()) > 0  or len(compte.client_reglements.all()) > 0:    
           return JsonResponse({'message': "Caisse ne peut pas être Supprimé !"})
      else:
        compte.delete()
    return JsonResponse({'message': "Elément Supprimé !"})

def ModifierCompte(request):
    data = json.loads(request.body)
    dataInvoice = data.get('formData', '')
    currentStore = models.store.objects.get(pk=request.session["store"]) 

    if dataInvoice:
        mybanque = None
        myagence = None

        if dataInvoice["banque"] != "":
            mybanque = Banque.objects.get(pk=dataInvoice["banque"])

        if dataInvoice["agence"] != "":
            myagence = Agence.objects.get(pk=dataInvoice["agence"])

        nature = dataInvoice["nature"]
        label = dataInvoice["label"]
        NumCompte = dataInvoice["Numcompte"]
        comptableCompte = dataInvoice["compteComptable"]
        journal = dataInvoice["journal"]
        monnaie = dataInvoice["monnaie"]

        MycomptableAccount = models.PlanComptableAccount.objects.get(code=comptableCompte)

        # Fetch the existing CompteEntreprise instance
        ce_instance = models.CompteEntreprise.objects.get(id=dataInvoice["id"])  # Assuming 'id' is the primary key

        # Update the fields
        ce_instance.nature = nature
        ce_instance.label = label
        ce_instance.numCompte = NumCompte
        ce_instance.banque = mybanque
        ce_instance.agence = myagence
        ce_instance.store = currentStore
        ce_instance.compteComptable = MycomptableAccount
        ce_instance.journal = journal
        ce_instance.monnaie = monnaie

        # Save the updated instance
        ce_instance.save() 
        return JsonResponse({'message': "Compte Entreprise Updated successfully."})  

def DeleteTypes(request):
    data = json.loads(request.body)
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    liste_id = data["liste_ids"]
    for id_bon in liste_id:
        category = models.typeClient.objects.get(id=id_bon, store=CurrentStore)
        with transaction.atomic():
              category.clients_type.all().update(categorie_client=None)
               # Delete the Category instance
              category.delete()
    return JsonResponse({'message': "Eléments Supprimé !"})

def ModifierType(request):
    data = json.loads(request.body)
    dataInvoice = data.get('formData', '')
    if dataInvoice:
        try:
            type_Cl= models.typeClient.objects.get(id=dataInvoice["id"])
        except models.Devise.DoesNotExist:
            type_Cl= None

        if type_Cl:
            type_Cl.type_desc = dataInvoice.get('type_desc', type_Cl.type_desc)
            type_Cl.montant_min = dataInvoice.get('montant',0)
            type_Cl.percent = dataInvoice.get('percent',0)
            type_Cl.dateCreation = dataInvoice.get('dateCreation', type_Cl.dateCreation)
            type_Cl.save()
    return JsonResponse({'message': "Devise Updated successfully."})  
    
class NewStoreView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "clientInfo/new_store.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return myuser.role=="manager"

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    def get_context_data(self, **kwargs):
       context = super().get_context_data(**kwargs)
       return context
     
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')    
        if dataInvoice :
          new_store = models.store(
            name=dataInvoice["codeOrg"],
            location=dataInvoice["adr1"],
            code=dataInvoice["codeOrg"],
            nAdherent=dataInvoice["numAdh"],
            denomination=dataInvoice["denom"],
            raisonSocial=dataInvoice["raissocial"],
            CodePostal=dataInvoice["codePostal"],
            monnaie=dataInvoice["monnaie"],
            IdentificationFis=dataInvoice["idFis"],
            registreCom=dataInvoice["regCom"],
            articleImpo=dataInvoice["artImpo"],
            identifiantStatistique=dataInvoice["numId"],
            banque=dataInvoice["banque"],
            compteBancaire=dataInvoice["cptbanc"],
            compteCCP=dataInvoice["ccp"],
            capitaleSocial=dataInvoice["capSoc"],
            address1=dataInvoice["adr1"],
            address2=dataInvoice["adr2"],
            address3=dataInvoice["adr3"],
            phone1=dataInvoice["tel1"],
            phone2=dataInvoice["tel2"],
            phone3=dataInvoice["tel3"],
            fax1=dataInvoice["fax1"],
            fax2=dataInvoice["fax2"],
            fax3=dataInvoice["fax3"],
            mobile1=dataInvoice["mob1"],
            mobile2=dataInvoice["mob2"],
            mobile3=dataInvoice["mob3"],
            product_variant=dataInvoice["productVariants"]
          )
          new_store.save() 
          return JsonResponse({'message': "Organisation Added successfully."})  

class EntrepriseIdentificationView (LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "clientInfo/identification.html"  
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return 'clientInfo.can_see_societe' in self.request.session.get('permissions', []) or self.request.session["role"] == 'manager' or self.request.session["role"] == 'DIRECTEUR EXECUTIF'

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, **kwargs):       
        if  self.kwargs.get('mag_id') :  
             store_id=self.kwargs.get('mag_id')
             store_obj=store.objects.get(pk=store_id)
             self.request.session["nomStore"]=store_obj.name
             self.request.session["store"]=store_id
             year_selected = self.kwargs.get('year')
             self.request.session['currentYear'] = year_selected

       
        store_pk = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_pk)    
        context = super().get_context_data(**kwargs)
        context["org_name"] = CurrentStore.name
        context["location"] = CurrentStore.location
        context["long_entrepot"] = len(CurrentStore.get_entrepots())
        context["employees"] = len(CurrentStore.mes_employees.all())
        context["totalrev"]= CurrentStore.total_bon_price
        context["nbrliv"] = len(CurrentStore.bonL_store.all())
        context["nbrvente"]=len(CurrentStore.bons_comptoir_store.all())
        context["nbrretour"] = len(BonRetourComptoir.objects.filter(bon_comptoir_associe__store=CurrentStore))
        context["clients"] = len(CurrentStore.client_store.all())
        context["vente_per_month"] = CurrentStore.bons_counts_per_month
        retours_per_month = []
        for month in range(1, 13):
            retours_count = BonRetourComptoir.objects.filter(
                bon_comptoir_associe__store=CurrentStore,
                dateBon__month=month
            ).count()
            retoursB_count = BonRetour.objects.filter(
                store=CurrentStore,
                dateBon__month=month
            ).count()
            total = retours_count + retoursB_count
            retours_per_month.append(total)

        context["retour_per_month"] = retours_per_month
        context['store']= CurrentStore
        return context
 
class DetailsPage(TemplateView):
   template_name="clientInfo/details_page.html"
   @method_decorator(login_required)
   def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
   def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        model_type = self.kwargs['model_type']
        pk = self.kwargs['pk']

        # Determine the model class based on the model_type parameter
        model_classes = {
            'compteentreprise': models.CompteEntreprise,
            'taxes': models.Taxes,
            'devise': models.Devise,
            'typeclient': models.typeClient,
        }

        model_class = model_classes.get(model_type)

        if model_class is None:
            # Handle the case where an invalid model type is provided in the URL
            context['invalid_model'] = True
        else:
            # Retrieve the specific model instance based on the primary key (pk)
            model_instance = get_object_or_404(model_class, pk=pk)

            # Get a list of fields for the model
            fields = model_instance._meta.get_fields()

            context['model_type'] = model_type
            context['model_instance'] = model_instance
            context['fields'] = fields

        return context
      
class TaxesView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "clientInfo/taxes_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        print('hello',self.request.session.get('permissions', []))
        return('clientInfo.can_see_tax_douan' in self.request.session.get('permissions', []) or 'clientInfo.can_see_tax_tva' in self.request.session.get('permissions', []))

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        type_tax= self.kwargs.get('type_tax')
        currentStore= models.store.objects.get(pk=self.request.session["store"]) 
        if type_tax== "DOUAN" :  
           taxes = models.Taxes.objects.filter(type_taxe="DOUAN", store=currentStore)
           context["type"]= "DOUAN"
           context["taxesList"]=taxes
        elif type_tax =="TVA":
            taxes = models.Taxes.objects.filter(type_taxe="TVA", store=currentStore)
            context["type"]= "TVA"
            context["taxesList"]=taxes
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
            taux = dataInvoice['taux']
            type = dataInvoice['type']            
            taxe_instance = models.Taxes(
              libelle=lib,
              taux=taux,
              type_taxe =type,
              store =currentStore
            )
            taxe_instance.save()
        return JsonResponse({'message': "Entrepot Added successfully."})

class DeviseView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "clientInfo/devise_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        print('hello',self.request.session.get('permissions', []))
        return'clientInfo.can_see_devises' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        Currentuser = self.request.user
        currentStore= models.store.objects.get(pk=self.request.session["store"])  
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        if(myuser.role =='manager'):
          devises= models.Devise.objects.filter(store=currentStore)
          context["devise"]=devises
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
          Currentstore = self.request.session["store"]
          my_store= models.store.objects.get(pk=Currentstore)
          devise_instance = models.Devise(
            reference=dataInvoice['reference'],
            designation=dataInvoice['designation'],
            symbole=dataInvoice['symbole'],
            actif=actif,
            store = my_store
          )
          devise_instance.save()
        return JsonResponse({'message': "Banque Added successfully."})

class DeviseUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "clientInfo/devise_page_update.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        print('hello',self.request.session.get('permissions', []))
        return'clientInfo.can_see_devises' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        devise_id=self.kwargs.get('devise_id')
        devise_inst= models.Devise.objects.filter(id=devise_id).first()
        Currentuser = self.request.user
        currentStore= models.store.objects.get(pk=self.request.session["store"])  
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        context["devise"]=devise_inst
        print(context["devise"])
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData', '')
      
        print(dataInvoice)
        if dataInvoice:
            try:
                devise = models.Devise.objects.get(id=dataInvoice["id"])
            except models.Devise.DoesNotExist:
                devise = None

            if devise:
                devise.designation = dataInvoice.get('designation', devise.designation)
                devise.symbole = dataInvoice.get('symbole', devise.symbole)
                status = dataInvoice.get('status', None)
                if status is not None:
                    devise.actif = status
                devise.save()
        return JsonResponse({'message': "Devise Updated successfully."})  

class DeviseValueView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "clientInfo/devise_value_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        print('hello',self.request.session.get('permissions', []))
        return'clientInfo.can_see_valeur_devis' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) 
        Currentuser = self.request.user
        currentStore= models.store.objects.get(pk=self.request.session["store"])  
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        devises= models.Devise.objects.filter(store=currentStore)
        devisesValeur= models.ValeurDevise.objects.filter(store=currentStore)
        context["devises"]=devises
        context["devise_valeurs"]=devisesValeur
        return context
      
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData', '')
      
        print(dataInvoice)
        if dataInvoice:
          deviseObj = models.Devise.objects.get(id=dataInvoice["devise"])
          Currentstore = self.request.session["store"]
          my_store= models.store.objects.get(pk=Currentstore)
          devise_instance = models.ValeurDevise(
            Devise=deviseObj,
            valeur=dataInvoice['valeur'],
            date=dataInvoice['date'],
            store = my_store
          )
          devise_instance.save()
        return JsonResponse({'message': "Devise Valeur Added successfully."})  
      
class TypeClientsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "clientInfo/typesClient_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        print('hello',self.request.session.get('permissions', []))
        return'clientInfo.can_see_type_client' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        currentStore= models.store.objects.get(pk=self.request.session["store"])  
        if(myuser.role =='manager'):
          types= models.typeClient.objects.filter(store=currentStore)
          context["types"]=types
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData', '')
        currentStore= models.store.objects.get(pk=self.request.session["store"]) 
        if dataInvoice:       
          typeClient_instance = models.typeClient(
            type_desc = dataInvoice['type'],
            dateCreation = dataInvoice['date'],
            montant_min = dataInvoice['montant'],
            percent = dataInvoice['percent'],
            store = currentStore
          )
          typeClient_instance.save()
        return JsonResponse({'message': "Banque Added successfully."})
  
class TypeClientsUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "clientInfo/typesClient_page_update.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'clientInfo.can_see_type_client' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        id_typecl= self.kwargs.get('id_typecl')
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        currentStore= models.store.objects.get(pk=self.request.session["store"])  
        type= models.typeClient.objects.filter(id=id_typecl).first()
        context["typeCl"]=type
        return context
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData', '')
      
        print(dataInvoice)
        if dataInvoice:
            try:
                type_Cl= models.typeClient.objects.get(id=dataInvoice["id"])
            except models.Devise.DoesNotExist:
                type_Cl= None

            if type_Cl:
                type_Cl.type_desc = dataInvoice.get('type_desc', type_Cl.type_desc)
                type_Cl.dateCreation = dataInvoice.get('dateCreation', type_Cl.dateCreation)
                type_Cl.save()
        return JsonResponse({'message': "Devise Updated successfully."})  

class comptesTresorerieView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "clientInfo/compteTres_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return'clientInfo.can_see_compteEntreprise' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        currentStore= models.store.objects.get(pk=self.request.session["store"]) 
        banques= Banque.objects.filter(store=currentStore)
        agences= Agence.objects.filter(store=currentStore)          
        comptes = models.CompteEntreprise.objects.filter(store=currentStore)
        plan_comptable = []
        classes = models.PlanComptableClass.objects.all()
        for comptable_class in classes:
            accounts = models.PlanComptableAccount.objects.filter(comptable_class=comptable_class)
            plan_comptable.append({
            'class': comptable_class,
            'accounts': accounts
            })
        context["comptes"] = comptes
        context["plan_comptable"]=plan_comptable 
        comptes = models.CompteEntreprise.objects.filter(store=currentStore)
        context["comptes"]=comptes
        context["banques"]=banques
        context["agences"]=agences
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData', '')
        currentStore= models.store.objects.get(pk=self.request.session["store"]) 
        if dataInvoice:
           mybanque=None
           myagence=None
           if dataInvoice["banque"] != "":
              mybanque = Banque.objects.get(pk=dataInvoice["banque"])
           if dataInvoice["agence"] != "":
              myagence = Agence.objects.get(pk=dataInvoice["agence"])
           nature=dataInvoice["nature"]
           label = dataInvoice["label"]
           NumCompte = dataInvoice["Numcompte"]
           comptableCompte= dataInvoice["compteComptable"]
           journal= dataInvoice["journal"]
           monnaie=dataInvoice["monnaie"]
           MycomptableAccount = models.PlanComptableAccount.objects.get(code=comptableCompte)
           ce_instance = models.CompteEntreprise(
            nature=nature,
            label=label,
            numCompte =NumCompte,
            banque =mybanque,
            agence=myagence,
            store=currentStore,
            compteComptable =MycomptableAccount,
            journal=journal,
            monnaie=monnaie,
           )
           ce_instance.save()
        return JsonResponse({'message': "Agence Added successfully."})
    
