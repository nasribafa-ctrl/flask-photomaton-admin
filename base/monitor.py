import os
import paramiko
import json
import sqlite3
import pandas as pd
from datetime import datetime
import re

# --- CONFIGURATION ---
DATABASE_FILE = os.environ.get('MONITOR_DB_FILE', './photomatons_status.db')
CONFIG_FILE = os.environ.get('MONITOR_CONFIG_FILE', './monitor.json')
PAPER_LOW_THRESHOLD = 20 # Seuil pour l'alerte de pénurie
SSH_PASSWORD = os.environ.get('SSH_BOOTH_PASSWORD')  # Mot de passe SSH des bornes, fourni via .env

# --- FONCTIONS ---

def send_alert(booth_name, paper_level):
    """Fonction d'alerte (à personnaliser)."""
    print(f"🚨 ALERTE PÉNURIE ! 🚨")
    print(f"Le photomaton '{booth_name}' a un niveau de papier bas : {paper_level} impressions restantes.")
    # Ici, vous pourriez envoyer un email, un SMS, une notif Telegram, etc.

def setup_database():
    """Crée la table de la base de données si elle n'existe pas."""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS status (
            nom TEXT PRIMARY KEY,
            ip TEXT,
            niveau_papier INTEGER,
            derniere_verif TEXT,
            statut TEXT
        )
    ''')
    conn.commit()
    conn.close()

def update_status_in_db(booth_info, paper_level=None, status="OK"):
    """Met à jour les informations d'un photomaton dans la BDD."""
    conn = sqlite3.connect(DATABASE_FILE)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Prépare les données à insérer ou mettre à jour
    if status == "Éteint" and paper_level is None:
        # Si la machine est éteinte, on garde le dernier niveau connu
        c = conn.cursor()
        c.execute("SELECT niveau_papier, derniere_verif FROM status WHERE nom = ?", (booth_info['nom'],))
        result = c.fetchone()
        if result:
            paper_level = result[0]
            now = result[1]  # Garde la dernière vérification connue

    # Utilisation de SQLite directement pour un meilleur contrôle
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO status (nom, ip, niveau_papier, derniere_verif, statut)
        VALUES (?, ?, ?, ?, ?)
    ''', (booth_info['nom'], booth_info['ip'], paper_level, now, status))
    
    conn.commit()
    conn.close()

def extract_paper_level(output):
    """Extrait le niveau de papier de la chaîne de caractères retournée."""
    # Recherche le motif numérique dans la chaîne
    # Exemple: "marker-message: 247 native prints remaining on 6x4 (PC) media"

    match = re.search(r'marker-message:\s*(\d+)', output)
    

    
    # . Si on ne trouve pas, on cherche n'importe quel nombre 
    if not match:
        match = re.search(r'(\d+)', output)

    # 3. Si on a trouvé un nombre
    if match:
        valeur = int(match.group(1))

      
        if "6*8" in output or "6x8" in output:
            return valeur * 2
        
        return valeur

    return None

def check_booth(booth_info):
    """Se connecte à un photomaton et récupère le niveau de papier."""
    print(f"Vérification de '{booth_info['nom']}' ({booth_info['ip']})...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(booth_info['ip'], username=booth_info['user'], port=22, timeout=10, password=SSH_PASSWORD)
        
        # Tue les anciens processus pour éviter les conflits
        ssh.exec_command("pkill -f printerInfos.py", timeout=5)
        
        # Exécute le script à distance
        stdin, stdout, stderr = ssh.exec_command(f"timeout 10s python3 {booth_info['script_path']}", timeout=15)
        
        # Attend la fin de l'exécution
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode().strip()
        errors = stderr.read().decode().strip()

        print(f"  -> Sortie brute: '{output}'")
        print(f"  -> Erreurs: '{errors}'")
        print(f"  -> Code de retour: {exit_status}")

        if exit_status != 0 and not output:
            print(f"  -> Erreur sur '{booth_info['nom']}' (timeout ou erreur)")
            update_status_in_db(booth_info, status="Erreur script")
            return

        if not output:
            print(f"  -> Aucune sortie détectée")
            update_status_in_db(booth_info, status="Aucune sortie")
            return

        # Extrait le niveau de papier de la chaîne
        paper_level = extract_paper_level(output)
        
        if paper_level is None:
            print(f"  -> Impossible d'extraire le niveau de papier de la réponse")
            update_status_in_db(booth_info, status="Format invalide")
            return

        print(f"  -> Niveau de papier extrait : {paper_level}")
        update_status_in_db(booth_info, paper_level, status="En ligne")
        
        # Vérification du seuil d'alerte
        if paper_level < PAPER_LOW_THRESHOLD:
            send_alert(booth_info['nom'], paper_level)

    except Exception as e:
        # Affiche l'erreur technique précise
        print(f"  -> ERREUR DÉTAILLÉE pour '{booth_info['nom']}': {e}") 
        update_status_in_db(booth_info, status="Éteint")
        
    finally:
        ssh.close()

# --- SCRIPT PRINCIPAL ---

if __name__ == "__main__":
    setup_database()
    
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
        
    for booth in config['photomatons']:
        check_booth(booth)
        print()  # Ligne vide pour séparer les résultats

    print("\n--- État actuel de tous les photomatons ---")
    conn = sqlite3.connect(DATABASE_FILE)
    
    # Utilisation de pandas uniquement pour l'affichage final
    df = pd.read_sql('SELECT * FROM status ORDER BY nom', conn)
    print(df.to_string(index=False))
    conn.close()