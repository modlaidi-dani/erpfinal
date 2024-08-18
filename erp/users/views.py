from django.http import HttpResponse
from django.http import Http404, JsonResponse
from django.shortcuts import render,redirect
from django.contrib.auth import login,authenticate
from . import models
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from clientInfo.models import store
from django.views.generic.base import TemplateView
import json
from django.contrib.auth.models import Permission
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
# from inventory.models import MyCustomPermission 
from .models import CustomGroup 
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Group
from notifications.signals import notify
from .models import UsersCustomPermission
from clientInfo.models import ClientInfoCustomPermission
from produits.models import ProduitsCustomPermission
from tiers.models import TiersCustomPermission
from ventes.models import VentesCustomPermission
from inventory.models import InventoryCustomPermission
from reglements.models import ReglementsCustomPermission
from comptoire.models import ComptoirCustomPermission 
from achats.models import AchatInfoCustomPermission
from notifications.models import Notification 
from target.models import Target
from django.utils import timezone
from django.db import IntegrityError
from datetime import datetime
from logistique.models import CourseLivraison

def signup(request):
      if request.method == 'POST':      
        name= request.POST['username']
        lname=request.POST['username']
        username= request.POST['username']          
        pswrd= request.POST['password']
        role = 'manager'       
        user = models.CustomUser.objects.create_user(
               username=username,
               first_name=name,
               last_name=lname,          
               role=role,
               password=pswrd)
        return HttpResponse('user created')   
      else:
        return render(request, 'home/home_page.html') 

def DeleteUser(request):
    try:
         # Find the product by reference
        data = json.loads(request.body)
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        user = models.CustomUser.objects.get(id=data["user_id"])
        if ( len(user.mes_bons_comptoire.all()) >0 or len(user.mes_bons.all()) >0):
            return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché, car cet utilisateur est lié aux autres composants '})
        else:
             user.delete()
        return JsonResponse({'message': 'Utilisateur Supprimé !'})
    except models.CustomUser.DoesNotExist:
        return JsonResponse({'error': 'Utilisateur Non-trouve.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché, car cet utilisateur est lié aux autres composants - {}'.format(str(e))})
    
def DeleteGroupe(request):
    try:
         # Find the product by reference
        data = json.loads(request.body)
        store_id = request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        user = models.CustomGroup.objects.get(id=data["user_id"])
        # if ( len(user.group_users.all()) > 0 ):
        #     return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché, Ce groupe a des utilisateurs associés'})
        # else:
        user.delete()
        return JsonResponse({'message': 'Groupe Supprimé !'})
    except models.CustomUser.DoesNotExist:
        return JsonResponse({'error': 'Groupe Non-trouve.'})
    except IntegrityError as e:
        return JsonResponse({'error': 'Integrity Erreur: La supressions a été échouché, Ce groupe a des utilisateurs associés - {}'.format(str(e))})
        
def marknotificationread(request):
    try:
        notification_id = request.POST.get('notification_id')
        notification = Notification.objects.get(id=notification_id)

        # Mark the notification as read
        notification.mark_as_read()

        # You can return a JsonResponse to the Axios call
        response_data = {'message': 'Notification marked as read'}
        return JsonResponse(response_data)
    except Notification.DoesNotExist:
        # Handle the case where the notification does not exist
        response_data = {'error': 'Notification not found'}
        return JsonResponse(response_data, status=404)
    
def loginInto(request):
    if request.method=='POST':
        username= request.POST['username']        
        password= request.POST['password']    
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request,user)
            myuser  = models.CustomUser.objects.get(username=username)
            request.session['username'] = user.username
            request.session['role'] = myuser.role     
            user_groups = myuser.group if myuser.group else None
            group_permissions = set()  
            print(user_groups)
            if  user_groups is not None:           
             # Get group-level permissions for each group
                group_permissions = set(
                    f"{app_label}.{codename}" for app_label, codename in user_groups.permissions.values_list('content_type__app_label', 'codename')
                )

                # Get user-level permissions
                user_permissions = set(
                    f"{app_label}.{codename}" for app_label, codename in myuser.user_permissions.values_list('content_type__app_label', 'codename')
                )

                # Combine group-level and user-level permissions
                all_permissions = group_permissions.union(user_permissions)

                # Store the combined permissions in the session
                request.session['permissions'] = list(all_permissions)

            if myuser.role=='manager':
                return redirect('magasins')  
            elif myuser.role == 'Chauffeur':
                myuser_employee_at_id = str(myuser.EmployeeAt.id) if myuser.EmployeeAt else ''
                request.session['store'] = myuser_employee_at_id
                request.session['username'] = myuser.username
                return redirect('chauffeur-page')
            else:
                stores = store.objects.all()
                request.session['magasins']= [{'name':store.name, 'id':store.pk} for store in stores]
                myuser_employee_at_id = str(myuser.EmployeeAt.id) if myuser.EmployeeAt else ''
                request.session['store'] = myuser_employee_at_id
                request.session['username'] = myuser.username
                current_year = datetime.now().year
                request.session['currentYear'] = current_year
                request.session['nomStore']= myuser.EmployeeAt.name if myuser.EmployeeAt else ''
                return redirect('user-page')
        else:
            return render(request, 'home/home_page.html', context={'error':'Login/mot de passe incorrect! Veuillez ré-essayer'})  
    else:
      return render(request, 'home/home_page.html')    

@login_required         
def adminMag(request):
    context={}
    if request.session["role"]=="manager":
        stores = store.objects.all()
        request.session['magasins']= [{'name':store.name, 'id':store.pk} for store in stores]
        context={
                  'magasins':stores
                }
    return render(request, 'users/admin_home_page.html', context) 

def logout_view(request):
    logout(request)
    return render(request, 'home/home_page.html')   

class RedirectPermissionNone(TemplateView):
    template_name="users/noaccess.html"
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)  
        return context
    
class Profile(TemplateView):
    template_name="users/profile.html"
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs) 
        Currentuser = self.request.user
        myuser  = models.CustomUser.objects.get(username=Currentuser.username)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        audit_logs = models.MyLogEntry.objects.filter(store=CurrentStore)
        context["audit_logs"] = audit_logs   

        return context  

class NotificationsView(TemplateView):
    template_name="users/notifications_page.html"
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs) 
        Currentuser = self.request.user
        myuser  = models.CustomUser.objects.get(username=Currentuser.username)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        audit_logs = Notification.objects.filter(recipient=myuser)
        for notification in audit_logs:
            notification.mark_as_read()
        context["notifications"] = audit_logs   
 

        return context  
     
class ChauffeurPageLogin(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "users/ChauffeuPage.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        return self.request.session["role"] == 'Chauffeur'

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)  
        Currentuser = self.request.user
        myuser = models.CustomUser.objects.get(username=Currentuser.username)
        liste_courses = myuser.mes_courses.all().order_by('-etat')
        liste_user =[]
        for course in liste_courses:
            user_dict ={
                'id': course.id,
                'adresse': course.adresse,
                'dateTimeAffectation': course.dateTimeAffectation.strftime('%d/%m/%y - %H:%M'),
                'note': course.note if course.note is not None else '',
                'typeCourse': course.typeCourse if course.typeCourse is not None else '/',
                'transporteur': course.transporteur if course.typeCourse == ' trans' else course.bonlivraison.client.name,
                'bonlivraison': course.bonlivraison.idBon if course.bonlivraison is not None else '',
                'montant': float(course.montant),
                'fraisTransport': float(course.fraisTransport),
                'etat': course.etat if course.etat is not None else '',
            }
            liste_user.append(user_dict)
        context ["users"]= liste_user

        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data
        if dataInvoice:  
            etat = dataInvoice["etat"]
            montantgot = 0
            if 'montantgot' in dataInvoice:
                montantgot = dataInvoice["montantgot"]
            justif = ''    
            if 'justif' in dataInvoice:    
                justif= dataInvoice["justif"]
            courseid = dataInvoice["Courseid"]
            course_instance = CourseLivraison.objects.get(id = courseid)
            if course_instance.etat == etat :
                return JsonResponse({'message': 'Etat Inchangé!!!!'})
            elif (course_instance.etat == "en-attente" or course_instance.etat == "En Attente")  and etat == "en-route":
                course_instance.etat = 'en-route'
                course_instance.dateTimeDebut = datetime.now()
                
            elif course_instance.etat == "en-route" and (etat == "livre" or etat =="annule"):
                course_instance.etat = etat
                if etat == 'livre':
                    course_instance.bonlivraison.livre = True
                course_instance.montantrecupere = montantgot   
                course_instance.dateTimeFin = datetime.now()
            else:
                 course_instance.bonlivraison.livre = etat
                 course_instance.dateTimeFin = datetime.now()
            course_instance.save()    
                
        return JsonResponse({'message': 'Information Mis à jour!'})
    
class ListeUsers(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "users/liste_utilisateurs.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=models.CustomUser.objects.get(username=self.request.user.username)
        print('hello',self.request.session.get('permissions', []))
        return'users.can_see_users' in self.request.session.get('permissions', []) or self.request.session["role"] == 'manager' or self.request.session["role"] == 'DIRECTEUR EXECUTIF'

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
      
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)  
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        users = models.CustomUser.objects.filter(EmployeeAt = CurrentStore)
        listes_groupes = models.CustomGroup.objects.filter(store=CurrentStore)
        context["groupes"]=listes_groupes
        liste_user =[]
        for user in users:
            user_dict ={
                'name': user.first_name,
                'id':user.id,
                'username': user.username,
                'lname': user.last_name,
                'email':user.email,
                'role':user.role
            }
            liste_user.append(user_dict)
        context ["users"]= liste_user
        print(context["users"])
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        dataInvoice = data.get('formData')
        if dataInvoice:  
            print(dataInvoice)
            name= dataInvoice['prenom']
            lname= dataInvoice['nom']
            username= dataInvoice['login']    
            email= dataInvoice['mail']
            pswrd= dataInvoice['password']
            group = dataInvoice['groupe']   
            custom_group = models.CustomGroup.objects.get(id=group)
            store_id = self.request.session["store"]
            CurrentStore = store.objects.get(pk=store_id)    
            user = models.CustomUser.objects.create_user(
               username=username,
               first_name=name,
               last_name=lname,          
               email=email,
               group=custom_group,
               role=custom_group.label,
               password=pswrd,
               EmployeeAt = CurrentStore)
        return JsonResponse({'message': 'User Added successfully'})

class UpdateUser(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "users/update_user_page.html" 
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=models.CustomUser.objects.get(username=self.request.user.username)

        return'users.can_see_users' in self.request.session.get('permissions', []) or self.request.session["role"] == 'manager' or self.request.session["role"] == 'DIRECTEUR EXECUTIF'

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
      
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs) 
        username_user= self.kwargs.get('username_user') 
        myuser = models.CustomUser.objects.get(id=username_user)
        context["myuser"]= myuser
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        listes_groupes = models.CustomGroup.objects.filter(store=CurrentStore)
        context["groupes"]=listes_groupes
        return context
        
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
     data = json.loads(request.body)
     dataInvoice = data.get('formData')
     if dataInvoice:
         if 'id' in dataInvoice:
           user_id = dataInvoice['id']
           try:
               myuser = models.CustomUser.objects.get(id=user_id)
               # Update the user fields with the provided data
               if 'prenom' in dataInvoice:
                   myuser.first_name = dataInvoice['prenom']
               if 'nom' in dataInvoice:
                   myuser.last_name = dataInvoice['nom']
               if 'login' in dataInvoice:
                   myuser.username = dataInvoice['login']
               if 'mail' in dataInvoice:
                   myuser.email = dataInvoice['mail']
               if 'groupe' in dataInvoice:
                   group_id = dataInvoice['groupe']
                   if group_id:
                       custom_group = models.CustomGroup.objects.get(id=group_id)
                       myuser.group = custom_group
                       myuser.role = custom_group.label
                   else:
                       myuser.group=None
                       myuser.role = ''
               if 'password' in dataInvoice:
                   password = dataInvoice['password']
                   if password:
                       myuser.set_password(password)  # Update the password

               # Save the updated user
               myuser.save()
               # Return a success JsonResponse
               return JsonResponse({'message': 'User updated successfully'})
           except models.CustomUser.DoesNotExist:
               # Handle the case where the user with the provided ID doesn't exist
               return JsonResponse({'error': 'User with ID {} not found.'.format(user_id)})      

class ListeGroupes(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "users/liste_groupes.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=models.CustomUser.objects.get(username=self.request.user.username)
        print('hello',self.request.session.get('permissions', []))
        return'users.can_see_grp_users' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs) 
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        listes_groupes =models.CustomGroup.objects.filter(store=CurrentStore)
        context["groupes"]=listes_groupes
        return context

class UserhomePage(TemplateView):
    template_name="users/user_homepage.html"
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs) 
        Currentuser = self.request.user
        myuser  = models.CustomUser.objects.get(username=Currentuser.username)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        context["ca"] = myuser.total_price_difference
        context["bonventes"] = len(myuser.mes_bons_comptoire.all())
        context["bonliv"] = len(myuser.mes_bons.all())
        context["bons_retour"] = len(myuser.mes_bons_retourcomptoire.all())
        context["clients"] = len(myuser.mes_clients.all())
        context["user_name"] = myuser.first_name + " " + myuser.last_name
        if myuser.equipe_affiliated:
            equipe = myuser.equipe_affiliated          
            if equipe.team_target.exists():
                # Fetch user targets that haven't expired
                user_targets = equipe.team_target.filter(end_date__gt=timezone.now()).first()
                if user_targets is not None:
                    context["user_targets"] = user_targets
                    products_list = []
                    for product in user_targets.target_products.all():
                        products_list.append({
                            'reference': product.product.reference,
                            'designation': product.product.name,
                            'qty': product.quantity
                        })
                    completion_rates = user_targets.get_taux_completion_per_member
                    percent_for_request_user = next((member["percent"] for member in completion_rates if member["name"] == myuser.username), 0)
                    context["percent"] = round((percent_for_request_user / user_targets.get_taux_completion) * 100, 2) if user_targets.get_taux_completion != 0 else 0
                    context['listProducts'] = products_list
                else:
                   context["user_targets"] = None 
        else:
            # Check if the user has any targets
            if myuser.my_target.exists():
                # Fetch user targets that haven't expired
                user_targets = myuser.my_target.filter(end_date__gte=timezone.now()).first()
                context["user_targets"] = user_targets
            else:
                context["user_targets"] = None

        # Check if the user has any targets
        
        return context
        
class GroupeUpdate(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "users/groupe_update_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=models.CustomUser.objects.get(username=self.request.user.username)
        print('hello',self.request.session.get('permissions', []))
        return'users.can_see_grp_users' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)   
        group_id= self.kwargs.get('group_id') 
        custom_group = CustomGroup.objects.get(id=group_id)
        grouup_users = models.CustomUser.objects.filter(group=custom_group)
        list_users=[]
        for grpuser in grouup_users:
            list_users.append(grpuser.username)
        context["list_users"] = list_users
        context["group"]= custom_group
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        users = models.CustomUser.objects.filter(EmployeeAt= CurrentStore).exclude(group=custom_group)
        liste_users=[]
        for user_obj in users:
            liste_users.append(user_obj.username)
        context["users"] = liste_users
        import html

        permissions_queryset = custom_group.permissions.values_list('codename', flat=True)
        permissions_list = [html.unescape(permission.strip()) for permission in permissions_queryset]
        context["permissions"] = permissions_list
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
     data = json.loads(request.body)
     dataInvoice = data.get('formData')
     if dataInvoice:
         custom_group = CustomGroup.objects.get(id=dataInvoice["id"])         
         custom_group.description = dataInvoice['description']
         custom_group.label = dataInvoice['labelGroup']
         print(dataInvoice["liste_users"])
         custom_group.custom_permissions.clear()
         print(dataInvoice["listPermissions"])
         permissions_to_assign = []
         listPermissions = dataInvoice.get("listPermissions", {})
         for key, permission_codenames in listPermissions.items():
            if isinstance(permission_codenames, list):
                permissions_to_assign += list(Permission.objects.filter(codename__in=permission_codenames))
         custom_group.permissions.set(permissions_to_assign)
         new_usernames = dataInvoice["liste_users"]
         existing_users = custom_group.group_users.all()

         # Find the users to remove from the group
         users_to_remove = existing_users.exclude(username__in=new_usernames)

         # Remove users not in the new list
         for user in users_to_remove:
             custom_group.group_users.remove(user)

         # Find the usernames that are not already in the group
         usernames_to_add = set(new_usernames) - set(existing_users.values_list('username', flat=True))

         # Add new users to the group
         for username in usernames_to_add:
             user = models.CustomUser.objects.get(username=username)
             custom_group.group_users.add(user)

         custom_group.save()    
     return JsonResponse({'message': 'User Added successfully'})

class user_permission(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "users/liste_utilisateurs_permissions.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=models.CustomUser.objects.get(username=self.request.user.username)
        return'users.can_see_users_perm' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
   
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)  
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        users = models.CustomUser.objects.filter(EmployeeAt = CurrentStore)
        listes_groupes = models.CustomGroup.objects.filter(store=CurrentStore)
        context["groupes"]=listes_groupes
        liste_user =[]
        for user in users:
            user_dict ={
                'name': user.first_name,
                'id':user.id,
                'username': user.username,
                'lname': user.last_name,
                'email':user.email,
                'role':user.role
            }
            liste_user.append(user_dict)
        context ["users"]= liste_user
        print(context["users"])
        return context
    
class Edituser_permission(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "users/user_permissions.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=models.CustomUser.objects.get(username=self.request.user.username)
        return'users.can_see_users_perm' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
   
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs) 
        username_user= self.kwargs.get('username_user') 
        myuser = models.CustomUser.objects.get(id=username_user)
        context["myuser"]= myuser.username
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        permissions_codenames = list(myuser.user_permissions.values_list('codename', flat=True))
        context["permissions"]=permissions_codenames
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
     data = json.loads(request.body)
     dataInvoice = data.get('formData')
     if dataInvoice:
        user_perm = models.CustomUser.objects.get(username = dataInvoice["user_username"])
        listPermissions = dataInvoice["listPermissions"]
        user_perm.user_permissions.clear()
        permissions_to_assign = []
        for key, permission_codenames in listPermissions.items():
         if isinstance(permission_codenames, list):
            permissions_to_assign = Permission.objects.filter(codename__in=permission_codenames)
            user_perm.user_permissions.add(*permissions_to_assign)
            user_perm.save()        
        return JsonResponse({'message': 'Permissions Mise a Jour!'})
        
class ListePermissions(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "users/liste_permissions.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=models.CustomUser.objects.get(username=self.request.user.username)
        return'users.can_see_users_perm' in self.request.session.get('permissions', []) 

    def handle_no_permission(self):
         # Redirect users without permission to the "noaccess" page
        return HttpResponseRedirect(reverse_lazy('noaccess'))
   
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        users = models.CustomUser.objects.filter(EmployeeAt = CurrentStore)
        liste_users=[]
        for user_obj in users:
            liste_users.append(user_obj.username)
        context["users"] = liste_users
        return context

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    def post(self, request, *args, **kwargs):
     data = json.loads(request.body)
     dataInvoice = data.get('formData')
     if dataInvoice:
        label = dataInvoice["labelGroup"]
        description = dataInvoice["description"]
        listPermissions = dataInvoice.get("listPermissions", {})  # Ensure it's a dictionary
        store_id = self.request.session["store"]
        CurrentStore = store.objects.get(pk=store_id)
        custom_group = CustomGroup.objects.create(name=label,label=label, description=description, store =CurrentStore )

        # Iterate through the keys in listPermissions and assign permissions
        permissions_to_assign = []
        for key, permission_codenames in listPermissions.items():
            if isinstance(permission_codenames, list):
                permissions_to_assign += Permission.objects.filter(codename__in=permission_codenames)
        custom_group.permissions.set(permissions_to_assign)
        return JsonResponse({'message': 'User Added successfully'})