def post(self, request, *args, **kwargs):     
      data = json.loads(request.body)
      dataInvoice = data.get('formData', '')
      Currentuser = request.user
      myuser  = CustomUser.objects.get(username=Currentuser.username)
      store_id = self.request.session["store"]
      CurrentStore = store.objects.get(pk=store_id)
      if dataInvoice:
        print(dataInvoice)
        idBon = dataInvoice["IdBon"]
        dateBon = dataInvoice["dateBp"]
        total = dataInvoice['total']
     
        client_info = dataInvoice['clientInfo']
        # Create or get the client
        client_name = client_info['name']
        client_address = client_info['address']
        client_phone = client_info['phone']

        client, _ = Client.objects.get_or_create(name=client_name, adresse=client_address, phone=client_phone,user=myuser)
        client.solde += total
        client.save()
        products_to_update = []   
        qte_transfered = 0   
        currentEntrepot = Entrepot.objects.get(name=dataInvoice["entrepotBon"]) 
        if dataInvoice["creationAutomatique"]:
          productsdifferent = dataInvoice["productsdifferent"]
          with transaction.atomic():
              for product in productsdifferent:
                stock_in_source = Stock.objects.select_for_update().get(
                    product__reference=product["reference"], entrepot__name=product["entrepot"]
                )
                
                new_quantity_in_source = stock_in_source.quantity - int(product["quantity"])

                # Check if the source warehouse has enough quantity
                if new_quantity_in_source < 0:
                    return JsonResponse({
                        'error': f"Insufficient stock for product: {product['reference']}",
                        'prompt_user': True
                    })

                products_to_update.append((stock_in_source, new_quantity_in_source))
                ent_arrive = Entrepot.objects.get(name=currentEntrepot)
                # Retrieve or create the stock entry in the destination warehouse (ent_arr)
                stock_in_destination, created = Stock.objects.get_or_create(
                    product=stock_in_source.product,
                    entrepot=ent_arrive,
                    defaults={'quantity': 0}  # Initialize with zero quantity if creating
                )

                # Update the quantity in the destination warehouse
                stock_in_destination.quantity += int(product["quantity"])
                stock_in_destination.save()
                print("before",qte_transfered)
                qte_transfered += int(product["quantity"])
                print("after",qte_transfered)
                ent_depart = Entrepot.objects.get(name=product["entrepot"])
                ent_arriv = Entrepot.objects.get(name=currentEntrepot)
                 # Update source warehouse quantities and create transfer bill
                current_year = datetime.now().strftime('%y')
                current_month = datetime.now().strftime('%m')
                last_bon = BonTransfert.objects.order_by('-id').first()
                if last_bon:
                  last_id = last_bon.idBon.split('-')[-1]  # Extract the last part of the ID
                  if last_id.isnumeric():
                    sequence_number = int(last_id) + 1
                  else:
                   sequence_number = 1
                else:
                  sequence_number = 1
                codeBon =f'BT{current_year}{current_month}-{sequence_number}'
                bon_trans = BonTransfert.objects.create(
                 idBon=codeBon,
                 dateBon=dataInvoice["dateBp"],
                 entrepot_depart=ent_depart,
                 entrepot_arrive=ent_arriv,
                 store=CurrentStore,
                 user=myuser
                )

                for stock, new_quantity in products_to_update:
                  stock.quantity = new_quantity
                  stock.save()
                  stock_dep = Stock.objects.get(
                     product__reference=product["reference"], entrepot__name=ent_depart
                  )
                  stock_arr = Stock.objects.get(
                    product=stock_in_source.product,
                    entrepot__name=currentEntrepot
                  )
                  # Create a record in ProduitsEnBonSortie for the transfer
                  ProduitsEnBonTransfert.objects.create(
                    BonNo=bon_trans,
                    stock_dep=stock_dep,
                    stock_arr= stock_arr,
                    quantity=int(product["quantity"]),                 
                  )
                  manager_user = CustomUser.objects.filter(role='manager').first()
                  if manager_user:
                        notify.send(
                            sender=myuser,
                            recipient=manager_user,
                            verb=f'Bon de transfert numero {codeBon} a été créer automatiquement par {myuser} :.',
                            level=1,
                        )
            
         
       
        for product in dataInvoice["produits"]:
            from django.db.models import Q
            p = Stock.objects.select_for_update().get( Q(product__reference=product["ref"]) & Q(entrepot__name=currentEntrepot))
            print(p.entrepot.name,p.quantity)
            # Ensure the quantity is greater than or equal to 0 after updating
            print(qte_transfered)
            quantity_in_bill = qte_transfered + int(product["qty"])
            print(quantity_in_bill, qte_transfered)
            new_quantity = p.quantity - quantity_in_bill ## la quantité dans l'entrepot qui convient
            print(p.entrepot.name,p.quantity)
            if new_quantity < 0:
                # If any product has insufficient quantity, return a response to inform the user
                return JsonResponse({'error': f"Insufficient stock for product: {product['ref']}", 'prompt_user': True})
             
            products_to_update.append((p, new_quantity))
       
        with transaction.atomic():
            for product, new_quantity in products_to_update:                             
                product.quantity = new_quantity
                product.save()

            bon_sortie = models.BonSortie.objects.create(idBon=idBon, dateBon=dateBon, totalPrice=total, client=client, user=myuser, store=CurrentStore)
            for product in dataInvoice["produits"]:
                p = Product.objects.get(reference=product["ref"])
                p.TotalQte -= int(product["qty"])
                p.save()
                prod_total_price = p.prix_vente * int(product["qty"])
                entrepot_inst = Entrepot.objects.get(name=product["ent"])
                models.ProduitsEnBonSortie.objects.create(
                    BonNo=bon_sortie,
                    stock=p,
                    entrepot=entrepot_inst,
                    quantity=int(product["qty"]),
                    unitprice=p.prix_vente,
                    totalprice=prod_total_price
                )
        return JsonResponse({'message': "Product Added successfully."})