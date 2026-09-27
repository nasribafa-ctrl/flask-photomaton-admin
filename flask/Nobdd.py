import sqlite3
import os
from werkzeug.security import generate_password_hash

# --- CONFIGURATION DU CHEMIN ---
# On récupère le dossier où se trouve bdd.py (dossier 'flask')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# On remonte d'un cran (..) pour aller dans 'base' et trouver 'booth.db'
# C'est ce chemin qui pointe vers ton fichier de 2048 Ko
db_path = os.path.normpath(os.path.join(BASE_DIR, '..', 'base', 'booth.db'))

def get_db_connection():
    """Établit la connexion avec la base de données réelle."""
    # CORRECTION : On utilise db_path (minuscules) définie plus haut
    conn = sqlite3.connect(db_path)
    # Permet d'accéder aux données par nom de colonne (ex: user['Login'])
    conn.row_factory = sqlite3.Row  
    return conn

# --- FONCTIONS DE BASE ---

def get_nom():
    """Récupère le nom du photomaton depuis la table PHOTOMATON."""
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT Nom FROM PHOTOMATON LIMIT 1').fetchone()
        return row['Nom'] if row else "MinutePapillons"
    except:
        return "MinutePapillons"
    finally:
        conn.close()

# --- GESTION DES UTILISATEURS ---

def getLogin(username):
    """Récupère un utilisateur par son login (indispensable pour app.py)."""
    conn = get_db_connection()
    try:
        # On cherche dans la table USER (vérifie bien que la table s'appelle USER)
        user = conn.execute('SELECT * FROM USER WHERE Login = ?', (username,)).fetchone()
        return user
    except Exception as e:
        print(f"Erreur getLogin: {e}")
        return None
    finally:
        conn.close()

def register_user(login, password):
    """Enregistre un nouvel utilisateur avec un mot de passe haché."""
    conn = get_db_connection()
    try:
        # Hachage sécurisé pour check_password_hash
        hashed_pwd = generate_password_hash(password)
        # Insertion dans les colonnes Login, Mdp et Role
        conn.execute('INSERT INTO USER (Login, Mdp, Role) VALUES (?, ?, ?)', 
                     (login, hashed_pwd, 'user'))
        conn.commit()
        return True
    except Exception as e:
        print(f"Erreur BDD (Register) : {e}")
        return False
    finally:
        conn.close()

# --- AUTRES FONCTIONS (Copie tes fonctions ici) ---

def all_photo():
    conn = get_db_connection()
    photos = conn.execute('SELECT * FROM PHOTO ORDER BY ID DESC').fetchall()
    conn.close()
    return photos

def all_photomaton():
    conn = get_db_connection()
    data = conn.execute('SELECT * FROM PHOTOMATON').fetchall()
    conn.close()
    return data

def all_configuration():
    conn = get_db_connection()
    configs = conn.execute('SELECT * FROM CONFIGURATION').fetchall()
    conn.close()
    return configs