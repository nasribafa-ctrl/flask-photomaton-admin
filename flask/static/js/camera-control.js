// static/js/camera-control.js
class CameraControl {
    constructor() {
        this.initialized = false;
    }

    init() {
        if (this.initialized) return;
    
        console.log('Initialisation CameraControl...');
        
        this.setupEventListeners();
        this.setupStartButton();
        this.loadCameraSettings();
        this.initialized = true;
    }

    setupEventListeners() {
        // Actualiser les paramètres
        document.getElementById('refreshSettings')?.addEventListener('click', () => {
            this.loadCameraSettings();
        });
        
        // Capture test
        document.getElementById('captureTest')?.addEventListener('click', () => {
            this.captureTest();
        });
        
        // Changer les paramètres
        document.querySelectorAll('.camera-setting').forEach(select => {
            select.addEventListener('change', (e) => {
                this.updateSetting(e.target.dataset.setting, e.target.value);
            });
        });
    }

    loadCameraSettings() {
        this.showLoadingState(true);
        
        fetch('/get_camera_settings')
            .then(response => response.json())
            .then(settings => {
                if (settings.error) {
                    this.showAlert('Erreur caméra: ' + settings.error, 'danger');
                    return;
                }
                
                this.updateSettingsUI(settings);
                this.showAlert('Paramètres actualisés', 'success');
            })
            .catch(error => {
                this.showAlert('Erreur de connexion', 'danger');
                console.error('Error:', error);
            })
            .finally(() => {
                this.showLoadingState(false);
            });
    }

    updateSettingsUI(settings) {
        Object.keys(settings).forEach(settingName => {
            const select = document.querySelector(`[data-setting="${settingName}"]`);
            if (select) {
                const setting = settings[settingName];
                
                // Vider le select
                select.innerHTML = '';
                
                // Vérifier si le paramètre est supporté
                if (setting.choices && setting.choices.length > 0) {
                    // Paramètre supporté - afficher les choix
                    setting.choices.forEach(choice => {
                        const option = document.createElement('option');
                        option.value = choice;
                        option.textContent = this.formatSettingDisplay(settingName, choice);
                        if (choice === setting.current) {
                            option.selected = true;
                        }
                        select.appendChild(option);
                    });
                } else {
                    // Paramètre non supporté
                    const option = document.createElement('option');
                    option.value = "";
                    option.textContent = "Non supporté";
                    option.disabled = true;
                    option.selected = true;
                    select.appendChild(option);
                    select.disabled = true;
                }
            }
        });
    }

    updateSetting(settingName, settingValue) {
        fetch('/set_camera_setting', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: settingName,
                value: settingValue
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showAlert('Paramètre mis à jour avec succès', 'success');
            } else {
                this.showAlert('Erreur: ' + data.error, 'danger');
                this.loadCameraSettings(); // Recharger les valeurs actuelles
            }
        })
        .catch(error => {
            this.showAlert('Erreur de connexion', 'danger');
        });
    }

    captureTest() {
        const button = document.getElementById('captureTest');
        const originalText = button.innerHTML;
        
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Capture...';
        
        const resultDiv = document.getElementById('captureResult');
        resultDiv.innerHTML = `
            <div class="text-center">
                <div class="spinner-border text-primary mb-2" role="status">
                    <span class="visually-hidden">Chargement...</span>
                </div>
                <p class="text-muted mb-0">Capture en cours...</p>
            </div>
        `;
        
        fetch('/capture_test')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const timestamp = new Date().toLocaleTimeString();
                    resultDiv.innerHTML = `
                        <div class="capture-preview">
                            <img src="${data.url}" 
                                class="img-fluid rounded shadow-sm mb-3" 
                                style="max-height: 200px; width: auto;" 
                                alt="Capture test">
                            <div class="d-grid gap-2">
                                <a href="${data.url}" 
                                target="_blank" 
                                class="btn btn-sm btn-outline-primary">
                                    <i class="fas fa-expand me-1"></i>Plein écran
                                </a>
                                <small class="text-muted">
                                    <i class="fas fa-clock me-1"></i>${timestamp}
                                </small>
                            </div>
                        </div>
                    `;
                } else {
                    resultDiv.innerHTML = `
                        <div class="alert alert-danger text-center py-2">
                            <i class="fas fa-exclamation-triangle me-1"></i>
                            <small>Erreur: ${data.error}</small>
                        </div>
                    `;
                }
            })
            .catch(error => {
                resultDiv.innerHTML = `
                    <div class="alert alert-danger text-center py-2">
                        <i class="fas fa-exclamation-triangle me-1"></i>
                        <small>Erreur de connexion</small>
                    </div>
                `;
            })
            .finally(() => {
                button.disabled = false;
                button.innerHTML = '<i class="fas fa-camera me-1"></i>Capture test';
            });
    }

    formatSettingDisplay(name, value) {
        if (name === 'shutterspeed' && value.startsWith('1/')) {
            return value;
        } else if (name === 'aperture') {
            return `f/${value}`;
        } else if (name === 'iso') {
            return `ISO ${value}`;
        } else if (name === 'exposureprogram') {
            const programs = {
                '0': 'Auto',
                '1': 'Manuel',
                '2': 'Priorité ouverture',
                '3': 'Priorité vitesse',
                '4': 'Programme'
            };
            return programs[value] || value;
        }
        return value;
    }

    showAlert(message, type) {
        // Supprimer les alertes existantes
        document.querySelectorAll('.temp-alert').forEach(alert => alert.remove());
        
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show temp-alert`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const cardBody = document.querySelector('#cameraControlCard .card-body');
        if (cardBody) {
            cardBody.insertBefore(alertDiv, cardBody.firstChild);
            
            setTimeout(() => {
                if (alertDiv.parentElement) {
                    alertDiv.remove();
                }
            }, 3000);
        }
    }

    showLoadingState(show) {
        const button = document.getElementById('refreshSettings');
        if (button) {
            if (show) {
                button.disabled = true;
                button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Chargement...';
            } else {
                button.disabled = false;
                button.innerHTML = '<i class="fas fa-sync-alt me-1"></i>Actualiser';
            }
        }
    }

    setupStartButton() {
        const startBtn = document.getElementById('startButton');
        const statusDiv = document.getElementById('startStatus');
        
        if (startBtn) {
            startBtn.addEventListener('click', () => {
                this.startPhotomaton(startBtn, statusDiv);
            });
        }
    }

    startPhotomaton(button, statusDiv) {
        const originalText = button.innerHTML;
        
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Démarrage...';
        
        if (statusDiv) {
            statusDiv.innerHTML = '<span class="text-warning">Création du fichier start.txt...</span>';
        }
        
        fetch('/start_photomaton', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (statusDiv) {
                    statusDiv.innerHTML = '<span class="text-success"><i class="fas fa-check me-1"></i>Démarré!</span>';
                }
                this.showAlert('Photomaton démarré avec succès', 'success');
            } else {
                if (statusDiv) {
                    statusDiv.innerHTML = `<span class="text-danger"><i class="fas fa-times me-1"></i>Erreur: ${data.error}</span>`;
                }
                this.showAlert('Erreur: ' + data.error, 'danger');
            }
        })
        .catch(error => {
            if (statusDiv) {
                statusDiv.innerHTML = '<span class="text-danger"><i class="fas fa-times me-1"></i>Erreur de connexion</span>';
            }
            this.showAlert('Erreur de connexion au serveur', 'danger');
        })
        .finally(() => {
            button.disabled = false;
            button.innerHTML = originalText;
            
            // Réinitialiser le statut après 5 secondes
            setTimeout(() => {
                if (statusDiv) {
                    statusDiv.innerHTML = '';
                }
            }, 5000);
        });
    }
}

// Initialisation globale
const cameraControl = new CameraControl();