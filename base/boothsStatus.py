import os
import sqlite3
import pandas as pd

# Affiche directement le contenu de la BDD
conn = sqlite3.connect(os.environ.get('MONITOR_DB_FILE', './photomatons_status.db'))
df = pd.read_sql('SELECT nom, niveau_papier as level, statut,derniere_verif FROM status ORDER BY nom', conn)
print(df.to_string(index=False))
conn.close()