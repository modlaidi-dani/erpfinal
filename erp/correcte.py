import sqlite3

# Chemin vers la base de données SQLite
database_path = 'db.sqlite3'

# Connexion à la base de données SQLite
conn = sqlite3.connect(database_path)
cursor = conn.cursor()

# Requête SQL pour supprimer les lignes où utilisateur_id = 8
delete_query = "DELETE FROM comptoire_cloture WHERE utilisateur_id = ?"

# Exécution de la requête
cursor.execute(delete_query, (8,))

# Validation des modifications dans la base de données
conn.commit()

# Vérification que la suppression a été effectuée
cursor.execute("SELECT * FROM comptoire_cloture WHERE utilisateur_id = 8")
rows = cursor.fetchall()

if not rows:
    print("Les lignes avec utilisateur_id = 8 ont été supprimées.")
else:
    print("La suppression a échoué ou il n'y avait aucune ligne correspondante.")

# Fermeture de la connexion à la base de données
conn.close()
