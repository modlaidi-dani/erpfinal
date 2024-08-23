from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser,  Group, Permission
from wagtail.snippets.models import register_snippet
from decimal import Decimal

class UsersCustomPermission(Permission):
    class Meta:
        verbose_name = 'Custom Permission'
        verbose_name_plural = 'Custom Permissions'
        
class CustomUser(User):
    role = models.CharField(max_length=100, null=True, blank=True, default='')
    group = models.ForeignKey('CustomGroup', on_delete=models.SET_NULL, related_name="group_users", null=True, blank=True, default=None)
    EmployeeAt = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE, related_name="mes_employees", null=True, blank=True)
    entrepots_responsible = models.ForeignKey('inventory.Entrepot', on_delete=models.SET_NULL, related_name="responsables" ,default=None, null=True, blank=True)
    equipe_affiliated = models.ForeignKey('Equipe', on_delete=models.SET_NULL, related_name="mes_membres" ,default=None, null=True, blank=True)
    adresse_ip = models.GenericIPAddressField(default='127.0.0.1', blank=True, null=True)
    def save(self, *args, **kwargs):
        if self.role == 'manager':
            self.Employee_At = None  
        super(CustomUser, self).save(*args, **kwargs)
        
    @property
    def total_price_difference(self):
        # Calculate the sum of totalprice of related BonComptoire objects
        bon_comptoire_total = sum([Decimal(str(bon.prix_payed)) for bon in self.mes_bons_comptoire.all()])
    
        # Calculate the sum of myTotalPrice of related BonRetourComptoire objects
        bon_retour_total = sum([Decimal(str(bon_retour.myTotalPrice)) for bon_retour in self.mes_bons_retourcomptoire.all()])
        bon_retourv_total = sum([Decimal(bon_retour.total_price_retour) * Decimal(1.19) for bon_retour in self.mes_bons_retour.all()])
        bon_vente_total = sum([Decimal(str(bon.get_total_soldprice)) for bon in self.mes_bons.all()])
        
        # Return the difference
        return round((bon_comptoire_total + bon_vente_total) - (bon_retour_total + bon_retourv_total), 0)
        
    def monChiffreAffaire(self, monthArg):
        chiffre_affaire = sum([float(bon.get_total_price) * float(1.19)  for bon in self.mes_bons.filter(dateBon__month=monthArg)])
        filtered_bons_retour = [bon for bon in self.mes_bons_retour.filter(valide=True, dateBon__month=monthArg) if bon.reintegrated]
        result_sum = sum(Decimal(bon.total_price_retour) * Decimal(1.19) for bon in filtered_bons_retour)
        return float(chiffre_affaire) - float(result_sum)
        
class cordinates(models.Model):
    User = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="mycoordinates")  # Link the log entry to an author (user)
    latitude = models.CharField(max_length=250, default="", null=True, blank=True)
    longitude = models.CharField(max_length=250, default="", null=True, blank=True)
    
class Equipe(models.Model):
    label = models.CharField(max_length=250, default="", null=True, blank=True)
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE, related_name="mes_equipes", null=True, blank=True)
    date_created = models.DateTimeField()

class MyLogEntry(models.Model):
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="myacts")  # Link the log entry to an author (user)
    description = models.TextField()  # Store the description of the event or change
    timestamp = models.DateTimeField(auto_now_add=True)  # Record the timestamp when the log entry is created
    store =models.ForeignKey('clientInfo.store', on_delete=models.CASCADE, related_name="ma_tracabilte", null=True, blank=True)
    def __str__(self):
        return f"Log Entry by {self.author.username} - {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']  # Display log entries in descending order of timestamp
               
class CustomGroup(Group):
    label = models.CharField(max_length=100, unique=False)
    description = models.TextField(max_length=2500)
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE, related_name="mes_groupes", null=True, blank=True, default=None)
    custom_permissions = models.ManyToManyField(Permission, blank=True)
    
    def __str__(self) :
        return self.label
