from ast import arg
from turtle import position
import gphoto2 as gp
#import cv2
import os
import time
import datetime
from datetime import date
import sys
from PIL import Image, ImageDraw, ImageFont
from tempfile import mktemp
import logging
from pathlib import Path
import uuid
#import serial
#from serial.tools import list_ports
import json
from io import BytesIO
import argparse
import traceback
import base64
import requests
#import usb.core
#import db
import webuiapi
import random
import threading
import RPi.GPIO as GPIO
from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.core.virtual import viewport
from luma.core.legacy import text, show_message
from luma.core.legacy.font import proportional, CP437_FONT, TINY_FONT, SINCLAIR_FONT, LCD_FONT, ATARI_FONT
import tm1637
import urllib3 as urllib
from urllib.parse import urlparse
import socket
import requests

# Neopixel
from multiprocessing.connection import Client

# analog to digital board ADS1115
import busio
import board
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

#database library
import sqlite3
import bdd as bdd

#printer
import printer as printer

# Pins def
COIN_PIN = 16
START_PIN = 20
AUX_PIN = 23
CB_PIN = 14
SELECTOR_PIN = 19

NOM_BOOTH = os.uname().nodename
ID_CURR_DESIGN = None

# constants
COINS_MULTI = 50
COINS = 0
WAITFORSTART = True
START = False

#Globals
CONFIG = bdd.Config()
NBPIECES = 0
CURR_LED_MATRIX = ""
MAX7219 = None
MODE_PAIEMENT = "FREE"  # CB, ESPECES, FREE

SERVER_ADDR = os.environ.get("SD_API_HOST", "127.0.0.1")
SERVER_PORT = int(os.environ.get("SD_API_PORT", "7860"))

global CURRENT_PATH, PROCESS_FILE_BACKGROUND, PROCESS_FILE_MASK
global LOGO1_POS, LOGO2_POS, IA, api, DETECT_FACES
global ADS1115, A0, A1, A2, A3, FORMAT
global connNeopixel
connNeopixel= None

#keypad phone
import digitalio
import adafruit_matrixkeypad
cols = [digitalio.DigitalInOut(x) for x in (board.D22, board.D24, board.D12)]
rows = [digitalio.DigitalInOut(x) for x in (board.D5, board.D6, board.D13, board.D26)]
keys = ((1, 2, 3), (4, 5, 6), (7, 8, 9), ("*", 0, "#"))
global keypad
keypad = None

#LCD screen phone
from time import sleep
from RPLCD.i2c import CharLCD
global lcd
lcd = None

#cashless MDB
import cashlessMDB
import queue
global mdb_manager, payment_events, cb_transaction_requested, cb_transaction_active
mdb_manager = None
payment_events = queue.Queue()
cb_transaction_requested = False  # Flag pour demander une transaction
cb_transaction_active = False     # Flag pour transaction en cours

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))
LOG_FILENAME = Path(CURRENT_PATH, "log.txt")
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    filename=LOG_FILENAME,
    level=logging.DEBUG,
    datefmt="%Y-%m-%d %H:%M:%S",
)
#output sur console
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
format=logging.Formatter("%(asctime)s %(levelname)s %(message)s")
console.setFormatter(format)
logging.getLogger("").addHandler(console)
#deactivate Pillow logging
logging.getLogger('PIL').setLevel(logging.WARNING)

#debug gphoto2
def callback(level, domain, string, data=None):
    logging.error('Callback: level =', level, ', domain =', domain, ', string =', string, 'data =', data)

callback_obj1 = gp.check_result(gp.gp_log_add_func(gp.GP_LOG_ERROR, callback))

# init apn
def init_camera():
    """Initialiser la caméra une seule fois au démarrage"""
    logging.info("Camera init - Wait loop for camera")
    
    camera = gp.gp_camera_new()[1]  # Récupère seulement l'instance camera
    
    while True:
        logging.info("Camera init - connexion")
        time.sleep(2)
        error = gp.gp_camera_init(camera)

        if error >= gp.GP_OK:
            # operation completed successfully so exit loop
            break
        if error != gp.GP_OK:
            logging.info("Erreur cam1:"+ str(error))
            raise gp.GPhoto2Error(error)
        # no camera, try again in 2 seconds
        time.sleep(5)

    logging.info("Camera init - first capture")
    time.sleep(5)
    init = False
    while init == False:
        try:
            camera.capture(gp.GP_CAPTURE_IMAGE)
            init = True
        except Exception as e:
            logging.info("Erreur caméra:"+ str(e))
        time.sleep(5)

    release_camera(camera)
    return camera

def release_camera(camera):
    """Libérer la caméra"""
    try:
        if camera:
            gp.gp_camera_exit(camera)
            logging.info("Caméra libérée")
    except Exception as e:
        logging.error(f"Erreur lors de la libération de la caméra: {e}")


def capture(camera, capture_uuid):
    global MAX7219, CURR_LED_MATRIX
    
    CAPTURE_PATH = Path(CAPTURE_FOLDER, str(capture_uuid))

    if not CAPTURE_PATH.exists():
        os.makedirs(CAPTURE_PATH)

    logging.info("Capture - Start shooting - " + str(capture_uuid))
    nextShot = time.time()
    current = nextShot
    
    # Initialiser la caméra pour cette session
    try:
        gp.gp_camera_init(camera)
    except Exception as e:
        logging.error(f"Erreur initialisation caméra: {e}")
        return

    for image_index in range(CONFIG.nbposes):
        logging.info("Shot " + str(image_index))
        filename = str(image_index) + ".jpg"
        target = os.path.join(CAPTURE_PATH, filename)
        
        #countdown
        MAX7219.clear()
        for second in reversed(range(1, CONFIG.photo_pause+1)):
            MAX7219.clear()
            with canvas(MAX7219) as draw:
                text(draw, (1, 1), str(second), fill="white", font=proportional(CP437_FONT))
            CURR_LED_MATRIX = str(second)
            time.sleep(1)
        showImg("smiley.png")

        max_retries = 3
        retry_delay = 1  # seconde
        for attempt in range(max_retries):
            try:
                file_path = camera.capture(gp.GP_CAPTURE_IMAGE)
                break  # Si la capture réussit, sortir de la boucle
            except gp.GPhoto2Error as e:
                if attempt == max_retries - 1:
                    raise  # Relancer l'erreur si tous les réessais échouent
                logging.warning(f"Échec de la capture (tentative {attempt + 1}), réessai...")
                time.sleep(retry_delay)
                # Réinitialiser la caméra avant de réessayer
                gp.gp_camera_exit(camera)
                time.sleep(1)
                gp.gp_camera_init(camera)
        
        # download
        camera_file = camera.file_get(
            file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL
        )
        camera_file.save(target)

        #logging.info("process image")
        if FORMAT == "2xPortrait":
            im1 = processImage(capture_uuid, str(image_index) + ".jpg")
        elif FORMAT == "2xPaysage":
            im1 = processImageVertical(capture_uuid, str(image_index) + ".jpg")
        elif FORMAT == "10x15Paysage" or FORMAT == "10x15PaysageNB":
            im1 = processImage10x15(capture_uuid, str(image_index) + ".jpg")
            
        if IA:
            logging.info("process ia")
            task = threading.Thread( target = threadIA, name=str(image_index), args   = ( capture_uuid, image_index ) )
            task.start()

    # Libérer la caméra après la session de capture
    try:
        gp.gp_camera_exit(camera)
        logging.info("Caméra libérée après capture")
    except Exception as e:
        logging.error(f"Erreur libération caméra après capture: {e}")

    logging.info("fin capture")

def is_server_available(url):
    """Vérifie si le serveur est accessible."""
    try:
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname
        port = parsed_url.port or (80 if parsed_url.scheme == "http" else 443)
        
        # Vérification DNS + connexion TCP
        with socket.create_connection((hostname, port), timeout=5):
            return True
    except (socket.gaierror, socket.timeout, ConnectionRefusedError):
        return False
    except Exception as e:
        logging.warning(f"Erreur de vérification du serveur: {str(e)}")
        return False    
def save_ia_image(capture_path, index, prompt):
    if not is_server_available("http://" + SERVER_ADDR + ":" + str(SERVER_PORT)):
        logging.error("Le serveur n'est pas disponible - annulation du traitement")
        return False  # Ou lancez une exception selon votre besoin

    try:
        source_image_path = Path(capture_path, f"{index}.jpg")
        with Image.open(source_image_path) as source:
            start = time.time()

            unit0 = webuiapi.ControlNetUnit(image=source, 
                                            enabled=True,
                                            module='canny', 
                                            model='sdxl_canny [a2e6a438]', 
                                            weight=0.8, 
                                            control_mode = 2,
                                            guidance_end = 1,
                                            guidance_start = 0,
                                            threshold_a = 100,
                                            threshold_b = 200)
            #ctrlUnit = []
            #if prompt["respect_pose"] == True:
            ctrlUnit = [unit0]

            reactor = webuiapi.ReActor(
                img=source,
                enable=True,
                source_faces_index = "0,1,2,3,4", #2 Comma separated face number(s) from swap-source image
                faces_index = "0,1,2,3,4", #3 Comma separated face number(s) for target image (result)
                model = 'inswapper_128.onnx', # None, #4 model path
                face_restorer_name = "CodeFormer", #4 Restore Face: None; CodeFormer; GFPGAN
                face_restorer_visibility = 1, #5 Restore visibility value
                restore_first = True,  #7 Restore face -> Upscale
                upscaler_name =  "None",# None, # "R-ESRGAN 4x+", #8 Upscaler (type 'None' if doesn't need), see full list here: http://127.0.0.1:7860/sdapi/v1/script-info -> reactor -> sec.8
                upscaler_scale = 2,#9 Upscaler scale value
                upscaler_visibility = 1,
                swap_in_source = True,
                swap_in_generated = True,
                console_logging_level = 2, #13 Console Log Level (0 - min, 1 - med or 2 - max)
                gender_source = 0, #14 Gender Detection (Source) (0 - No, 1 - Female Only, 2 - Male Only)
                gender_target = 0, #14 Gender Detection (Target) (0 - No, 1 - Female Only, 2 - Male Only)
                save_original = False,
                codeFormer_weight = 1,
                source_hash_check = True,
                target_hash_check = True,
                device = "CUDA", #or CPU
                mask_face = False,
                select_source = 0, #IMPORTANT. MUST BE 0 or faceswap won't work
                face_model = None,
            )

            
            try:
                result1 = api.txt2img(prompt=prompt["positive"],
                                    negative_prompt=prompt["negative"],
                                    seed=-1,
                                    cfg_scale=1,
                                    steps=9,
                                    width=1150,
                                    height=875,
                                    controlnet_units=ctrlUnit,
                                    restore_faces=False,
                                    reactor=reactor)
            except Exception as e:
                logging.error("Déconnexion, nouvelle tentative:")
                #deuxiéme tentative
                result1 = api.txt2img(prompt=prompt["positive"],
                                    negative_prompt=prompt["negative"],
                                    seed=-1,
                                    cfg_scale=1,
                                    steps=9,
                                    width=1150,
                                    height=875,
                                    controlnet_units=ctrlUnit,
                                    restore_faces=False,
                                    reactor=reactor)
                                    
            #capture_uuid = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            filepath = Path(capture_path, f"{index}.ia.jpg")
            filepathSD = Path(capture_path, f"{index}.iabkp.jpg")
            result1.image.save(filepath)
            #Resize sinon image en 872 x 1144
            imageIA = Image.open(filepath)
            (width, height) = (1150, 875)
            imageIA = imageIA.resize((width, height))
            imageIA.save(filepath)
            
            end = time.time()
            logging.info(str(index) + ": %s seconds ---" % (end - start))

            # Ouverture de l'image recue pour traitement
            with Image.open(filepath) as img:
                
                # Save the final image after cropping, resizing, and adding the label
                font_size = 54
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
                draw = ImageDraw.Draw(img) 
                if FORMAT == "2xPaysage":
                    draw.text((20, 20), prompt["name"],(255, 255, 255), font=font)
                else:
                    draw.text((20, 20), prompt["name"],(255, 255, 255), font=font)
                img.save(filepath)
            
            logging.info(f"Image resized and saved successfully: {filepath}")
    
    except Exception as e:
        logging.error("An exception occurred while processing the image:")
        logging.error(traceback.format_exc())

def threadIA(capture_uuid, id):
    CAPTURE_PATH = Path(CAPTURE_FOLDER, str(capture_uuid))
    # choix 
    if CONFIG.analog_read:
        pose = 0
        if id == 0:
            pose = getPotPosition(ADS.P0)
        if id == 1:
            pose = getPotPosition(ADS.P2)
        if id == 2:
            pose = getPotPosition(ADS.P1)
        if id == 3:
            pose = getPotPosition(ADS.P3)
        pose = 10 - pose
        lettres = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']
        save_ia_image(CAPTURE_PATH, id, CONFIG.prompts[str(id+1)+ str(lettres[pose])])
    else:
        # mode alÃ©atoire
        lettres = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']
        save_ia_image(CAPTURE_PATH, id, CONFIG.prompts[str(id+1)+ str(random.choice(lettres))])



def processImage(capture_uuid, imgName):
    CAPTURE_PATH = Path(CAPTURE_FOLDER, str(capture_uuid))
    with Image.open(Path(CAPTURE_PATH, imgName)) as img:
        crop = (832, 0, 2144, 1728) # RÃ©solution 2592x1728 
        img = img.crop(crop)
        (width, height) = (875, 1150)
        img = img.resize((width, height))
        img.save(Path(CAPTURE_PATH,imgName))
    return img

def processImageVertical(capture_uuid, imgName):
    CAPTURE_PATH = Path(CAPTURE_FOLDER, str(capture_uuid))
    with Image.open(Path(CAPTURE_PATH, imgName)) as img:
        #crop = (164, 0, 2428, 1728) # RÃ©solution 2592x1728 
        crop = (233, 0, 3223, 2304) # RÃ©solution 3456x2304
        #crop = (270, 0, 3185, 2229) # RÃ©solution spécial la centrale
        img = img.crop(crop)
        (width, height) = (1150, 875)
        #(width, height) = (1075, 800) #centrale
        img = img.resize((width, height))
        img.save(Path(CAPTURE_PATH,imgName))
    return img
    
def processImage10x15(capture_uuid, imgName):
    CAPTURE_PATH = Path(CAPTURE_FOLDER, str(capture_uuid))
    with Image.open(Path(CAPTURE_PATH, imgName)) as img:
        (width, height) = (1728, 1152)
        img = img.resize((width, height))
        img.save(Path(CAPTURE_PATH,imgName))
    return img


def capture_to_montage(capture_uuid):

    CAPTURE_PATH = Path(CAPTURE_FOLDER, str(capture_uuid))
    images = []
    images_ia = []

    img_bytes_io = BytesIO(CONFIG.background)
    PROCESS_FILE_BACKGROUND = Image.open(img_bytes_io)
    PROCESS_FILE_MASK = Image.open(Path(PROCESS_ASSETS_FOLDER, "maskVertical.jpg"))
        
    for i in range(CONFIG.nbposes):
        # Récupère l'image normale
        img_path = Path(CAPTURE_PATH, f"{i}.jpg")
        img = Image.open(img_path)

        # Essaie de récupérer l'image traitée par IA ou crée une version en niveau de gris
        try:
            img_ia = Image.open(Path(CAPTURE_PATH, f"{i}.ia.jpg"))
        except FileNotFoundError:
            img_ia = img.convert("L")
        images_ia.append(img_ia)

        if FORMAT == "10x15PaysageNB":
            img = img.convert("L")
        images.append(img)

    mask = PROCESS_FILE_MASK.resize(images[0].size).convert("L")
    
    if CONFIG.bkpimg:
        for idx, img_ia in enumerate(images_ia):
            img.save(Path(CONFIG.bkp_path, f"{capture_uuid}_{idx+1}.jpg"), quality=95)
            img_ia.save(Path(CONFIG.bkp_path, f"{capture_uuid}_{idx+1}NB.jpg"), quality=95)

    # positionnement des images suivant leur positionnement (slot) correspondant au format
    i = 0
    for img, img_ia in zip(images, images_ia):

        # Récup des slots correspondants au numéro de pose
        tmpSlot = []
        for key, slot in CONFIG.slot_photos.items():
            if int(slot['num_pose']) == i:
                tmpSlot.append(slot)
        
        # rotation du mask une seule fois.
        if i == 0:
            mask = mask.rotate(-int(tmpSlot[0]['rotate']), expand=True)

        img = img.rotate(-int(tmpSlot[0]['rotate']), expand=True, resample=Image.BICUBIC) 
        PROCESS_FILE_BACKGROUND.paste(img, (tmpSlot[0]['posX'], tmpSlot[0]['posY']), mask)
        # si pose noir et blanc ou IA pour le format en cours.
        if len(tmpSlot) > 1:
            img_ia = img_ia.rotate(-int(tmpSlot[1]['rotate']), expand=True)
            PROCESS_FILE_BACKGROUND.paste(img_ia, (tmpSlot[1]['posX'], tmpSlot[1]['posY']), mask)

        i = i+1

    # Gestion des layers
    for key,layer in CONFIG.layers.items():
        bytesIO = BytesIO(layer["img"])
        img = Image.open(bytesIO)
        x = layer["x"] - (img.width // 2)
        y = layer["y"] - (img.height // 2)
        PROCESS_FILE_BACKGROUND.paste(img, (x, y), img)
        img.close()

    # Enregistrement
    if PROCESS_FILE_BACKGROUND.mode in ("RGBA", "P"): PROCESS_FILE_BACKGROUND = PROCESS_FILE_BACKGROUND.convert("RGB")
    PROCESS_FILE_BACKGROUND.save(Path(CAPTURE_PATH, "print.jpg"), quality=95)
    if CONFIG.bkpimg:
        PROCESS_FILE_BACKGROUND.save(Path(CONFIG.bkp_path, f"{capture_uuid}_print.jpg"), quality=95)

    #Fermeture ressources
    mask.close()
    PROCESS_FILE_BACKGROUND.close()

     
def showImg(img):
    #logging.info("showImg")
    global MAX7219, PROCESS_ASSETS_FOLDER, CURR_LED_MATRIX
    if CURR_LED_MATRIX != img:
        MAX7219.clear()
        logging.info(f"showImg: {img}")
        pixels = Image.open(Path(PROCESS_ASSETS_FOLDER, img))
        pixels = pixels.convert('1')
        MAX7219.display(pixels)    
        CURR_LED_MATRIX = img  
        pixels.close()


def getPotPosition(analogPin):
    global ADS1115
    
    avg = 0
    for i in range(4):
        avg = avg + AnalogIn(ADS1115, analogPin).value
    avg = avg / 4
    #print("avg:", avg)
    #time.sleep(1)
    if avg < 5500 :
        return 0
    elif avg >=5500 and avg <7000:
        return 1
    elif avg >=7000 and avg <10500:
        return 2
    elif avg >=10500 and avg <12500:
        return 3
    elif avg >=12500 and avg <15000:
        return 4
    elif avg >=15000 and avg <19500:
        return 5
    elif avg >=19500 and avg <21500:
        return 6
    elif avg >=21500 and avg <24000:
        return 7
    elif avg >=24000 and avg <26000:
        return 8
    elif avg >=26000 and avg <27300:
        return 9
    elif avg >=27300:
        return 10

    return 0
    
    
def refreshStrip():
    global ADS, connNeopixel, CONFIG
    
    bClassic = GPIO.input(SELECTOR_PIN)

    pose1 = getPotPosition(ADS.P0)
    pose2 = getPotPosition(ADS.P1)
    pose3 = getPotPosition(ADS.P2)
    pose4 = getPotPosition(ADS.P3)
    #appel serveur managing neopixel (sudo permission)
    try:
        connNeopixel.send([bClassic,pose1,pose2,pose3,pose4])
    except (BrokenPipeError,ConnectionRefusedError):
        connNeopixel.close()
        try:
            connNeopixel = Client(('localhost', 6000), authkey=b'neopixel')
        except ConnectionRefusedError:
            logging.error("Erreur accés serveur neopixel. Neopixel desactivé")
            CONFIG.ledstrip = False
        
    #time.sleep(1)
    #conn.send('close connection')
    #conn.close()
    #strip.show()


def CB_interrupt(channel):
    global COINS, WAITFORSTART, MODE_PAIEMENT
    #Calc signal duration
    startMillis = time.monotonic()
    endMillis = startMillis
    while GPIO.input(CB_PIN):
        endMillis = time.monotonic()
    #startMillis = startMillis * 1000
    #endMillis = endMillis * 1000
    #logging.debug("CB duration=")
    #logging.debug(endMillis - startMillis)
    if endMillis - startMillis > 0:
        WAITFORSTART = True
        COINS = 0
        MODE_PAIEMENT = "CB"
        #GPIO.remove_event_detect(COIN_PIN)
        #GPIO.remove_event_detect(CB_PIN)
        #GPIO.add_event_detect(START_PIN, GPIO.RISING, callback=start_interrupt)
        logging.info("CB")

def mdb_callback_handler(event, data):
    """
    Callback ultra-simplifié
    """
    payment_events.put({
        'event': event,
        'data': data,
        'timestamp': time.time()
    })

def process_mdb_events():
    """
    Traiter les événements MDB
    """
    global START, WAITFORSTART, MODE_PAIEMENT, COINS, cb_transaction_active
    
    while not payment_events.empty():
        try:
            event_data = payment_events.get_nowait()
            event = event_data['event']
            
            if event == 'PAYMENT_APPROVED':
                # SEULEMENT CES 3 LIGNES
                WAITFORSTART = True
                COINS = 0
                MODE_PAIEMENT = "CB"
                cb_transaction_active = True  # Transaction validée
                
                logging.info("[MDB] Paiement accepté - Prêt pour START")
                
            elif event == 'PAYMENT_FAILED':
                logging.warning("[MDB] Paiement échoué")
                cb_transaction_active = False  # Réinitialiser
            
            payment_events.task_done()
            
        except queue.Empty:
            break

def coin_interrupt(channel):
    global COINS, COINS_MULTI, START, WAITFORSTART, TM1637, NBPIECES, MODE_PAIEMENT

    COINS = COINS - COINS_MULTI
    NBPIECES = NBPIECES +1
    if COINS <= 0 and not WAITFORSTART:
        #GPIO.remove_event_detect(COIN_PIN)
        #GPIO.remove_event_detect(CB_PIN)
        WAITFORSTART = True
        COINS = 0
        MODE_PAIEMENT = "ESPECES"
        logging.info("COINS")
        logging.info(NBPIECES)
        #GPIO.add_event_detect(START_PIN, GPIO.RISING, callback=start_interrupt)
    
        
def start_interrupt(channel):
    global START, WAITFORSTART
    logging.info("start_interrupt")
    if WAITFORSTART :
        #Calc signal duration
        startMillis = time.monotonic()
        startMillis = startMillis * 1000
        endMillis = startMillis

        while GPIO.input(START_PIN) and endMillis - startMillis < 5:  # timeout after 10 seconds
            endMillis = time.monotonic()
            endMillis = endMillis * 1000
        
        logging.debug("start duration=")
        logging.debug(endMillis - startMillis)
        if endMillis - startMillis > 5:
            logging.info("startBtn")
            START = True

def checkKeypad():
    global lcd
    keys = keypad.pressed_keys
    if keys:
        print("Pressed: ", keys)
        if( '1' in keys):
            lcd.cursor_pos = (1, 2)
            lcd.write_string('Choix 1       ')
        elif( '2' in keys):

            lcd.cursor_pos = (1, 2)
            lcd.write_string('Choix 2       ')  
        elif( '3' in keys):
            lcd.cursor_pos = (1, 2)
            lcd.write_string('Choix 3       ')
        elif( '#' in keys): 
            lcd.cursor_pos = (1, 2)
            lcd.write_string("C'est parti !   ")
            START = True   
    #time.sleep(0.1)    
def boothScreen():
    global lcd
    lcd.clear()
    lcd.cursor_pos = (1, 0)
    lcd.write_string('Demarrage en cours')
  
def welcomeScreen():
    global lcd
    lcd.clear()
    lcd.cursor_pos = (0, 2)
    lcd.write_string('Bienvenue dans ce')
    lcd.cursor_pos = (1, 5)
    lcd.write_string('Photophone')
    lcd.cursor_pos = (3, 1)
    lcd.write_string('-Minute papillons-')

def formatScreen():
    global lcd
    #affiche menu choix de design sur le lcd.
    lcd.clear()
    lcd.cursor_pos = (0, 0)
    lcd.write_string(' Choix du format:')
    lcd.cursor_pos = (1, 0)
    lcd.write_string('>1:2x4  2:1x4 color')
    lcd.cursor_pos = (2, 0)
    lcd.write_string(' 3:1x4 N&B')
    lcd.cursor_pos = (3, 0)
    lcd.write_string('     # => START')
    FORMAT = "2xPaysage"

def refreshFormatScreen():
    global lcd, START, FORMAT
    keys = keypad.pressed_keys
    
    if keys:
        if( 1 in keys):
            logging.info("format 1")
            lcd.cursor_pos = (1, 0)
            lcd.write_string('>1:2x4  2:1x4 color')
            lcd.cursor_pos = (2, 0)
            lcd.write_string(' 3:1x4 N&B')
            FORMAT = "2xPaysage"
        elif( 2 in keys):
            logging.info("format 2")
            lcd.cursor_pos = (1, 0)
            lcd.write_string(' 1:2x4 >2:1x4 color')
            lcd.cursor_pos = (2, 0)
            lcd.write_string(' 3:1x4 N&B')
            FORMAT = "10x15Paysage"
        elif( 3 in keys):
            logging.info("format 3")
            lcd.cursor_pos = (1, 0)
            lcd.write_string(' 1:2x4  2:1x4 color')
            lcd.cursor_pos = (2, 0)
            lcd.write_string('>3:1x4 N&B')
            FORMAT = "10x15PaysageNB"
        elif( '#' in keys):
            lcd.clear()
            lcd.cursor_pos = (1, 0)
            lcd.write_string('    SOURIEZ!')
            START = True
def initCashlessMDB():
    global mdb_manager
    #cashless MDB
    logging.info("initCashlessMDB")
    try:
        mdb_manager = cashlessMDB.MDBManager(
            port='/dev/ttyACM0',
            debug_mode=False,
            callback=mdb_callback_handler
        )
        
        if mdb_manager.start():
            logging.info("Manager MDB démarré")
        else:
            logging.error("Échec démarrage MDB")
            mdb_manager = None
    except Exception as e:
        logging.error(f"Erreur MDB: {e}")
        mdb_manager = None       
    
def initPhotobooth():
    logging.info("initPhotobooth")
    global MAX7219, TM1637, ADS1115, connNeopixel
    global CONFIG, lcd, keypad, mdb_manager
    
    logging.info("initGPIO")
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(COIN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(START_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(SELECTOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(CB_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(AUX_PIN, GPIO.OUT)
    GPIO.output(AUX_PIN, False)
    
    GPIO.add_event_detect(COIN_PIN, GPIO.FALLING, callback=coin_interrupt)
    GPIO.add_event_detect(START_PIN, GPIO.RISING, callback=start_interrupt)
    GPIO.add_event_detect(CB_PIN, GPIO.RISING, callback=CB_interrupt)
    
    #7 segment
    logging.info("initSegment")
    TM1637 = tm1637.TM1637(clk=15, dio=18)
    TM1637.brightness(1)
    TM1637.show(str("    "), colon=True)
    
    #led matrix
    logging.info("initLedMatrix")
    CURR_LED_MATRIX = ""
    serial = spi(port=0, device=0, gpio=noop())
    MAX7219 = max7219(serial)
    
    #init config
    initConfig()
    applyConfig()


def initConfig():
    logging.info("initConfig")
    global CONFIG, START, WAITFORSTART, COINS
    global CURRENT_PATH, PROCESS_ASSETS_FOLDER
    global CAPTURE_FOLDER, PROCESS_FILE_BACKGROUND, PROCESS_FILE_MASK
    global IA, api, FORMAT

    #config json
    parser = argparse.ArgumentParser(description="Read config file path")
    parser.add_argument(
        "--config",
        type=str,
        default=Path(CURRENT_PATH, "config.json"),
        help="Path to the configuration file"
    )
    args = parser.parse_args()

    with open(args.config, "r") as f:
        JSON = json.load(f)

    #init bdd si inexistante
    bdd.initBDD(NOM_BOOTH)
    #load config depuis bdd
    CONFIG = bdd.loadConfig(JSON, NOM_BOOTH)

    FORMAT = CONFIG.format # 2xPortrait :2 strips portrait / 2xPaysage 2 strips paysage / 10x15Paysage : planche entiére 10x15cm 

    # Folder containing background
    PROCESS_ASSETS_FOLDER = Path(CURRENT_PATH, "assets/")
    if not PROCESS_ASSETS_FOLDER.exists():
        os.makedirs(PROCESS_ASSETS_FOLDER)

    showImg("cross.png")

    # Root folder for `capture_uuid` captures
    CAPTURE_FOLDER = Path(CURRENT_PATH, "captures/")
    if not CAPTURE_FOLDER.exists():
        os.makedirs(CAPTURE_FOLDER)


# Applique la configuration sur la machine       
def applyConfig():
    global CONFIG, IA, api, FORMAT, WAITFORSTART, COINS, TM1637, NBPIECES
    global CURR_LED_MATRIX, keypad, lcd, ADS1115, connNeopixel, MAX7219, MODE_PAIEMENT
    global PROCESS_FILE_BACKGROUND, PROCESS_FILE_MASK

    # Create background image if it doesn't exist
    try:
        background_bytes_io = BytesIO(CONFIG.background)
        PROCESS_FILE_BACKGROUND = Image.open(background_bytes_io)
    except Exception as e:
        logging.error(f"Erreur lors du chargement de l'image de fond : {e}")
        PROCESS_FILE_BACKGROUND = Image.new("RGB", (3700, 2500), color="white")
        CONFIG.background = PROCESS_FILE_BACKGROUND
    finally:
        PROCESS_FILE_BACKGROUND.close()
    
    # Create mask image if it doesn't exist
    try:
        PROCESS_FILE_MASK = Image.open(Path(PROCESS_ASSETS_FOLDER, "maskVertical.jpg"))
    except FileNotFoundError:
        PROCESS_FILE_MASK = Image.new("RGB", (875, 1150), color="white")
        PROCESS_FILE_MASK.save(Path(PROCESS_ASSETS_FOLDER, "maskVertical.jpg"))
    finally:
        PROCESS_FILE_MASK.close()

    #Api serveur IA
    IA = CONFIG.ia
    if IA:
        logging.info("connexion serveur IA")
        time.sleep(10)
        api = webuiapi.WebUIApi(host=SERVER_ADDR, port=SERVER_PORT, sampler = "Euler a")
        logging.info("Serveur IA OK")

    COINS = CONFIG.price
    WAITFORSTART = CONFIG.price == 0

    if WAITFORSTART:
        showImg("arrow.png")
    else:
        if CONFIG.ia:
            IA = not GPIO.input(SELECTOR_PIN)
            if IA:
                showImg("ia.png")
            else:
                showImg("smiley.png")
        else:
            showImg("smiley.png")

    showImg("cross.png")

    #keypad phone
    if CONFIG.keypad:
        logging.info("initKeypad")
        keypad = adafruit_matrixkeypad.Matrix_Keypad(rows, cols, keys)

    #lcd
    if CONFIG.lcd:
        logging.info("initLCD")
        lcd = CharLCD(i2c_expander='PCF8574', address=0x27, cols=20, rows=4)
        boothScreen()

    #init cashless MDB
    if CONFIG.cashless_mdb:
        logging.info("attente démarrage lecteur CB")
        #time.sleep(180) #Attente 3mn démarrage lecteur 4G du lecteur CB
        initCashlessMDB()

    if CONFIG.rotate_matrix:
        MAX7219.rotate = 2
    
    if CONFIG.analog_read:
        # Initialize the I2C interface
        i2c = busio.I2C(board.SCL, board.SDA)
        ADS1115 = ADS.ADS1115(i2c)
        gains = (2 / 3, 1, 2, 4, 8, 16)
        ADS1115.gain = gains[0]

    if CONFIG.ledstrip:
        try:
            connNeopixel = Client(('localhost', 6000), authkey=b'neopixel')
        except ConnectionRefusedError:
            logging.error("Erreur accés serveur neopixel. Neopixel desactivé")
            CONFIG.ledstrip = False
            
        #strip = neopixel.NeoPixel(board.D12, 169)
        #strip.auto_write = False

    if CONFIG.price == 0:
        TM1637.show("Free", colon=False)
    else:
        TM1637.show(" " + str(CONFIG.price), colon=True)
        
    

    #re init led matrix
    CURR_LED_MATRIX = ""
    serial = spi(port=0, device=0, gpio=noop())
    MAX7219 = max7219(serial)
    if WAITFORSTART:
        showImg("arrow.png")
        if CONFIG.lcd:
            formatScreen()
    else:
        showImg("smiley.png")
    
    if CONFIG.lcd:
        welcomeScreen()

def main():

    global START, WAITFORSTART, COINS, TM1637, NBPIECES, FORMAT, CURR_LED_MATRIX,CONFIG, IA, MAX7219, MODE_PAIEMENT
    global mdb_manager, cb_transaction_active, lcd

    camera = None
    try:
        currTime = time.time()
        lastRefreshConfig = currTime
        lastRefresh = currTime
        lastNbPieces = 0
        camera = init_camera()
        logging.info(f"Démarrage OK")

        # Boucle de la mort
        while True:
            currTime = time.time()

            #refresh config toutes les 30 secondes
            if currTime - lastRefreshConfig >= 30:
                lastRefreshConfig = currTime
                dateBDD = bdd.get_dateMAJ()
                idConfig = bdd.getCurrentIDConfig()
                # si modif de config détectée ou config en cours à activer
                if dateBDD > CONFIG.dateMAJ or idConfig != CONFIG.idconfig:
                    logging.info("Refresh config from BDD")
                    CONFIG = bdd.refreshConfig(CONFIG, FORMAT)
                    applyConfig()
                    

            if lastNbPieces != NBPIECES:
                #logging.info(NBPIECES)
                lastNbPieces = NBPIECES
                
            #refresh Segment
            if CONFIG.price > 0 and currTime - lastRefresh >= 0.5:
                TM1637.show(" " + str(COINS), colon=True)
                lastRefresh = currTime
                
            #refresh led matrix
            if CONFIG.ia:
                IA = not GPIO.input(SELECTOR_PIN)
                if not WAITFORSTART and IA and CURR_LED_MATRIX != "ia.png":
                    showImg("ia.png")
                elif not WAITFORSTART and not IA and CURR_LED_MATRIX!="smiley.png":
                    showImg("smiley.png")
                    
            if WAITFORSTART and CURR_LED_MATRIX != "arrow.png":
                #affiche menu choix de design sur le lcd.
                if CONFIG.lcd:
                    formatScreen()

            if WAITFORSTART and not START:
                if CONFIG.keypad:
                    checkKeypad()
                if CONFIG.ia:
                    refreshFormatScreen()

            # refresh strips
            if CONFIG.ledstrip:
                refreshStrip()

            #check fichier de démarrage.
            if os.path.exists("start.txt"):
                os.remove("start.txt")
                if CONFIG.lcd:
                    WAITFORSTART = True
                else:
                    START = True

            # Traiter les événements MDB
            if CONFIG.cashless_mdb:
                process_mdb_events()

                if not cb_transaction_active:
                    if mdb_manager and mdb_manager.initialized:
                        # Lancer la transaction
                        amount_eur = CONFIG.price / 100
                        logging.info(f"Lancement transaction CB: {amount_eur}€")
                        success = mdb_manager.start_payment(amount_eur)
                        if success:
                            cb_transaction_active = True  # Transaction lancée
                            logging.info("Transaction CB lancée")
                        else:
                            logging.error("Échec lancement transaction")
                            cb_transaction_active = False
                    else:
                        logging.error("Manager MDB non disponible")
                        initCashlessMDB()
                        cb_transaction_active = False


            if START:
                START = False

                #Récupération du design à appliquer.
                if CONFIG.bChoixDesign:
                    if not GPIO.input(SELECTOR_PIN):
                        FORMAT = "10x15Paysage"
                    else:
                        FORMAT = "2xPaysage"
                    CONFIG.format = FORMAT
                CONFIG = bdd.refreshConfig(CONFIG, FORMAT)
                logging.info("Start sequence")

                #aux lamp on
                GPIO.output(AUX_PIN, True)

                #recreate led matrix (noise from aux_pin)
                TM1637.show("BUSY", colon=False)
                CURR_LED_MATRIX = ""
                
                currDate = datetime.datetime.now()
                capture_uuid = currDate.strftime("%Y_%m_%d_%H_%M_%S")

                try:
                    capture(camera, capture_uuid)
                    startIA = time.time()
                    if IA:
                        showImg("ia.png")
                        logging.info("Process:" + str(threading.active_count()))
                        logging.info("wait for IA")
                        # time.sleep(30)
                        while threading.active_count() > 6:
                            time.sleep(1) 
                            logging.info("Process:" + str(threading.active_count()))

                    output = capture_to_montage(capture_uuid)

                    if CONFIG.print:
                        printer.print_image(capture_uuid, FORMAT)

                    #Validation paiement CB
                    if CONFIG.cashless_mdb and mdb_manager and cb_transaction_active:
                        logging.info("Validation transaction CB")
                        mdb_manager.confirm_service()
                        cb_transaction_active = False  # Réinitialiser après validation

                    #insert photo
                    bdd.insertPhoto(currDate, CONFIG.IDDESIGN, printer.getPaperCounter(), (MODE_PAIEMENT, str(Path(CAPTURE_FOLDER, str(capture_uuid)))))

                    logging.info("Done: %s seconds ---" % (time.time() - startIA))

                except Exception as e:
                    logging.error(f"Erreur pendant la session: {e}")
                    logging.error(traceback.format_exc())
                    # Annuler la transaction MDB si elle est active
                    try:
                        if CONFIG.cashless_mdb and mdb_manager and cb_transaction_active:
                            logging.info("Annulation transaction MDB suite erreur")
                            mdb_manager.cancel_service()
                    except Exception as e2:
                        logging.error(f"Erreur lors de l'annulation MDB: {e2}")
                    
                    if CONFIG.cashless_mdb:
                        cb_transaction_active = False

                finally:
                    GPIO.output(AUX_PIN, False)

                    #Re init
                    START = False
                    WAITFORSTART = CONFIG.price == 0
                    COINS = CONFIG.price
                    MODE_PAIEMENT = "FREE"

                    #refresh led matrix & lcd
                    #re init led matrix
                    CURR_LED_MATRIX = ""
                    serial = spi(port=0, device=0, gpio=noop())
                    MAX7219 = max7219(serial)
                    CURR_LED_MATRIX=""
                    if WAITFORSTART:
                        showImg("arrow.png")
                        if CONFIG.lcd:
                            formatScreen()
                    else:
                        showImg("smiley.png")
                        if CONFIG.lcd:
                            welcomeScreen()

                    #sleep de 2 secondes le temps de valider la transaction CB.
                    time.sleep(2)
                
    except KeyboardInterrupt:
        logging.info("Received keyboard interrupt, shutting down")
    except Exception as e:
        logging.error(f"Fatal error in main: {str(e)}")
        raise
            
    return 0

if __name__ == "__main__":
    try:
        print("START")
        initPhotobooth()
        logging.info("Init OK")
        main()
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        logging.error(traceback.format_exc())
    finally:
        GPIO.cleanup()
        if 'connNeopixel' in globals() and connNeopixel:
            connNeopixel.close()
        if CONFIG.cashless_mdb and mdb_manager and cb_transaction_active:
            logging.info("Annulation transaction MDB (shutdown)")
            mdb_manager.cancel_service()
        if CONFIG.cashless_mdb and mdb_manager:
            mdb_manager.stop()
        logging.info("Stop")