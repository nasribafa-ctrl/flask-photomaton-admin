/**
 * Enregistre la pose sélectionnée via AJAX pour éviter le rechargement de la page
 * @param {HTMLSelectElement} selectElement - L'élément select qui a changé
 * @param {number} promptId - L'ID du prompt concerné
 */
function enregistrerPoseRapide(selectElement, promptId) {
    const poseId = selectElement.value;
    
    // Création des données à envoyer
    const formData = new FormData();
    formData.append('pose_id', poseId);

    // Appel à la route Flask /prompt/<id>/pose définie dans app.py
    fetch(`/prompt/${promptId}/pose`, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (response.ok) {
            // Petit feedback visuel : bordure verte temporaire sur le select
            selectElement.style.borderColor = "#198754";
            selectElement.style.boxShadow = "0 0 0 0.25rem rgba(25, 135, 84, 0.25)";
            
            setTimeout(() => {
                selectElement.style.borderColor = "";
                selectElement.style.boxShadow = "";
            }, 1000);
        } else {
            console.error("Erreur serveur lors de l'enregistrement");
            alert("Erreur lors de l'enregistrement de la pose.");
        }
    })
    .catch(error => {
        console.error('Erreur réseau:', error);
    });
}