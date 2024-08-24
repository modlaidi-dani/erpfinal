from django.db import models
from datetime import timedelta
from django.contrib.auth.models import Permission
from tiers.models import Client
import ast
from ventes.models import BonSortie, ProduitsEnBonSortie
from django.db.models import Sum, F, FloatField
from collections import defaultdict
from decimal import Decimal
import json
from produits.models import Product
from django.db.models import  Prefetch
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Q

class TargetCustomPermission(Permission):
    class Meta:
        verbose_name = 'Custom Permission'
        verbose_name_plural = 'Custom Permissions'
        
class Target(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    is_done = models.BooleanField(default=False)   
    user = models.ForeignKey('users.CustomUser', related_name="my_target" ,on_delete=models.CASCADE, default=None, null=True, blank=True)
    team = models.ForeignKey('users.Equipe',related_name="team_target", on_delete=models.CASCADE, default=None, null=True, blank=True)
    seuil_prime = models.CharField(max_length=255, default = '')
    prime = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    def __str__(self):
        return self.name
        
    @property
    def formatted_dateDeb(self):
        return self.start_date.strftime('%Y-%m-%d')
    
    @property
    def formatted_dateEnd(self):
        return self.end_date.strftime('%Y-%m-%d')
        
    @property
    def target_ca(self):
        target_products = TargetProduct.objects.filter(target=self)   
        total_ca = sum(float(target_product.product.revendeur_price + target_product.product.prix_livraison + target_product.product.tva_douan) * 1.19 * target_product.quantity for target_product in target_products)
        return round(total_ca,2)
    
    @property
    def target_ca_accomplished(self):
        total_ca_acc  = sum(product["price"]  for product in self.target_products_stat)
        return total_ca_acc
    
    @property
    def target_store(self):
        if self.user:
            return self.user.EmployeeAt
        else:
           return self.team.mes_membres.first().EmployeeAt
    
    @property
    def target_total_qte(self):
        target_products = TargetProduct.objects.filter(target=self)
        # Calculate total quantity expected
        total_quantity_expected = sum(target_product.quantity for target_product in target_products)
        return total_quantity_expected

    @property
    def total_quantity_rsold(self):
       total_quantity_sold = sum(product["quantity_sold"]for product in self.target_products_stat or 0)
       
       return total_quantity_sold
   
    @property
    def total_quantity_sold(self):
        total_quantity_sold = sum(product["quantity_sold"] if product["quantity_sold"] < product["quantity_to_sell"] else product["quantity_to_sell"] for product in self.target_products_stat)
        return total_quantity_sold
    
    @property
    def target_products_stat(self):
        target_products = TargetProduct.objects.filter(target=self)
        team_members = self.team.mes_membres.all() if self.team else []
        user_list = list(team_members)
        data = []
        for target_product in target_products:
            product = target_product.product
            quantity_to_sell = target_product.quantity

            # Calculate total quantity sold (combined bons_sortie and bons_comptoir)
            bons_sortie_quantity = product.bons_sortie.filter(
                BonNo__dateBon__gte=self.start_date,
                BonNo__dateBon__lte=self.end_date,
                BonNo__user__in=user_list + [self.user]
            ).aggregate(total_quantity_sold=Sum('quantity'))['total_quantity_sold'] or 0

            # Query for bons_comptoir
            bons_comptoir_quantity = product.bons_comptoir.filter(
                BonNo__dateBon__gte=self.start_date,
                BonNo__dateBon__lte=self.end_date,
                BonNo__user__in=user_list + [self.user]
            ).aggregate(total_quantity_sold=Sum('quantity'))['total_quantity_sold'] or 0

            # Calculate total quantity sold
            total_quantity_sold = bons_sortie_quantity + bons_comptoir_quantity
            # Add product information to data dictionary
            price_product =round(float(product.revendeur_price + product.prix_livraison + product.tva_douan)* 1.19 * total_quantity_sold if total_quantity_sold < quantity_to_sell else float(product.revendeur_price + product.prix_livraison + product.tva_douan) * 1.19 * quantity_to_sell ,2)
            data.append({
                "ref": product.reference,  # Assuming 'ref' is the product reference field
                "name": product.name,  # Assuming 'ref' is the product reference field
                "quantity_to_sell": quantity_to_sell,
                "quantity_sold": total_quantity_sold,
                "price": price_product,   # Assuming 'price' is the product price field
            })
        with open('targetData.json', 'w') as f:
            json.dump(data, f, indent=4)  # Add indent for readability
        return data
    
    @property
    def get_taux_completion(self):
        # Get all target products for this target
        target_products = TargetProduct.objects.filter(target=self)

        # Get the team members
        team_members = self.team.mes_membres.all() if self.team else []

        # Calculate total quantity expected
        total_quantity_expected = sum(target_product.quantity for target_product in target_products)
        # Calculate the completion rate as a percentage
        if total_quantity_expected > 0:
            completion_rate = (self.total_quantity_sold / total_quantity_expected) * 100
        else:
            completion_rate = 0

        return completion_rate
    
    @property
    def get_taux_Overcompletion(self):
        # Get all target products for this target
        target_products = TargetProduct.objects.filter(target=self)

        # Get the team members
        team_members = self.team.mes_membres.all() if self.team else []

        # Calculate total quantity expected
        total_quantity_expected = sum(target_product.quantity for target_product in target_products)
        # Calculate the completion rate as a percentage
        if total_quantity_expected > 0:
            completion_rate = (self.total_quantity_rsold / total_quantity_expected) * 100
        else:
            completion_rate = 0

        return completion_rate
    
    @property
    def get_bills(self):
        bills = []
        target_products = TargetProduct.objects.filter(target=self)
        team_members = self.team.mes_membres.all() if self.team else []

        for target_product in target_products:
            for produit in target_product.product.bons_sortie.all():
                if (
                    produit.BonNo.dateBon >= self.start_date
                    and produit.BonNo.dateBon <= self.end_date
                    and (produit.BonNo.user == self.user or produit.BonNo.user in team_members)
                    and produit.BonNo.idBon not in [bill['idBon'] for bill in bills]
                ):
                    bill_details = {
                        'idBon': produit.BonNo.idBon,
                        'dateBon': produit.BonNo.dateBon,
                        'client': produit.BonNo.client.name,
                        'regle': produit.BonNo.regle,
                        'prix': produit.BonNo.get_total_price,
                        'user': produit.BonNo.user.username,
                    }
                    bills.append(bill_details)

            for produit in target_product.product.bons_comptoir.all():
                if (
                    produit.BonNo.dateBon >= self.start_date
                    and produit.BonNo.dateBon <= self.end_date
                    and (produit.BonNo.user == self.user or produit.BonNo.user in team_members)
                    and produit.BonNo.idBon not in [bill['idBon'] for bill in bills]
                ):
                    bill_details = {
                        'idBon': produit.BonNo.idBon,
                        'dateBon': produit.BonNo.dateBon,
                        'client': produit.BonNo.client.name,
                        'regle': produit.BonNo.regle,
                        'prix': produit.BonNo.prixtotal,
                        'user': produit.BonNo.user.username,
                    }
                    bills.append(bill_details)

        return bills
        
    @property
    def get_taux_completion_per_member(self):
        # Get all target products for this target
        target_products = TargetProduct.objects.filter(target=self)

        # Get the team members
        team_members = self.team.mes_membres.all() if self.team else []

        # Initialize an empty list to store completion rates for each member
        completion_rates = []

        for member in team_members:
            # Calculate total quantity expected for the member
            total_quantity_expected_member = sum(
                target_product.quantity
                for target_product in target_products
            )
             
            
            # Calculate total quantity sold for the member in ProduitsEnBonSortie
            total_quantity_sold_sortie_member = sum(
                produit.quantity
                for target_product in target_products
                for produit in target_product.product.bons_sortie.all()
                if (
                    produit.BonNo.dateBon >= self.start_date
                    and produit.BonNo.dateBon <= self.end_date
                    and produit.BonNo.user == member
                )
            )
            
            # Calculate total quantity sold for the member in ProduitsEnBonComptoir
            total_quantity_sold_comptoir_member = sum(
                produit.quantity
                for target_product in target_products
                for produit in target_product.product.bons_comptoir.all()
                if (
                    produit.BonNo.dateBon >= self.start_date
                    and produit.BonNo.dateBon <= self.end_date
                    and produit.BonNo.user == member
                )
            )
           
            # Calculate the total quantity sold for the member
            total_quantity_sold_member = (
                total_quantity_sold_sortie_member + total_quantity_sold_comptoir_member
            )

            # Calculate the completion rate for the member as a percentage
            if total_quantity_expected_member > 0:
                completion_rate_member = (
                    total_quantity_sold_member / total_quantity_expected_member
                ) * 100
            else:
                completion_rate_member = 0


            completion_rates.append({"name": member.username,"quantity_sold":total_quantity_sold_sortie_member, "percent": completion_rate_member})

        return completion_rates
    
    @property
    def get_taux_cacompletion_per_member(self):
        # Get all target products for this target
        target_products = TargetProduct.objects.filter(target=self)

        # Get the team members
        team_members = self.team.mes_membres.all() if self.team else []

        # Initialize an empty list to store completion rates for each member
        completion_rates = []

        for member in team_members:
            total_quantity_sold_sortie_member = 0
            total_quantity_sold_comptoir_member = 0

            for target_product in target_products:
                # Track quantity sold for the current target product
                sold_quantity_sortie = 0
                sold_quantity_comptoir = 0

                for produit in target_product.product.bons_sortie.all():
                    if (
                        produit.BonNo.dateBon >= self.start_date
                        and produit.BonNo.dateBon <= self.end_date
                        and produit.BonNo.user == member
                    ):
                        # Check if exceeding target quantity (sortie)
                        if sold_quantity_sortie + produit.quantity > target_product.quantity:
                            # Don't sum, directly use target quantity
                            total_price = (
                                Decimal(target_product.product.revendeur_price)
                                + Decimal(target_product.product.prix_livraison)
                                + Decimal(target_product.product.tva_douan)
                            )
                            total_quantity_sold_sortie_member += target_product.quantity * total_price * Decimal(1.19)
                            break  # Exit inner loop for this target product

                        else:
                            sold_quantity_sortie += produit.quantity
                            total_quantity_sold_sortie_member += (
                                Decimal(produit.unitprice) * Decimal(1.19) * produit.quantity
                            )

                for produit in target_product.product.bons_comptoir.all():
                    if (
                        produit.BonNo.dateBon >= self.start_date
                        and produit.BonNo.dateBon <= self.end_date
                        and produit.BonNo.user == member
                    ):
                        # Check if exceeding target quantity (comptoir)
                        if sold_quantity_comptoir + produit.quantity > target_product.quantity:
                            # Don't sum, directly use target quantity
                            total_quantity_sold_comptoir_member +=target_product.quantity * float(target_product.product.revendeur_price + target_product.product.prix_livraison + target_product.product.tva_douan)* 1.19
                            break  # Exit inner loop for this target product

                        else:
                            # Add to sold quantity and potentially continue
                            sold_quantity_comptoir += produit.quantity
                            total_quantity_sold_comptoir_member += produit.unitprice * produit.quantity

            # Total quantity sold for the member (considering targets)
            total_quantity_sold_sortie_member = sum([total_quantity_sold_sortie_member])
            total_quantity_sold_comptoir_member = sum([total_quantity_sold_comptoir_member])
            # Calculate the total quantity sold for the member
            total_quantity_sold_member = (
                total_quantity_sold_sortie_member + total_quantity_sold_comptoir_member
            )

            # Calculate the completion rate for the member as a percentage
            if self.target_ca > 0:
                completion_rate_member = (
                    float(total_quantity_sold_sortie_member) / float(self.target_ca)
                ) * 100
            else:
                completion_rate_member = 0


            completion_rates.append({"name": member.username, "quantity_sold":round(float(total_quantity_sold_sortie_member),2),  "percent": float(completion_rate_member)
                                     })
        with open('targetPerUserData.json', 'w') as f:
            json.dump(completion_rates, f, indent=4)  # Add indent for readability
        return completion_rates

class TargetProduct(models.Model):
    target = models.ForeignKey(Target, on_delete=models.CASCADE, related_name="target_products", default=None, null=True, blank=True)
    product = models.ForeignKey('produits.Product', default=None, null=True, blank=True , on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    chiffreAffaire = models.DecimalField(max_digits=35, decimal_places=2, default=0)

class SalesPrediction(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True, default=None, related_name="mes_previsions")
    date_start = models.DateField()
    date_end = models.DateField()
    store = models.ForeignKey('clientInfo.store', related_name = "previsionsclient", on_delete=models.CASCADE, null=True, blank=True, default=None)            
    
    class Meta:
        unique_together = ('client', 'date_start', 'date_end')

    def __str__(self):
        return (f"{self.client.name} -  "
                f"{self.date_start} to {self.date_end}")

class ComponentsInPrediction(models.Model):
    prevision = models.ForeignKey(SalesPrediction, on_delete=models.CASCADE, null=True, blank=True, default=None, related_name="quantity_previsions")
    component = models.TextField(default="")
    predicted_quantity = models.PositiveIntegerField()
    
    @property
    def prediction_stats(self):
        prediction = self.prevision
        products_component = ProduitsEnBonSortie.objects.filter(
            stock__category__pc_component=self.component, 
            stock__store=self.prevision.store,
            BonNo__dateBon__gte=self.prevision.date_start,
            BonNo__dateBon__lte=self.prevision.date_end,
            BonNo__client=self.prevision.client
        )

        # Aggregate total quantity and total price sold in a single query
        sold_details = products_component.aggregate(
            total_quantity_sold=Sum('quantity'),
            total_price_sold=Sum(F('totalprice') * 1.19, output_field=FloatField())
        )

        quantity_sold = sold_details.get('total_quantity_sold') or 0
        total_revenue = sold_details.get('total_price_sold') or 0

        # Query to get the name, reference, quantity sold, and price sold for each product
        product_references = products_component.values(
            'stock__name', 'stock__reference'
        ).annotate(
            quantity_sold=Sum('quantity'),
            price_sold=Sum(F('totalprice') * 1.19 , output_field=FloatField())
        )

        # Prepare the list of product references with their quantities and prices sold
        sold_products = [
            {
                'name': item['stock__name'], 
                'reference': item['stock__reference'], 
                'quantity_sold': item['quantity_sold'],
                'price_sold': item['price_sold']
            }
            for item in product_references
        ]

        return {
            'composant': self.component,
            'predicted_quantity': self.predicted_quantity,
            'sold_quantity': quantity_sold,
            'total_revenue': total_revenue,
            'sold_products': sold_products
        }
        
        
class PrevisionClient(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    region = models.ForeignKey('tiers.region',on_delete = models.CASCADE, related_name='client_prev', default=None, null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    is_done = models.BooleanField(default=False)  
    store = models.ForeignKey('clientInfo.store', related_name = "store_previsionclient", on_delete=models.CASCADE, null=True, blank=True, default=None)
    
    
    @property
    def get_completion_per_region(self):
        categories_quantities = self.get_product_category
        completion_statuses = self.get_product_sold
        # Calculate the completion rate for each category
        
        completion_rates = []
        for completion_status in completion_statuses:
            category = completion_status['category']
            completion_quantity = completion_status['quantity']
            # Find the quantity in 'categories_quantities' for the same category
            category_quantity = next((item['quantity'] for item in categories_quantities if item['category'] == category), 0)
            # Calculate the completion rate as a percentage
            if category_quantity > 0:
                rate = round(((completion_quantity / category_quantity) * 100),2)
            else:
                rate = 0
            completion_rates.append({'category': category, 'quantity_sold': completion_quantity, 'quantity_required': category_quantity,  'completion_rate': rate})

        return(completion_rates)

    @property
    def get_total_completion(self):
        categories_quantities = self.get_product_category
        completion_statuses = self.get_product_sold
        
        total_qte = sum(item['quantity'] for item in categories_quantities)
        total_qte_sold = sum(item['quantity'] for item in completion_statuses)

        # Calculate the percentage of quantity sold in the total quantity
        if total_qte > 0:
            completion_percentage = round((total_qte_sold / total_qte) * 100, 2)
        else:
            completion_percentage = 0
        return completion_percentage
        
    @property
    def get_product_sold(self):
        region = self.region
        if not region:
            return None 
        
        wilayas_list = ast.literal_eval(region.wilayas)
        region_clients = Client.objects.filter(region_client__in=wilayas_list, store__id=1)
        
        region_bills = BonSortie.objects.filter(client__in=region_clients, dateBon__range=[self.start_date, self.end_date], store__id=1)
        completion_statuses = []

        for bill in region_bills:
            for product in bill.produits_en_bon_sorties.all():
                category = product.stock.category.pc_component
                quantity = product.quantity
                
                # Check if the category already exists in completion_statuses
                category_exists = False
                for entry in completion_statuses:
                    if entry['category'] == category:
                        entry['quantity'] += quantity
                        category_exists = True
                        break
                
                # If the category doesn't exist, add a new entry
                if not category_exists:
                    completion_statuses.append({'category': category, 'quantity': quantity})
                    
        return completion_statuses            
    
    @property
    def get_product_category(self):
        region = self.region
        if not region:
            return None  # No region associated with this PrevisionClient

        # Get all ProductPrevision instances related to this PrevisionClient
        products = self.prevision_products.all()

        # Create a list to store dictionaries for each category and quantity
        categories_quantities = []

        for product in products:
            category = product.categorie
            quantity = product.quantity
            categories_quantities.append({'category': category, 'quantity': quantity})
            
        return categories_quantities

    @property
    def get_completion_per_wilaya(self):
        region = self.region
        if not region:
            return None

        region_clients = region.getClients()

        # Get the length of the result
        clients_length = len(region_clients)
        wilayas_list = ast.literal_eval(region.wilayas)
        completion_statuses = []
        
        for wilaya in wilayas_list:
            # Get clients for the current wilaya
            wilaya_clients = Client.objects.filter(region_client=wilaya, store__id=1)
            # Get ProductPrevision instances for the current wilaya and category
            wilaya_products = ProductPrevision.objects.filter(prevision__region=region, wilaya=wilaya)

            # Calculate total initial quantity for the current wilaya
            initial_qte = wilaya_products.aggregate(Sum('quantity'))['quantity__sum'] or 0

            # Get bills for the clients within the date range
            wilaya_bills = BonSortie.objects.filter(client__in=wilaya_clients, dateBon__range=[self.start_date, self.end_date])

            # Calculate total quantity sold for the current wilaya
            wilaya_quantity_sold = 0
            for bill in wilaya_bills:
                for product in bill.produits_en_bon_sorties.all():
                    quantity = product.quantity
                    wilaya_quantity_sold += quantity

            # Get ProductPrevision instances for the specified wilaya and category
            wilaya_products = ProductPrevision.objects.filter(prevision__region=region, wilaya=wilaya)

            # Calculate total initial quantity for the specified wilaya
            initial_qte_per_category = defaultdict(int)
            for product in wilaya_products:
                category = product.categorie
                initial_qte_per_category[category] += product.quantity

            # Get bills for the clients within the date range
            wilaya_bills = BonSortie.objects.filter(client__region_client=wilaya, dateBon__range=[self.start_date, self.end_date])

            # Calculate quantities sold for each category for the specified wilaya
            quantities_sold_per_category = defaultdict(int)
            for bill in wilaya_bills:
                for product in bill.produits_en_bon_sorties.all():
                    category = product.stock.category.pc_component
                    quantity = product.quantity
                    quantities_sold_per_category[category] += quantity

            # Convert the defaultdict to a list of dictionaries
            result = [{'category': category, 'initial_quantity': initial_qte_per_category[category],
                       'quantity_sold': quantities_sold_per_category[category]} for category in quantities_sold_per_category]

            # Append the result to the completion_statuses list
            completion_statuses.append({
                'name': wilaya,
                'initial_quantity': initial_qte,
                'quantity_sold': wilaya_quantity_sold,
                'percent': round(((wilaya_quantity_sold / initial_qte) * 100), 2) if initial_qte > 0 else 0,
                'qte_per_cat': result
            })

        return completion_statuses

  
    def get_statistiques_wilaya(self, wilaya):
        wilaya_products = ProductPrevision.objects.filter(prevision=self, wilaya=wilaya)
        region = self.region
        if not region:
            return None 
            
        wilayas_list = ast.literal_eval(region.wilayas)
        # Calculate total initial quantity for the current wilaya
        initial_qte = (wilaya_products.aggregate(Sum('quantity'))['quantity__sum'] or 0) / len(wilayas_list)
        
        # Get all clients in the specified region
        all_clients = Client.objects.filter(region_client=wilaya, store__id = 1)
        
        # Get bills for the clients within the date range
        wilaya_bills = BonSortie.objects.filter(client__in=all_clients, dateBon__range=[self.start_date, self.end_date])

        # Calculate total quantity sold and initial quantity for the current wilaya
        wilaya_quantity_sold = 0
        quantities_sold_per_category = defaultdict(int)
        initial_quantity_per_category = defaultdict(int)

        for bill in wilaya_bills:
            for product in bill.produits_en_bon_sorties.all():
                category = product.stock.category.pc_component
                quantity_sold = product.quantity
                initial_quantity = ProductPrevision.objects.get(prevision = self, categorie=category, wilaya= wilaya).quantity
                quantities_sold_per_category[category] += quantity_sold
                initial_quantity_per_category[category] += initial_quantity
                wilaya_quantity_sold += quantity_sold

        # Calculate quantities sold per client per category
        quantities_sold_per_client = defaultdict(lambda: defaultdict(int))
        for bill in wilaya_bills:
            for product in bill.produits_en_bon_sorties.all():
                category = product.stock.category.pc_component
                quantity_sold = product.quantity
                quantities_sold_per_client[bill.client.id][category] += quantity_sold
                
        wilaya_products = ProductPrevision.objects.filter(prevision__region=region, wilaya=wilaya)
        # Calculate total initial quantity for the specified wilaya
        initial_qte_client = int(initial_qte / len(all_clients))
        # Convert the defaultdict to a list of dictionaries for each client
        client_statistics = []
        for client in all_clients:
            client_stats = {
                'client_id': client.name,
                'initial_quantity_client': initial_qte_client,
                'percent': round((( (sum(quantities_sold_per_client[client.id].values())) / initial_qte_client
                ) * 100),2),
                'client_total_quantity_sold': sum(quantities_sold_per_client[client.id].values()),
                'quantities_sold_per_category': [{'category': category,
                                                  'quantity_sold': quantities_sold_per_client[client.id][category],                                                 
                                                  'initial_quantity': initial_quantity_per_category[category]} for category in quantities_sold_per_client[client.id]]
            }
            client_statistics.append(client_stats)

        result = {
            'initial_quantity': initial_qte,
            'total_quantity_sold': wilaya_quantity_sold,
            'quantities_sold_per_category': [{'category': category,
                                              'quantity_sold': quantities_sold_per_category[category],
                                              'initial_quantity': initial_quantity_per_category[category]} for category in quantities_sold_per_category],
            'client_statistics': client_statistics
        }

        return result
            
            
class ProductPrevision(models.Model):
    prevision = models.ForeignKey(PrevisionClient, on_delete=models.CASCADE, related_name="prevision_products", default=None, null=True, blank=True)
    wilaya = models.TextField(default="", null=True, blank=True)
    categorie = models.TextField(default="", null=True, blank=True)
    quantity = models.PositiveIntegerField()
  
class PrevisionGlobal(models.Model):
    designation = models.TextField()
    qty_prevu = models.PositiveIntegerField()
    ca_prevu = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    date_creation = models.DateField()
    period =  models.CharField(max_length=255, null=True, blank=True, default='')
    store = models.ForeignKey('clientInfo.store', related_name = "store_previsionglobal", on_delete=models.CASCADE, null=True, blank=True, default=None)
    
    @classmethod
    def get_active_prevision(cls, date_start, date_end):
        search_duration = date_end - date_start
        period_duration = {
            'annuel': 365,
            'trimestriel': 3 * 30,  # approximating trimester as 3 months
            'mensuel': 30,  # approximating month as 30 days
        }.get(cls.period, 30)  # default to 30 days if period is unspecified
        periods_count = int(search_duration.days / period_duration)
        active_end_date = date_end - timedelta(days=(search_duration.days % period_duration))
        active_start_date = active_end_date - timedelta(days=(period_duration - 1))
        active_previsions = cls.objects.filter(
            Q(date_creation__lte=active_end_date) & Q(date_creation__gte=active_start_date)
        )
        
        return active_previsions