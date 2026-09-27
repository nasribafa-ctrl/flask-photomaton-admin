document.addEventListener('DOMContentLoaded', () => {
    btn_Print = document.getElementById('imprimer')
    document.querySelectorAll('.img-photo').forEach(image => {
        image.addEventListener('click', () => {
            image.classList.toggle('open');
            document.body.style.overflow = image.classList.contains('open') ? 'hidden' : '';
        });
    });

    const forms = document.querySelectorAll('.needs-validation');

    Array.from(forms).forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    const userIcon = document.getElementById('userIcon');
    const loginOverlay = document.getElementById('loginOverlay');
    const closeLogin = document.getElementById('closeLogin');

    userIcon.addEventListener('click', () => {
        loginOverlay.style.display = 'flex';
    });

    closeLogin.addEventListener('click', () => {
        loginOverlay.style.display = 'none';
    });

    // Optional: close if clicking outside form
    loginOverlay.addEventListener('click', (e) => {
        if (e.target === loginOverlay) {
            loginOverlay.style.display = 'none';
        }
    });

    const checkboxPrinterStatus = document.querySelector('.checkboxImprimante')
    checkboxPrinterStatus.addEventListener('change', () =>{
        if (checkboxPrinterStatus && !checkboxPrinterStatus.checked) {
          fetch('/printerStatus',{
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                "newPrintStatus": "0"
            })
        })
        } else if (checkboxPrinterStatus) {
          fetch('/printerStatus',{
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                "newPrintStatus": "1"
            })
        })
        }
    })

    const formatDefautIndex = document.getElementById('formatDefautIndex')
    formatDefautIndex.addEventListener('change', () => {
        fetch('/changeIndexFormat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                newDefautIndex: formatDefautIndex.value
            })
        })
    })

    const secretWord = 'gales';
    let typedChars = [];
    const maxLength = secretWord.length;
    document.addEventListener('keydown', function(event) {
        // Only listen to letter keys (ignore Shift, Ctrl, etc.)
        if (event.key.length === 1) {
            typedChars.push(event.key.toLowerCase());
            // Keep only the last N characters (length of secret word)
            if (typedChars.length > maxLength) {
                typedChars.shift();
            }
            // Check if the last N characters match the secret word
            if (typedChars.join('') === secretWord) {
                document.getElementById('output').textContent = 'Easter egg activated!';
                doSomething();
                typedChars = []; // Reset
            }
        }
    });
    function doSomething() {
        window.location.href = 'https://www.minutepapillons.org/'
    }
});

function printImage(photoId, filename) {
    fetch(`/print/${photoId}/${filename}`, {
        method: 'POST'
    })
    .then(response => response.text())
    .then(data => {
        alert(data);
    })
    .catch(error => {
        console.error('Error:', error);
    });
}
function delete_alert(designs_id) {

  alert("Vous venez de supprimer cette config");

  fetch(`/delete_design/${designs_id}`, {
    method: 'POST'
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      location.reload(); // or redirect
    }
  })
  .catch(error => {
    console.error('Error:', error);
  });
}
