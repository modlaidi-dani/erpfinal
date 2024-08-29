import pytz
from django.shortcuts import render
from django.shortcuts import render
from django.views.generic.base import TemplateView
from django.http import Http404, JsonResponse
import json
from django.db import transaction,  IntegrityError
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from users.models import CustomUser
from clientInfo.models import store
from produits.models import Category, Product
from tiers.models import Fournisseur, Client
from . import models
from ventes.models import BonSortie, ProduitsEnBonSortie, AvoirVente, DemandeTransfert
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
from comptoire.models import pointVente, ProduitsEnBonComptoir
from collections import defaultdict
from notifications.signals import notify
from django.db.models import Max
from django.utils import timezone
from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from decimal import Decimal
from collections import defaultdict
from datetime import datetime, time

from users.models import MyLogEntry


def importPointage(request):
    data = json.loads(request.body)
    list_pointage = data['pointage']
    if len(list_pointage) > 0:
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        for point in list_pointage:
            name = point['name']
            name = name.lower()
            if name == 'abderahmene':
                name = 'abderahmane'
            elif name == 'mohameddib':
                name = 'mohamed'
            salarie_instance = models.Salarie.objects.filter(nom__icontains=name+' ').first()
            if salarie_instance is not None :
                models.Pointage.objects.create(
                    salarie = salarie_instance,
                    date = datetime.strptime(point["date"], '%d-%m-%Y').strftime('%Y-%m-%d'),
                    temps_arrive =datetime.strptime(point['tems_arrive'], '%H:%M:%S').time(),
                    temps_depart  = datetime.strptime(point['tems_depart'], '%H:%M:%S').time(),
                )
                
            else:
                continue
        return JsonResponse({'Message':f'Pointage Importé!'})      
    else:
        return JsonResponse({'Message':'Erreur: Ajout Fichier Vide'})    

def deleteRequete(request):
    try:
         # Find the product by reference
        data = json.loads(request.body)
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        user = models.RequeteSalarie.objects.get(id=data["user_id"])
        user.delete()
        return JsonResponse({'success': True})
    except models.Absence.DoesNotExist:
        return JsonResponse({'error': 'Elément Non-trouve.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché - {}'.format(str(e))}) 
        
def editRequete(request):
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
                req_ins = models.RequeteSalarie.objects.get(id = cloture_id)
                if req_ins:
                    if myuser.role == "DIRECTEUR EXECUTIF" or myuser.role == "manager":
                        req_ins.reponse = data["reponse"]
                        req_ins.datereponse = datetime.now()
                        req_ins.save()
                    else: 
                        # Update the attributes
                        req_ins.objet = data["objet"]
                        req_ins.destinataire = data["destinataire"]
                        req_ins.message =  data["message"]

                        req_ins.save()
                return JsonResponse({'message': 'Informations du requete Modifié.'})
          except models.Absence.DoesNotExist:
            return JsonResponse({'error': 'Informations Ne peuvent pas être modifié.'})
        return JsonResponse({'error': 'Re-essayer S il vous plait.'})
        
def DeleteArchives(request):
    data = json.loads(request.body)
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    liste_id = data["liste_ids"]
    for id_bon in liste_id:
        bon_c = models.BoiteArchive.objects.get(id=id_bon)
        bon_c.delete()
    return JsonResponse({'message': "Eléments Supprimé !"})
    
def editPointage(request):
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
                salarie_instance = models.Pointage.objects.get(id=cloture_id)
                salarie_instance.temps_arrive = data.get('tpsarr', salarie_instance.temps_arrive)
                salarie_instance.temps_depart = data.get('tpsdep', salarie_instance.temps_depart)
                # Save the changes
                salarie_instance.save()
                return JsonResponse({'message': 'Informations du Salarié Modifié.'})
          except models.AffectationCaisse.DoesNotExist:
            return JsonResponse({'error': 'Informations Ne peuvent pas être modifié.'})
        return JsonResponse({'error': 'Re-essayer S il vous plait.'})

class DecisionNomination(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "gestionRH/decisioon_nomination.html"
    login_url = 'home' 
    raise_exception = True  

    def test_func(self):
        return  self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF" or  self.request.session["role"] == "assistante"

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess')) 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Define the model for which you want to create custom permissions
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        bill_id=self.kwargs.get('id_salarie')
        
        cl = models.Salarie.objects.get(id=bill_id)
        cl_dict={
                "client_id":cl.id,
                "name" :cl.nom,
                "cout_heure":float(cl.cout_heure),
                "ccp": cl.ccp,
                "association": cl.association,
                "email" : cl.email,      
                "fonction":cl.fonction,
                "nomarabe"  :cl.nomarabe,
                "fonctionarabe" :cl.fonctionarabe,
                "num_assurancesocial" :cl.num_assurancesocial,
                "datenaiss" :cl.datenaiss.date().strftime('%Y-%m-%d'),
                "lieu_naissance" :cl.lieu_naissance,
                "lieu_naissancearabe" :cl.lieu_naissancearabe,
                "echellon" :cl.echellon,
                "degre" :cl.degre,
                "phone":cl.phone,
                "actif":'true' if cl.actif else 'false',
                'salaire': round(float(cl.salaire),0),
                'prime_espece': float(cl.prime_espece),
        }
        context["salarie"]= cl_dict
        return context  
        
def VerifyHeureSup(request):
        data = json.loads(request.body)
        print(data)
        user = request.user
        # Verify if the provided password matches the current user's password
        if user.check_password(data["password"]):
            print('true')
            reglement = models.HeureSup.objects.filter(id=data["idheure"]).first()
            reglement.valide=True
            reglement.save()
            store_id = request.session["store"]
            CurrentStore = store.objects.get(pk=store_id)
            myuser= CustomUser.objects.get(username=user.username)
            current_timestamp = datetime.now()
            logs_saving = MyLogEntry.objects.create(
                author= myuser,
                description= f' A Valider l\'Heure Sup Numero  n°=  {data["idheure"]} ',
                timestamp = current_timestamp.strftime("%d/%m/%Y at %H:%Mh"),
                store  = CurrentStore
            )
            return JsonResponse({'success': True})
        else:
            print('false')
            return JsonResponse({'success': False})
        
def deleteSalarie(request):
    try:
         # Find the product by reference
        data = json.loads(request.body)

        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        user = models.Salarie.objects.get(id=data["user_id"])
        user.delete()
        return JsonResponse({'success': True})
    except models.Salarie.DoesNotExist:
        return JsonResponse({'error': 'Elément Non-trouve.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché - {}'.format(str(e))}) 
    
def deleteContrat(request):
    try:
         # Find the product by reference
        data = json.loads(request.body)

        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        user = models.Contrat.objects.get(id=data["user_id"])
        user.delete()
        return JsonResponse({'success': True})
    except models.Salarie.DoesNotExist:
        return JsonResponse({'error': 'Elément Non-trouve.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché - {}'.format(str(e))}) 

def deleteAbsence(request):
    try:
         # Find the product by reference
        data = json.loads(request.body)

        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        user = models.Absence.objects.get(id=data["user_id"])
        user.delete()
        return JsonResponse({'success': True})
    except models.Absence.DoesNotExist:
        return JsonResponse({'error': 'Elément Non-trouve.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché - {}'.format(str(e))}) 
    
def deletePrixSocial(request):
    try:
         # Find the product by reference
        data = json.loads(request.body)

        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        user = models.PrixSocial.objects.get(id=data["user_id"])
        user.delete()
        return JsonResponse({'success': True})
    except models.Absence.DoesNotExist:
        return JsonResponse({'error': 'Elément Non-trouve.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché - {}'.format(str(e))}) 
    
def deleteHeureSup(request): 
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    data = json.loads(request.body)
    try:
      # Find the product by reference
      liste_id = data["liste_ids"]
      for id_bon in liste_id:   
        user = models.HeureSup.objects.get(id=id_bon)
        user.delete()
      return JsonResponse({'success': True})
    except models.HeureSup.DoesNotExist:
        return JsonResponse({'error': 'Elément Non-trouve.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché - {}'.format(str(e))}) 
        
def deleteConge(request): 
    store_id = request.session["store"]
    CurrentStore = store.objects.get(pk=store_id)
    data = json.loads(request.body)
    try:
      # Find the product by reference
      liste_id = data["liste_ids"]
      for id_bon in liste_id:   
        user = models.Conge.objects.get(id=id_bon)
        user.delete()
      return JsonResponse({'success': True})
    except models.HeureSup.DoesNotExist:
        return JsonResponse({'error': 'Elément Non-trouve.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché - {}'.format(str(e))}) 
    
def deleteAvance(request): 
    try:
         # Find the product by reference
        data = json.loads(request.body)

        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        user = models.AvanceSalaire.objects.get(id=data["user_id"])
        user.delete()
        return JsonResponse({'success': True})
    except models.AvanceSalaire.DoesNotExist:
        return JsonResponse({'error': 'Elément Non-trouve.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché - {}'.format(str(e))}) 
    
def deletePrime(request): 
    try:
         # Find the product by reference
        data = json.loads(request.body)

        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        user = models.PrimeMotivation.objects.get(id=data["user_id"])
        user.delete()
        return JsonResponse({'success': True})
    except models.AvanceSalaire.DoesNotExist:
        return JsonResponse({'error': 'Elément Non-trouve.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché - {}'.format(str(e))}) 
    
def editSalarie(request):
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
                salarie_instance = models.Salarie.objects.get(id=cloture_id)
                cout_heure = Decimal(data.get('coutH', '0'))
                salaire = Decimal(data.get('salaire', '0'))
                prime_espece = Decimal(data.get('salaireEsp', '0'))

                # Determine the value for the 'actif' field based on the 'status' value
                actif_value = data.get('status', '').lower() == 'true'
                # Update the attributes
                salarie_instance.nom = data.get('name', '')
                salarie_instance.fonction = data.get('fonction', '')
                salarie_instance.nomarabe = data.get('nomarabe', '')
                salarie_instance.fonctionarabe = data.get('fonctionarabe', '')
                salarie_instance.num_assurancesocial = data.get('num_assurancesocial', '')
                salarie_instance.datenaiss = data.get('datenaiss', '')
                salarie_instance.lieu_naissance = data.get('lieu_naissance', '')
                salarie_instance.lieu_naissancearabe = data.get('lieu_naissancearabe', '')
                salarie_instance.echellon = data.get('echellon', '')
                salarie_instance.degre = data.get('degre', '')
                salarie_instance.ccp = data.get('ccp', '')
                salarie_instance.association = data.get('association', '')
                salarie_instance.email = data.get('email', '')
                salarie_instance.phone = data.get('phone', '')
                salarie_instance.cout_heure = cout_heure
                salarie_instance.salaire = salaire
                salarie_instance.prime_espece = prime_espece
                salarie_instance.actif = actif_value
                salarie_instance.dateDebut = data.get('datedeb','')
                salarie_instance.dateEnd = data.get('datefin','')
                # Save the changes
                
                salarie_instance.save()
                if 'reglement' in data and  not actif_value:
                    models.ReglementCompte.objects.create(
                        salarie = salarie_instance,
                        dateSortie = data.get('datefin',''),
                        montant = data.get('reglement')
                    )
                return JsonResponse({'message': 'Informations du Salarié Modifié.'})
          except models.Salarie.DoesNotExist:
            return JsonResponse({'error': 'Informations Ne peuvent pas être modifié.'})
        return JsonResponse({'error': 'Re-essayer S il vous plait.'})
    
def editAbsence(request):
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
                absence_instance = models.Absence.objects.get(id = cloture_id)
                if absence_instance:
                    # Update the attributes
                    absence_instance.date = data["date"]
                    absence_instance.salarie = models.Salarie.objects.get(nom=data["salarie"], store=CurrentStore)
                    absence_instance.motif = data["motif"]
                    absence_instance.nombre_heure = data["nbrHeure"]
                    absence_instance.justifie = True if data["justifie"] == 'true' else False
                    absence_instance.minusSource = data["decision"]

                    absence_instance.save()

                return JsonResponse({'message': 'Informations d\'absence Modifié.'})
          except models.Absence.DoesNotExist:
            return JsonResponse({'error': 'Informations Ne peuvent pas être modifié.'})
        return JsonResponse({'error': 'Re-essayer S il vous plait.'})
        
def editPrixSocial(request):
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
                absence_instance = models.PrixSocial.objects.get(id = cloture_id)
                if absence_instance:
                    # Update the attributes
                    absence_instance.date = data["date"]
                    absence_instance.salarie = models.Salarie.objects.get(nom=data["salarie"], store=CurrentStore)
                    absence_instance.motif = data["motif"]
                    absence_instance.nombre_heure = data["nbrHeure"]
                    absence_instance.justifie = True if data["justifie"] == 'true' else False

                    absence_instance.save()

                return JsonResponse({'message': 'Informations d\'absence Modifié.'})
          except models.AffectationCaisse.DoesNotExist:
            return JsonResponse({'error': 'Informations Ne peuvent pas être modifié.'})
        return JsonResponse({'error': 'Re-essayer S il vous plait.'})
    
def resetPointage(request):
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)   
        try:
            with transaction.atomic():  
                models.Pointage.objects.all().delete()

                return JsonResponse({'message': 'Pointage Ré-initialisé!.'})
        except models.Pointage.DoesNotExist:
            return JsonResponse({'error': 'Informations Ne peuvent pas être modifié.'})

def editHeureSup(request):
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
                heuresup_instance = models.HeureSup.objects.get(id=cloture_id)

                # Update the attributes
                heuresup_instance.nombre_heure = data["tauxHeure"]
                heuresup_instance.datetimedeb = data["datetimedeb"]
                heuresup_instance.datetimeend = data["datetimefin"]
                heuresup_instance.salarie = models.Salarie.objects.get(nom=data["salarie"], store=CurrentStore)
                heuresup_instance.motif = data["motif"]

                # Save the changes
                heuresup_instance.save()
                return JsonResponse({'message': 'Informations d\'Heure Supplémentaire Modifié.'})
          except models.HeureSup.DoesNotExist:
            return JsonResponse({'error': 'Informations Ne peuvent pas être modifié.'})
        return JsonResponse({'error': 'Re-essayer S il vous plait.'})
    
def editContract(request):
     # Find the product by reference
        data = json.loads(request.body)
        Currentuser = request.user
        myuser = CustomUser.objects.get(username=Currentuser.username)
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)   
        cloture_id = data.get('user_id')  # Assuming you have a field for the AffectationCaisse's ID in dataInvoice
        if  cloture_id:
            try:
                salary_depense = models.Contrat.objects.get(numero_contrat=data["numcontrat"])
                salary_depense.salarie = models.Salarie.objects.get(nom=data["salarie"], store=CurrentStore)
                salary_depense.numero_decision_recrutement = data["numero_decision_recrutement"]
                salary_depense.numero_pv_installation = data["numero_pv_installation"]
                salary_depense.datedeb = data["datedeb"]
                salary_depense.datesignature = data["datesignature"]
                salary_depense.datefin = data["datefin"]
                salary_depense.type_contrat = data["type"]
                salary_depense.save()
                return JsonResponse({'message': 'Informations  Modifié.'})
            except models.Contrat.DoesNotExist:
                return JsonResponse({'message': 'Instance with provided contract number does not exist..'})
        else:
            return JsonResponse({'message': 'Try again!'})
    
def editAvance(request):
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
                heuresup_instance = models.AvanceSalaire.objects.get(id=cloture_id)

                # Update the attributes
                heuresup_instance.montant = data["montant"]
                heuresup_instance.date = data["date"]
                heuresup_instance.salarie = models.Salarie.objects.get(nom=data["salarie"], store=CurrentStore)
                heuresup_instance.motif = data["motif"]

                # Save the changes
                heuresup_instance.save()
                return JsonResponse({'message': 'Informations d\'avance Modifié.'})
          except models.AvanceSalaire.DoesNotExist:
            return JsonResponse({'error': 'Informations Ne peuvent pas être modifié.'})
        return JsonResponse({'error': 'Re-essayer S il vous plait.'})
    
def editPrime(request):
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
                heuresup_instance = models.PrimeMotivation.objects.get(id=cloture_id)
                if heuresup_instance.motif.startswith('SANCTION'):
                    salarieObj = models.Salarie.objects.get(nom=data["salarie"], store=CurrentStore)
                    heuresup_instance.date = data["date"]
                    heuresup_instance.salarie = salarieObj
                    montantSanc = Decimal(data["nbrHeure"]) * salarieObj.cout_heure
                    heuresup_instance.montant = montantSanc
                    if data['motif'].startswith('SANCTION'):
                        heuresup_instance.motif = data["motif"]
                    else:
                        heuresup_instance.motif = 'SANCTION - '+data["motif"]
                else:
                    # Update the attributes
                    heuresup_instance.montant = data["montant"]
                    heuresup_instance.date = data["date"]
                    heuresup_instance.salarie = models.Salarie.objects.get(nom=data["salarie"], store=CurrentStore)
                    if heuresup_instance.motif != "fix":
                        heuresup_instance.motif = data["motif"]

                # Save the changes
                heuresup_instance.save()
                return JsonResponse({'message': 'Informations Modifié.'})
          except models.AvanceSalaire.DoesNotExist:
            return JsonResponse({'error': 'Informations Ne peuvent pas être modifié.'})
        return JsonResponse({'error': 'Re-essayer S il vous plait.'})
        
def editPrixSocial(request):
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
                heuresup_instance = models.PrixSocial.objects.get(id=cloture_id)

                # Update the attributes
                heuresup_instance.montanttotal = data["montant"]
                heuresup_instance.date = data["date"]
                heuresup_instance.salarie = models.Salarie.objects.get(nom=data["salarie"], store=CurrentStore)
                heuresup_instance.montantperMonth = data["montantmensuel"]
                heuresup_instance.nombre_months = data["nbr_mois"]
                
                # Save the changes
                heuresup_instance.save()
                return JsonResponse({'message': 'Informations du Prix Social Modifié.'})
          except models.AffectationCaisse.DoesNotExist:
            return JsonResponse({'error': 'Informations Ne peuvent pas être modifié.'})
        return JsonResponse({'error': 'Re-essayer S il vous plait.'})
    
class CalendrierPage(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "gestionRH/charges_calendar.html"
    login_url = 'home' 
    raise_exception = True  

    def test_func(self):
        return  self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF" or  self.request.session["role"] == "assistante"

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess')) 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Define the model for which you want to create custom permissions
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        events = models.Event.objects.all()
        eventList = []
        for ev in events:
            eventList.append({
                "event_title": ev.name,
                "event_date": str(ev.event_date),
                "description": ev.description,
                "period": ev.remember_months,
                "remeberdays": ev.remind_days_before,
            })
        context["events"] = eventList
        return context    
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData', '')
        with transaction.atomic():  
          if dataInvoice:
              models.Event.objects.create(
                 name = dataInvoice["event_title"], 
                 description = dataInvoice["description"],
                 event_date = dataInvoice["event_date"],
                 remember_months = dataInvoice["period"],
                 remind_days_before = dataInvoice["days_remind"],
              )
              return JsonResponse({'message': "Evenement Ajoute."})

class ListeCongesView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "gestionRH/listeConges.html"
    login_url = 'home' 
    raise_exception = True  

    def test_func(self):
        return self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF" or  self.request.session["role"] == "assistante"

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess')) 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Define the model for which you want to create custom permissions
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        Currentuser = self.request.user
        myuser = CustomUser.objects.get(username=Currentuser.username)
        conges_list = models.Conge.objects.all().order_by('-id')
        congeList=[]
        for cl in conges_list:   
            cl_dict={
                "id":cl.id,
                "salarie" :cl.salarie.nom,
                "fontion": cl.salarie.fonction,
                "date":str(cl.dateDebut.date()),  
                "type": cl.type_conge if cl.type_conge is not None else '',
                "dateFin" :  str(cl.dateFin), 
                "nbrJour": (cl.dateFin - cl.dateDebut).days + 1
            }
            congeList.append(cl_dict)
        context["listeconges"]=congeList
        users_salaries =[ {"nom":s.nom, "fonction":s.fonction} for s in models.Salarie.objects.filter(store=CurrentStore)]
        context["salaries"]= users_salaries
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        timezone = pytz.timezone('Africa/Algiers')
        data = json.loads(request.body)
        dataInvoice = data.get('formData', '')
        print(dataInvoice)
        with transaction.atomic():  
          if dataInvoice:
            liste_salaries = dataInvoice["list2"]
            datedeb =  datetime.strptime(dataInvoice["datetimedeb"]+" 00:00:00" , "%Y-%m-%d %H:%M:%S")
            datefin = datetime.strptime(dataInvoice["datetimefin"]+" 00:00:00" , "%Y-%m-%d %H:%M:%S")
            datedeb = timezone.localize(datedeb)
            datefin = timezone.localize(datefin)
            
            for salarie in liste_salaries:
                salarieObject = models.Salarie.objects.filter(nom = salarie["nom"]).first()
                if salarieObject:
                    conge = models.Conge.objects.create(
                        salarie=salarieObject,
                        dateDebut=datedeb,  # Access value using key
                        type_conge = dataInvoice["type_conge"],
                        dateFin=datefin,   # Access value using key
                    )
                else:
                    return JsonResponse({'message': "Salarié Non existant!."})
        return JsonResponse({'message': "Congé Added successfully."})

        
class PageSituationSalarie(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "gestionRH/SituationSalaire.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        return self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF" or  self.request.session["role"] == "assistante"

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        Currentuser = self.request.user
        currentStore= store.objects.get(pk=self.request.session["store"])
        
        all_renumeration = []
        for month in range(1, 13):
            for salary in models.Salarie.objects.all():
                num_heuresup = salary.mes_heure_sup.filter(valide=True, datetimedeb__month=month).aggregate(Sum('nombre_heure'))['nombre_heure__sum'] or 0
                avance_salaire = float(salary.mes_avances_salaire.filter(date__month=month).aggregate(Sum('montant'))['montant__sum'] or 0)
                prix_social = float(salary.current_prix_social(month))              
                jour_retard = salary.get_late_minutes(month) / 480 
                absentdays = len(salary.mes_absences.filter(date__month=month)) - len(salary.mes_absences.filter(justifie = True, date__month=month))
                absenthours = salary.mes_absences.filter(justifie=False, date__month=month).aggregate(Sum('nombre_heure'))['nombre_heure__sum'] or 0
                montantPrime = salary.mes_primesmotivation.filter(motif="fix").aggregate(Sum('montant'))['montant__sum'] or 0
                zero_pointages = salary.mon_pointage.filter(temps_arrive=time(0, 0, 0), date__month=month)
                sanction = salary.mes_primesmotivation.filter(motif__startswith='SANCTION', date__month=month).aggregate(Sum('montant'))['montant__sum'] or 0
                don = salary.mes_primesmotivation.filter(motif__startswith='DON', date__month=month).aggregate(Sum('montant'))['montant__sum'] or 0
                # Initialize a variable to count the absent pointages
                absent_count = 0
                daysnotworked = salary.days_not_worked(month)
                for pointage in zero_pointages:
                    if pointage.date.weekday() != 4 and pointage.date.weekday() != 5:   
                        # Check if there is an absence for the salarie on the same date
                        absence_exists = salary.mes_absences.filter(
                            salarie=pointage.salarie,
                            date=pointage.date.date()  # Extract date from datetime
                        ).exists()
                        
                        # If there's no absence, increment the absent count
                        if not absence_exists:
                            absent_count += 1
                salaireCalculated = 0
                EspeceCalculated = 0
                montantNotWorked = round(daysnotworked * 8 * float(salary.cout_heure),0)
                if  month >= 4 :
                   salaireCalculated = float(salary.salaire) + float(don) - float(jour_retard * 2 * 4 * float(salary.cout_heure)) - float(montantNotWorked) - float(prix_social) - float(absenthours * float(salary.cout_heure)) - float(sanction) 
                   EspeceCalculated = float(salary.prime_espece) + (float(num_heuresup) * float(salary.cout_heure) * 1.25) - float(avance_salaire) + float(montantPrime) - round(daysnotworked * 8 * float(salary.cout_heure),0)
                else:
                   salaireCalculated = float(salary.salaire) - float(prix_social) - float(sanction)  - float(montantNotWorked)
                   EspeceCalculated = float(salary.prime_espece) + (float(num_heuresup) * float(salary.cout_heure) * 1.25) - float(avance_salaire) + float(montantPrime)- float(absenthours * float(salary.cout_heure)) - float(jour_retard * 2 * 4 * float(salary.cout_heure)) - round(daysnotworked * 8 * float(salary.cout_heure),0)
                renum_dict = {
                    'month': month,
                    'nom': salary.nom,
                    'degre': salary.degre,
                    'started': salary.getActifEtat(month),
                    'fonction': salary.fonction,
                    'datenaiss': str(salary.datenaiss.strftime('%Y-%m-%d')),
                    'cout_heure': float(salary.cout_heure),
                    'don': float(don),
                    'social': prix_social,
                    'nombreMinuteRetard': salary.get_late_minutes(month),  # Pass month for filtering
                    'nombreJourR': jour_retard,  
                    'notworkeddays': daysnotworked,
                    'montantNotWorked':montantNotWorked ,
                    'montantPrime': float(montantPrime),
                    'nombreJourN': absent_count,
                    'montant_retard': jour_retard * 2 * 4 * float(salary.cout_heure),  # Pass month for filtering
                    'jourabsent': absentdays,  # Pass month for filtering
                    'montantabsence': absenthours * float(salary.cout_heure),
                    'sanction': float(sanction),
                    'salaire': float(salary.salaire),
                    'espece': float(salary.prime_espece),
                    'salaireCalculated': salaireCalculated,
                    'especeCalculated': EspeceCalculated
                }
                all_renumeration.append(renum_dict)
        context["liste_paie"] = all_renumeration
        return context
        
class RequetesSalarieView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "gestionRH/reqssalarie_page.html"
    login_url = 'home' 
    raise_exception = True  
    def test_func(self):
        return True
    
    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess')) 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Define the model for which you want to create custom permissions
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        Currentuser = self.request.user
        myuser = CustomUser.objects.get(username=Currentuser.username)
        if myuser.role == 'manager' or myuser.role == 'DIRECTEUR EXECUTIF':
            reqs_list = models.RequeteSalarie.objects.filter(store=CurrentStore).order_by('-id')
        else:
            reqs_list = models.RequeteSalarie.objects.filter(store=CurrentStore, user =myuser).order_by('-id')
        reqs=[]
        for cl in reqs_list:   
            cl_dict={
                "id":cl.id,
                "date":str(cl.date.date()),
                "datereponse":str(cl.datereponse.date()),
                "objet" : cl.objet,      
                "message":cl.message,
                "reponse":cl.reponse,
                "valide": 'true' if cl.reponse != "" else 'false',
                "destinataire":cl.destinataire,
                "salarie":cl.user.username,
            }       
            reqs.append(cl_dict)
        context["reqs"]=reqs
        print(reqs)
        users_bills = models.Salarie.objects.filter(store=CurrentStore)
        context["users"]=users_bills
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData', '')
        with transaction.atomic():  
          if dataInvoice:
            Currentuser = self.request.user
            myuser  = CustomUser.objects.get(username=Currentuser.username)
            Currentstore = self.request.session["store"]
            my_store= store.objects.get(pk=Currentstore)
            salary_depense = models.RequeteSalarie.objects.create(
                objet= dataInvoice["objet"],
                destinataire =  dataInvoice["destinataire"],
                message =  dataInvoice["message"],
                user = myuser,
                store = my_store,
            )
            salary_depense.save()
            destinataire = "DIRECTEUR EXECUTIF" if dataInvoice["destinataire"] == 'executif' else 'manager'
            responsable_entrepot = CustomUser.objects.filter(role = destinataire)
            if responsable_entrepot:
                for resp in responsable_entrepot : 
                        notify.send(
                            sender=myuser,
                            recipient=resp,
                            verb=f'vous a envoyé une nouvelle requête! Cliquez Pour la consulter',
                            description=f'/gestionRh/ReqsSalariePage',
                            level=1,
                        )   
        return JsonResponse({'message': "Avance Added successfully."})
        
class AvanceSalaireView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "gestionRH/avancesalaire_page.html"
    login_url = 'home' 
    raise_exception = True  

    def test_func(self):
        return self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF" or  self.request.session["role"] == "assistante"

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess')) 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Define the model for which you want to create custom permissions
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        Currentuser = self.request.user
        myuser = CustomUser.objects.get(username=Currentuser.username)
        clients_list = models.AvanceSalaire.objects.filter(salarie__store=CurrentStore)
        clients=[]
        for cl in clients_list:   
            cl_dict={
                "id":cl.id,
                "date":str(cl.date.date()),
                "salarie" : cl.salarie.nom,      
                "motif":cl.motif,
                "montant":float(cl.montant),
            }
            clients.append(cl_dict)
        context["clients"]=clients
        users_bills = models.Salarie.objects.filter(store=CurrentStore)
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
            print(dataInvoice)
            Currentuser = self.request.user
            myuser  = CustomUser.objects.get(username=Currentuser.username)
            Currentstore = self.request.session["store"]
            my_store= store.objects.get(pk=Currentstore)
            salary_depense = models.AvanceSalaire.objects.create(
                date= dataInvoice["date"],
                salarie = models.Salarie.objects.get(nom = dataInvoice["salarie"], store = my_store),
                motif =  dataInvoice["motif"],
                montant = dataInvoice["montant"]
            )

            salary_depense.save()
        return JsonResponse({'message': "Avance Added successfully."})
    
class PrimeView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "gestionRH/prime_don.html"
    login_url = 'home' 
    raise_exception = True  

    def test_func(self):
        return self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF" 

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess')) 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Define the model for which you want to create custom permissions
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        Currentuser = self.request.user
        myuser = CustomUser.objects.get(username=Currentuser.username)
        clients_list = models.PrimeMotivation.objects.filter(salarie__store=CurrentStore)
        clients=[]
        for cl in clients_list:   
            cl_dict={
                "id":cl.id,
                "date":str(cl.date.date()),
                "salarie" : cl.salarie.nom,      
                "motif":cl.motif,
                "montant":float(cl.montant),
            }
            clients.append(cl_dict)
        context["clients"]=clients
        users_bills = models.Salarie.objects.filter(store=CurrentStore)
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
            print(dataInvoice)
            Currentuser = self.request.user
            myuser  = CustomUser.objects.get(username=Currentuser.username)
            Currentstore = self.request.session["store"]
            my_store= store.objects.get(pk=Currentstore)
            salary_depense = models.PrimeMotivation.objects.create(
                date= dataInvoice["date"],
                salarie = models.Salarie.objects.get(nom = dataInvoice["salarie"], store = my_store),
                motif =  dataInvoice["motif"],
                montant = dataInvoice["montant"]
            )

            salary_depense.save()
        return JsonResponse({'message': "Avance Added successfully."})
    
class PrimeSanctionView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "gestionRH/prime_sanction.html"
    login_url = 'home' 
    raise_exception = True  

    def test_func(self):
        return self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF" 

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess')) 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Define the model for which you want to create custom permissions
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        Currentuser = self.request.user
        myuser = CustomUser.objects.get(username=Currentuser.username)
        clients_list = models.PrimeMotivation.objects.filter(salarie__store=CurrentStore, motif__startswith ="SANCTION - ")
        clients=[]
        for cl in clients_list:   
            cl_dict={
                "id":cl.id,
                "date":str(cl.date.date()),
                "salarie" : cl.salarie.nom,      
                "motif":cl.motif,
                "montant":float(cl.montant),
                "coutheure":float(cl.salarie.cout_heure),
            }
            clients.append(cl_dict)
        context["clients"]=clients
        users_bills = models.Salarie.objects.filter(store=CurrentStore)
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
            print(dataInvoice)
            Currentuser = self.request.user
            myuser  = CustomUser.objects.get(username=Currentuser.username)
            Currentstore = self.request.session["store"]
            my_store= store.objects.get(pk=Currentstore)
            salarieObject = models.Salarie.objects.get(nom = dataInvoice["salarie"], store = my_store)
            montantSanc = Decimal(dataInvoice["nbrHeure"]) * salarieObject.cout_heure
            salary_depense = models.PrimeMotivation.objects.create(
                date= dataInvoice["date"],
                salarie = salarieObject,
                motif =  "SANCTION - "+dataInvoice["motif"],
                montant = montantSanc
            )

            salary_depense.save()
        return JsonResponse({'message': "Mise A Pieds Added successfully."})
    
class PrimeFixView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "gestionRH/prime_fix.html"
    login_url = 'home' 
    raise_exception = True  

    def test_func(self):
        return self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF" 

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess')) 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Define the model for which you want to create custom permissions
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        Currentuser = self.request.user
        myuser = CustomUser.objects.get(username=Currentuser.username)
        clients_list = models.PrimeMotivation.objects.filter(salarie__store=CurrentStore, motif="fix")
        clients=[]
        for cl in clients_list:   
            cl_dict={
                "id":cl.id,
                "date":str(cl.date.date()),
                "salarie" : cl.salarie.nom,      
                "montant":float(cl.montant),
            }
            clients.append(cl_dict)
        context["clients"]=clients
        users_bills = models.Salarie.objects.filter(store=CurrentStore)
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
            print(dataInvoice)
            Currentuser = self.request.user
            myuser  = CustomUser.objects.get(username=Currentuser.username)
            Currentstore = self.request.session["store"]
            my_store= store.objects.get(pk=Currentstore)
            salary_depense = models.PrimeMotivation.objects.create(
                date= dataInvoice["date"],
                salarie = models.Salarie.objects.get(nom = dataInvoice["salarie"], store = my_store),
                motif =  "fix",
                montant = dataInvoice["montant"]
            )

            salary_depense.save()
        return JsonResponse({'message': "Avance Added successfully."})
    
class ReglementComptes(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "gestionRH/reglement_compte.html"
    login_url = 'home' 
    raise_exception = True  

    def test_func(self):
        return self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF" or  self.request.session["role"] == "assistante"

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess')) 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        Currentuser = self.request.user
        myuser = CustomUser.objects.get(username=Currentuser.username)
        clients_list = models.ReglementCompte.objects.filter(salarie__store=CurrentStore)
        clients=[]
        for cl in clients_list:   
            cl_dict={
                "id":cl.id,
                "datedeb":str(cl.salarie.dateDebut),
                "datefin": str(cl.dateSortie.date()),
                "salarie" : cl.salarie.nom,      
                "note":cl.note,
                "montant":float(cl.montant),           
            }
            clients.append(cl_dict)
        context["clients"]=clients
        users_bills = models.Salarie.objects.filter(store=CurrentStore)
        context["users"]=users_bills
        return context

class PrixSocialView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "gestionRH/prixsocial_page.html"
    login_url = 'home' 
    raise_exception = True  

    def test_func(self):
        return self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF" or  self.request.session["role"] == "assistante"

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess')) 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        Currentuser = self.request.user
        myuser = CustomUser.objects.get(username=Currentuser.username)
        clients_list = models.PrixSocial.objects.filter(salarie__store=CurrentStore)
        clients=[]
        for cl in clients_list:   
            cl_dict={
                "id":cl.id,
                "date":str(cl.date.date()),
                "datefin": str(cl.end_month),
                "salarie" : cl.salarie.nom,      
                "motif":cl.motif,
                "montanttotal":float(cl.montanttotal),
                "montantperMonth":float(cl.montantperMonth),
                "nombre_months": int(cl.nombre_months)
            }
            clients.append(cl_dict)
        context["clients"]=clients
        users_bills = models.Salarie.objects.filter(store=CurrentStore)
        context["users"]=users_bills
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData', '')
        with transaction.atomic():  
          if dataInvoice:
            Currentuser = self.request.user
            myuser  = CustomUser.objects.get(username=Currentuser.username)
            Currentstore = self.request.session["store"]
            my_store= store.objects.get(pk=Currentstore)
            salary_depense = models.PrixSocial.objects.create(
                date= dataInvoice["date"],
                salarie = models.Salarie.objects.get(nom = dataInvoice["salarie"], store = my_store),
                motif =  dataInvoice["motif"],
                montanttotal = dataInvoice["montant"],
                montantperMonth  = dataInvoice["montantmensuel"],
                nombre_months = dataInvoice["nbr_mois"]
            )
            salary_depense.save()
        return JsonResponse({'message': "Prix Social Added successfully."})
    
class ContractPage(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "gestionRH/contracts_page.html"
    login_url = 'home' 
    raise_exception = True  

    def test_func(self):
        return self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF" or  self.request.session["role"] == "assistante"

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess')) 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Define the model for which you want to create custom permissions
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        Currentuser = self.request.user
        myuser = CustomUser.objects.get(username=Currentuser.username)
        clients_list = models.Contrat.objects.filter(salarie__store=CurrentStore)
        clients=[]
        for cl in clients_list:   
            cl_dict={
                "id":cl.id,
                "numcontrat" :cl.numero_contrat,
                "datedeb":str(cl.datedeb.date()),
                "datefin":str(cl.datefin.date()),
                "datesignature":str(cl.datesignature),
                "numero_decision_recrutement": cl.numero_decision_recrutement,
                "numero_pv_installation" :  cl.numero_pv_installation, 
                "salarie" : cl.salarie.nom,      
                "type_contrat":cl.type_contrat,
            }
            clients.append(cl_dict)
        context["clients"]=clients
        users_bills = models.Salarie.objects.filter(store=CurrentStore)
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
            print(dataInvoice)
            Currentuser = self.request.user
            myuser  = CustomUser.objects.get(username=Currentuser.username)
            Currentstore = self.request.session["store"]
            my_store= store.objects.get(pk=Currentstore)


            salary_depense = models.Contrat.objects.create(
                salarie = models.Salarie.objects.get(nom = dataInvoice["salarie"], store = my_store),
                numero_contrat = dataInvoice["numcontrat"],
                numero_decision_recrutement = dataInvoice["numero_decision_recrutement"],
                numero_pv_installation = dataInvoice["numero_pv_installation"],
                datedeb = dataInvoice["datedeb"],
                datesignature = dataInvoice["datesignature"],
                datefin = dataInvoice["datefin"],
                type_contrat = dataInvoice["type"]
            )
                
            salary_depense.save() 
        return JsonResponse({'message': "Contrat Added successfully."})
    
class HeureSuppView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "gestionRH/heuresup_page.html"
    login_url = 'home' 
    raise_exception = True  

    def test_func(self):
        return self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF" or  self.request.session["role"] == "assistante"

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess')) 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Define the model for which you want to create custom permissions
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        Currentuser = self.request.user
        myuser = CustomUser.objects.get(username=Currentuser.username)
        clients_list = models.HeureSup.objects.filter(store=CurrentStore).order_by('-date')
        clients=[]
        for cl in clients_list:   
            cl_dict={
                "id":cl.id,
                "nbr_heure" :cl.nombre_heure,
                "date":str(cl.date.date()),
                "datetimedeb": str(cl.datetimedeb),
                "datetimeend" :  str(cl.datetimeend), 
                "salarie" : cl.salarie.nom,      
                "motif":cl.motif,
                "valide":'true' if cl.valide else 'false',
                "user":cl.user.username,
            }
            clients.append(cl_dict)
        context["clients"]=clients
        users_bills = models.Salarie.objects.filter(store=CurrentStore)
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
            print(dataInvoice)
            Currentuser = self.request.user
            myuser  = CustomUser.objects.get(username=Currentuser.username)
            Currentstore = self.request.session["store"]
            my_store= store.objects.get(pk=Currentstore)
            valide = False
            if myuser.role == 'DIRECTEUR EXECUTIF':
                valide = True
            salary_depense = models.HeureSup.objects.create(
               nombre_heure = dataInvoice["tauxHeure"],
                datetimedeb = dataInvoice["datetimedeb"],
                datetimeend = dataInvoice["datetimefin"],
                salarie = models.Salarie.objects.get(nom = dataInvoice["salarie"], store = my_store),
                motif =  dataInvoice["motif"],
                valide = valide,
                user = myuser,
                store = my_store
            )
                
            salary_depense.save()
            responsable_entrepot = CustomUser.objects.filter(role ="DIRECTEUR EXECUTIF")
            if responsable_entrepot:
                for resp in responsable_entrepot : 
                        notify.send(
                            sender=myuser,
                            recipient=resp,
                            verb=f'a ajouté une nouvelle heure supplémentaire pour {dataInvoice["salarie"]} , Veuillez valider',
                            description=f'/gestionRh/HeureSupPage',
                            level=1,
                        )   
        return JsonResponse({'message': "Client Added successfully."})
    
class AbsentDays(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "gestionRH/absentdays_page.html"
    login_url = 'home' 
    raise_exception = True  

    def test_func(self):
        return self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF" or  self.request.session["role"] == "assistante"

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess')) 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Define the model for which you want to create custom permissions
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        Currentuser = self.request.user
        myuser = CustomUser.objects.get(username=Currentuser.username)
        clients_list = models.Absence.objects.filter(store=CurrentStore).order_by('-id')
        clients=[]
        for cl in clients_list:   
            cl_dict={
                "id":cl.id,
                "date":str(cl.date.date()),
                "salarie" : cl.salarie.nom, 
                "nbrHeure" : cl.nombre_heure,     
                "motif":cl.motif,
                "justifie":'true' if cl.justifie else 'false',
                "decision": cl.minusSource,
                "user":cl.user.username,
            }
            clients.append(cl_dict)
        context["clients"]=clients
        users_bills = models.Salarie.objects.filter(store=CurrentStore)
        context["users"]=users_bills
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData', '')
        with transaction.atomic():  
          if dataInvoice:
            Currentuser = self.request.user
            myuser  = CustomUser.objects.get(username=Currentuser.username)
            Currentstore = self.request.session["store"]
            my_store= store.objects.get(pk=Currentstore)
            salary_depense = models.Absence.objects.create(
                date = dataInvoice["date"],
                salarie = models.Salarie.objects.get(nom = dataInvoice["salarie"], store = my_store),
                motif =  dataInvoice["motif"],
                nombre_heure = dataInvoice["nbrHeure"],
                justifie = True if dataInvoice["justifie"] == 'true' else False,
                minusSource = dataInvoice["decision"],
                user = myuser,
                store = my_store
            )
            salary_depense.save()
            responsable_entrepot = CustomUser.objects.filter(role ="DIRECTEUR EXECUTIF")
            if responsable_entrepot:
                for resp in responsable_entrepot : 
                        notify.send(
                            sender=myuser,
                            recipient=resp,
                            verb=f'a ajouté une nouvelle Absence/Retard pour {dataInvoice["salarie"]}.',
                            description=f'/gestionRh/AbsencePage',
                            level=1,
                        )   
        return JsonResponse({'message': "Client Added successfully."})

class SalariePageView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "gestionRH/salarie_page.html"
    login_url = 'home' 
    raise_exception = True  

    def test_func(self):
        return self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF" or  self.request.session["role"] == "assistante"

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess')) 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Define the model for which you want to create custom permissions
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        Currentuser = self.request.user
        myuser = CustomUser.objects.get(username=Currentuser.username)
        clients_list = models.Salarie.objects.filter(store=CurrentStore)
        clients=[]
        for cl in clients_list:  
            cl_dict={
                "client_id":cl.id,
                "name" :cl.nom,
                "cout_heure":float(cl.cout_heure),
                "ccp": cl.ccp,
                "association": cl.association,
                "email" : cl.email,      
                "fonction":cl.fonction,
                "nomarabe"  :cl.nomarabe,
                "fonctionarabe" :cl.fonctionarabe,
                "num_assurancesocial" :cl.num_assurancesocial,
                "datenaiss" :cl.datenaiss.date().strftime('%Y-%m-%d'),
                "datedeb" :cl.dateDebut.strftime('%Y-%m-%d'),
                "datefin" :cl.dateEnd.strftime('%Y-%m-%d'),
                "lieu_naissance" :cl.lieu_naissance,
                "lieu_naissancearabe" :cl.lieu_naissancearabe,
                "echellon" :cl.echellon,
                "degre" :cl.degre,
                "phone":cl.phone,
                "actif":'true' if cl.actif else 'false',
                'salaire': float(cl.salaire),
                'prime_espece': float(cl.prime_espece),
                'note':'RAS',
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

        with transaction.atomic():
            if dataInvoice:                
                    Currentuser = self.request.user
                    myuser = CustomUser.objects.get(username=Currentuser.username)
                    Currentstore = self.request.session.get("store")
                    my_store = store.objects.get(pk=Currentstore)

                    # Convert string values to Decimal
                    cout_heure = Decimal(dataInvoice.get('coutH', '0'))
                    salaire = Decimal(dataInvoice.get('salaire', '0'))
                    prime_espece = Decimal(dataInvoice.get('salaireEsp', '0'))

                    # Determine the value for the 'actif' field based on the 'status' value
                    actif_value = dataInvoice.get('status', '').lower() == 'true'

                    # Create an instance of the Salarie model using the provided data
                    salarie_instance = models.Salarie.objects.create(
                        nom=dataInvoice.get('name', ''),
                        fonction=dataInvoice.get('fonction', ''),
                        email=dataInvoice.get('email', ''),
                        phone=dataInvoice.get('phone', ''),
                        ccp=dataInvoice.get('ccp', ''),
                        nomarabe =dataInvoice.get('nomarabe', ''),
                        fonctionarabe =dataInvoice.get('fonctionarabe', ''),
                        num_assurancesocial =dataInvoice.get('num_assurancesocial', ''),
                        datenaiss =dataInvoice.get('datenaiss', ''),
                        lieu_naissance =dataInvoice.get('lieu_naissance', ''),
                        lieu_naissancearabe =dataInvoice.get('lieu_naissancearabe', ''),
                        echellon =dataInvoice.get('echellon', ''),
                        degre =dataInvoice.get('degre', ''),
                        association=dataInvoice.get('association', ''),
                        cout_heure=cout_heure,
                        salaire=salaire,
                        prime_espece=prime_espece,
                        actif=actif_value,
                        store=my_store,
                        user=myuser
                    )
        return JsonResponse({'message': "Client Added successfully."}) 

class EtatCongeView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "gestionRH/etat_conge.html"
    login_url = 'home' 
    raise_exception = True  
    def test_func(self):
        return self.request.session["role"] == "manager" or self.request.session["role"] == "DIRECTEUR EXECUTIF"
    
    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess')) 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        Currentuser = self.request.user
        currentStore= store.objects.get(pk=self.request.session["store"])        
        all_renumeration = []
        for salary in models.Salarie.objects.all():
            today = date.today()
            salary_date_debut = salary.dateDebut
            salary_date_end = salary.dateEnd
            difference =0
            nbrJourPris = 0
            if salary.actif:
                # Calculate difference for active employees (today - dateDeb)
                years_diff = today.year - salary_date_debut.year
                months_diff = today.month - salary_date_debut.month
                if months_diff < 0:
                    years_diff -= 1
                    months_diff += 12
                difference = years_diff * 12 + months_diff
            else:
                # Calculate difference for inactive employees (dateEnd - salary_date_debut)
                years_diff = salary_date_end.year - salary_date_debut.year
                months_diff = salary_date_end.month - salary_date_debut.month
                if months_diff < 0:
                    years_diff -= 1
                    months_diff += 12
                difference = years_diff * 12 + months_diff

            nbrJourConge = difference * 2.5
            if salary.mon_conge.exclude(type_conge='maladie').exists():
                nbrJourPris = sum(conge.getNbrJour for conge in salary.mon_conge.exclude(type_conge='maladie'))
           
            
            nbrJourPris += len(salary.mes_absences.filter(minusSource='conge'))
            nbrJourRestant = nbrJourConge - nbrJourPris
            renum_dict = {
                'nom': salary.nom,
                'datetimedeb': salary.dateDebut.strftime('%Y-%m-%d'),
                'etat': 'true' if salary.actif else 'false',
                'nbr_jrconge': nbrJourConge,
                'nbr_jrpris': nbrJourPris,
                'nbr_jrrest': nbrJourRestant,
            }
            all_renumeration.append(renum_dict)  
        context["conges"] = all_renumeration
        return context
            
class PagePaie(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "gestionRH/etat_paie.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        return self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF" or  self.request.session["role"] == "assistante"

    def handle_no_permission(self):
        # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        Currentuser = self.request.user
        currentStore= store.objects.get(pk=self.request.session["store"])
        
        all_renumeration = []
        for month in range(1, 13):
            for salary in models.Salarie.objects.all():
              if salary.getActifEtat(month) == 'true':   
                num_heuresup = salary.mes_heure_sup.filter(valide=True, datetimedeb__month=month).aggregate(Sum('nombre_heure'))['nombre_heure__sum'] or 0
                avance_salaire = float(salary.mes_avances_salaire.filter(date__month=month).aggregate(Sum('montant'))['montant__sum'] or 0)
                prix_social = float(salary.current_prix_social(month))              
                jour_retard = salary.get_late_minutes(month) / 480 
                absentdays = len(salary.mes_absences.filter(date__month=month)) - len(salary.mes_absences.filter(justifie = True, date__month=month))
                absenthours = salary.mes_absences.filter(justifie=False, date__month=month).aggregate(Sum('nombre_heure'))['nombre_heure__sum'] or 0
                montantPrime = salary.mes_primesmotivation.filter(motif="fix").aggregate(Sum('montant'))['montant__sum'] or 0
                zero_pointages = salary.mon_pointage.filter(temps_arrive=time(0, 0, 0), date__month=month)
                sanction = salary.mes_primesmotivation.filter(motif__startswith='SANCTION', date__month=month).aggregate(Sum('montant'))['montant__sum'] or 0
                don = salary.mes_primesmotivation.filter(motif__startswith='DON', date__month=month).aggregate(Sum('montant'))['montant__sum'] or 0
                # Initialize a variable to count the absent pointages
                absent_count = 0
                daysnotworked = 0
                daysnotworked = salary.days_not_worked(month)
                # Loop through each zero pointage
                for pointage in zero_pointages:
                    if pointage.date.weekday() != 4 and pointage.date.weekday() != 5:   
                        # Check if there is an absence for the salarie on the same date
                        absence_exists = salary.mes_absences.filter(
                            salarie=pointage.salarie,
                            date=pointage.date.date()  # Extract date from datetime
                        ).exists()
                        
                        # If there's no absence, increment the absent count
                        if not absence_exists:
                            absent_count += 1
                salaireCalculated = 0
                EspeceCalculated = 0
                if  month >= 4 :
                   salaireCalculated = float(salary.salaire) + float(don) - float(jour_retard * 2 * 4 * float(salary.cout_heure)) - float(prix_social) - float(absenthours * float(salary.cout_heure)) - float(sanction) 
                   EspeceCalculated = float(salary.prime_espece) + (float(num_heuresup) * float(salary.cout_heure) * 1.25) - float(avance_salaire) + float(montantPrime) - round(daysnotworked * 8 * float(salary.cout_heure),0)
                else:
                   salaireCalculated = float(salary.salaire) - float(prix_social) - float(sanction) 
                   EspeceCalculated = float(salary.prime_espece) + (float(num_heuresup) * float(salary.cout_heure) * 1.25) - float(avance_salaire) + float(montantPrime)- float(absenthours * float(salary.cout_heure)) - float(jour_retard * 2 * 4 * float(salary.cout_heure)) - round(daysnotworked * 8 * float(salary.cout_heure),0)
                renum_dict = {
                    'month': month,
                    'nom': salary.nom,
                    'ccp': salary.ccp,
                    'association': salary.association,
                    'nombreHeureSup': num_heuresup,
                    'cout_heure': float(salary.cout_heure),
                    'prime_sup': float(num_heuresup) * float(salary.cout_heure) * 1.25,
                    'avance': avance_salaire,
                    'social': prix_social,
                    'nombreMinuteRetard': salary.get_late_minutes(month),  # Pass month for filtering
                    'nombreJourR': jour_retard,  
                    'notworkeddays': daysnotworked,
                    'montantNotWorked': round(daysnotworked * 8 * float(salary.cout_heure),0),
                    'montantPrime': float(montantPrime),
                    'nombreJourN': absent_count,
                    'montant_retard': jour_retard * 2 * 4 * float(salary.cout_heure),  # Pass month for filtering
                    'jourabsent': absentdays,  # Pass month for filtering
                    'montantabsence': absenthours * float(salary.cout_heure),
                    'sanction': float(sanction),
                    'salaire': float(salary.salaire),
                    'espece': float(salary.prime_espece),
                    'salaireCalculated': salaireCalculated,
                    'especeCalculated': EspeceCalculated
                }
                all_renumeration.append(renum_dict)
        context["liste_paie"] = all_renumeration
        return context
        
class PagePaieCommercial(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "gestionRH/etat_paiecommercial.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        return self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF" or  self.request.session["role"] == "assistante"

    def handle_no_permission(self):
        # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        Currentuser = self.request.user
        currentStore= store.objects.get(pk=self.request.session["store"])
        
        all_renumeration = []
        for month in range(1, 13):
            for salary in models.Salarie.objects.all():
              if salary.getActifEtat(month) == 'true':   
                num_heuresup = salary.mes_heure_sup.filter(valide=True, datetimedeb__month=month).aggregate(Sum('nombre_heure'))['nombre_heure__sum'] or 0
                avance_salaire = float(salary.mes_avances_salaire.filter(date__month=month).aggregate(Sum('montant'))['montant__sum'] or 0)
                prix_social = float(salary.mes_prox_social.all().aggregate(Sum('montantperMonth'))['montantperMonth__sum'] or 0)
                jour_retard = salary.get_late_minutes(month) / 480 
                absentdays = len(salary.mes_absences.filter(date__month=month)) - len(salary.mes_absences.filter(justifie = True, date__month=month))
                absenthours = salary.mes_absences.filter(justifie=False, date__month=month).aggregate(Sum('nombre_heure'))['nombre_heure__sum'] or 0
                montantPrime = salary.mes_primesmotivation.filter(motif="fix").aggregate(Sum('montant'))['montant__sum'] or 0
                zero_pointages = salary.mon_pointage.filter(temps_arrive=time(0, 0, 0), date__month=month)
                sanction = salary.mes_primesmotivation.filter(motif__startswith='SANCTION').aggregate(Sum('montant'))['montant__sum'] or 0
                salaire_commercial = 0
                chiffreAffaire = 0
                if salary.fonction == 'Commercial' or salary.fonction == 'Responsable Commercial':
                    username = salary.fonctionarabe.lower()
                    salarie_user = CustomUser.objects.filter(username = username).first()
                    if salarie_user:
                        chiffreAffaire = salarie_user.monChiffreAffaire(month)
                        if chiffreAffaire <= 10000000:
                            tranches = (chiffreAffaire) / 10000000
                            salaire_commercial = (tranches * 30000)
                        elif 10000000 < chiffreAffaire <= 20000000:
                            tranches = (chiffreAffaire - 10000000) / 10000000
                            salaire_commercial = 30000 + (tranches * 25000)
                        elif 20000000 < chiffreAffaire <= 30000000:
                            tranches = (chiffreAffaire - 20000000) / 10000000
                            salaire_commercial = 55000 + (tranches * 20000)
                        # elif 30000000 < chiffreAffaire <= 40000000:
                        #     tranches = (chiffreAffaire - 30000000) / 10000000
                        #     salaire_commercial = 75000 + (tranches * 15000)
                        # else:  # chiffreAffaire > 40000000
                        #     tranches = (chiffreAffaire - 40000000) / 10000000
                        #     salaire_commercial = 75000 + (tranches * 15000)
                        elif 30000000 < chiffreAffaire: 
                            salaire_commercial=75000
                            chifresup=(chiffreAffaire-30000000)
                            for repet in range(int(chifresup/10000000)+1):
                                if chifresup<=10000000:
                                    salaire_commercial = salaire_commercial + ((chifresup/10000000)*15000)
                                else:
                                    salaire_commercial=salaire_commercial+ 15000
                                    chifresup=chifresup-10000000
                # Initialize a variable to count the absent pointages
                absent_count = 0
                daysnotworked = 0
                daysnotworked = salary.days_not_worked(month) 
                # Loop through each zero pointage
                for pointage in zero_pointages:
                    if pointage.date.weekday() != 4 and pointage.date.weekday() != 5:   
                        # Check if there is an absence for the salarie on the same date
                        absence_exists = salary.mes_absences.filter(
                            salarie=pointage.salarie,
                            date=pointage.date.date()  # Extract date from datetime
                        ).exists()
                        
                        # If there's no absence, increment the absent count
                        if not absence_exists:
                            absent_count += 1
                salaireCalculated = 0
                EspeceCalculated = 0
                if  month >= 4 :
                   salaireCalculated = float(salary.salaire) - float(jour_retard * 2 * 4 * float(salary.cout_heure)) - float(prix_social) - float(absenthours * float(salary.cout_heure)) - float(sanction) 
                   EspeceCalculated = float(salary.prime_espece) + (float(num_heuresup) * float(salary.cout_heure) * 1.25) - float(avance_salaire) + float(montantPrime) - round(daysnotworked * 8 * float(salary.cout_heure),0)
                else:
                   salaireCalculated = float(salary.salaire) - float(prix_social) - float(sanction) 
                   EspeceCalculated = float(salary.prime_espece) + (float(num_heuresup) * float(salary.cout_heure) * 1.25) - float(avance_salaire) + float(montantPrime)- float(absenthours * float(salary.cout_heure)) - float(jour_retard * 2 * 4 * float(salary.cout_heure)) - round(daysnotworked * 8 * float(salary.cout_heure),0)
                renum_dict = {
                    'month': month,
                    'nom': salary.nom,
                    'ccp': salary.ccp,
                    'association': salary.association,
                    'nombreHeureSup': num_heuresup,
                    'cout_heure': float(salary.cout_heure),
                    'prime_sup': float(num_heuresup) * float(salary.cout_heure) * 1.25,
                    'avance': avance_salaire,
                    'social': prix_social,
                    'nombreMinuteRetard': salary.get_late_minutes(month),  # Pass month for filtering
                    'nombreJourR': jour_retard,  
                    'notworkeddays': daysnotworked,
                    'montantNotWorked': round(daysnotworked * 8 * float(salary.cout_heure),0),
                    'montantPrime': float(montantPrime),
                    'nombreJourN': absent_count,
                    'montant_retard': jour_retard * 2 * 4 * float(salary.cout_heure),  # Pass month for filtering
                    'jourabsent': absentdays,  # Pass month for filtering
                    'montantabsence': absenthours * float(salary.cout_heure),
                    'salaire': float(salary.salaire),
                    'espece': float(salary.prime_espece),
                    'salaireCommercial': salaire_commercial,
                    'chiffreAffaire': chiffreAffaire,
                    'salaireCalculated': salaireCalculated,
                    'especeCalculated': EspeceCalculated
                }
                if salary.fonction == 'Commercial' or salary.fonction == 'Responsable Commercial':
                    all_renumeration.append(renum_dict)
        context["liste_paie"] = all_renumeration
        return context
        
class PageReglementPaie(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "gestionRH/reglement_rh.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        return self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF" or  self.request.session["role"] == "assistante"

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        Currentuser = self.request.user
        currentStore= store.objects.get(pk=self.request.session["store"])
        salaries = models.Salarie.objects.filter(store = currentStore)
        all_renumeration = []
        for month in range(1, 13):
            for salary in models.Salarie.objects.all():
              if salary.getActifEtat(month) == 'true':   
                num_heuresup = salary.mes_heure_sup.filter(valide=True, datetimedeb__month=month).aggregate(Sum('nombre_heure'))['nombre_heure__sum'] or 0
                avance_salaire = float(salary.mes_avances_salaire.filter(date__month=month).aggregate(Sum('montant'))['montant__sum'] or 0)
                prix_social = float(salary.current_prix_social(month))              
                jour_retard = salary.get_late_minutes(month) / 480 
                absentdays = len(salary.mes_absences.filter(date__month=month)) - len(salary.mes_absences.filter(justifie = True, date__month=month))
                absenthours = salary.mes_absences.filter(justifie=False, date__month=month).aggregate(Sum('nombre_heure'))['nombre_heure__sum'] or 0
                montantPrime = salary.mes_primesmotivation.filter(motif="fix").aggregate(Sum('montant'))['montant__sum'] or 0
                zero_pointages = salary.mon_pointage.filter(temps_arrive=time(0, 0, 0), date__month=month)
                sanction = salary.mes_primesmotivation.filter(motif__startswith='SANCTION', date__month=month).aggregate(Sum('montant'))['montant__sum'] or 0
                don = salary.mes_primesmotivation.filter(motif__startswith='DON', date__month=month).aggregate(Sum('montant'))['montant__sum'] or 0
                # Initialize a variable to count the absent pointages
                absent_count = 0
                daysnotworked = 0
                daysnotworked = salary.days_not_worked(month)
                # Loop through each zero pointage
                for pointage in zero_pointages:
                    if pointage.date.weekday() != 4 and pointage.date.weekday() != 5:   
                        # Check if there is an absence for the salarie on the same date
                        absence_exists = salary.mes_absences.filter(
                            salarie=pointage.salarie,
                            date=pointage.date.date()  # Extract date from datetime
                        ).exists()
                        
                        # If there's no absence, increment the absent count
                        if not absence_exists:
                            absent_count += 1
                salaireCalculated = 0
                EspeceCalculated = 0
                if  month >= 4 :
                   salaireCalculated = float(salary.salaire) + float(don) - float(jour_retard * 2 * 4 * float(salary.cout_heure)) - float(prix_social) - float(absenthours * float(salary.cout_heure)) - float(sanction) 
                   EspeceCalculated = float(salary.prime_espece) + (float(num_heuresup) * float(salary.cout_heure) * 1.25) - float(avance_salaire) + float(montantPrime) - round(daysnotworked * 8 * float(salary.cout_heure),0)
                else:
                   salaireCalculated = float(salary.salaire) - float(prix_social) - float(sanction) 
                   EspeceCalculated = float(salary.prime_espece) + (float(num_heuresup) * float(salary.cout_heure) * 1.25) - float(avance_salaire) + float(montantPrime)- float(absenthours * float(salary.cout_heure)) - float(jour_retard * 2 * 4 * float(salary.cout_heure)) - round(daysnotworked * 8 * float(salary.cout_heure),0)
                renum_dict = {
                    'month': month,
                    'nom': salary.nom,
                    'ccp': salary.ccp,
                    'association': salary.association,
                    'nombreHeureSup': num_heuresup,
                    'cout_heure': float(salary.cout_heure),
                    'prime_sup': float(num_heuresup) * float(salary.cout_heure) * 1.25,
                    'avance': avance_salaire,
                    'social': prix_social,
                    'nombreMinuteRetard': salary.get_late_minutes(month),  # Pass month for filtering
                    'nombreJourR': jour_retard,  
                    'notworkeddays': daysnotworked,
                    'montantNotWorked': round(daysnotworked * 8 * float(salary.cout_heure),0),
                    'montantPrime': float(montantPrime),
                    'nombreJourN': absent_count,
                    'montant_retard': jour_retard * 2 * 4 * float(salary.cout_heure),  # Pass month for filtering
                    'jourabsent': absentdays,  # Pass month for filtering
                    'montantabsence': absenthours * float(salary.cout_heure),
                    'sanction': float(sanction),
                    'salaire': float(salary.salaire),
                    'espece': float(salary.prime_espece),
                    'salaireCalculated': salaireCalculated,
                    'especeCalculated': EspeceCalculated
                }
                all_renumeration.append(renum_dict)
        context["liste_paie"] = all_renumeration
        return context

class PointagePageView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "gestionRH/pointage_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        return self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF" or  self.request.session["role"] == "assistante"

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        Currentuser = self.request.user
        currentStore= store.objects.get(pk=self.request.session["store"])
        list_attend = []
        pointages_list = models.Pointage.objects.filter(salarie__store = currentStore)
        
        for pointage in pointages_list:
            is_weekend = pointage.date.date().weekday() in [4, 5]
            # if not is_weekend:
            attend_dict = {
                'id': pointage.id,
                'name': pointage.salarie.nom,
                'date': str(pointage.date.date()),
                'temps_arrive': str(pointage.temps_arrive),
                'temps_depart': str(pointage.temps_depart),
            }
            list_attend.append(attend_dict)
        users = models.Salarie.objects.filter(store = currentStore)
        context['users'] = users
        context["attendances"] = list_attend
        return context

class BoiteArchiveView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "gestionRH/boitearchive_page.html"
    login_url = 'home' 
    raise_exception = True  

    def test_func(self):
        return self.request.session["role"] == 'manager' or  self.request.session["role"] == "DIRECTEUR EXECUTIF" or  self.request.session["role"] == "assistante"

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse_lazy('noaccess')) 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Define the model for which you want to create custom permissions
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        Currentuser = self.request.user
        myuser = CustomUser.objects.get(username=Currentuser.username)
        archives = models.BoiteArchive.objects.all()
        archive_list=[]
        for cl in archives:  
            cl_dict={
                "id":cl.id,
                "date": str(cl.date.date()),
                "label": cl.label,
                "date_facturation_fournisseur": str(cl.date_facturation_fournisseur.date()),
                "date_facturation_transitaire": str(cl.date_facturation_transitaire.date()),
                "montant": cl.montant,
                "typedocument": cl.typedocument,
                "document": cl.document,
            }
            archive_list.append(cl_dict)
            
        context["clients"]= archive_list
        users_bills = CustomUser.objects.filter(EmployeeAt=CurrentStore)
        context["users"]=users_bills
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        if request.method == 'POST':
            print(request.POST)
            date_facturation_fournisseur = request.POST['datefactfour']
            date_facturation_transitaire = request.POST['datefacttrans']
            montant = request.POST['montant']  # Convert to decimal if necessary
            typedocument = request.POST['type']
            label = request.POST['label']
            document = request.FILES['file']  # Access uploaded file

            # Validation (optional, but recommended)
            # Add checks for required fields, data types, etc.
            # If validation fails, return a response with error messages.

            # Create BoiteArchive instance
            boitearchive = models.BoiteArchive(
                date_facturation_fournisseur=date_facturation_fournisseur,
                date_facturation_transitaire=date_facturation_transitaire,
                montant=Decimal(montant),
                typedocument=typedocument,
                label=label,
                document=document,
            )

            # Save the instance
            boitearchive.save()

            # Handle success (redirect, success message, etc.)
        return render(request, 'gestionRH/boitearchive_page.html')  

        
