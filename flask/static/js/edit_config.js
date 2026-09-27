document.addEventListener('DOMContentLoaded', function() {
    const dtDebutBtn = document.getElementById('dtDebutEdit')
    const dtFinBtn = document.getElementById('dtFinEdit')
    const bdefautBtn = document.getElementById('flexCheckDefaultEdit');

    if (bdefautBtn) {
      bdefautBtn.addEventListener('change', () => {
        if(bdefautBtn.checked){
            //disable the inputs
            dtDebutBtn.readOnly = true
            dtFinBtn.readOnly = true
            dtFinBtn.value = ""
            dtDebutBtn.value = ""
            //set the require to false
            dtDebutBtn.removeAttribute('required')
            dtFinBtn.removeAttribute('required')
        }else{
            dtDebutBtn.readOnly = false
            dtFinBtn.readOnly = false
        }
      });
    } else {
      console.error("Element #flexCheckDefaultEdit not found!");
    }
});