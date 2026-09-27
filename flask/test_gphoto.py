try:
    import gphoto2 as gp
    print("✓ gphoto2 importé avec succès")
    
    # Test basique
    context = gp.Context()
    camera = gp.Camera()
    camera.init(context)
    print("✓ Appareil photo détecté")
    camera.exit(context)
    
except ImportError as e:
    print(f"✗ Erreur d'import: {e}")
except Exception as e:
    print(f"✗ Autre erreur: {e}")