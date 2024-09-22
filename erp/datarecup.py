import sqlite3

# Connexion à la base de données source
conn_source = sqlite3.connect('db_backup_2024-09-22_10_17_02.db')
cursor_source = conn_source.cursor()

# Connexion à la base de données destination
conn_dest = sqlite3.connect('db.sqlite3')
cursor_dest = conn_dest.cursor()

# Filtre de dates
date_debut = '2024-09-18'
date_fin = '2024-09-21'  # ou utilise 'DATE('now')' pour la date d'aujourd'hui

# Fonction pour vérifier si un ID existe déjà dans la table de destination
def id_exists(cursor, table, row_id):
    query = f"SELECT 1 FROM {table} WHERE id = ? LIMIT 1"
    cursor.execute(query, (row_id,))
    return cursor.fetchone() is not None

# Étape 1: Récupérer les données de la table `comptoire_boncomptoire` entre deux dates
query_boncomptoire = '''
    SELECT * FROM comptoire_boncomptoire WHERE dateBon BETWEEN ? AND ?
'''
cursor_source.execute(query_boncomptoire, (date_debut, 'DATE("now")'))
data_boncomptoire = cursor_source.fetchall()

# Vérifier s'il y a des données récupérées
if data_boncomptoire:
    # Générer une requête INSERT pour insérer toutes les colonnes dans la table `comptoire_boncomptoire` de la base destination
    query_insert_boncomptoire = '''
        INSERT INTO comptoire_boncomptoire
        VALUES ({})
    '''.format(', '.join(['?'] * len(data_boncomptoire[0])))  # Générer les placeholders pour chaque colonne

    # Insérer chaque ligne dans la table destination, après vérification de l'ID
    for row in data_boncomptoire:
        row_id = row[0]  # Supposons que l'ID est dans la première colonne
        if id_exists(cursor_dest, 'comptoire_boncomptoire', row_id):
            print(f"ID {row_id} existe déjà dans `comptoire_boncomptoire`, saut de l'insertion.")
            continue
        cursor_dest.execute(query_insert_boncomptoire, row)

    # Valider les changements dans la base destination
    conn_dest.commit()
    print("Données de `comptoire_boncomptoire` transférées avec succès.")
else:
    print("Aucune donnée trouvée dans `comptoire_boncomptoire` pour la plage de dates spécifiée.")

# Étape 2: Récupérer les données de la table `comptoire_cloture` entre deux dates
query_cloture = '''
    SELECT * FROM comptoire_cloture WHERE date BETWEEN ? AND ?
'''
cursor_source.execute(query_cloture, (date_debut, 'DATE("now")'))
data_cloture = cursor_source.fetchall()

# Vérifier s'il y a des données récupérées
if data_cloture:
    # Générer une requête INSERT pour insérer toutes les colonnes dans la table `comptoire_cloture` de la base destination
    query_insert_cloture = '''
        INSERT INTO comptoire_cloture
        VALUES ({})
    '''.format(', '.join(['?'] * len(data_cloture[0])))  # Générer les placeholders pour chaque colonne

    # Insérer chaque ligne dans la table destination, après vérification de l'ID
    for row in data_cloture:
        row_id = row[0]  # Supposons que l'ID est dans la première colonne
        if id_exists(cursor_dest, 'comptoire_cloture', row_id):
            print(f"ID {row_id} existe déjà dans `comptoire_cloture`, saut de l'insertion.")
            continue
        cursor_dest.execute(query_insert_cloture, row)

    # Valider les changements dans la base destination
    conn_dest.commit()
    print("Données de `comptoire_cloture` transférées avec succès.")
else:
    print("Aucune donnée trouvée dans `comptoire_cloture` pour la plage de dates spécifiée.")

# Fermer les connexions
cursor_source.close()
conn_source.close()

cursor_dest.close()
conn_dest.close()
