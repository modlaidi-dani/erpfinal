from django.shortcuts import render
from django.views.generic.base import TemplateView
from django.http import Http404, JsonResponse
import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from . import models
from users.models import CustomUser
from clientInfo.models import typeClient, CompteEntreprise
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from .models import TiersCustomPermission
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction,  IntegrityError
from clientInfo.models import store
from produits.models import Product
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from django.shortcuts import redirect
from django.utils.translation import gettext as _

def importClients(request):
   data = json.loads(request.body)
   products_list = data["clients"]
   store_id = request.session["store"]
   current_store = store.objects.get(pk=store_id)
   for prod_data in products_list:
      clientIns = models.Client.objects.filter(name = prod_data['nomClient'], store = current_store).first()
      if clientIns is not None :
        if 'region' in prod_data:  
         clientIns.region_client = prod_data['region'] 
         clientIns.save()
   return JsonResponse({'message':'Clients Importé!'})

def createFournisseur(request):
        # try:
            data = json.loads(request.body)
            Currentuser = request.user
            myuser  = CustomUser.objects.get(username=Currentuser.username)
            store = request.session["store"]
            CurrentStore = models.store.objects.get(pk=store)
            # Extract data from the JSON object
            acronym = data.get('acronym')
            adresse = data.get('adresse')
            phone = data.get('phone')
            email = data.get('email')
            rsocial = data.get('rsocial')
            typefour = data.get('typefour')
            client = data.get('client')
            etrange = data.get('etrange')
            print(acronym)
            codeFournisseur = f'F{models.Fournisseur.objects.count():03d}'
            print(codeFournisseur)
            # Create the Fournisseur instance
            fournisseur = models.Fournisseur(
                acronym=acronym,
                adresse=adresse,
                phone=phone,
                email=email,
                raison_Social=rsocial,
                typefournisseur=typefour,
                fournisseurClient=client,
                fournisseurEtrange=etrange,
                store = CurrentStore
            )           
            # Assuming you have access to the current user
            fournisseur.user = myuser          
            fournisseur.save()            
            return JsonResponse({'message': 'Fournisseur instance created successfully.'})

def supprimerClient(request):
    try:
         # Find the product by reference
        data = json.loads(request.body)
        print(data)
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        user = models.Client.objects.get(id=data["user_id"])
        user.delete()
        return JsonResponse({'message': 'Client Supprimé !'})
    except models.CustomUser.DoesNotExist:
        return JsonResponse({'error': 'Client Non-trouve.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché, car ce client est lié aux autres composants - {}'.format(str(e))})
        
def supprimerFournisseur(request):
    try:
         # Find the product by reference
        data = json.loads(request.body)
        print(data)
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        user = models.Fournisseur.objects.get(id=data["user_id"])
        products_fournis = Product.objects.filter(fournisseur=user.acronym)
        if products_fournis :
           return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché, car ce Fournisseur est lié aux autres composants'})
        else :
          user.delete()
          return JsonResponse({'success': 'Fournisseur Supprimé !'})
    except models.CustomUser.DoesNotExist:
        return JsonResponse({'error': 'Fournisseur Non-trouve.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché, car ce Fournisseur est lié aux autres composants - {}'.format(str(e))})

def supprimerBanque(request):
    try:
         # Find the product by reference
        data = json.loads(request.body)
        print(data)
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        user = models.Banque.objects.get(id=data["user_id"])
        caisses = CompteEntreprise.objects.filter(banque=user)
        if caisses :
           return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché, car ce Banque est lié aux autres composants'})
        else :
          user.delete()
          return JsonResponse({'success': 'Banque Supprimé !'})
    except models.CustomUser.DoesNotExist:
        return JsonResponse({'error': 'Banque Non-trouve.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché, car ce Banque est lié aux autres composants - {}'.format(str(e))})

def editBanque(request):   
         # Find the product by reference
        data = json.loads(request.body)
        Currentuser = request.user
        myuser = CustomUser.objects.get(username=Currentuser.username)
        store = request.session["store"]
        CurrentStore = models.store.objects.get(pk=store)
        
        if data:
            banque_id = data.get('id', None)
            
            if banque_id:
                # Get the existing Banque instance
                banque_instance = get_object_or_404(models.Banque, id=banque_id)
                
                # Update the fields
                banque_instance.nom = data['nom']
                banque_instance.code = data['code']
                banque_instance.bic = data['bic']
                banque_instance.store = CurrentStore
                
                # Save the changes
                banque_instance.save()

                return JsonResponse({'message': 'Banque instance updated successfully'}, status=200)
            else:
                return JsonResponse({'error': 'Banque id not provided in formData'}, status=400)
        else:
            return JsonResponse({'error': 'formData not provided'}, status=400)

def editFournisseur(request):   
         # Find the product by reference
        data = json.loads(request.body)
        Currentuser = request.user
        myuser = CustomUser.objects.get(username=Currentuser.username)
        store = request.session["store"]
        CurrentStore = models.store.objects.get(pk=store)
        
        # Extract data from the JSON object
        acronym = data.get('acronym')
        adresse = data.get('adresse')
        phone = data.get('phone')
        email = data.get('email')
        rsocial = data.get('rsocial')
        typefour = data.get('typefour')
        client = data.get('client')
        etrange = data.get('etrange')

        # Get the existing Fournisseur instance by its ID
        fournisseur = models.Fournisseur.objects.get(id=data["user_id"])
        
        # Update the Fournisseur instance with the new data
        fournisseur.acronym = acronym
        fournisseur.adresse = adresse
        fournisseur.phone = phone
        fournisseur.email = email
        fournisseur.raison_Social = rsocial
        fournisseur.typefournisseur = typefour
        fournisseur.fournisseurClient = client
        fournisseur.fournisseurEtrange = etrange
        fournisseur.store = CurrentStore
        
        # Assuming you have access to the current user
        fournisseur.user = myuser
        
        # Save the changes
        fournisseur.save()
        
        return JsonResponse({'message': 'Fournisseur instance updated successfully.'})

def editClient(request):
        # Find the product by reference
        data = json.loads(request.body)
        Currentuser = request.user
        myuser = CustomUser.objects.get(username=Currentuser.username)
        store = request.session["store"]
        CurrentStore = models.store.objects.get(pk=store)
        typeClient = models.typeClient.objects.get(id=data['catclient'])

        # Get the existing client instance by its ID
        client_instance = models.Client.objects.get(id=data["user_id"])

        # Update the client instance with the new data
        client_instance.name = data['nomClient']
        client_instance.adresse = data['adresse']
        client_instance.phone = data['phone']
        client_instance.email = data['email']
        client_instance.registreCommerce = data['regcom']
        client_instance.Nif = data['nif']
        client_instance.solde = data['solde']
        client_instance.Nis = data['nis']
        client_instance.num_article = data['numarticle']
        client_instance.region_client = data['region']
        if 'valide' in data:
            client_instance.valide = data['valide'] == 'true'
        client_instance.categorie_client = typeClient
        if 'clientuser' in data :
            newUser = CustomUser.objects.get(username = data['clientuser'])
            client_instance.user = newUser

        # Save the changes
        client_instance.save()

        return JsonResponse({'message': 'Client instance updated successfully'})

def VerifyClient(request):
        data = json.loads(request.body)
        user = request.user
        # Verify if the provided password matches the current user's password
        if user.check_password(data["password"]):
            client = models.Client.objects.filter(id=data["idclient"]).first()
            client.valide=True
            client.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False})

class FournisseursDetailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "tiers/fournisseurs_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        print('hello',self.request.session.get('permissions', []))
        return 'tiers.can_see_fournisseurs' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess')) 
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        store = self.request.session["store"]
        CurrentStore = models.store.objects.get(pk=store)
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        if(myuser.role =='manager'):
         print(CurrentStore)        
         clients_list = models.Fournisseur.objects.filter(store=CurrentStore)
         clients=[]
         for cl in clients_list:                        
            cl_dict={
                "id":cl.id,
               "acronym": cl.acronym,
               "adresse": cl.adresse,
               "phone":cl.phone,
               "email": cl.email,
               "etrange":cl.fournisseurEtrange,
               "raison_Social": cl.raison_Social,
               "typefournisseur" : cl.typefournisseur             
              }
            clients.append(cl_dict)
            context["clients"]=clients       
        return context  

class ClientAddView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "tiers/addClient.html"
    login_url = 'home'
    raise_exception = True  # Raise a PermissionDenied exception

    def test_func(self):
        # Custom test function for permission
        return (
            'tiers.can_see_clients' in self.request.session.get('permissions', []) or
            self.request.session["role"] == "Veille Concurentielle" or
            self.request.session["username"] == "fares"
        )

    def handle_no_permission(self):
        # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        # Context for the template
        context = super().get_context_data(**kwargs)
        store_id = self.request.session["store"]
        current_store = store.objects.get(pk=store_id)
        types_clients = typeClient.objects.filter(store=current_store)
        context['types_clients'] = types_clients
        users_bills = CustomUser.objects.filter(EmployeeAt=current_store)
        context["users"] = users_bills
        return context

    def post(self, request, *args, **kwargs):
        # Capture errors in a list to return them if needed
        errors = []
        # Validate fields
        name = request.POST.get('name', '').strip()
        if not name:
            errors.append(_('Name is required'))

        region = request.POST.get('region', '').strip()
        address = request.POST.get('address', '').strip()
        phone = request.POST.get('phone', '').strip()
        
        email = request.POST.get('email', '').strip()
        nai=''  
        naidocument=''
        nif=''
        nifdocument=''
        nis=''
        nisdocument=''
        regcom=''
        regcomdocument=''
        if email:
            try:
                validate_email(email)
            except ValidationError:
                errors.append(_('Invalid email address'))
        catclient = request.POST.get('catclient', '').strip()
        if not catclient:
            errors.append(_('Categorie de client est requise!'))
            
        # if catclient != '1' and catclient != '9' :
        nai = request.POST.get('nai', '').strip()
        #   if nai == '':
        #       errors.append(_('Nai est requis pour les clients revendeurs!'))
          
        naidocument = request.FILES.get('naiDoc')
        #   print(naidocument)
        #   if  not naidocument:
        #       print('noaidocument')
        #       errors.append(_('Document NAI est requis pour les clients revendeurs!'))
          
        nif = request.POST.get('nif', '').strip()
        #   if not nif:
        #       errors.append(_('Nif est requis pour les clients revendeurs!'))
          
        nifdocument = request.FILES.get('nifDoc')
        #   if not nifdocument:
        #       errors.append(_('Document Nif est requis pour les clients revendeurs!'))
              
        nis = request.POST.get('nis', '').strip()
        #   nisdocument = request.FILES.get('nisDoc')
          
        regcom = request.POST.get('regcom', '').strip()
        if regcom == '':
            if catclient != '1' and catclient != '9':
             errors.append(_('Numero du Registre de Commerce est requis pour les clients revendeurs!'))

        regcomdocument = request.FILES.get('regcomDoc')
        #   if not regcomdocument:
        #       errors.append(_('Document du Registre de Commerce est requis pour les clients revendeurs!'))

        

        solde = request.POST.get('solde', 0)

        clientSource = request.POST.get('clientSource', '').strip()

        # Check if client already exists based on conditions
        current_store = store.objects.get(pk=self.request.session["store"])
        typeClientObj = typeClient.objects.get(id=catclient)
        
        existing_client = None
        if catclient == '1' or catclient == '9':
            existing_client = models.Client.objects.filter(
                Q(name=name) & Q(store=current_store)
            ).first()
        else:
          if nif != '':
            existing_client = models.Client.objects.filter(
                Q(Nif=nif) & Q(store=current_store) & Q(name=name)
            ).first()

        if existing_client:
            errors.append(_(f"Client '{name}' avec NIF '{nif}' déjà existant!"))

        if errors :
            return render(request, 'tiers/addClient.html', context={'errors':errors}) 

        # If all validations pass
        current_user = self.request.user
        user_for_client = CustomUser.objects.get(username=current_user.username) if self.request.session["role"] != 'MARKETING' else CustomUser.objects.get(username=clientSource)
        valide = True
        if current_store.id == 1:
          valide =  catclient == '1'  
        client_instance = models.Client(
            name=name,
            adresse=address,
            phone=phone,
            email=email,
            registreCommerce=regcom or '',
            RCDoc=regcomdocument or '',
            Nif=nif or '',
            NifDoc=nifdocument or '',
            AIDoc=naidocument or '',
            Nis=nis or '',
            NisDoc=nisdocument or '',
            num_article = nai,
            region_client=region,
            categorie_client=typeClientObj,
            solde=solde or 0,
            valide= valide,
            sourceClient=self.request.session["role"],
            store=current_store,
            user=user_for_client
        )

        client_instance.save()
        if catclient == '1' or catclient == '9':
            etatProspect = 'confirme'
        else:
            etatProspect = 'en-negociation'    
        source = request.POST.get('source', '').strip()
        if etatProspect : 
            models.ProspectionClient.objects.create(
                client = client_instance,
                SourceClient= source,
                etatProspection = etatProspect
            )

        return redirect('customers')

class ClientsDetailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "tiers/customers_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        print('hello',self.request.session.get('permissions', []))
        return 'tiers.can_see_clients' in self.request.session.get('permissions', []) or self.request.session["role"] == "Veille Concurentielle" or self.request.session["username"] == "fares"

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess')) 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Define the model for which you want to create custom permissions
        store_id = self.request.session["store"]
        CurrentStore = models.store.objects.get(pk=store_id)
        Currentuser = self.request.user
        myuser = CustomUser.objects.get(username=Currentuser.username)
        if(myuser.role =='manager' or myuser.role == 'DIRECTEUR EXECUTIF' or myuser.username == 'ziad' or myuser.username == 'fares'):      
         clients_list = models.Client.objects.filter(store=CurrentStore).order_by('-id')
         clients=[]
         for cl in clients_list:
            cl_dict={
               "client_id":cl.pk,
               "client_name" :cl.name,
               "client_address":cl.adresse,
               "client_phone" : cl.phone,      
               "client_mail":cl.email,
               "client_nif":cl.Nif,
               "client_nis":cl.Nis,
               "solde": float(cl.solde),
               "ca": float(cl.total_amount),
               "remain": float(cl.remaining_amount),
               "client_narticle":cl.num_article,
               "client_region":cl.region_client,
               "client_type":cl.categorie_client.type_desc,
               "source":cl.sourceClient,
               "client_typeid":cl.categorie_client.id,
               "NisDocument":cl.getNisDoc,
               "NifDocument":cl.getNifDoc,
               "AIDocument":cl.getAIDoc,
               "RCDocument":cl.getRCDoc,
               "client_registreComm": cl.registreCommerce,  
               "valide": cl.getEtatClient,            
               "client_user": cl.user.username,                     
              }
            clients.append(cl_dict)
            context["clients"]=clients
        elif myuser.role == 'MARKETING' :
          clientsList = models.Client.objects.filter(sourceClient='MARKETING').order_by('-id')
          clients=[]
          for cl in clientsList:
             cl_dict={
               "client_id":cl.pk,
               "client_name" :cl.name,
               "client_address":cl.adresse,
               "client_phone" : cl.phone,      
               "client_mail":cl.email,
               "client_nif":cl.Nif,
               "client_nis":cl.Nis,
               "solde": float(cl.solde),
               "ca": float(cl.total_amount),
               "remain": float(cl.remaining_amount),
               "client_narticle":cl.num_article,
               "client_region":cl.region_client,
               "client_type":cl.categorie_client.type_desc,
               "client_registreComm": cl.registreCommerce,
               "valide": 'true' if cl.valide else 'false',  
               "client_user": cl.user.username,                     
              }
             clients.append(cl_dict)
             context["clients"]=clients
        else:
          clientsList = models.Client.objects.filter(user=Currentuser).order_by('-id')
          clients=[]
          for cl in clientsList:
             cl_dict={
               "client_id":cl.pk,
               "client_name" :cl.name,
               "client_address":cl.adresse,
               "client_phone" : cl.phone,      
               "client_mail":cl.email,
               "client_nif":cl.Nif,
               "client_nis":cl.Nis,
               "solde": float(cl.solde),
               "ca": float(cl.total_amount),
               "remain": float(cl.remaining_amount),
               "client_narticle":cl.num_article,
               "client_region":cl.region_client,
               "client_type":cl.categorie_client.type_desc,
               "client_registreComm": cl.registreCommerce, 
               "valide": 'true' if cl.valide else 'false',  
               "client_user": cl.user.username,                     
              }
             clients.append(cl_dict)
             context["clients"]=clients
        types_clients=typeClient.objects.filter(store=CurrentStore)
        context['types_clients']=  types_clients
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
        if dataInvoice:
          Currentuser = self.request.user
          myuser  = CustomUser.objects.get(username=Currentuser.username)
          Currentstore = self.request.session["store"]
          my_store= models.store.objects.get(pk=Currentstore)
          typeClient = models.typeClient.objects.get(id =dataInvoice['catclient'])
          existing_client = models.Client.objects.filter(
                name=dataInvoice['nomClient'],
                store=my_store
            ).first()

          if existing_client:
                return JsonResponse({
                    'message': f"Client '{dataInvoice['nomClient']}' Existe déjâ!."
                })
          if self.request.session["role"] == 'MARKETING':
             myuser = CustomUser.objects.get(username=dataInvoice["clientuser"])   
             
          client_instance = models.Client(
            name=dataInvoice['nomClient'],
            adresse=dataInvoice['adresse'],
            phone=dataInvoice['phone'],
            email=dataInvoice['email'],
            registreCommerce=dataInvoice['regcom'],
            Nif = dataInvoice['nif'],
            Nis = dataInvoice['nis'],
            solde = dataInvoice['solde'],
            sourceClient = self.request.session["role"],
            num_article=dataInvoice['numarticle'],
            region_client = dataInvoice['region'],
            categorie_client=typeClient,
            store = my_store,
            user=myuser
          )
          client_instance.save()
        return JsonResponse({'message': "Client Ajouté!"})
    
class ClientsProspectionView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "tiers/customers_prospection.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        return 'tiers.can_see_clients' in self.request.session.get('permissions', []) or self.request.session["role"] == "Veille Concurentielle" or self.request.session["username"] == "fares"

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess')) 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        store_id = self.request.session["store"]
        CurrentStore = models.store.objects.get(pk=store_id)
        Currentuser = self.request.user
        clients_list = models.Client.objects.filter(store=CurrentStore).order_by('-id')
        clients=[]
        for cl in clients_list:
            dernier_tentative = {}
            if cl.ma_prospection.last() is not None:
                dernier_tentative = cl.ma_prospection.last().getLastTentative
                print(dernier_tentative['user'])
            else:                
                dernier_tentative = {
                    'user': cl.user.username,
                    'dateTime': '',
                    'etat': cl.getEtatClient,
                }
            cl_dict={
                "client_id":cl.pk,
                "client_name" :cl.name,
                "client_address":cl.adresse,
                "client_phone" : cl.phone,      
                "client_mail":cl.email,           
                "client_user": cl.user.username,  
                "client_type":cl.categorie_client.type_desc,
                "etatProspection": cl.getEtatClient,
                'dernierTentativeUser': dernier_tentative["user"],                  
                'dernierTentativedateTime': dernier_tentative["dateTime"] or '',                  
                'dernierTentativeetat': dernier_tentative["etat"],                  
            }
            clients.append(cl_dict)
        context["clients"]=clients       
        types_clients=typeClient.objects.filter(store=CurrentStore)
        context['types_clients']=  types_clients
        users_bills = CustomUser.objects.filter(EmployeeAt=CurrentStore)
        context["users"]=users_bills
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData', '')
        if dataInvoice:
          Currentuser = self.request.user
          myuser  = CustomUser.objects.get(username=Currentuser.username)
          Currentstore = self.request.session["store"]
          my_store= models.store.objects.get(pk=Currentstore)
          ClientObj = models.Client.objects.get(id =dataInvoice['id'])
          prospection = None
          if len(ClientObj.ma_prospection.all()) > 0:
            propspection = ClientObj.ma_prospection.last()
          client_tentative = models.Tentatives.objects.create(
            propspection = ClientObj.ma_prospection.last(),
            dateDebutTentative = dataInvoice['datedeb'],
            dateFinTentative = dataInvoice['datedeb'],
            MoyenContact = dataInvoice['moyencontact'],
            user=myuser
          )
          if 'operation' in dataInvoice:
            if dataInvoice['operation'] == 'add':
                if propspection:
                    propspection.etatProspection = 'en-negociation'
                    propspection.save()
            elif dataInvoice['operation'] == 'finish':  
                    propspection.etatProspection = dataInvoice['etatProspect']
                    ClientObj.user = myuser
                    ClientObj.save()
                    propspection.save()
        return JsonResponse({'message': "Tentative Ajouté!"})

class BanquesView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "tiers/banque_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        print('hello',self.request.session.get('permissions', []))
        return 'tiers.can_see_banques' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess')) 
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        store = self.request.session["store"]
        CurrentStore = models.store.objects.get(pk=store)
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        if(myuser.role =='manager'):
          banques= models.Banque.objects.filter(store=CurrentStore)
          context["banques"]=banques
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
          
          banque_instance = models.Banque(
            nom=dataInvoice['nom'],
            code=dataInvoice['code'],
            bic=dataInvoice['bic'],
            actif=actif,
            store = my_store,
          )
          banque_instance.save()
        return JsonResponse({'message': "Banque Added successfully."})

class AgenceBancairesView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "tiers/agences_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        print('hello',self.request.session.get('permissions', []))
        return 'tiers.can_see_agences' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess')) 
     
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        store = self.request.session["store"]
        CurrentStore = models.store.objects.get(pk=store)
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        if(myuser.role =='manager'):
          banques= models.Banque.objects.filter(store=CurrentStore)
          agences= models.Agence.objects.filter(store=CurrentStore)
          context["banques"]=banques
          context["agences"]=agences
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
          store = self.request.session["store"]
          CurrentStore = models.store.objects.get(pk=store)
          mybanque = models.Banque.objects.get(pk=dataInvoice["banque"])
          agence_instance = models.Agence(
            banque=mybanque,
            code=dataInvoice['code'],
            adresse=dataInvoice['adresse'],
            actif=actif,
            store = CurrentStore
          )
          agence_instance.save()
        return JsonResponse({'message': "Agence Added successfully."})

class ComptesBancairesView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "tiers/compteBancaire_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception

    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        print('hello',self.request.session.get('permissions', []))
        return 'tiers.can_see_comptesBancaire' in self.request.session.get('permissions', [])

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess')) 
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        store = self.request.session["store"]
        CurrentStore = models.store.objects.get(pk=store)
        Currentuser = self.request.user
        myuser  = CustomUser.objects.get(username=Currentuser.username)
        if(myuser.role =='manager'):
          banques= models.Banque.objects.filter(store=CurrentStore)
          agences= models.Agence.objects.filter(store=CurrentStore)
          clients = models.Client.objects.filter(store=CurrentStore)
          context["clients"]=clients
          context["banques"]=banques
          context["agences"]=agences
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
          store = self.request.session["store"]
          CurrentStore = models.store.objects.get(pk=store)
          mybanque = models.Banque.objects.get(pk=dataInvoice["banque"])
          agence_instance = models.Agence(
            banque=mybanque,
            code=dataInvoice['code'],
            adresse=dataInvoice['adresse'],
            actif=actif,
            store = CurrentStore
          )
          agence_instance.save()
        return JsonResponse({'message': "Agence Added successfully."})

# class ClientDetailView(TemplateView):
#     template_name = "tiers/client_details.html"

#     @method_decorator(login_required)
#     def dispatch(self, *args, **kwargs):
#         return super().dispatch(*args, **kwargs)  
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         client_id=self.kwargs.get('client_id')
#         Currentuser = self.request.user
#         myuser = CustomUser.objects.get(username=Currentuser.username)
#         cl= models.Client.objects.get(pk=client_id)
#         client_bons = cl.client_bonS.all()
#         total_CA= 0
#         totals_by_date = defaultdict(float)
#         for bon in client_bons:
#               total_CA += bon.totalPrice              
#               totals_by_date[bon.dateBon] += bon.totalPrice
#             # Convert the dictionary to lists for Plotly
#         dates = list(totals_by_date.keys())
#         total_prices = list(totals_by_date.values())         
#         # Create a bar chart using Plotly Express
#         fig = go.Figure(data=[go.Bar(x=dates, y=total_prices)])
#         plot_div = fig.to_html(full_html=False)    
#         cl_dict={
#                  "client_id":cl.pk,
#                  "client_name" :cl.name,
#                  "client_address":cl.adresse,
#                  "client_phone" : cl.phone,      
#                  "client_mail":cl.email,
#                  "client_type":cl.categorie_client,
#                  "client_registreComm": cl.registreCommerce,   
#                  "client_ca":total_CA,
#                  "client_solde":float(cl.solde),
#                  'ca_chart':plot_div,           
#                "client_user": cl.user.username,                     
#               }
#         print(cl_dict)
#         context["client"]=cl_dict   
#         return context