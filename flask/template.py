from flask import (
    Blueprint, request, jsonify, render_template,
    redirect, url_for, send_from_directory
)
import os, io, base64
from PIL import Image
import sys

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'base'))
assets_path = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','base','assets'))
UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','base', 'Uploads'))

sys.path.append(base_path)
from bdd import *

name = get_nom()

templates_bp = Blueprint(
    'templates',
    __name__
)

@templates_bp.route('/api/template-slots/<format_name>')
def api_template_slots(format_name):
    format_row = getFormatIdByName(format_name)
    if not format_row:
        return jsonify([])

    format_id = format_row['ID']
    slots = getTemplateSlots(format_id)

    payload = []
    for s in slots:
        img = s["IMG"]

        if not img:
            print("EMPTY IMG for slot ID:", s.get("ID"))
            continue
        if isinstance(img, str):
            print("IMG IS STRING for slot ID:", s.get("ID"))
            img = img.encode("latin1")

        payload.append({
            "left": s["POSX"],
            "top": s["POSY"],
            "width": s["WIDTH"],
            "height": s["HEIGHT"],
            "image": base64.b64encode(s["IMG"]).decode("utf-8"),
            "rotate": s["ROTATE"]
        })

    return jsonify(payload)

@templates_bp.route('/<int:config_id>/editeur_templates', methods=['GET', 'POST'])
def editeurTemplate(config_id):
    format = get_format()
    usedFormat = get_design_linked_with_config(config_id)
    
    #on parcours les noms du format
    used_format_names = {u['FORMAT'] for u in usedFormat}
    nbposes = {u['NBPOSES'] for u in usedFormat}
    print("nbposes:", nbposes)

    server_images = os.listdir(UPLOAD_FOLDER) if os.path.exists(UPLOAD_FOLDER) else []
    return render_template('editeur_templates.html',config_id=config_id,server_images=server_images,name=name,nbposes=nbposes,mode="create",Return="config", formats = format,used_format_names=used_format_names)

@templates_bp.route('/<int:config_id>/editeur_templates/<int:design_id>', methods=['GET'])
def edit_Template(config_id, design_id):

    layers = get_layers(design_id)
    design = getDesignById(design_id, config_id)
    formats = get_format()

    layers_payload = []

    background_b64 = None
    if design['Background']:
        background_b64 = base64.b64encode(design['Background']).decode('utf-8')

    for layer in layers:
        layers_payload.append({
            "id": layer['ID'],
            "image": base64.b64encode(layer['Image']).decode('utf-8'),
            "x": layer['PosX'],
            "y": layer['PosY'],
            "image_name": layer['ImageNom'],
        })

    return render_template( "editeur_templates.html", mode="edit", design_id=design_id, design_nbposes=design['NBPOSES'], design_name=design['NomDesign'], design_format=design['Format'], layers=layers_payload, background=background_b64, Return="config", config_id=config_id, formats=formats)

@templates_bp.route('/saveTemplate', methods=['POST'])
def saveTemplate():
    data = request.get_json()

    name = data['name']
    format_ = data['format']
    config_id = data['config_id']
    background = data.get('background')
    layers = data.get('layers', [])
    nbposes = data.get('nbposes')

    usedFormat = get_design_linked_with_config(config_id)
    
    #on parcours les noms du format
    used_format_names = {u['FORMAT'] for u in usedFormat}

    if format_ in used_format_names:
        return jsonify({"succes": False, "error": "Le format choisi existe déjà"})

    # ---- CREATE DESIGN ----
    # insertIntoDesign returns the actual ID
    design_id = insertIntoDesign(name, format_, None, nbposes, config_id)

    # ---- SAVE BACKGROUND ----
    if background:
        bg_source = None
        server_path = os.path.join(assets_path, background)
        upload_path = os.path.join(UPLOAD_FOLDER, background)

        if os.path.exists(server_path):
            bg_source = server_path
        elif os.path.exists(upload_path):
            bg_source = upload_path

        if bg_source:
            with Image.open(bg_source) as img:
                img = img.convert("RGBA")
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                bg_binary = buf.getvalue()
            updateDesignBackground(design_id, bg_binary)

    # ---- SAVE LAYERS ----
    for layer in layers:
        header, encoded = layer['image'].split(",", 1)
        binary_image = base64.b64decode(encoded)

        insertIntoLayer(
            binary_image,
            layer['x'],
            layer['y'],
            design_id,
            layer.get('image_name', f'layer_{layer.get("index",0)}')
        )

    return jsonify({"success": True, "design_id": design_id})

@templates_bp.route('/update_template', methods=['POST'])
def update_template():

    data = request.get_json()
    if not data:
        return jsonify(error="Invalid JSON"), 400

    design = data.get('design', {})
    design_id = design.get('id')

    if not design_id:
        return jsonify(error="Missing design ID"), 400

    # ==========================================
    # 1️⃣ UPDATE DESIGN INFO
    # ==========================================
    updateDesign(
        design.get('name'),
        design.get('format'),
        None,  # background handled separately
        design.get('nbposes'),
        design_id
    )

    # ==========================================
    # 2️⃣ UPDATE BACKGROUND
    # ==========================================
    if 'background' in design:

        background_data = design['background']

        if background_data is None:
            updateDesignBackground(design_id, None)

        elif isinstance(background_data, str) and ',' in background_data:
            _, encoded = background_data.split(',', 1)
            bg_binary = base64.b64decode(encoded)
            updateDesignBackground(design_id, bg_binary)

    # ==========================================
    # 3️⃣ UPDATE EXISTING LAYERS
    # ==========================================
    for layer in data.get("existingLayers", []):
        binary_image = None
        image_data_url = layer.get('image')

        if image_data_url:
            _, encoded = image_data_url.split(',', 1)
            binary_image = base64.b64decode(encoded)

        update_layer(
            binary_image,
            layer['posX'],
            layer['posY'],
            layer['id'],
            design_id
        )

    # ==========================================
    # 4️⃣ INSERT NEW LAYERS
    # ==========================================
    for layer in data.get("newLayers", []):
        image_data = layer['image']

        if ',' in image_data:
            _, image_data = image_data.split(',', 1)

        binary_image = base64.b64decode(image_data)

        insertIntoLayer(
            binary_image,
            layer['posX'],
            layer['posY'],
            design_id,
            layer['image_name']
        )

    # ==========================================
    # 5️⃣ DELETE LAYERS
    # ==========================================
    for layer_id in data.get("deletedLayers", []):
        delLayer(layer_id)

    return jsonify(success=True)