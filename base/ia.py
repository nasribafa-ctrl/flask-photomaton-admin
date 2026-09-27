import webuiapi
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import logging
import time
import os
import socket
from urllib.parse import urlparse
import traceback
import webuiapi


SERVER_ADDR = os.environ.get("SD_API_HOST", "127.0.0.1")
SERVER_PORT = int(os.environ.get("SD_API_PORT", "7860"))

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))
LOG_FILENAME = Path(CURRENT_PATH, "log.txt")
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    filename=LOG_FILENAME,
    level=logging.DEBUG,
    datefmt="%Y-%m-%d %H:%M:%S",
)

def save_ia_image(capture_path, index, prompt, filename, FORMAT=None):

  

   
    

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
                logging.info("Lancement de la génetation d'image (txt2img)")
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
                logging.info("Génération terminer")
                
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

            filepath = Path(capture_path) / filename
          

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


    return filename



    
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


api = webuiapi.WebUIApi(
    host = SERVER_ADDR,
    port = SERVER_PORT
)




if __name__ == "__main__":

    prompt_test = {
        "name" :"Test IA",
        "positive":"realistic, ((masterpiece)), ((best quality)), (detailed), cinematic, dynamic lighting, soft shadow, detailed background, professional photography, depth of field, intricate subsurface scattering, realistic hair,portrait,magic, smoke, bubbles, acidzlime <lora:acidzlime:1>",
        "negative": "(low quality:1.3), (worst quality:1.3)"

    }


    save_ia_image(

        capture_path= r"C:\Users\kenza\Documents\programme_stage_nasri\Photomaton\base\ia_images",
        index =1,
        prompt = prompt_test


    )
