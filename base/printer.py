import cups
from pathlib import Path
from PIL import Image
from tempfile import mktemp
import sys
import os
import logging
import re

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'base'))
sys.path.append(base_path)

#récupération du chemin du dossier qui contiens les dossiers qui contiens les photos
BASE_CAPTURE_FOLDER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'base', 'captures')
)

CAPTURE_FOLDER = BASE_CAPTURE_FOLDER

def print_image(capture_uuid, FORMAT):
    # impression
    #logging.info("Print Image - start")
    print("Print Image - start")
    # Set up CUPS
    conn = cups.Connection()
    printers = conn.getPrinters()
    printer_name = list(printers.keys())[0]
    cups.setUser("pi")

    # Save data to a temporary file
    CAPTURE_PATH = Path(CAPTURE_FOLDER, str(capture_uuid))
    imgPrint = Image.open(os.path.join(CAPTURE_PATH, "print.jpg"))

    output = mktemp(prefix="jpg")
    imgPrint.save(output, format="jpeg")


    # Options d'impression incluant le nombre de copies
    if FORMAT == "10x15Paysage":
        print_options = {
            'PageSize': 'w288h432'  # 10x15
        }
    else:
        print_options = {
            'PageSize': 'w288h432-div2'  # 2 x 2x3
        }
    
    print_id = conn.printFile(printer_name, output, "nofilterbooth", print_options)
    imgPrint.close()
    
    logging.info("Print Image - print id: " + str(print_id))
    # Wait until the job finishes
    # from time import sleep
    # while conn.getJobs().get(print_id, None):
    # sleep(1)

def getPaperCounter():
    counter = 0
    msg = ""
    conn = cups.Connection()
    printers = conn.getPrinters()
    printer_name = list(printers.keys())[0]
    cups.setUser("pi")
    attr = conn.getPrinterAttributes(printer_name)
    for key, value in attr.items():
        if key=="marker-message":
            msg = value
    counter = msg
    match = re.search(r"\d+", msg)  # Cherche le 1er nombre dans la chaîne
    if match:
        counter = int(match.group()) 

    return counter