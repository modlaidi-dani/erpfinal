import sqlite3

# Connexion à la base de données source
conn_source = sqlite3.connect('db_backup_2024-09-22_10_17_02.db')
cursor_source = conn_source.cursor()

# Connexion à la base de données destination
conn_dest = sqlite3.connect('db.sqlite3')
cursor_dest = conn_dest.cursor()

# Fonction pour vérifier si un ID existe déjà dans la table de destination
def id_exists(cursor, table, row_id):
    query = f"SELECT 1 FROM {table} WHERE id = ? LIMIT 1"
    cursor.execute(query, (row_id,))
    return cursor.fetchone() is not None

# Étape 1: Récupérer et insérer les données de la table `comptoire_boncomptoire`
query_boncomptoire = '''SELECT * FROM comptoire_boncomptoire'''
cursor_source.execute(query_boncomptoire)
data_boncomptoire = cursor_source.fetchall()

if data_boncomptoire:
    query_insert_boncomptoire = '''
        INSERT INTO comptoire_boncomptoire
        VALUES ({})
    '''.format(', '.join(['?'] * len(data_boncomptoire[0])))

    for row in data_boncomptoire:
        row_id = row[0]  # On suppose que l'ID est dans la première colonne
        if id_exists(cursor_dest, 'comptoire_boncomptoire', row_id):
            print(f"ID {row_id} existe déjà dans `comptoire_boncomptoire`, saut de l'insertion.")
            continue
        cursor_dest.execute(query_insert_boncomptoire, row)

    conn_dest.commit()
    print("Données de `comptoire_boncomptoire` transférées avec succès.")
else:
    print("Aucune donnée trouvée dans `comptoire_boncomptoire`.")

# Étape 2: Récupérer et insérer les données de la table `comptoire_cloture`
query_cloture = '''SELECT * FROM comptoire_cloture'''
cursor_source.execute(query_cloture)
data_cloture = cursor_source.fetchall()

if data_cloture:
    query_insert_cloture = '''
        INSERT INTO comptoire_cloture
        VALUES ({})
    '''.format(', '.join(['?'] * len(data_cloture[0])))

    for row in data_cloture:
        row_id = row[0]
        if id_exists(cursor_dest, 'comptoire_cloture', row_id):
            print(f"ID {row_id} existe déjà dans `comptoire_cloture`, saut de l'insertion.")
            continue
        cursor_dest.execute(query_insert_cloture, row)

    conn_dest.commit()
    print("Données de `comptoire_cloture` transférées avec succès.")
else:
    print("Aucune donnée trouvée dans `comptoire_cloture`.")

# Étape 3: Récupérer et insérer les données de la table `comptoire_produitsenboncomptoir`
query_produitsenboncomptoir = '''SELECT * FROM comptoire_produitsenboncomptoir'''
cursor_source.execute(query_produitsenboncomptoir)
data_produitsenboncomptoir = cursor_source.fetchall()

if data_produitsenboncomptoir:
    query_insert_produitsenboncomptoir = '''
        INSERT INTO comptoire_produitsenboncomptoir
        VALUES ({})
    '''.format(', '.join(['?'] * len(data_produitsenboncomptoir[0])))

    for row in data_produitsenboncomptoir:
        row_id = row[0]
        if id_exists(cursor_dest, 'comptoire_produitsenboncomptoir', row_id):
            print(f"ID {row_id} existe déjà dans `comptoire_produitsenboncomptoir`, saut de l'insertion.")
            continue
        cursor_dest.execute(query_insert_produitsenboncomptoir, row)

    conn_dest.commit()
    print("Données de `comptoire_produitsenboncomptoir` transférées avec succès.")
else:
    print("Aucune donnée trouvée dans `comptoire_produitsenboncomptoir`.")

# Fermer les connexions
cursor_source.close()
conn_source.close()

cursor_dest.close()
conn_dest.close()
