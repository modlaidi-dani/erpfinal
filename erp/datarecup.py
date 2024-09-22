import sqlite3

# Connexion à la base de données source
conn_source = sqlite3.connect('db_backup_2024-09-22_10_17_02.db')
cursor_source = conn_source.cursor()

# Connexion à la base de données destination
conn_dest = sqlite3.connect('db.sqlite3')
cursor_dest = conn_dest.cursor()

# Fonction pour récupérer l'enregistrement existant dans la table de destination
def get_existing_row(cursor, table, row_id):
    query = f"SELECT * FROM {table} WHERE id = ? LIMIT 1"
    cursor.execute(query, (row_id,))
    return cursor.fetchone()

# Fonction pour vérifier si deux lignes sont identiques (excluant la date)
def rows_are_equal(row1, row2):
    return row1[:-1] == row2[:-1]  # Exclure la dernière colonne (date)

# Étape 2 : Récupérer les données de la table `comptoire_cloture` de la source
query_cloture = '''SELECT * FROM comptoire_cloture'''
cursor_source.execute(query_cloture)
data_cloture = cursor_source.fetchall()

if data_cloture:
    for row in data_cloture:
        row_id = row[0]  # L'ID est supposé être dans la première colonne

        # Vérifier si l'enregistrement existe dans la destination
        existing_row = get_existing_row(cursor_dest, 'comptoire_cloture', row_id)
        if existing_row:
            # Vérifier si la date n'est pas égale à 2024-09-22
            if existing_row[-1] == '2024-09-22':  # Date dans la dernière colonne
                print(f"ID {row_id} ignoré, car la date est égale à 2024-09-22.")
                continue
            
            # Si les données ne sont pas identiques, effectuer la mise à jour
            if not rows_are_equal(existing_row, row):
                query_update_cloture = '''
                    UPDATE comptoire_cloture
                    SET montant = ?, collected = ?, store_id = ?, utilisateur_id = ?, date = ?
                    WHERE id = ?
                '''
                # Exécuter la mise à jour en excluant l'ID de row
                cursor_dest.execute(query_update_cloture, (*row[1:], row_id))
                print(f"ID {row_id} mis à jour dans `comptoire_cloture`.")
            else:
                print(f"ID {row_id} déjà à jour dans `comptoire_cloture`, aucune modification nécessaire.")
        else:
            # Insérer la nouvelle ligne
            query_insert_cloture = '''
                INSERT INTO comptoire_cloture (id, montant, collected, store_id, utilisateur_id, date)
                VALUES (?, ?, ?, ?, ?, ?)
            '''
            cursor_dest.execute(query_insert_cloture, row)
            print(f"ID {row_id} inséré dans `comptoire_cloture`.")

    # Commit pour valider les modifications
    conn_dest.commit()
    print("Données de `comptoire_cloture` traitées avec succès.")
else:
    print("Aucune donnée trouvée dans `comptoire_cloture`.")

# Fermer les connexions
cursor_source.close()
conn_source.close()
cursor_dest.close()
conn_dest.close()
