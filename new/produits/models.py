from django.db import models
from wagtail.snippets.models import register_snippet
from clientInfo.models import store, typeClient
from users.models import CustomUser
from django.contrib.auth.models import Permission
from datetime import datetime, timedelta
from inventory.models import ProduitsEnBonEntry, ProduitsEnBonRetour
from ventes.models import ProduitsEnBonSortie
from comptoire.models import ProduitsEnBonComptoir
class ProduitsCustomPermission(Permission):
    class Meta:
        verbose_name = 'Custom Permission'
        verbose_name_plural = 'Custom Permissions'
       
class Category(models.Model):
     MotherCategory = models.ForeignKey('self', on_delete=models.SET_NULL, default=None, null=True, blank=True, related_name='variants')
     kit = models.BooleanField(default=True)
     kitcomponents = models.TextField(default='')
     Libellé = models.CharField(max_length=100)
     categoryDesc = models.CharField(max_length=250, default="", blank=True, null=True)
     status = models.BooleanField(default=True)
     pc_component = models.CharField(max_length=250, default="", blank=True, null=True)
     store=models.ForeignKey(store, on_delete=models.CASCADE, default=None, null=True, blank=True)
     
     def __str__(self) :
         return f'{self.Libellé}'
         
     @property
     def getkitComp(self):
        return eval(self.kitcomponents) if self.kitcomponents else []
        
     def get_products(self):
         return self.products.all()
               
class Product(models.Model):
    reference = models.CharField( ("Référence du produit"), help_text=("Référence interne pour ce produit"),
          max_length=120,
          blank=False,
          null=False,
          unique=False
    )
    parent_product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name="myvariants",default=None, null=True, blank=True)
    name = models.CharField( ("Désignation"), help_text=("La désignation du produit"),
        max_length=200,
        blank=False,
        null=True
    )
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products", blank=True, null=True)
    prix_vente = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    prix_vente_pc = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    prix_vente_kit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    prix_achat = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    prix_livraison = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tva = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tva_douan = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    marge = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    initial_qte = models.IntegerField()
    QuantityPerCarton = models.IntegerField(default=0)
    TotalQte = models.IntegerField(default=0)
    reforme = models.BooleanField(default=False)
    fournisseur = models.CharField(max_length=100, default='', blank=True)
    store = models.ForeignKey(store, on_delete=models.CASCADE, default=None, null=True, blank=True)
    
    def weekly_stock_report(self):
        # Initialize the result list
        report = []

        # Get the initial quantity for the first week
        initial_quantity = self.Totalquantity_initial

        # Set the start date to the first day of 2024
        start_date = datetime(2024, 1, 1)

        # Loop through each week of 2024
        for week in range(1, 53):
            # Calculate the end date of the current week
            end_date = start_date + timedelta(days=6)

            # Get the quantities for the current week
            entered_quantity = self.get_entered_quantity(start_date, end_date)
            sold_quantity = self.get_sold_quantity(start_date, end_date)
            returned_quantity = self.get_returned_quantity(start_date, end_date)
            final_quantity = initial_quantity + entered_quantity - sold_quantity + returned_quantity 

            # Append the data to the report list
            report.append({
                'week': week,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'reference': self.reference,
                'name': self.name,
                'categorie': self.category.pc_component if self.category else '',
                'initial_quantity': initial_quantity,
                'entered_quantity': entered_quantity,
                'sold_quantity': sold_quantity,
                'final_quantity': final_quantity,
                'returned_quantity': returned_quantity,
            })

            # Update the initial quantity for the next week
            initial_quantity = final_quantity

            # Move to the next week
            start_date = end_date + timedelta(days=1)

        return report


    def get_entered_quantity(self, start_date, end_date):
        # Calculate quantity from entry transactions within the given date range
        entry_quantity = ProduitsEnBonEntry.objects.filter(
            stock=self,
            BonNo__dateBon__range=[start_date, end_date]
        ).aggregate(models.Sum('quantity'))['quantity__sum'] or 0

        return entry_quantity 
    
    def get_returned_quantity(self, start_date, end_date):
        # Calculate quantity from entry transactions within the given date range
        entry_quantity = ProduitsEnBonRetour.objects.filter(
            produit=self,
            reintegrated =True,
            BonNo__dateBon__range=[start_date, end_date]
        ).aggregate(models.Sum('quantity'))['quantity__sum'] or 0

        return entry_quantity 

    def get_sold_quantity(self, start_date, end_date):
        produits_en_bon_sortie_list = ProduitsEnBonSortie.objects.filter(
            stock=self,
            BonNo__dateBon__range=[start_date, end_date]
        )

        filtered_produits_en_bon_sortie = [
            produit_en_bon_sortie for produit_en_bon_sortie in produits_en_bon_sortie_list
            if produit_en_bon_sortie.BonNo.get_etat_transfert
        ]

        sold_quantity = sum(produit_en_bon_sortie.quantity for produit_en_bon_sortie in filtered_produits_en_bon_sortie)

        return  sold_quantity
    
    @property
    def get_codeEA(self):
        codeean = self.moncodeEAN.filter(produit=self).first()
        if codeean :
            return codeean.code
        else:
            return ''
            
    @property
    def available_quantity(self):
        reforme_quantity = self.mes_bons_reforme.aggregate(total_reforme_quantity=models.Sum('quantity'))['total_reforme_quantity']
        return self.TotalQte - (reforme_quantity or 0)
        
    @property    
    def qty_in_store(self):
        product_first = Product.objects.filter(reference=self.reference, store__id=1).first()
        if product_first:
            return product_first.total_quantity_in_stock
        else:
            return 0
        
    @property
    def get_price_variants(self):
         produits_variants = self.produit_var.all()  
         variant_list = []
         for product in produits_variants:
             variant_list.append(float(product.prix_vente))
         return variant_list  
    
    @property
    def firstAchatBill(self):
        idBonFirst = self.mes_bons_achat.first()
        if idBonFirst:
            return idBonFirst.BonNo.idBon
        else:
            return ''
    
    @property
    def Totalquantity_initial(self):
        total_quantity_bl = sum(stock.quantity_initial for stock in self.mon_stock.all())
        return total_quantity_bl 
        
    @property
    def ancestor_categories(self):
        categories = []
        current_category = self.category
        while current_category:
            categories.append(current_category.Libellé)
            current_category = current_category.MotherCategory
        return categories
        
    @property
    def reforme_quantity(self):        
        reforme_quantity = self.mes_bons_reforme.aggregate(total_reforme_quantity=models.Sum('quantity'))['total_reforme_quantity']
        return reforme_quantity if reforme_quantity else 0
    
    def get_Monstock(self):
        return self.mon_stock.first()
        
    @property
    def total_quantity_in_stock(self):
        total_quantity = sum(stock.get_quantity for stock in self.mon_stock.all())
        return total_quantity

    
    @property
    def revendeur_price(self):
        try:
            obj = self.produit_var.filter(type_client__type_desc="Revendeur", produit=self).first()
            price =0
            if obj is not None:
                price = obj.prix_vente
            return price
        except variantsPrixClient.DoesNotExist:
            return self.prix_vente    
            
    @property
    def clientfinal_price(self):
        try:
            obj = self.produit_var.filter(type_client__type_desc="Client Final", produit=self).first()
            price =0
            if obj is not None:
                price = obj.prix_vente
            return price
        except variantsPrixClient.DoesNotExist:
            return self.prix_vente    
            
    @property
    def quantity_vendu(self):
        total_qte_compt = sum(stock.quantity for stock in self.bons_comptoir.all())
        total_quantity_bl = sum(stock.quantity for stock in self.bons_sortie.all())
        return total_quantity_bl + total_qte_compt 
        
    @property
    def quantity_retour(self):
        total_quantity_bl = sum(stock.quantity for stock in self.mes_bons_retour.all())
        return total_quantity_bl 
    
    def get_price_per_type(self, type, type_bill):
          price = 0
          try:
            if type_bill == 'kit':
                productins = self.produit_var.filter(type_client=type, produit=self).first()
                if productins is not None:
                    price = productins.prix_vente_kit
            elif type_bill == 'pc':
               productins = self.produit_var.filter(type_client=type, produit=self).first()
               if productins is not None:
                    price = productins.prix_vente_pc
            elif type_bill == 'carton':
               productins = self.produit_var.filter(type_client=type, produit=self).first()
               if productins is not None:
                    price = productins.prix_vente_carton        
            else:  
               productins = self.produit_var.filter(type_client=type, produit=self).first()
               if productins is not None:
                    price = productins.prix_vente
            return price
          except variantsPrixClient.DoesNotExist:
            return self.prix_vente    

    @property
    def quantities_per_entrepot(self):
        variant_quantities = {}

        # Helper function to update the quantities in the dictionary
        def update_quantities(entrepot_name, quantity, quantity_kit, quantity_pc):
            if entrepot_name in variant_quantities:
                variant_quantities[entrepot_name]['quantity'] += quantity
                variant_quantities[entrepot_name]['quantity_kit'] += quantity_kit
                variant_quantities[entrepot_name]['quantity_pc'] += quantity_pc
            else:
                variant_quantities[entrepot_name] = {
                    'quantity': quantity,
                    'quantity_kit': quantity_kit,
                    'quantity_pc': quantity_pc,
                }

        # Check if the product has variants
        if self.myvariants.exists():
            # Iterate through variants and sum quantities by entrepot
            for variant in self.myvariants.all():
                for stock_entry in variant.mon_stock.all():
                    entrepot_name = stock_entry.entrepot.name
                    quantity = stock_entry.get_quantity
                    quantity_kit = stock_entry.quantity_kit
                    quantity_pc = stock_entry.quantity_pc
                    update_quantities(entrepot_name, quantity, quantity_kit, quantity_pc)
        else:
            # If no variants, use the quantities of the main product
            for stock_entry in self.mon_stock.all():
                entrepot_name = stock_entry.entrepot.name
                quantity = stock_entry.get_quantity
                quantity_kit = stock_entry.quantity_kit
                quantity_pc = stock_entry.quantity_pc
                update_quantities(entrepot_name, quantity, quantity_kit, quantity_pc)

        return variant_quantities    
        
    @property
    def quantitiesblocked_per_entrepot(self):
        variant_quantities = {}
        for stock_entry in self.mon_stock.all():
            entrepot_name = stock_entry.entrepot.name
            quantity = stock_entry.quantity_blocked
            # Update the variant_quantities dictionary
            if entrepot_name in variant_quantities:
                    variant_quantities[entrepot_name] += quantity
            else:
                    variant_quantities[entrepot_name] = quantity
        return variant_quantities     
    
    def is_integrated(self):
        # Check if the product is integrated in any related objects
        related_names = [
           'mes_bons_reforme', 'mes_bons_retour','bons_entry','bons_reintegration' , 'bons_sorties_stock', 'bons_sortie' ,
           'mes_bons_garantie', 'mes_bons_devis', 'mes_bons_commande', 'facture', 'mes_bons_achat','mes_bons_retourcomptoir' , 'bons_comptoir'
        ]

        for related_name in related_names:
            related_manager = getattr(self, related_name.lower())
            if related_manager.all().count() > 0:
                 return True

        return False
    
    def __str__(self):
	    return f"Name: {self.name}, ID: {self.id}"

class HistoriqueAchatProduit(models.Model):
    produit =  models.ForeignKey(Product, on_delete=models.CASCADE, related_name='monHIstoriqueAchat',  default=None, null=True, blank=True) 
    qty_qctuelle = models.IntegerField(default= 0)
    prix_achat_actuelle = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    qty_achete = models.IntegerField(default= 0)
    prix_achat= models.DecimalField(max_digits=15, decimal_places=2, default=0)
    prix_achat_calcule = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    dateAchat = models.DateField()
    
class codeEA(models.Model):
    produit =  models.ForeignKey(Product, on_delete=models.CASCADE, related_name='moncodeEAN',  default=None, null=True, blank=True)
    code = models.CharField(max_length=250)

    
class NumSeries(models.Model):
    produit =  models.ForeignKey(Product, on_delete=models.CASCADE, related_name='myserialnumbers',  default=None, null=True, blank=True)
    numseries = models.CharField(max_length=250)
    used = models.BooleanField(default=False)
  
   
class variantsPrixClient(models.Model):
     type_client = models.ForeignKey('clientInfo.typeClient', on_delete=models.CASCADE, related_name="prix_var",default='', blank=True)
     produit =  models.ForeignKey(Product, on_delete=models.CASCADE, related_name="produit_var",default='', blank=True)
     prix_vente = models.DecimalField(max_digits=15, decimal_places=2, default=0)
     prix_vente_pc = models.DecimalField(max_digits=15, decimal_places=2, default=0)
     prix_vente_kit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
     prix_vente_carton = models.DecimalField(max_digits=15, decimal_places=2, default=0)
     
class Promotion(models.Model):
    type_client = models.ForeignKey('clientInfo.TypeClient', on_delete=models.CASCADE,
                                    related_name="promotions", default='', blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="promotions",
                                default='', blank=True)
    prix_vente = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    prix_vente_pc = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    prix_vente_kit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    prix_vente_carton = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    start_date = models.DateField()
    end_date = models.DateField()
    
class Variantes_product(models.Model):
    variant_lib = models.CharField(max_length=100)
    values_list = models.CharField(max_length=25)
    def __str__(self):
	    return f'{self.variant_lib} : {self.values_list}' 
    
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variant_set')
    variant = models.ForeignKey(Variantes_product, on_delete=models.CASCADE, related_name='variant_set', default=None, null=True, blank=True)
    value = models.CharField(max_length=10)
    quantity = models.PositiveIntegerField(default=0)
    reference = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
	    return f'{self.product} : {self.variant}' 
    
class historique_prix_achat(models.Model):
     product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="products",default='', blank=True)
     version = models.IntegerField()
     prix_achat_original = models.DecimalField(max_digits=15, decimal_places=2, default=0)
     prix_achat_newer = models.DecimalField(max_digits=15, decimal_places=2, default=0)
  
class VerificationArchive(models.Model):
    codeArchive = models.CharField(max_length=255)
    store = models.ForeignKey(store, on_delete=models.CASCADE, null=True, blank=True)
    entrepot = models.ForeignKey('inventory.Entrepot', on_delete=models.CASCADE, null=True, blank=True)
    date_verification = models.DateTimeField(auto_now_add=True)
    def get_produit(self):
         return self.produits_verification.all()
      
class ListProductVerificationArchive(models.Model):
    verification = models.ForeignKey(VerificationArchive, on_delete=models.CASCADE, related_name="produits_verification")
    product_reference = models.CharField(max_length=255)
    realQuantity = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField()
    verification_result = models.CharField(max_length=255)