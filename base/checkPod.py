import os
import requests
import subprocess
from datetime import datetime

available_urls = [
    url.strip() for url in os.environ.get("GPU_CLUSTER_URLS", "").split(",") if url.strip()
]

url_found = False
for url in available_urls:
    try:
        # get Ã  la con.
        response = requests.get(url)
        response.raise_for_status() 

        # il existe, refresh
        print("Refresh Pod", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        subprocess.call(["sudo", os.environ.get("VMGPU_RESTART_SCRIPT", "./vmgpu.sh"), "restart"])
        url_found = True
        break
    except requests.exceptions.RequestException as e:
        print("Pod pas trouvé:", url, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        continue

if not url_found:
    # Aucun serveur n'est disponible, exÃ©cuter votre script shell initial
    subprocess.call([os.environ.get("RUNPOD_START_SCRIPT", "./runpod/start.sh")])
    print("Restart Pod", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
