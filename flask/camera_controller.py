# camera_controller.py
import gphoto2 as gp
from datetime import datetime
import os

class CameraController:
    def __init__(self):
        self.camera = None
        self.context = gp.Context()
    
    def connect(self):
        """Établir la connexion avec l'appareil"""
        try:
            self.camera = gp.Camera()
            self.camera.init(self.context)
            return True
        except gp.GPhoto2Error:
            return False
    
    def disconnect(self):
        """Fermer la connexion"""
        if self.camera:
            self.camera.exit(self.context)
    
    def get_camera_settings(self):
        """Récupérer tous les paramètres de l'appareil"""
        try:
            if not self.camera:
                if not self.connect():
                    return {'error': 'Impossible de se connecter à la caméra'}
            
            config = self.camera.get_config(self.context)
            settings = {}
            
            params = ['aperture', 'shutterspeed', 'iso', 'whitebalance', 'exposureprogram']
            
            for param in params:
                try:
                    widget = config.get_child_by_name(param)
                    current_value = widget.get_value()
                    choices = [widget.get_choice(i) for i in range(widget.count_choices())]
                    settings[param] = {
                        'current': current_value,
                        'choices': choices
                    }
                except:
                    settings[param] = {'current': '', 'choices': []}
            self.disconnect()
            return settings
            
        except Exception as e:
            self.disconnect()
            return {'error': str(e)}
    
    def set_camera_setting(self, setting_name, setting_value):
        """Modifier un paramètre de l'appareil"""
        try:
            if not self.camera:
                if not self.connect():
                    return {'error': 'Impossible de se connecter à la caméra'}
            
            config = self.camera.get_config(self.context)
            widget = config.get_child_by_name(setting_name)
            widget.set_value(setting_value)
            self.camera.set_config(config, self.context)
            
            self.disconnect()

            return {'success': True}
            
        except Exception as e:
            self.disconnect()
            return {'error': str(e)}
    
    def capture_test(self, upload_folder):
        """Capturer une image de test"""
        try:
            if not self.camera:
                if not self.connect():
                    return {'error': 'Impossible de se connecter à la caméra'}
            
            # Capture l'image
            file_path = self.camera.capture(gp.GP_CAPTURE_IMAGE, self.context)
            print(f"Image capturée: {file_path.folder}/{file_path.name}")
            
            # Créer un objet CameraFile pour récupérer l'image
            camera_file = gp.CameraFile()
            
            # Télécharger l'image depuis l'appareil
            self.camera.file_get(
                file_path.folder, 
                file_path.name,
                gp.GP_FILE_TYPE_NORMAL,
                camera_file,
                self.context
            )
            
            # Générer un nom de fichier unique
            test_filename = f"test_capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            test_path = os.path.join(upload_folder, test_filename)
            
            # Sauvegarder l'image
            camera_file.save(test_path)
            print(f"Image sauvegardée: {test_path}")

            self.disconnect()
            
            return {
                'success': True, 
                'filename': test_filename
            }
            
        except Exception as e:
            self.disconnect()
            print(f"Erreur lors de la capture: {str(e)}")
            return {'error': str(e)}

# Instance globale
camera_controller = CameraController()