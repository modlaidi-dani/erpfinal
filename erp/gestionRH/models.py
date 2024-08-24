from django.db import models
from datetime import datetime, time, date
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
import calendar


class RequeteSalarie(models.Model):
    date = models.DateTimeField(default=datetime.now)
    objet = models.CharField(max_length=255, default='')
    message = models.TextField(default='')
    reponse = models.TextField(default='') 
    datereponse = models.DateTimeField(default=datetime.now)
    destinataire = models.CharField(max_length=255, default='')
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, default=None, null=True, blank=True)
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE, default=None, null=True, blank=True) 

class Event(models.Model):
    name = models.CharField(max_length=100, help_text="The name of the event.")
    description = models.TextField(default='', help_text="The name of the event.")
    event_date = models.DateField(help_text="The date of the event.")
    remember_months = models.IntegerField(
        default=0,
        help_text="Number of months in advance to remember the event."
    )
    remind_days_before = models.IntegerField(
        default=0,
        help_text="Number of days before the event to send a reminder."
    )

    def __str__(self):
        return f"{self.name} on {self.event_date}"

    def get_reminder_date(self):
        """
        Calculate the reminder date based on `remind_days_before`.
        """
        return self.event_date - timedelta(days=self.remind_days_before)

    def get_next_remember_date(self):
        """
        Calculate the next remember date based on `remember_months`.
        """
        return self.event_date - timedelta(days=30 * self.remember_months)
        
class Salarie(models.Model):
    nom = models.CharField(max_length=255, default='')
    nomarabe = models.CharField(max_length=255, default='')
    fonction = models.CharField(max_length=255, default='')
    fonctionarabe = models.CharField(max_length=255, default='')
    email = models.CharField(max_length=255, default='')
    phone = models.CharField(max_length=255, default='')
    ccp = models.CharField(max_length=255, default='')
    association = models.CharField(max_length=255, default='')
    actif = models.BooleanField(default=True)
    num_assurancesocial = models.CharField(max_length=255, default='')
    datenaiss = models.DateTimeField(auto_now_add=False, default=datetime.now)
    lieu_naissance = models.CharField(max_length=255, default='')
    lieu_naissancearabe = models.CharField(max_length=255, default='')
    echellon = models.CharField(max_length=255, default='')
    degre = models.CharField(max_length=255, default='')
    cout_heure = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    salaire = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    prime_espece = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, default=None, null=True, blank=True)
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE, default=None, null=True, blank=True)
    dateDebut = models.DateField(help_text="The date of start.", default=datetime.now)
    dateEnd = models.DateField(help_text="The date of start.", default=datetime.now)
    
    def current_prix_social(self, month):
        current_date = timezone.now().replace(day=1, month=month)
        total_montant = 0
        for prix_social in self.mes_prox_social.all():
            start_date = prix_social.date
            end_date = prix_social.end_month
            
            # Ensure start_date and end_date are timezone aware
            if timezone.is_aware(start_date):
                start_date = start_date.replace(day=1).astimezone(timezone.utc)
            if timezone.is_aware(end_date):
                end_date = end_date.replace(day=1).astimezone(timezone.utc)
            
            # Check if current_date is within the date range
            
            if (start_date <= current_date <= end_date):
                total_montant += prix_social.montantperMonth
                
        return total_montant
    
    def days_not_worked(self, month):
        year = timezone.now().year
        month_as_int = int(month)  # Convert month to integer if necessary
        start_of_month = date(year, month_as_int, 1)  # Use date from the imported module
        end_of_month = date(year, month_as_int, calendar.monthrange(year, month_as_int)[1])
 
        if self.actif:
            if self.dateDebut and self.dateDebut.month == month_as_int and self.dateDebut.year == year:
                return self.dateDebut.day - 1
            else:
                return 0
        else:
            if self.dateEnd and self.dateEnd.month == month_as_int and self.dateEnd.year == year:
                return (end_of_month - self.dateEnd).days + 1
            else:
                return 0  # Or handle this case as needed
            
    @property
    def total_valid_Supphours(self):
        return self.mes_heure_sup.filter(valide=True).aggregate(Sum('nombre_heure'))['nombre_heure__sum'] or 0
    
    def getActifEtat(self, month):
        if self.actif:
            return 'true'
        else:
           if month < self.dateEnd.month:
              return 'true'
           else:
               if month == self.dateEnd.month and (self.dateEnd.day <= 30 or self.dateEnd.day <= 31):
                   return 'true'
               else:
                return 'false'
    @property
    def total_late_days(self):
        return self.get_late_minutes / 480
    
    @property
    def total_daysnopoint(self):
       return len(self.mon_pointage.filter(temps_arrive=time(0, 0, 0)))
    @property
    def total_avances(self):
        return self.mes_avances_salaire.filter(date__month=2).aggregate(Sum('montant'))['montant__sum'] or 0
    
    @property
    def total_prixsocial(self):
        return self.mes_prox_social.all().aggregate(Sum('montantperMonth'))['montantperMonth__sum'] or 0
    
    @property
    def get_total_absent_days(self):
        return len(self.mes_absences.filter(date__month=2)) - len(self.mes_absences.filter(justifie = True, date__month=2))
    
    @property
    def get_total_absent_Hours(self):
        if self.get_total_absent_days>0:
           return  self.mes_absences.filter(justifie=False, date__month=2).aggregate(Sum('nombre_heure'))['nombre_heure__sum'] or 0
        else:
            return 0     
            
    def get_late_minutes(self, month):
        minutes_after_15 = 0
        if len(self.mon_pointage.filter(date__month = month)) > 0:
            for time_p in self.mon_pointage.filter(date__month = month):
                arrive_time = datetime.combine(datetime.today(), time_p.temps_arrive)
                reference_time = datetime.combine(datetime.today(), time(9, 30, 0))
                zero_time = datetime.combine(datetime.today(), time(0, 0, 0))
                # Check if the day is a weekend (Saturday or Sunday)
                if time_p.date.weekday() != 4 and time_p.date.weekday() != 5:
                    if arrive_time > reference_time:
                        absence_exists = self.mes_absences.filter(
                            salarie=self,
                            date=time_p.date.date()  # Extract date from datetime
                        ).exists()
                        
                        # If there's no absence, increment the absent count
                        if not absence_exists:
                            minutes_after_15 += 240
                    elif arrive_time == zero_time:
                        absence_exists = self.mes_absences.filter(
                            salarie=self,
                            date=time_p.date.date()  # Extract date from datetime
                        ).exists()
                        
                        # If there's no absence, increment the absent count
                        if not absence_exists:
                            minutes_after_15 += 480
            return minutes_after_15
        else:
            return minutes_after_15
        
class ReglementCompte(models.Model):
    salarie = models.ForeignKey(Salarie, on_delete= models.CASCADE, related_name="mes_reglementscompte", null=True, blank = True, default=None)
    dateSortie = models.DateTimeField(auto_now_add=False)
    montant = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    note = models.TextField(default='') 
    
class Conge(models.Model):
    salarie = models.ForeignKey(Salarie, on_delete= models.CASCADE, null=True,related_name="mon_conge", blank = True, default=None)
    dateDebut = models.DateTimeField(default=datetime.now)
    dateFin = models.DateTimeField(default=datetime.now)
    type_conge = models.TextField(default="")
    nbrJourPris = models.IntegerField(default='0')

    @property
    def getNbrJour(self):
        return (self.dateFin - self.dateDebut).days + 1
        
    def __str__(self):
        return f'Salarie {self.salarie.nom} - Date: {self.dateDebut.strftime("%Y-%m-%d")}'
    
    
class Pointage(models.Model):
    salarie = models.ForeignKey(Salarie, on_delete= models.CASCADE, null=True,related_name="mon_pointage", blank = True, default=None)
    date = models.DateTimeField(default=datetime.now)
    temps_arrive = models.TimeField(default='09:00:00')
    temps_depart = models.TimeField(default='17:00:00')
    
    def __str__(self):
        return f'Salarie {self.salarie.nom} - Date: {self.date.strftime("%Y-%m-%d")}'

class AvanceSalaire(models.Model):
    date = models.DateTimeField(auto_now_add=False)
    salarie = models.ForeignKey(Salarie, on_delete= models.CASCADE, related_name="mes_avances_salaire", null=True, blank = True, default=None)
    motif = models.CharField(max_length=255, default='') 
    montant = models.DecimalField(max_digits=10, decimal_places=2, default=0)

class PrixSocial(models.Model):
    date = models.DateTimeField(auto_now_add=False)
    salarie = models.ForeignKey(Salarie, on_delete= models.CASCADE, related_name="mes_prox_social", null=True, blank = True, default=None)
    motif = models.CharField(max_length=255, default='') 
    montanttotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    montantperMonth = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    nombre_months = models.CharField(max_length=255, default='')
    
    @property
    def end_month(self):
        end_date = self.date + timedelta(days=int(int(self.nombre_months) + 1) * 30)
        current_date = datetime.now()

        return end_date.replace(day=self.date.day)
        
class HeureSup(models.Model):
    nombre_heure = models.CharField(max_length=255, default='')
    date = models.DateTimeField(auto_now_add=True)
    datetimedeb = models.DateTimeField(default=datetime.now)
    datetimeend = models.DateTimeField(default=datetime.now)
    salarie = models.ForeignKey(Salarie, on_delete= models.CASCADE, related_name="mes_heure_sup", null=True, blank = True, default=None)
    motif = models.CharField(max_length=255, default='') 
    valide = models.BooleanField(default=True)
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, default=None, null=True, blank=True)
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE, default=None, null=True, blank=True)
    
class PrimeMotivation(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    salarie = models.ForeignKey(Salarie, on_delete= models.CASCADE, related_name="mes_primesmotivation", null=True, blank = True, default=None)
    motif = models.CharField(max_length=255, default='') 
    valide = models.BooleanField(default=True)
    montant = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    viremenet = models.BooleanField(default=True)
    
class Absence(models.Model):
    date = models.DateTimeField(auto_now_add=False)
    salarie = models.ForeignKey(Salarie, on_delete= models.CASCADE, related_name="mes_absences", null=True, blank = True, default=None)
    nombre_heure = models.CharField(max_length=255, default='')
    motif = models.CharField(max_length=255, default='') 
    minusSource = models.CharField(max_length=255, default='') 
    justifie = models.BooleanField(default=False)
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, default=None, null=True, blank=True)
    store = models.ForeignKey('clientInfo.store', on_delete=models.CASCADE, default=None, null=True, blank=True)
    
class Contrat(models.Model):
    salarie = models.ForeignKey(Salarie, on_delete= models.CASCADE, related_name="ma_contrat", null=True, blank = True, default=None)
    numero_contrat = models.CharField(max_length=255, default='')
    numero_decision_recrutement = models.CharField(max_length=255, default='')
    numero_pv_installation = models.CharField(max_length=255, default='')
    datedeb = models.DateTimeField(default=datetime.now)
    datesignature = models.DateTimeField(default=datetime.now)
    datefin = models.DateTimeField(default=datetime.now)
    type_contrat = models.CharField(max_length=255, default='')

class Renumeration(models.Model):
   mois = models.CharField(max_length=255, default='')
   salarie = models.ForeignKey(Salarie, on_delete= models.CASCADE, null=True, blank = True, default=None)
   virement_valide = models.BooleanField(default=False)

class BoiteArchive(models.Model):
   date = models.DateTimeField(auto_now_add=True)
   date_facturation_fournisseur = models.DateTimeField(auto_now_add=False)
   date_facturation_transitaire = models.DateTimeField(auto_now_add=False)
   montant = models.DecimalField(max_digits=35, decimal_places=2, default=0)
   typedocument  = models.CharField(max_length=255, default='')
   label  = models.CharField(max_length=255, default='')
   document = models.FileField(upload_to="media/document") 