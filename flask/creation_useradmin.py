import os
import sys
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'base'))
sys.path.append(base_path)

import bdd as bdd

conn = bdd.get_db_connection()

cursor = conn.cursor()

#cursor.execute("""
#    ALTER TABLE CONFIGURATION
#    ADD Nom VARCHAR(50);
#""")
#cursor.execute("""
#    ALTER TABLE DESIGN
#    RENAME Nom TO NomDesign;
#""")
#cursor.execute("""
#            CREATE TABLE DESIGN(
#                ID INTEGER PRIMARY KEY AUTOINCREMENT,
#                NomDesign VARCHAR(255),
#                Format VARCHAR(10),
#                Background VARCHAR(10),
#                ID_CONFIG INT,
#                FOREIGN KEY (ID_CONFIG) REFERENCES CONFIGURATION(ID)
#            );
#            """)
#cursor.execute("""
#    ALTER TABLE PHOTOMATON
#    ADD NbConsoleLeft INT;
#""")
#cursor.execute(
#    """
#    CREATE TABLE CONFIGURATION(
#                ID INTEGER PRIMARY KEY AUTOINCREMENT,
#                bDefault BOOL DEFAULT 0,
#                Prix INT,
#                Bkpimg BOOL,
#                BkpPath BOOL,
#                dtDebut DATETIME DEFAULT (datetime('now', 'localtime')),
#                dtFin DATETIME DEFAULT (datetime('now', 'localtime')),
#                nbPOSES INT,
#                ID_PHOTOMATON INT,
#                IA BOOL DEFAULT 0,
#                bChoixDesign BOOL DEFAULT 0, NomConfig VARCHAR(255),
#                FOREIGN KEY (ID_PHOTOMATON) REFERENCES PHOTOMATON(ID)
#            );
#    """
#)
#cursor.execute(
#    """
#    DELETE FROM LAYER;
#    """
#)
#cursor.execute("""
#                CREATE TABLE IF NOT EXISTS USER(
#                    ID INTEGER PRIMARY KEY AUTOINCREMENT,
#                    Login VARCHAR(25),
#                    Mdp VARCHAR(50)
#                )
#            """)

#cursor.execute("""
#        CREATE TABLE IF NOT EXISTS PROMPT(
#            ID INTEGER PRIMARY KEY AUTOINCREMENT,
#            ID_PHOTOMATON INT,
#            POSITIVE TEXT,
#            NEGATIVE TEXT,
#            NOM VARCHAR(50),
#            EMPLACEMENT VARCHAR(255),
#            FOREIGN KEY (ID_PHOTOMATON) REFERENCES PHOTOMATON(ID)
#        )
#    """
#    )

#cursor.execute("""
#        CREATE TABLE IF NOT EXISTS USER(
#        ID INTEGER PRIMARY KEY AUTOINCREMENT,
#        Login varchar(50),
#        Mdp varchar(150),
#        Role TEXT DEFAULT 'user'
#        )
#    """
#)

# Creates one demo admin account. Set DEMO_ADMIN_LOGIN / DEMO_ADMIN_PASSWORD in .env before running.
login = os.environ.get("DEMO_ADMIN_LOGIN", "demo_admin")
plain_pwd = os.environ["DEMO_ADMIN_PASSWORD"]
hashed_pwd = generate_password_hash(plain_pwd, method='pbkdf2:sha256')
cursor.execute("INSERT INTO USER (Login, Mdp, role) VALUES (?, ?, ?)", (login, hashed_pwd,'admin',))
conn.commit()
