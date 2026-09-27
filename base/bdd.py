import sqlite3
import logging
import datetime
import os

#Globals
global ID_BOOTH
ID_BOOTH = 0

class Config:
    def __init__(self):
        self.idconfig = 0
        self.price = 0
        self.format = "2xPortrait"
        self.bkpimg = False
        self.bkp_path = ""
        self.background = None
        self.photo_pause = 5
        self.print = True
        self.ledstrip = False
        self.rotate_matrix = False
        self.analog_read = False
        self.ia = False
        self.layers = {}
        self.prompts = {}
        self.bChoixDesign = False
        self.lcd = False
        self.keypad = False
        self.cashless_mdb = False
        self.format_rotate = False
        self.format_cut = True
        self.slot_photos = {}
        self.dateMAJ = None
        self.IDDESIGN = None # ID du design pour la session photo courante.
        self.nbposes = 4
        

#recupération de la directory absolue de la base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

#récupération du chemin du dossier qui contiens les dossiers qui contiens les photos
BASE_CAPTURE_FOLDER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'base', 'captures')
)

#acces a la directory de la base
db_path = os.path.join(BASE_DIR, '..', 'base', 'booth.db')

db_path = os.path.normpath(db_path)

#connection a la base données
def get_db_connection():
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	return conn

def check_if_table_exist(connexion,table):
    cursor = connexion.cursor()

    # Query to check if the table exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?;
    """, (table,))

    # Fetch result
    table_exists = cursor.fetchone()

    return table_exists

def initBDD(ID):#nous pemert d'appeler la fonction crée table de deux manière différente

    #1er manière est d'appeler la fonction creeTable(connexion)
    #2ème est de l'appeler mais avec des données à inserer dans la base de données
    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        ligneTable = check_if_table_exist(conn,'PHOTOMATON')
        if not ligneTable:
            print("initBDD")
            # Création des tables
            cursor.execute("""
                PRAGMA foreign_keys = ON
            """
            )

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS PHOTOMATON(
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Nom VARCHAR(20),
                FormatDefaut VARCHAR(10),
                TPECP INT,
                bPRINT BOOL DEFAULT 1,
                bLEDSTRIP BOOL DEFAULT 0,
                bROTATE_MATRIX BOOL DEFAULT 0,
                bANALOG_READ BOOL DEFAULT 0,
                nbPhotoLeft INT DEFAULT 0,
                bLCD BOOL DEFAULT 0,
                bKEYPAD BOOL DEFAULT 0,
                bCASHLESS_MDB BOOL DEFAULT 0,
                DATE_MAJ DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS CONFIGURATION(
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                NomConfig VARCHAR(255),
                bDefault BOOL DEFAULT 0,
                Prix INT,
                Bkpimg BOOL,
                BkpPath BOOL,
                dtDebut DATETIME DEFAULT CURRENT_TIMESTAMP,
                dtFin DATETIME DEFAULT CURRENT_TIMESTAMP,
                ID_PHOTOMATON INT,
                IA BOOL DEFAULT 0,
                bChoixDesign BOOL DEFAULT 0,
                FOREIGN KEY (ID_PHOTOMATON) REFERENCES PHOTOMATON(ID)
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS DESIGN(
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                NomDesign VARCHAR(255),
                Format VARCHAR(10),
                Background BLOB,
                ID_CONFIG INT,
                NBPOSES INT DEFAULT 4,
                FOREIGN KEY (ID_CONFIG) REFERENCES CONFIGURATION(ID)
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS PHOTO(
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                ID_PHOTOMATON INT,
                Date DATETIME DEFAULT CURRENT_TIMESTAMP,
                ModePaiement VARCHAR(10),
                Repertoire VARCHAR(10),
                ID_DESIGN INT,
                FOREIGN KEY (ID_DESIGN) REFERENCES DESIGN(ID),
                FOREIGN KEY (ID_PHOTOMATON) REFERENCES PHOTOMATON(ID)
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS LAYER(
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                image BLOB,
                PosX INT,
                PosY INT,
                ID_DESIGN INTEGER,
                FOREIGN KEY (ID_DESIGN) REFERENCES DESIGN(ID)
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS PROMPT(
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                ID_PHOTOMATON INT,
                positive VARCHAR(255),
                negative VARCHAR(255),S
                name VARCHAR(255),
                emplacement VARCHAR(2),
                FOREIGN KEY (ID_PHOTOMATON) REFERENCES PHOTOMATON(ID)
            );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS USER(
                    ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Login VARCHAR(25),
                    Mdp VARCHAR(50),
                    Role VARCHAR(10)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS FORMAT (
                    ID	INTEGER  PRIMARY KEY AUTOINCREMENT,
                    NOM	VARCHAR2(50) NOT NULL,
                    ROTATE INTEGER NOT NULL DEFAULT 0,
                    CUT BOOL NOT NULL DEFAULT 1)
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS SLOT (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                POSX	INTEGER NOT NULL DEFAULT 0,
                POSY	INTEGER NOT NULL DEFAULT 0,
                WIDTH	INTEGER NOT NULL DEFAULT 0,
                HEIGHT	INTEGER NOT NULL DEFAULT 0,
                IMG	BLOB NOT NULL,
                ID_FORMAT	INTEGER NOT NULL,
                NUM_POSE    INTEGER NOT NULL DEFAULT 0)
            """)

            conn.commit()
            logging.info("Les tables ont été créées avec succès.")
    except sqlite3.Error as e:
        logging.error(f"Les tables n'ont pas pu être créées : {e}")

def loadConfig(JSON, NOM_BOOTH):
    global ID_BOOTH
    config = Config()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM PHOTOMATON")
    
    #si aucune donnnée on va créer les infos dans la bdd.
    row = cursor.fetchone()
    if row is None:
        ID_BOOTH = initConfig(JSON, NOM_BOOTH)
        config.format = JSON["format"]
    else:
        config.format = row[2]

    refreshConfig(config, config.format)
       
    return config

def initConfig(CONFIG, NOM_BOOTH):
    global ID_BOOTH
    logging.info("Création config par défaut issue du fichier json sur la machine")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO PHOTOMATON (Nom, FormatDefaut, TPECP, bPRINT, bLEDSTRIP, bROTATE_MATRIX, bANALOG_READ, bLCD, bKEYPAD, bCASHLESS_MDB) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (NOM_BOOTH, CONFIG["format"], CONFIG["photo_count"], CONFIG["print"], CONFIG["ledstrip"], CONFIG["analog_read"], CONFIG["rotate_matrix"], CONFIG["lcd"], CONFIG["keypad"], CONFIG["cashlessMDB"])
    )
    ID_BOOTH = cursor.lastrowid

    layers = CONFIG["layers"]
    for layer in layers.values():
        format = layer["format"]

        #check si on a déja créé cette config.
        cursor.execute("SELECT * FROM CONFIGURATION")
        row = cursor.fetchone()
        if row is None:
            cursor.execute("INSERT INTO CONFIGURATION (NomConfig, bDefault, Prix, Bkpimg, BkpPath, IA, ID_PHOTOMATON, bChoixDesign) VALUES (?,?,?, ?, ?, ?, ?, ?)",
                ("Default",1, CONFIG["price"], CONFIG["bkpimg"], CONFIG["bkp_path"], CONFIG["ia"], ID_BOOTH, CONFIG["bChoixDesign"]))
            IDCONFIG = cursor.lastrowid
        else:
            IDCONFIG = row[0]

        #check si on a déja créé ce design.        
        cursor.execute("SELECT * FROM DESIGN WHERE ID_CONFIG = ? AND Format = ?", (IDCONFIG, format))
        row = cursor.fetchone()
        if row is None:
            #création design
            cursor.execute("INSERT INTO DESIGN (NomDesign, Format,  ID_CONFIG, NBPOSES) VALUES (?,?,?,?)",
                    (format, format, IDCONFIG, 4))
            IDDESIGN = cursor.lastrowid
        else:
            IDDESIGN = row[0]

        #création des layers associés à ce design
        cursor.execute("INSERT INTO LAYER (image, PosX, PosY, ID_DESIGN) VALUES (?, ?, ?, ?)",
                (layer["img"], layer["x"], layer["y"], IDDESIGN))

    prompts = CONFIG["prompts"]
    for promptId, prompt in prompts.items():
         cursor.execute("INSERT INTO PROMPT (ID_PHOTOMATON, positive, negative, name, emplacement) VALUES (?,?, ?, ?, ?)",
                (ID_BOOTH, prompt["positive"], prompt["negative"], prompt["name"], promptId))
    # On commit les changements                                         
    conn.commit()


def refreshConfig(config: Config, FORMAT):
    global ID_BOOTH
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM PHOTOMATON")
    
    row = cursor.fetchone()
    ID_BOOTH = row[0] 
    if FORMAT is None: # on prend le format par défaut
        config.format = row[2]
    else:
        config.format = FORMAT # l'utilisateur a choisi un format spécifique.
    config.photo_pause = row[3]
    config.print = bool(row[4] )
    config.ledstrip = bool(row[5])
    config.rotate_matrix = bool(row[6])
    config.analog_read = bool(row[7])
    config.lcd = bool(row[9])
    config.keypad = bool(row[10])
    config.cashless_mdb = bool(row[11])
    config.dateMAJ =  datetime.datetime.strptime(row[12], "%Y-%m-%d %H:%M:%S")

    #chargement des données de config par défaut depuis la bdd
    cursor.execute("SELECT ID_CONFIG, Prix, Bkpimg, BkpPath, IA, bChoixDesign, DtDebut, DtFin, bDefault " \
    "FROM CONFIGURATION, DESIGN, LAYER " \
    "WHERE CONFIGURATION.ID = DESIGN.ID_CONFIG " \
    "AND DESIGN.ID = LAYER.ID_DESIGN " \
    "AND ID_PHOTOMATON = ?", (ID_BOOTH,))

    activeRow = None
    currentDate = datetime.datetime.now()
    for row in cursor:
        if row[8] == 1:  # Vérifie si c'est la config par défaut
            activeRow = row
        else:
            dtDebut = datetime.datetime.strptime(row[6], "%Y-%m-%d %H:%M:%S")
            dtFin = datetime.datetime.strptime(row[7], "%Y-%m-%d %H:%M:%S")
            if dtDebut <= currentDate <= dtFin:
                print("config date active trouvée")
                activeRow = row
                break

    config.idconfig = activeRow[0]
    config.price = activeRow[1]
    print(config.price)
    config.bkpimg = bool(activeRow[2])
    config.bkp_path = activeRow[3]
    config.ia = bool(activeRow[4])
    config.bChoixDesign = bool(activeRow[5])

    #chargement du design
    cursor.execute("SELECT DESIGN.ID, DESIGN.Format, DESIGN.Background, DESIGN.NBPOSES " \
                   "FROM DESIGN " \
                   "WHERE DESIGN.ID_CONFIG = ? ", (config.idconfig,))
    for row in cursor:
        if config.format == row[1]:  # Vérifie si le format correspond à la config
            config.IDDESIGN = row[0]
            config.background = row[2]
            config.format = row[1]
            config.nbposes = row[3]

    #chargement des layers
    cursor.execute("SELECT LAYER.ID, LAYER.image, LAYER.PosX, LAYER.PosY " \
                   "FROM LAYER " \
                   "WHERE LAYER.ID_DESIGN = ? ", (config.IDDESIGN,))

    config.layers = {}
    for row in cursor:
        config.layers[row[0]] = {
            "img": row[1],
            "x": row[2],
            "y": row[3]
        }

    # Chargement du infos format et du positionnement des photos.
    cursor.execute("SELECT FORMAT.ROTATE, SLOT.ID, SLOT.POSX, SLOT.POSY, SLOT.WIDTH, SLOT.HEIGHT, SLOT.NUM_POSE "\
                "FROM FORMAT, SLOT " \
                "WHERE FORMAT.ID = SLOT.ID_FORMAT AND FORMAT.NOM = ? "
                "ORDER BY SLOT.NUM_POSE ", (config.format,))

    for row in cursor:
        config.format_rotate = bool(row[0])
        config.slot_photos[row[1]] = {
            "posX": row[2],
            "posY": row[3],
            "width": row[4],
            "height": row[5],
            "num_pose": row[6],
            "rotate": row[0]
        }

    #chargement des prompts
    cursor.execute("SELECT ID_PHOTOMATON, positive, negative, name, emplacement FROM PROMPT WHERE ID_PHOTOMATON = ?", (ID_BOOTH,))
    for lrow in cursor:
        config.prompts[lrow[4]] = {
            "positive": lrow[1],
            "negative": lrow[2],
            "name": lrow[3]
        }
    return config

def insertPhoto(currDate, IDDESIGN, paperCounter, values):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sqlite_date = currDate.isoformat(" ", "seconds")
        cursor.execute("INSERT INTO PHOTO (ID_PHOTOMATON, Date, ID_DESIGN, ModePaiement, Repertoire) VALUES (?, ?, ?, ?, ?)", (ID_BOOTH, sqlite_date, IDDESIGN, *values))
        cursor.execute("UPDATE PHOTOMATON SET nbPhotoLeft = ? WHERE ID = ?", (paperCounter, ID_BOOTH))
        
        conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Erreur insert photo : {e}")

#fonction qui va recuperer le chemin insérer dans la base données afin qu'on puisse accéder aux photos
def get_folder_name_from_db(photo_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT Repertoire FROM PHOTO WHERE ID = ?', (photo_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result['Repertoire']
    return None

def get_full_folder_from_db(photo_id):
    folder_name = get_folder_name_from_db(photo_id)

    if not folder_name:
        return None

    full_path = os.path.join(BASE_CAPTURE_FOLDER, folder_name)
    return full_path

def description_photo(photoId):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        photo = cursor.execute("SELECT * FROM PHOTO where ID = ?",(photoId,)).fetchall()
        conn.commit()
        return photo
    except Exception as e:
        conn.rollback()
        print(f"Il y'a eu une erreur : {e}")
    finally:
        conn.close()

def all_photo():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        photo = cursor.execute("SELECT * FROM PHOTO ORDER BY Date DESC").fetchall()

        return photo
    except Exception as e:
        conn.rollback()
        print(f"Il y'a eu une erreur : {e}")
    finally:
        conn.close()

def photomaton():
    global ID_BOOTH
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        photomaton = cursor.execute("SELECT * FROM PHOTOMATON").fetchone()
        ID_BOOTH = photomaton[0]
        return photomaton
    except Exception as e:
        conn.rollback()
        print(f"Il ya eu une erreur: {e}")
    finally:
        conn.close()

def all_configuration():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        configuration = cursor.execute("SELECT * FROM CONFIGURATION").fetchall()
        return configuration
    except Exception as e:
        conn.rollback()
        print(f"Il ya eu une erreur: {e}")
    finally:
        conn.close()

def get_all_configuration_from_id(configuration_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        config = cursor.execute("SELECT * FROM CONFIGURATION WHERE ID = ?", (configuration_id,)).fetchone()
        conn.commit()
        return config
    except Exception as e:
        conn.rollback()
        print(f"Il ya eu une erreur: {e}")
    finally:
        conn.close()

def updateConfig(bDefault, Bkpimg, BkpPath, dtDebut, dtFin, IA, bChoixDesign, NomConfig,Prix, ID):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE CONFIGURATION
            SET bDefault = ?, Bkpimg = ?, BkpPath = ?, dtDebut = strftime('%Y-%m-%d %H:%M:%S',?), dtFin = strftime('%Y-%m-%d %H:%M:%S',?),
                IA = ?, bChoixDesign = ?, NomConfig = ?, Prix= ?
            WHERE ID = ?;
        """, (bDefault, Bkpimg, BkpPath, dtDebut, dtFin, IA, bChoixDesign, NomConfig, Prix, ID))
        conn.commit()
        update_dateMAJ()
    except Exception as e:
        conn.rollback()
        print(f"There was an error: {e}")
    finally:
        conn.close()

def insertConfig(bDefault, Bkpimg, c, dtDebut, dtFin, bIA, bChoixDesign, h, i):
    global ID_BOOTH
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if bIA is None:
            bIA = 0
        if bChoixDesign is None:
            bChoixDesign = 0
        if bDefault is None:
            bDefault = 0
        if Bkpimg is None:
            Bkpimg = 0
            
        cursor.execute("""
            INSERT INTO CONFIGURATION (bDefault,Bkpimg,BkpPath,dtDebut,dtFin,IA,bChoixDesign,NomConfig,Prix, ID_PHOTOMATON)
            VALUES (?,?,?,strftime('%Y-%m-%d %H:%M:%S',?),strftime('%Y-%m-%d %H:%M:%S',?),?,?,?,?,?);
        """, (bDefault, Bkpimg, c, dtDebut, dtFin, bIA, bChoixDesign, h, i, ID_BOOTH))
        conn.commit()
        update_dateMAJ()
    except Exception as e:
        conn.rollback()
        print(f"There was an error: {e}")
    finally:
        conn.close()

def Delete(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM CONFIGURATION WHERE ID = ?", (id,))
        conn.commit()
        update_dateMAJ()
    except Exception as e:
        conn.rollback()
        print(f"There was an error: {e}")
    finally:
        conn.close()

def detail_photo(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT PHOTO.ID AS photo_id, *
            FROM DESIGN 
            JOIN PHOTO ON DESIGN.ID = PHOTO.ID_DESIGN 
            JOIN CONFIGURATION ON CONFIGURATION.ID = DESIGN.ID_CONFIG
            WHERE PHOTO.ID = ?;
        """, (id,))
        return cursor.fetchone()

    except Exception as e:
        print(f"There was an error: {e}")
    finally:
        conn.close()
def get_nom():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT Nom FROM PHOTOMATON")
        row = cursor.fetchone()
        return row[0]
    except Exception as e:
        print(f"There was an error: {e}")
    finally:
        conn.close()

def get_format(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT Format FROM DESIGN WHERE ID = ?", (id,))
        row = cursor.fetchone()
        return row[0]

    except Exception as e:
        print(f"There was an error: {e}")
    finally:
        conn.close()

def get_design_linked_with_config(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        linked = cursor.execute("SELECT * FROM DESIGN WHERE ID_CONFIG = ?", (id,)).fetchall()
        return linked
    except Exception as e:
        print(f"There was an error: {e}")
    finally:
        conn.close()
        
def update_bdefault(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE CONFIGURATION
            SET bDefault = CASE
                WHEN ID = ? THEN 1
                ELSE 0
            END;
        """, (id,))
        conn.commit()
        update_dateMAJ()
    except Exception as e:
        print(f"There was an error: {e}")
    finally:
        conn.close()


def reset_all_bdefault_except(config_id):
    """
    Sets bDefault = 0 for all rows except the given config_id.
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE CONFIGURATION SET bDefault = 0 WHERE ID != ?", (config_id,))
    conn.commit()
    conn.close()
    update_dateMAJ()


def set_bdefault_only_for(config_id):
    """
    Resets all others, sets bDefault = 1 only for the given config_id.
    """
    reset_all_bdefault_except(config_id)

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE CONFIGURATION SET bDefault = 1 WHERE ID = ?", (config_id,))
    conn.commit()
    conn.close()
    update_dateMAJ()

def get_layers(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM LAYER WHERE ID_DESIGN = ?", (id,))
        return cursor.fetchall()
    except Exception as e:
        print(f"There was an error: {e}")
    finally:
        conn.close()

def get_format():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM FORMAT")
        return cursor.fetchall()
    except Exception as e:
        print(f"There was an error: {e}")
    finally:
        conn.close()

def update_layer(image, posX, posY, layer_id, design_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE LAYER
            SET Image = ?, PosX = ?, PosY = ?
            WHERE ID = ? AND ID_DESIGN = ?
        """, (image, posX, posY, layer_id, design_id))
        conn.commit()
        update_dateMAJ()
    except Exception as e:
        conn.rollback()
        print("UPDATE LAYER ERROR:", e)
    finally:
        conn.close()


def updateDesign(nomDesign, format, background, nbposes,id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if background is not None:
            cursor.execute("""
                UPDATE DESIGN
                SET NomDesign = ?, Format = ?, Background = ?, NBPOSES = ?
                WHERE ID = ?
            """, (nomDesign, format, background, nbposes, id))
        else:
            cursor.execute("""
                UPDATE DESIGN
                SET NomDesign = ?, Format = ?, NBPOSES = ?
                WHERE ID = ?
            """, (nomDesign, format, nbposes, id))

        conn.commit()
        update_dateMAJ()
    except Exception as e:
        conn.rollback()
        print(f"Erreur updateDesign: {e}")
    finally:
        conn.close()

def getDesignById(id, configId):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        linked = cursor.execute("SELECT * FROM DESIGN WHERE ID = ? AND ID_CONFIG = ?", (id,configId,)).fetchone()
        return linked
    except Exception as e:
        print(f"There was an error: {e}")
    finally:
        conn.close()

def delDesign(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            DELETE FROM DESIGN
            WHERE ID = ?
        """, (id,))
        conn.commit()
        update_dateMAJ()
    except Exception as e:
        conn.rollback()
        print(f"Il y a eu une erreur : {e}")
    finally:
        conn.close()

def delLayer(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            DELETE FROM LAYER
            WHERE ID = ?
        """, (id,))
        conn.commit()
        update_dateMAJ()
    except Exception as e:
        conn.rollback()
        print(f"Il y a eu une erreur : {e}")
    finally:
        conn.close()

def insertIntoDesign(nomDesign,format,background,nbposes,id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO DESIGN (NomDesign,Format,Background,NBPOSES,ID_CONFIG)
            VALUES(?,?,?,?,?)
        """, (nomDesign,format,background,nbposes, id,))
        conn.commit()
        update_dateMAJ()
        return cursor.lastrowid
    except Exception as e:
        conn.rollback()
        print(f"Il y a eu une erreur (insertIntoDesign) : {e}")
        return None
    finally:
        conn.close()

def getConfigId(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT ID FROM CONFIGURATION WHERE ID = ?",(id,))
        row = cursor.fetchone()
        return row[0]
    except Exception as e:
        print(f"Il Y a eu une erreur (insertIntoConfig): {e}")
    finally:
        conn.close()

def insertIntoLayer(image,posX,posY,id,filename):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO LAYER (Image, PosX, PosY,ID_DESIGN,ImageNom)
            VALUES (?,?,?,?,?)
        """, (image,posX,posY,id,filename,))
        conn.commit()
        update_dateMAJ()
    except Exception as e:
        conn.rollback()
        print(f"Il y a eu une erreur (insertIntoLayaer): {e}")
    finally:
        conn.close()
    
def delDesignAssocieAConfig(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM DESIGN WHERE ID_CONFIG = ?", (id,))
        conn.commit()
        update_dateMAJ()
    except Exception as e:
        conn.rollback()
        print(f"Il y a eu une erreur: {e}")
    finally:
        conn.close()
    
def delLayerAssocieADesign(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(" DELETE FROM LAYER WHERE ID_DESIGN = ?", (id,))
        conn.commit()
        update_dateMAJ()
    except Exception as e:
        conn.rollback()
        print(f"Il y a eu une erreur: {e}")
    finally:
        conn.close()
        
def get_design_Id_linked_with_config(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        linked = cursor.execute("SELECT ID FROM DESIGN WHERE ID_CONFIG = ?", (id,)).fetchone()
        return linked[0]
    except Exception as e:
        print(f"There was an error: {e}")
    finally:
        conn.close()

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

def register_user(login, hash_pwd,role):
    """Enregistre un nouvel utilisateur avec un mot de passe haché."""
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO USER (Login, Mdp, Role) VALUES (?, ?, ?)', 
                     (login, hash_pwd, role))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Erreur BDD (Register) : {e}")
        return False
    finally:
        conn.close()

#recuperer le dernier élémenet de la table 
def getDesignId():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM DESIGN ORDER BY ID DESC LIMIT 1")
        id = cursor.fetchone()
        return id['ID']
    except Exception as e:
        print(f"Il y a eu une erreur: {e}")
    finally:
        conn.close()

def getBackgroundByDesignId(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        background = cursor.execute("SELECT Background FROM DESIGN WHERE ID = ?",(id,)).fetchone()
        return background
    except Exception as e:
        print(f"Il y a eu une erreur: {e}")
    finally:
        conn.close()

def updateDesignBackground(design_id, bg_binary):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE design
            SET background = ?
            WHERE id = ?
            """,(bg_binary, design_id))
        conn.commit()
        update_dateMAJ()
    except Exception as e:
        conn.rollback()
        print(f"Il y a eu une erreur: {e}")
    finally:
        conn.close()

def all_users():
    """Récupère la liste de tous les utilisateurs pour l'affichage admin."""
    conn = get_db_connection()
    try:
        users = conn.execute("SELECT ID, Login, Role FROM USER").fetchall()
        return users
    except Exception as e:
        print(f"Erreur lors de la récupération des utilisateurs : {e}")
        return []
    finally:
        conn.close()

def updatePrinterStatus(newStatus):
    conn = get_db_connection()
    cursor = conn.cursor()
    id = 1
    try:
        cursor.execute("UPDATE PHOTOMATON set bPRINT = ? WHERE ID = ?", (newStatus,id,))
        conn.commit()
        update_dateMAJ()
    except Exception as e:
        print(f"Il y a eu une érreur: {e}")
        conn.rollback()
    finally:
        conn.close()

def update_dateMAJ():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE PHOTOMATON
            SET DATE_MAJ = datetime(current_timestamp, 'localtime')""")
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Il y a eu une erreur: {e}")
    finally:
        conn.close()

def get_dateMAJ():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DATE_MAJ FROM PHOTOMATON")
        row = cursor.fetchone()

        # Dans le cas ou une configuration dois être activée dans le 
        # créneau de temps actuel alors on renvoi la date actuelle pour forcer un refresh de la config.
        cursor.execute("SELECT * FROM CONFIGURATION WHERE DtDebut >= CURRENT_TIMESTAMP AND DtFin <= CURRENT_TIMESTAMP AND bDefault = 0")
        row2 = cursor.fetchone()
        if row2 is not None:
            return datetime.datetime.now()
        
        return datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
    
    except Exception as e:
        print(f"Il y a eu une erreur: {e}")
    finally:
        conn.close()

def getTemplateSlots(formatID):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        SELECT POSX, POSY, WIDTH, HEIGHT, IMG, ROTATE
        FROM SLOT s
        LEFT JOIN FORMAT f ON f.ID = s.ID_FORMAT
        WHERE ID_FORMAT = ?
        """, (formatID,))
        return cursor.fetchall()
    except Exception as e:
        print(f"Il y a eu une erreur(getTemplateSlots): {e}")
    finally:
        conn.close()

def getFormatIdByName(FormatName):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM FORMAT WHERE NOM = ?", (FormatName,))
        return cursor.fetchone()
    except Exception as e:
        print(f"Il y a eu une erreur(getFormatIdByName): {e}")
    finally:
        conn.close()

def getAllFormat():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM FORMAT")
        return cursor.fetchall()
    except Exception as e:
        print(f"Il y a eu une erreur: {e}")
    finally:
        conn.close()

def updateFormatPageIndex(newFormat):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE PHOTOMATON set FormatDefaut = ?", (newFormat,))
        conn.commit()
        update_dateMAJ()
    except Exception as e:
        conn.rollback()
        print(f"Il y a eu une erreur: {e}")
    finally:
        conn.close

def getCurrentIDConfig():
    global ID_BOOTH
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        #chargement des données de config par défaut depuis la bdd
        cursor.execute("SELECT ID, DtDebut, DtFin, bDefault " \
        "FROM CONFIGURATION WHERE ID_PHOTOMATON = ?", (ID_BOOTH,))

        activeRow = None
        currentDate = datetime.datetime.now()
        for row in cursor:
            if row[3] == 1:  # Vérifie si c'est la config par défaut
                activeRow = row
            else:
                dtDebut = datetime.datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S")
                dtFin = datetime.datetime.strptime(row[2], "%Y-%m-%d %H:%M:%S")
                if dtDebut <= currentDate <= dtFin:
                    activeRow = row
                    break

        return activeRow[0]
    except Exception as e:
        print(f"Il y a eu une erreur: {e}")
    finally:
        conn.close()

def getAllPrompts():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM PROMPT ORDER BY ID DESC")
        return cursor.fetchall()
    except Exception as e:
        print(f"Il y a eu une erreur (getAllPrompts): {e}")
    finally:
        conn.close()

def updatePrompt(positive,negative,prompt_id,pose_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(""" UPDATE PROMPT SET positive = :pos, negative=:neg , pose_id=:pose WHERE ID=:id""" , {
            "pos":positive,
            "neg": negative,
            "pose": pose_id,
            "id":prompt_id})
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Il y a eu une erreur (updatePrompt): {e}")
    finally:
        conn.close()

def getPromptFromId(prompt_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM PROMPT WHERE ID=:id", {"id":prompt_id})
        return cursor.fetchone()
    except Exception as e:
        print(f"Il y a eu une erreur (getPromptFromId): {e}")
    finally:
        conn.close()

def getPromptPositiveNotNull():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""SELECT DISTINCT positive FROM PROMPT
        WHERE positive IS NOT NULL AND positive!='' """)
        return cursor.fetchall()
    except Exception as e:
        print(f"Il y a eu une erreur (getPromptPositiveNotNull): {e}")
    finally:
        conn.close()

def getPromptNegativeNotNull():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""SELECT DISTINCT negative FROM PROMPT WHERE
        negative IS NOT NULL AND negative!='' """)
        return cursor.fetchall()
    except Exception as e:
        print(f"Il y a eu une erreur (getPromptNegativeNotNull): {e}")
    finally:
        conn.close()




def insertPrompt(name, positive, negative):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO PROMPT (name, positive, negative, pose_id)
        VALUES (?, ?, ?, 0)
    """, (name, positive, negative))

    conn.commit()

    new_id = cur.lastrowid   # récupère l'ID créé
    conn.close()

    return new_id


def deleteUser(user_id):
    """Supprime un utilisateur par son ID."""
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM USER WHERE ID = ?", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Erreur suppression utilisateur : {e}")
        return False
    finally:
        conn.close()

