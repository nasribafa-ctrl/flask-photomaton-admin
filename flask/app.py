import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from flask import Flask,render_template,url_for,redirect,send_file,request,redirect,jsonify,session, flash,send_from_directory,current_app
import sqlite3
from werkzeug.exceptions import abort
from werkzeug.security import generate_password_hash, check_password_hash
import subprocess
import platform
from functools import wraps
from pathlib import Path
import base64
from PIL import Image
import io
from template import templates_bp
from auth import normalize_roles, has_role, login_required, role_required, admin_required
import hashlib
from base.ia import save_ia_image
from werkzeug.utils import secure_filename
import logging
import time
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger('werkzeug')
log.setLevel(logging.DEBUG)
#output sur console
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
format=logging.Formatter("%(asctime)s %(levelname)s %(message)s")
console.setFormatter(format)
logging.getLogger("").addHandler(console)

os.environ['OPENSSL_CONF'] = '/dev/null'

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'base'))
assets_path = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','base','assets'))
UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','base', 'Uploads'))
ALLOWED_EXTENSIONS = {'jpg', 'jpeg'}
#Option pour activer les opérations relatives à l'appareil photo
CAMERA = False

if CAMERA:
    from camera_controller import camera_controller

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

#from printer import print_image
from bdd import *

name = get_nom()

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]

app.register_blueprint(templates_bp)

#permet a celui qui est connecter d'avoir access sur chacune des templates
@app.context_processor
def inject_user():
    """Permet d'utiliser l'objet 'current_user' dans n'importe quel template HTML."""
    return {
        'current_user': {
            'is_logged_in': 'user_id' in session,
            'username': session.get('username'),
            'role': session.get('role')
        },
        'has_role': has_role
    }

@app.route('/Authentification', methods=['GET', 'POST'])
def login():
    # Si l'utilisateur est déjà connecté, on l'envoie direct à l'index
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        # 1. On récupère proprement les données du formulaire
        username = request.form.get('username', '')
        pwd = request.form.get('password', '')
        
        # 2. On cherche l'utilisateur via la fonction getLogin (de bdd.py)
        user = getLogin(username)

        # 3. Vérification de sécurité
        # check_password_hash compare le texte clair (pwd) avec le hash (user['Mdp'])
        if user and pwd and check_password_hash(user['Mdp'], pwd):
            # On vide la session avant de la remplir pour éviter les vieux résidus
            session.clear()
            
            # On remplit la session avec les noms exacts utilisés partout ailleurs
            session['user_id'] = user['ID']
            session['username'] = user['Login']
            
            # Gestion du rôle : si c'est vide en BDD, on met 'user' par défaut
            permissions = normalize_roles(user['Role'])
            session['permissions'] = permissions
            session['role'] = ",".join(permissions) if permissions else 'user'

            flash('Heureux de vous revoir, ' + user['Login'] + ' !', 'success')
            return redirect(url_for('index'))
        
        else:
            # 4. En cas d'erreur
            flash('Identifiant ou mot de passe invalide.', 'danger')
            # On redirige vers la même page pour vider le formulaire
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('login'))
@app.route('/')
@role_required('lecture')
def index():

    # 1. On récupère les données et on s'assure que ce sont des listes
    try:
        photomatons = photomaton() or []
        raw_photos = all_photo() or []
        config = all_configuration() or []
        formats = getAllFormat() or []
    except Exception as e:
        print(f"Erreur lors de la récupération des données : {e}")
        photomatons, raw_photos, config = [], [], []

    processed_photos = []

    for p in raw_photos:
        photo_dict = dict(p)

        folder_name = os.path.basename(p['Repertoire'].strip().rstrip('/\\'))
        directory = os.path.join(base_path, 'captures', folder_name)

        if not os.path.isdir(directory):
            break

        photo_dict['folder_name'] = folder_name
        processed_photos.append(photo_dict)

    pm_data = photomatons if photomatons else {'Nom': 'Non configuré', 'nbPhotoLeft': 0}

    return render_template(
        'index.html',
        photo=processed_photos,
        photomatons=photomatons,
        photomaton=pm_data,
        config=config,
        name=name,
        formats=formats
    )

@app.route('/admin/utilisateurs', methods=['GET', 'POST'])
@admin_required
def liste_utilisateurs():
    


    if request.method == 'POST':

        username = request.form.get('username')
        pwd = request.form.get('password')
        confirmer_mdp = request.form.get('confirmer_mdp')
        roles = normalize_roles(request.form.getlist('roles'))  # IMPORTANT

        # Vérification champs obligatoires
        if not username or not pwd:
            flash("Tous les champs sont obligatoires.", "warning")
            return redirect(url_for('liste_utilisateurs'))

        # Vérification confirmation mot de passe
        if pwd != confirmer_mdp:
            flash("Les deux mots de passe ne correspondent pas.", "warning")
            return redirect(url_for('liste_utilisateurs'))

        # Sécurité : mot de passe ≠ identifiant
        if username.lower() == pwd.lower():
            flash("Le mot de passe ne peut pas être identique à l'identifiant.", "warning")
            return redirect(url_for('liste_utilisateurs'))

        # Vérification droits
        if not roles:
            flash("Veuillez choisir au moins un droit.", "warning")
            return redirect(url_for('liste_utilisateurs'))

        # Utilisateur déjà existant
        if getLogin(username):
            flash(f"L'utilisateur '{username}' existe déjà.", "warning")
            return redirect(url_for('liste_utilisateurs'))

        # Hash mot de passe
        hashed_pwd = generate_password_hash(pwd)
        role_string = ",".join(roles)

        # Création utilisateur
        if register_user(username, hashed_pwd, role_string):
            flash("Compte créé avec succès.", "success")
        else:
            flash("Erreur lors de la création du compte.", "danger")

        return redirect(url_for('liste_utilisateurs'))

    # ===== GET =====
    utilisateurs = all_users()
    return render_template(
        'user.html',
        users=utilisateurs,
        name=name,
        Return="index"
    )



   

@app.route('/photo/<int:photo_id>')
@role_required('lecture')
def photo(photo_id):
    try:
        # 1. Récupérer le nom brut depuis 
        raw_folder_path = get_folder_name_from_db(photo_id)
        
        if not raw_folder_path:
            return "Aucun répertoire enregistré pour cette photo.", 404

        # 2. Nettoyage : On ne garde que le nom du dossier final (ex: 2025_09_19_00_32_02)
        # Cela évite d'envoyer un chemin Linux complet dans l'URL
        folder_name = os.path.basename(raw_folder_path.strip('/'))

        # 3. Tentative de localisation du dossier sur le serveur
        # On teste les deux chemins possibles que tu as mentionnés
        path_options = [
            os.path.join(base_path, 'captures', folder_name),
            os.path.join(base_path, 'captures', 'Photos', folder_name)
        ]

        local_path = None
        for path in path_options:
            if os.path.exists(path):
                local_path = path
                break

        if not local_path:
            print(f"ERREUR : Dossier introuvable. Tenté : {path_options}")
            return f"Dossier introuvable sur le serveur ({folder_name})", 404

        # 4. Liste des images valides
        image_filenames = [
            f for f in os.listdir(local_path)
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))
        ]
        image_filenames.sort() # Optionnel : pour les avoir dans l'ordre (0.jpg, 1.jpg...)

        # 5. Récupération des détails pour le tableau
        details = detail_photo(photo_id)

        # 6. Envoi au template
        return render_template(
            'photo.html', 
            photo_id=photo_id, 
            images=image_filenames, 
            details=details, 
            name=name,
            folder_name=folder_name, # CRUCIAL pour url_for('serve_image')
            Return="index"
        )

    except Exception as e:
        print(f"ERREUR CRITIQUE ROUTE PHOTO : {e}")
        return f"Erreur interne : {str(e)}", 500

@app.route('/serve_image/<int:photo_id>/<folder_name>/<filename>')
@role_required('lecture')
def serve_image(photo_id, folder_name, filename):
    # Path to captures
    directory = os.path.join(base_path, 'captures', folder_name)
    return send_from_directory(directory, filename)

@app.route('/printer/<int:photo_id>', methods = ['GET','POST'])
@role_required('modification')
def printer(photo_id):
    repertoire = get_folder_name_from_db(photo_id)
    Format = get_format(photo_id)
    printer = print_image(repertoire,Format)
    return "Printing started", 200

@app.route('/add', methods=['GET', 'POST'])
@role_required('modification')
def add():
    if request.method == 'POST':
        form = request.form
        succes = insertConfig(form.get('checkBdefault'), form.get('Bkpimg'), form['BkpPath'], form.get('IA'), form.get('bChoixDesign'), form['NomConfig'], form['Prix'])
        if succes:
            succes()
        return redirect(url_for('index'))
    return render_template('create.html', name=name, Return = "index")

@app.route('/<int:config_id>/edit_configuration', methods=['GET', 'POST'])
@role_required('modification')
def edit_configuration(config_id):
    if request.method == 'POST':
            
        # It's a form submission
        form = request.form
        action = updateConfig(form.get('checkBdefault'),form.get('Bkpimg'), form['BkpPath'], form['dtDebut'], form['dtFin'], form.get('IA'), form.get('bChoixDesign'), form['NomConfig'], form['Prix'], config_id)
        if action:
            action()
        if form.get('checkBdefault') == '1':
                update_bdefault(config_id)
        return redirect(url_for('index'))     
      
    config = get_all_configuration_from_id(config_id)
    design = get_design_linked_with_config(config_id)
    return render_template('edit_configuration.html', config=config, name = name, designs = design, config_id = config_id, Return = "index")

@app.route('/<int:config_id>/add/design', methods = ['GET', 'POST'])
@role_required('modification')
def addDesign(config_id):
    if request.method == "POST":
        form = request.form
        insertIntoDesign(form['nomDesign'],form['format'],form['background'],config_id)
        return redirect(url_for('edit_configuration', config_id = config_id))
    return render_template('createDesign.html', name = name, config_id = config_id)

@app.route('/<int:config_id>/delete', methods=['POST'])
@role_required('suppression')
def delete(config_id):
    design_id = get_design_Id_linked_with_config(config_id)

    Delete(config_id)
    delDesignAssocieAConfig(config_id)
    delLayerAssocieADesign(design_id)
    return redirect(url_for('index'))

@app.route('/delete_design/<int:designs_id>', methods=['POST'])
@role_required('suppression')
def deleteDesign(designs_id):
    delDesign(designs_id)
    delLayerAssocieADesign(designs_id)
    return jsonify({
        "success": True,
    })

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):

    # empêcher auto-suppression
    if user_id == session.get('user_id'):
        flash("Vous ne pouvez pas supprimer votre propre compte.", "danger")
        return redirect(url_for('liste_utilisateurs'))

    # protéger root
    if user_id == 1:
        flash("Le compte administrateur principal est protégé.", "warning")
        return redirect(url_for('liste_utilisateurs'))

    if deleteUser(user_id):
        flash("Utilisateur supprimé avec succès.", "success")
    else:
        flash("Erreur lors de la suppression.", "danger")

    return redirect(url_for('liste_utilisateurs'))

@app.route('/list_images')
@role_required('lecture')
def list_images():
    folder = assets_path
    files = []
    for f in os.listdir(folder):
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            files.append(f)
    return jsonify(files)

@app.route('/base/assets/<path:filename>')
@role_required('lecture')
def serve_assets(filename):
    return send_from_directory(assets_path, filename)

def get_filenames(files):
    filenames = []
    for file in files:
        if file and file.filename:
            filenames.append(file.filename)
    return filenames

#upload folder image selection handler
@app.route('/upload', methods=['POST'])
@role_required('modification')
def upload():
    files = request.files.getlist('files[]')
    filenames = get_filenames(files)
    return jsonify({"files": filenames})

@app.route('/uploads/<filename>')
@role_required('lecture')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/base/captures/<template>/<filename>')
@role_required('lecture')
def serve_captures(template, filename):
    folder = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','base','captures',template))
    return send_from_directory(folder, filename)

@app.route('/printerStatus', methods=['POST'])
@role_required('modification')
def changePrinterStatus():
    data = request.get_json(silent=True)

    newvalue = int(data.get('newPrintStatus'))

    updatePrinterStatus(newvalue)

    return jsonify({"success": True})

@app.route('/changeIndexFormat', methods=['POST'])
@role_required('modification')
def changeIndexFormat():
    data = request.get_json(silent=True)

    updateFormatPageIndex(data['newDefautIndex'])

    return jsonify({"succes": True})

#### <CAMERA ####
if CAMERA:
    @app.route('/get_camera_settings')
    @admin_required
    def get_camera_settings():
        settings = camera_controller.get_camera_settings()
        return jsonify(settings)

    @app.route('/set_camera_setting', methods=['POST'])
    @admin_required
    def set_camera_setting():
        data = request.get_json()
        result = camera_controller.set_camera_setting(data.get('name'), data.get('value'))
        return jsonify(result)

    @app.route('/capture_test')
    @admin_required
    def capture_test():
        result = camera_controller.capture_test(UPLOAD_FOLDER)
        if result.get('success'):
            result['url'] = url_for('uploaded_file', filename=result['filename'])
        return jsonify(result)

    @app.route('/start_photomaton', methods=['POST'])
    @admin_required
    def start_photomaton():
        #Créer le fichier start.txt pour démarrer le photomaton
        try:
            # Chemin vers le fichier start.txt
            start_file_path = os.path.join(base_path, 'start.txt')
            with open(start_file_path, 'w') as f:
                pass  # Fichier créé vide
            # Vérifier que le fichier a été créé
            if os.path.exists(start_file_path):
                return jsonify({
                    'success': True, 
                    'message': f'Photomaton démarré - fichier créé: {start_file_path}'
                })
            else:
                return jsonify({
                    'success': True, 
                    'error': 'Go!'
                })
                
        except Exception as e:
            return jsonify({
                'success': False, 
                'error': f'Erreur: {str(e)}'
            })

@app.route('/prompt')
@role_required('lecture')
def prompt():
    prompts = getAllPrompts()

    # MAINTENANT seulement on peut créer poses
    poses = {
        p["ID"]: p["pose_id"] or 0
        for p in prompts
    }

    return render_template(
        "prompt.html",
        prompts=prompts,
        poses=poses,
        name = name
    )

@app.route('/prompt/<int:prompt_id>/edit', methods=['GET', 'POST'])
@role_required('modification')
def modifier_prompt(prompt_id):
    prompt = getPromptFromId(prompt_id)
    if not prompt:
        flash("Prompt introuvable", "danger")
        return redirect(url_for('prompt'))

    if request.method =="POST":

        positive = request.form.get("positive")
        negative = request.form.get("negative")
        pose_id = request.form.get("pose_id", type=int, default=0)


        if not positive or not positive.strip():
             flash("Prompt positif requis", "warning")
             return redirect(url_for("modifier_prompt", prompt_id=prompt_id))


       


        updatePrompt(positive,negative,prompt_id,pose_id)

        return redirect(url_for('prompt'))


    rows_positive = getPromptPositiveNotNull()

    positive_suggestion =[row["positive"] for row in rows_positive]
               
    rows_negative = getPromptNegativeNotNull()

    negative_suggestion= [row["negative"] for row in rows_negative]
    return render_template("modifier_prompt.html", prompt=prompt , positive_suggestion=positive_suggestion , all_prompts = getAllPrompts(),negative_suggestion=negative_suggestion, name = name)








@app.route('/prompt/<int:prompt_id>/test', methods=['GET','POST'])
@role_required('modification')
def utiliser_prompt(prompt_id):


    pose_test_id = 0   

    if request.method == "POST":
        positive = request.form.get("positive")
        negative = request.form.get("negative")
        pose_test_id = request.form.get("pose_id", type=int, default=0)
        




        if not positive or not  positive.strip():
            flash("Prompt positif requis", "warning")
            return redirect(url_for("modifier_prompt", prompt_id=prompt_id))


        updatePrompt(positive, negative, prompt_id, pose_test_id)


    prompt = getPromptFromId(prompt_id)

    if not prompt:
        flash("Prompt introuvable", "danger")
        return redirect(url_for('prompt'))
    
    # Vérification de la pose en session

    if  pose_test_id is None:
        pose_test_id = 0
        flash("Erreur : Vous devez choisir une image dans la liste avant de tester.", "warning")

    # Préparation de l'image
    nom_image = secure_filename(f"{prompt['name']}.ia.jpg")

    analyse = {
        "positive_longeur": len(prompt["positive"] or ""),
        "negative_longeur": len(prompt["negative"] or ""),
        "est_positive": bool((prompt["positive"] or "").strip()),
        "est_negative": bool((prompt["negative"] or "").strip()),
        "status": "Prêt pour l'utilisation IA" if prompt["positive"] else "Prompt incomplet"
    }

    prompt_instruction = {
        "name": prompt["name"],
        "positive": prompt["positive"],
        "negative": prompt["negative"]
    }

    # Génération de l'image
    try:
        save_ia_image(
            capture_path=os.path.join(base_path, "ia_images"),
            index=pose_test_id,
            prompt=prompt_instruction,
            filename=nom_image
        )
    except Exception as e:
        flash(f"Erreur lors de la génération IA : {str(e)}", "danger")

    return render_template(
        "prompt_test.html",
        prompt=prompt,
        analyse=analyse,
        nom_image=nom_image,
        name = name
    )

@app.route("/ia/<path:nom_image>")
@role_required('lecture')
def image_ia(nom_image):
    return send_from_directory(
        os.path.join(base_path, "ia_images"),
        nom_image
    )

@app.route('/prompt/<int:prompt_id>/pose', methods=['POST'])
@role_required('modification')
def enregistrer_pose(prompt_id):
    pose_id = request.form.get("pose_id", type=int)

    if pose_id in (None, "", "add"):
        return jsonify({"success": False})

    pose_id = int(pose_id)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "UPDATE PROMPT SET pose_id = ? WHERE ID = ?",
        (pose_id, prompt_id)
    )

    conn.commit()
    conn.close()

    return jsonify({"success": True})






@app.route('/ia_images/<filename>')
@role_required('lecture')
def serve_ia_base_images(filename):


    # On pointe directement vers le dossier base/ia_images
    folder = os.path.join(base_path, 'ia_images')
    return send_from_directory(folder, filename)



@app.route("/prompt/create", methods=["GET", "POST"])
@role_required('modification')
def creer_prompt():

    name = get_nom()   

    if request.method == "POST":

        session.pop("ia_generated", None)


        nom = request.form.get("nom")
        positive = request.form.get("positive")
        negative = request.form.get("negative")
        pose_id = request.form.get("pose_id", type=int , default=0)



    
        if not positive or not positive.strip():
          flash("Prompt positif requis", "warning")
          return redirect(url_for("creer_prompt"))
        


        if "tester" in request.form:
            session['prompt_creationTest']={
                "name":nom,
                "positive":positive,
                "negative":negative,
                "pose_id":pose_id
            }

            return redirect(url_for("tester_prompt_creer"))
        

  ##ici on crée"
        
        insertPrompt(nom,positive,negative)

        session.pop("prompt_creationTest", None)

        
        flash("prompt créé avec succès", "success")
        


        return redirect(url_for("prompt"))

    rows_positive = getPromptPositiveNotNull()
    positive_suggestion = [row["positive"] for row in rows_positive]

    rows_negative = getPromptNegativeNotNull()
    negative_suggestion = [row["negative"] for row in rows_negative]

    return render_template(
        "crée_prompt.html",
        name=name,
        positive_suggestion=positive_suggestion,
        negative_suggestion=negative_suggestion
    )




@app.route("/prompt/<int:prompt_id>/delete", methods=["POST"])
@role_required('suppression')
def supprimer_prompt(prompt_id):

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM PROMPT WHERE ID = ?", (prompt_id,))
        conn.commit()

    except Exception as e:
        conn.rollback()
        print("Erreur suppression:", e)

    finally:
        conn.close()   

    
    return redirect(url_for("prompt"))



@app.route("/prompt/test-create")
@role_required('modification')
def tester_prompt_creer():

    prompt = session.get("prompt_creationTest")

    if not prompt:
        flash("Aucun prompt à tester", "warning")
        return redirect(url_for("creer_prompt"))

    nom_image = secure_filename(
        f"{prompt['name']}_{int(time.time())}.ia.jpg"
    )

    # ✅ génération UNE SEULE FOIS
    if not session.get("ia_generated"):

        save_ia_image(
            capture_path=os.path.join(base_path, "ia_images"),
            index=prompt.get("pose_id", 0),
            prompt=prompt,
            filename=nom_image
        )

        session["ia_generated"] = True


    analyse = {
    "positive_longeur": len(prompt.get("positive", "")),
    "negative_longeur": len(prompt.get("negative", "")),
    "est_positive": bool(prompt.get("positive", "").strip()),
    "est_negative": bool(prompt.get("negative", "").strip()),
    "status": "Prêt pour l'utilisation IA" if prompt.get("positive") else "Prompt incomplet"
}


    return render_template(
        "prompt_test.html",
        prompt=prompt,
        analyse=analyse,
        nom_image=nom_image,
        temp_mode=True,
        name=name
    )








    

if __name__ == "__main__":
    app.run(debug=True)

    