import sqlite3
from pprint import pprint  # Pour un affichage clair

# Fonction pour se connecter à la base de données
def connect_db(database_path):
    return sqlite3.connect(database_path)

# Fonction pour récupérer les ordres
def get_orders(conn):
    cursor = conn.cursor()
    # Requête pour récupérer pc_created_id de l'ordre
    query = "SELECT id, pc_created_id FROM production_ordrefabrication"
    cursor.execute(query)
    return cursor.fetchall()

# Fonction pour récupérer la quantité du premier produit associé à un ordre
def get_first_product_quantity(conn, order_id):
    cursor = conn.cursor()
    # Requête pour récupérer la quantité du premier produit
    query = """
    SELECT quantity
    FROM production_produitsenordrefabrication
    WHERE BonNo_id = ?
    ORDER BY id
    LIMIT 1
    """
    cursor.execute(query, (order_id,))
    result = cursor.fetchone()
    return result[0] if result else 0  # Retourne 0 si pas de produit

# Fonction pour récupérer la quantité totale de ventes pour un produit
def get_sales_quantity(conn, pc_created_id):
    cursor = conn.cursor()
    query = """
    SELECT SUM(quantity)
    FROM ventes_produitsenbonsortie
    WHERE stock_id = ?
    """
    cursor.execute(query, (pc_created_id,))
    result = cursor.fetchone()
    return result[0] if result and result[0] is not None else 0  # Retourne 0 si pas de vente

# Fonction pour récupérer tous les produits associés à un ordre
def get_products_for_order(conn, order_id):
    cursor = conn.cursor()
    # Requête pour récupérer tous les produits associés à l'ordre
    query = """
    SELECT stock_id, quantity
    FROM production_produitsenordrefabrication
    WHERE BonNo_id = ?
    """
    cursor.execute(query, (order_id,))
    return cursor.fetchall()

# Fonction pour mettre à jour la quantité de stock de l'ordre
def update_order_stock(conn, store_id, order_quantity):
    cursor = conn.cursor()
    query = """
    UPDATE inventory_stock
    SET quantity = quantity + ?
    WHERE product_id = ?
    """
    cursor.execute(query, (order_quantity, store_id))
    conn.commit()

# Fonction pour mettre à jour la quantité de stock pour chaque produit
def update_product_stocks(conn, products):
    cursor = conn.cursor()
    insufficient_quantity_products = []  # Liste pour garder trace des produits avec quantité insuffisante
    for stock_id, product_quantity in products:
        # Vérifiez la quantité actuelle avant de soustraire
        cursor.execute("SELECT quantity FROM inventory_stock WHERE product_id = ?", (stock_id,))
        current_quantity = cursor.fetchone()
        
        if current_quantity and current_quantity[0] >= product_quantity > 0:
            query = """
            UPDATE inventory_stock
            SET quantity = quantity - ?
            WHERE product_id = ?
            """
            cursor.execute(query, (product_quantity, stock_id))
        else:
            # Ajoutez l'ID du produit à la liste s'il y a une quantité insuffisante
            insufficient_quantity_products.append(stock_id)
            print(f"Erreur : Quantité insuffisante pour product_id {stock_id}. Quantité actuelle : {current_quantity[0] if current_quantity else 'N/A'}")

    conn.commit()
    # Afficher les IDs des produits qui n'ont pas pu être soustraits
    if insufficient_quantity_products:
        print(f"Produits non soustraits : {insufficient_quantity_products}")

# Fonction pour construire la structure de données finale
def build_order_data(conn, orders):
    order_list = []
    for order in orders:
        order_id = order[0]
        pc_created_id = order[1]

        # Récupérer la quantité du premier produit
        first_product_quantity = get_first_product_quantity(conn, order_id)

        # Récupérer la quantité totale des ventes pour le pc_created_id
        sales_quantity = get_sales_quantity(conn, pc_created_id)

        # Calculer la nouvelle quantité
        new_quantity = first_product_quantity - sales_quantity

        # Récupérer tous les produits associés à l'ordre
        products = get_products_for_order(conn, order_id)

        # Construire le dictionnaire pour l'ordre
        order_dict = {
            'pc_created_id': pc_created_id,
            'quantity': new_quantity,  # Utiliser la nouvelle quantité calculée
            'produit': [{'stock_id': product[0], 'quantity': product[1]} for product in products]
        }
        order_list.append(order_dict)

        # Mettre à jour la quantité de stock pour l'ordre lui-même (pc_created_id)
        update_order_stock(conn, pc_created_id, new_quantity)  # Utilisez pc_created_id comme store_id

        # Mettre à jour la quantité de stock pour chaque produit
        update_product_stocks(conn, products)

    return order_list

# Chemin de la base de données
database_path = 'db.sqlite3'  # La base de données se trouve dans le même fichier

# Étape 1 : Connexion à la base de données
conn = connect_db(database_path)

# Étape 2 : Récupérer les ordres
orders = get_orders(conn)

# Étape 3 : Construire la structure de données finale
final_data = build_order_data(conn, orders)

# Étape 4 : Afficher le résultat final de manière claire
pprint(final_data)  # Utiliser pprint pour un affichage lisible

# Étape 5 : Fermer la connexion
conn.close()
