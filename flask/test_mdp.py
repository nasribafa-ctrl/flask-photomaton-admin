from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
import os

# Configuration du chemin vers ta base de 2048ko
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.abspath(os.path.join(BASE_DIR, '..', 'base', 'booth.db'))

def test_connexion(login_tape, mdp_tape):
    print(f"--- TEST DE CONNEXION POUR : {login_tape} ---")
    
    if not os.path.exists(db_path):
        print(f"ERREUR : Le fichier bdd est introuvable ici : {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # 1. On cherche l'utilisateur
        user = cursor.execute("SELECT * FROM USER WHERE Login = ?", (login_tape,)).fetchone()
        
        if user:
            print(f"ID trouvé : {user['ID']}")
            print(f"Login en BDD : {user['Login']}")
            print(f"Hash en BDD : {user['Mdp']}")
            
            # 2. On teste le mot de passe
            est_valide = check_password_hash(user['Mdp'], mdp_tape)
            
            if est_valide:
                print("✅ SUCCÈS : Le mot de passe correspond au hash !")
            else:
                print("❌ ÉCHEC : Le mot de passe ne correspond PAS au hash.")
                # Optionnel : générer ce que devrait être le hash correct
                print(f"Note : Le hash correct pour '{mdp_tape}' devrait être : {generate_password_hash(mdp_tape)}")
        else:
            print(f"❌ ÉCHEC : L'utilisateur '{login_tape}' n'existe pas dans la base.")

    except Exception as e:
        print(f"Erreur durant le test : {e}")
    finally:
        conn.close()

# --- EXÉCUTION DU TEST ---
# Remplace par les identifiants que tu veux tester
test_connexion("admin", "admin")