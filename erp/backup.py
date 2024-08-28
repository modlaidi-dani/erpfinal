import sqlite3
import datetime
import os
import shutil  # Import pour la compression

# Chemin de la base de données source
DB_PATH = "db.sqlite3"

# Répertoire de sauvegarde
BACKUP_DIR = "/root/archivage/erpdb"  # Mettez ici le chemin où vous voulez enregistrer les sauvegardes

def create_backup_filename(db_path, backup_dir):
    # Créer un nom de fichier de sauvegarde avec horodatage
    filename = f"{os.path.splitext(os.path.basename(db_path))[0]}_backup_{datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}.db"
    return os.path.join(backup_dir, filename)

def compress_backup_file(file_path):
    # Compresser le fichier de sauvegarde en .zip
    zip_path = f"{file_path}.zip"
    shutil.make_archive(file_path, 'zip', os.path.dirname(file_path), os.path.basename(file_path))
    print(f"Fichier compressé créé : {zip_path}")
    
   # Supprimer le fichier original non compressé après compression
    os.remove(file_path)
    print(f"Fichier original supprimé : {file_path}")
    
    return zip_path

def create_and_backup_database(source_db_path, backup_dir):
    # Chemin complet du fichier de sauvegarde
    new_db_path = create_backup_filename(source_db_path, backup_dir)
    try:
        # Connexion à la base de données source et à la nouvelle base de données de sauvegarde
        source_conn = sqlite3.connect(source_db_path)
        new_conn = sqlite3.connect(new_db_path)
        
        with new_conn:
            source_conn.backup(new_conn)
        print(f"Nouvelle base de données créée et sauvegarde réussie : {new_db_path}")
        
        # Compresser la base de données de sauvegarde
        compress_backup_file(new_db_path)
        
    except sqlite3.Error as e:
        print(f"Erreur lors de la sauvegarde de la base de données : {e}")
    finally:
        # Fermer les connexions aux bases de données
        source_conn.close()
        new_conn.close()

# Créer et sauvegarder la base de données
create_and_backup_database(DB_PATH, BACKUP_DIR)
