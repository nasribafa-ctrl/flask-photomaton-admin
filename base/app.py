from flask import Flask,render_template,url_for,redirect,send_file,request,redirect,jsonify,session, flash,send_from_directory,current_app
import os
import sqlite3
from werkzeug.exceptions import abort
from werkzeug.security import generate_password_hash, check_password_hash
import subprocess
import platform
from functools import wraps
import sys
from pathlib import Path
import base64
from PIL import Image
import io
from template import templates_bp
import hashlib
from dotenv import load_dotenv

load_dotenv()

os.environ['OPENSSL_CONF'] = '/dev/null'

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'base'))
assets_path = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','base','assets'))
UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','base', 'Uploads'))
ALLOWED_EXTENSIONS = {'jpg', 'jpeg'}
#Option pour activer les opérations relatives à l'appareil photo
CAMERA = True

if CAMERA:
    import camera_controller

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
sys.path.append(base_path)

from printer import print_image
from bdd import *

name = get_nom()

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Veuillez vous connecter.', 'warning')
            return redirect(url_for('login'))
        # On vérifie si le rôle enregistré en session est bien 'admin'
        if 'admin' not in session.get('permissions', []):
            flash('Accès refusé : réservé aux administrateurs.', 'danger')
            return redirect(url_for('index'))
        return view_func(*args, **kwargs)
    return wrapper

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
        }
    }

@app.route('/Authentification', methods=['GET', 'POST'])
def login():
    # Si l'utilisateur est déjà connecté, on l'envoie direct à l'index
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        # 1. On récupère proprement les données du formulaire
        username = request.form.get('username')
        pwd = request.form.get('password')
        
        # 2. On cherche l'utilisateur via la fonction getLogin (de bdd.py)
        user = getLogin(username)

        # 3. Vérification de sécurité
        # check_password_hash compare le texte clair (pwd) avec le hash (user['Mdp'])
        if user and check_password_hash(user['Mdp'], pwd):
            # On vide la session avant de la remplir pour éviter les vieux résidus
            session.clear()
            
            # On remplit la session avec les noms exacts utilisés partout ailleurs
            session['user_id'] = user['ID']
            session['username'] = user['Login']
            
            # Gestion du rôle : si c'est vide en BDD, on met 'user' par défaut
            session['role'] = user['Role'] if user['Role'] else 'user'

            if user['Role']:
                 session['permissions'] = user['Role'].split(',')
            else:
                 session['permissions'] = []

            flash('Heureux de vous revoir, ' + user['Login'] + ' !', 'success')
            return redirect(url_for('index'))
        
        else:
            # 4. En cas d'erreur
            flash('Identifiant ou mot de passe invalide.', 'danger')
            # On redirige vers la même page pour vider le formulaire
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/Inscription', methods=['GET', 'POST'])
@admin_required
def register():
    # 1. Vérification de sécurité (Admin obligatoire)
    if 'admin' not in (session.get('role') or '').lower():    
        flash("Accès refusé. Seul l'administrateur peut créer des comptes.", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        pwd = request.form.get('password')
        selected_permissions = request.form.getlist('permissions[]')
        
        # 2. Validation des champs
        if not username or not pwd:
            flash("L'identifiant et le mot de passe sont obligatoires.", "warning")
            return render_template('register.html', name=name)
            
        if not selected_permissions:
            flash("Veuillez attribuer au moins un droit.", "warning")
            return render_template('register.html', name=name)

        # 3. Vérification d'existence (Évite les doublons)
        if getLogin(username):
            flash(f"L'utilisateur '{username}' existe déjà.", 'danger')
            return render_template('register.html', name=name)

        # 4. HACHAGE OBLIGATOIRE (Comme demandé)
        # On transforme le mot de passe clair en hash ici même
        hashed_pwd = generate_password_hash(pwd)

        # 5. Préparation des droits ("lecture,edition")
        role_string = ",".join(selected_permissions)

        # 6. Envoi vers bdd.py
        # On passe 'hashed_pwd' car le travail est déjà fait !
        if register_user(username, hashed_pwd, role_string):
            flash(f"Compte '{username}' créé avec succès !", 'success')
            return redirect(url_for('liste_utilisateurs'))
        else:
            flash('Erreur technique lors de la création.', 'danger')
                
    return render_template('register.html', name=name)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('login'))
    
@app.route('/')
@admin_required
def index():
    # 1. On récupère les données et on s'assure que ce sont des listes (même vides)
    try:
        photomatons = photomaton() or []
        raw_photos = all_photo() or []
        config = all_configuration() or []
        formats = getAllFormat() or []
    except Exception as e:
        print(f"Erreur lors de la récupération des données : {e}")
        photomatons, raw_photos, config, formats = [], [], [], []


    processed_photos = []
    for p in raw_photos:
        # On transforme l'objet SQL en dictionnaire pour pouvoir ajouter des clés
        photo_dict = dict(p)
        
        # On extrait le nom du dossier à partir du chemin enregistré en BDD
        # (Si ta colonne s'appelle 'Repertoire', on utilise p['Repertoire'])
        raw_path = p['Repertoire'] or ""

        if not raw_path:
            continue
        
        folder_name = os.path.basename(raw_path.strip().rstrip('/\\'))
        directory = os.path.join(base_path, 'captures', folder_name)

        # FILTER HERE
        if not os.path.isdir(directory):
            continue  # skip this photo entirely

        photo_dict['folder_name'] = folder_name
        processed_photos.append(photo_dict)

    pm_data = photomatons if photomatons else {'Nom': 'Non configuré', 'nbPhotoLeft': 0}

    return render_template('index.html', photo=processed_photos,photomatons = photomatons,photomaton=pm_data,config=config, name=name,formats=formats)

@app.route('/admin/utilisateurs')
@admin_required
def liste_utilisateurs():
    """Affiche la liste de tous les utilisateurs (pour l'admin)."""
    # Appel de la fonction all_users que tu as ajoutée dans bdd.py
    utilisateurs = all_users()
    return render_template('user.html', users=utilisateurs, name=name,Return="index")

@app.route('/photo/<int:photo_id>')
@admin_required
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
@admin_required
def serve_image(photo_id, folder_name, filename):
    # Path to captures
    directory = os.path.join(base_path, 'captures', folder_name)
    return send_from_directory(directory, filename)

@app.route('/printer/<int:photo_id>', methods = ['GET','POST'])
@admin_required
def printer(photo_id):
    repertoire = get_folder_name_from_db(photo_id)
    Format = get_format(photo_id)
    printer = print_image(repertoire,Format)
    return "Printing started", 200

@app.route('/add', methods=['GET', 'POST'])
@admin_required
def add():
    if request.method == 'POST':
        form = request.form
        succes = insertConfig(form.get('checkBdefault'), form.get('Bkpimg'), form['BkpPath'], form['dtDebut'], form['dtFin'], form.get('IA'), form.get('bChoixDesign'), form['NomConfig'], form['Prix'])
        if succes:
            succes()
        return redirect(url_for('index'))
    return render_template('create.html', name=name, Return = "index")

@app.route('/<int:config_id>/edit_configuration', methods=['GET', 'POST'])
@admin_required
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
@admin_required
def addDesign(config_id):
    if request.method == "POST":
        form = request.form
        insertIntoDesign(form['nomDesign'],form['format'],form['background'],form['nbposes'],config_id)
        return redirect(url_for('edit_configuration', config_id = config_id))
    return render_template('createDesign.html', name = name, config_id = config_id)

@app.route('/<int:config_id>/delete')
@admin_required
def delete(config_id):
    design_id = get_design_Id_linked_with_config(config_id)

    Delete(config_id)
    delDesignAssocieAConfig(config_id)
    delLayerAssocieADesign(design_id)
    return redirect(url_for('index'))

@app.route('/delete_design/<int:designs_id>', methods=['POST'])
@admin_required
def deleteDesign(designs_id):
    delDesign(designs_id)
    delLayerAssocieADesign(designs_id)
    return jsonify({
        "success": True,
    })

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/admin/delete_user/<int:user_id>')
@admin_required
def delete_user(user_id):
    """Supprime un utilisateur spécifique."""
    # SÉCURITÉ : Empêcher de supprimer son propre compte
    if user_id == session.get('user_id'):
        flash("Action impossible : vous ne pouvez pas supprimer votre propre compte.", "danger")
        return redirect(url_for('liste_utilisateurs'))

    # SÉCURITÉ : Empêcher de supprimer l'ID 1 (souvent l'admin principal)
    if user_id == 1:
        flash("Action interdite : le compte administrateur racine est protégé.", "warning")
        return redirect(url_for('liste_utilisateurs'))

    # Appel de la fonction deleteUser que tu as ajoutée dans bdd.py
    if deleteUser(user_id):
        flash("L'utilisateur a été supprimé avec succès.", "success")
    else:
        flash("Erreur lors de la suppression.", "danger")

    return redirect(url_for('liste_utilisateurs'))

@app.route('/list_images')
@admin_required
def list_images():
    folder = assets_path
    files = []
    for f in os.listdir(folder):
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            files.append(f)
    return jsonify(files)

@app.route('/base/assets/<path:filename>')
@admin_required
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
@admin_required
def upload():
    files = request.files.getlist('files[]')
    filenames = get_filenames(files)
    return jsonify({"files": filenames})

@app.route('/uploads/<filename>')
@admin_required
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/base/captures/<template>/<filename>')
@admin_required
def serve_captures(template, filename):
    folder = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','base','captures',template))
    return send_from_directory(folder, filename)

@app.route('/printerStatus', methods=['POST'])
def changePrinterStatus():
    data = request.get_json(silent=True)

    newvalue = int(data.get('newPrintStatus'))

    updatePrinterStatus(newvalue)

    return jsonify({"success": True})

@app.route('/changeIndexFormat', methods=['POST'])
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
    #### CAMERA/> ####

if __name__ == "__main__":
    app.run(debug=True)