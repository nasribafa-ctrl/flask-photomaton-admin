let selectedBackgroundImage = null
document.addEventListener('DOMContentLoaded', ()=>{
  const selectPhotoOption = document.querySelector(".selectPhotoButton")
  const photoDisplay = document.querySelector(".selection_photo_display")

  selectPhotoOption.addEventListener('click', ()=>{
      photoDisplay.classList.remove('close');
      photoDisplay.classList.add('open');
  })

  //canvas
  document.getElementById('serverBtn').addEventListener('click', (e) => {
      e.preventDefault(); // prevent form submit

      fetch('/list_images')
          .then(res => res.json())
          .then(images => {
              const container = document.querySelector('.Images');
              container.innerHTML = ''; 
              if (container.style.display !== 'block') {
                  container.style.display = 'block';
              }
          
              let selectedEl = null; // track the current selected element
          
              images
              .filter(img => img.toLowerCase().endsWith('.jpg') || img.toLowerCase().endsWith('.jpeg'))
              .forEach(img => {
                  const el = document.createElement('img');
                  el.src = '/base/assets/' + img;
                  el.style.width = '100px';
                  el.style.margin = '5px';
                  el.style.cursor = 'pointer';
                  el.style.border = '2px solid transparent';
              
                  el.onclick = () => {
                      // remove highlight
                      if (selectedEl) {
                          selectedEl.style.border = '2px solid transparent';
                      }
                  
                      // highlight current
                      el.style.border = '2px solid blue';
                      selectedEl = el;
                  
                      // save URL
                      selectedImageUrl = el.src;
                      selectedBackgroundImage = img
                      document.getElementById("selectedImage").value = img;
                  
                      // === SET CANVAS BACKGROUND ===
                      fabric.Image.fromURL(selectedImageUrl, function (bg) {
                          //Always use the logical canvas size (not the zoomed one)
                          const cw = 3700; // base logical width
                          const ch = 2500; // base logical height
                          const iw = bg.width;
                          const ih = bg.height;
                                          
                          //Scale proportionally to cover the canvas (no distortion)
                          const scale = Math.max(cw / iw, ch / ih);
                                          
                          bg.set({
                            scaleX: scale,
                            scaleY: scale,
                            originX: 'center',
                            originY: 'center',
                            left: cw / 2,
                            top: ch / 2,
                            isUserLayer: true,
                            selectable: false,
                            evented: false,
                          });
                        
                          //Use Fabric's background setter properly
                          canvas.setBackgroundImage(bg, canvas.renderAll.bind(canvas), {
                            originX: 'center',
                            originY: 'center',
                            left: cw / 2,
                            top: ch / 2,
                            scaleX: bg.scaleX,
                            scaleY: bg.scaleY,
                          });
                        
                          currentBackground = bg;
                        
                          //Ensure it re-renders correctly after resizeCanvas runs
                          setTimeout(() => canvas.requestRenderAll(), 100);
                      });
                  };
                  container.appendChild(el);
              });
          });
      
      photoDisplay.classList.remove('open');
      photoDisplay.classList.add('close');
  });

  const readerUpload = new FileReader();
  const upload = document.getElementById('uploadBtn');
  let currentBackground = null; // Keep track of current background image

  // When file is selected
  upload.addEventListener('change', () => {
    const file = upload.files[0];
    if (file) readerUpload.readAsDataURL(file);
    photoDisplay.classList.remove('open');
    photoDisplay.classList.add('close');
  });

  readerUpload.addEventListener('load', () => {
    fabric.Image.fromURL(readerUpload.result, (bg) => {
      // Remove any previous background
      if (currentBackground) {
        canvas.setBackgroundImage(null);
        currentBackground = null;
      }
    
      //Always use the logical canvas size (not the zoomed one)
      const cw = 3700; // base logical width
      const ch = 2500; // base logical height
      const iw = bg.width;
      const ih = bg.height;
    
      //Scale proportionally to cover the canvas (no distortion)
      const scale = Math.max(cw / iw, ch / ih);
    
      bg.set({
        scaleX: scale,
        scaleY: scale,
        originX: 'center',
        originY: 'center',
        left: cw / 2,
        top: ch / 2,
        isUserLayer: true,
        selectable: false,
        evented: false,
      });
    
      //Use Fabric's background setter properly
      canvas.setBackgroundImage(bg, canvas.renderAll.bind(canvas), {
        originX: 'center',
        originY: 'center',
        left: cw / 2,
        top: ch / 2,
        scaleX: bg.scaleX,
        scaleY: bg.scaleY,
      });
    
      currentBackground = bg;
    
      //Ensure it re-renders correctly after resizeCanvas runs
      setTimeout(() => canvas.requestRenderAll(), 100);
    });

  });

  // Reset upload input so you can re-upload the same file again
  upload.addEventListener('click', (e) => {
    e.target.value = ''; // allow reselecting same file
  });


  // --- Fabric.js setup ---
  const canvas = new fabric.Canvas("canvas", {
      //backgroundColor: "white",
      selection: false,
  });

  // Canvas "logical" size (before CSS scaling)
  canvas.setWidth(3700);
  canvas.setHeight(2500);

  const formatSelect = document.getElementById("format");

  // Build initial format
  buildTemplate(formatSelect.value);
  
  // store previous value
  formatSelect.dataset.previousValue = formatSelect.value;

  formatSelect.addEventListener("focus", (e) => {
    formatSelect.dataset.previousValue = e.target.value;
  });

  formatSelect.addEventListener("change", (e) => {

    const hasContent = canvas.getObjects().some(
      o => !o.isSlot && !o.isSlotImage
    );

    // Ask FIRST
    if (hasContent) {
      const confirmChange = confirm(
        'En changeant le format, si vous aviez déjà un background ou un layer, cette action va tout supprimer. Souhaitez-vous continuer ?'
      );

      if (!confirmChange) {
        e.preventDefault();
        e.stopPropagation();
        e.target.value = formatSelect.dataset.previousValue;
        return;
      }
    }

    // ✅ User confirmed → NOW destroy stuff
    buildTemplate(e.target.value);

    canvas.getObjects().forEach(o => {
      if (!o.isSlot && !o.isSlotImage) {
        canvas.remove(o);
      }
    });

    // reset inputs safely
    document.getElementById("pos_X").value = '';
    document.getElementById("pos_Y").value = '';
    document.getElementById("size-1").value = '';

    canvas.requestRenderAll();
  });

  // Optional: keep responsive scaling on window resize
  function resizeCanvas() {
      const wrapper = document.querySelector(".canvas-wrapper");
      const scale = wrapper.clientWidth / 3700; // base width
      canvas.setZoom(scale);
      canvas.setDimensions({ width: wrapper.clientWidth, height: 2500 * scale });
      canvas.renderAll();
  }

  function buildTemplate(formatName) {
    currentTemplate = formatName;
    canvas.clear();

    fetch(`/api/template-slots/${formatName}`)
      .then(res => res.json())
      .then(slots => {

        slots.forEach(slot => {

          // Slot rectangle
          const rect = new fabric.Rect({
            left: slot.left + 5,
            top: slot.top + 2,
            width: slot.width,
            height: slot.height,
            fill: "white",
            stroke: "gray",
            strokeWidth: 5,
            selectable: false,
            isSlotElement: true,
          });
          canvas.add(rect);

          // Slot image (from DB)
          fabric.Image.fromURL(
            `data:image/png;base64,${slot.image}`,
            img => {

              img.rotate(slot.rotate);

              // IMPORTANT: scale AFTER rotation/origin
              const bounds = img.getBoundingRect();
                const scaleX = slot.width / bounds.width;
                const scaleY = slot.height / bounds.height;
                const scale = Math.max(scaleX, scaleY);
                img.scale(scale);

              // CENTER the image inside the slot
              img.set({
                left: slot.left + slot.width / 2 + 5,
                top: slot.top + slot.height / 2 + 2,
                originX: "center",
                originY: "center",
                selectable: false,
                evented: false,
                isSlotImage: true,
                isSlotElement: true,
              });

              // Clip exactly to slot
              img.clipPath = new fabric.Rect({
                left: slot.left + 5,
                top: slot.top + 2,
                width: slot.width,
                height: slot.height,
                selectable: false,
                evented: false,
                absolutePositioned: true,
              });

              canvas.add(img);
              setTimeout(normalizeZOrder, 100);
              canvas.renderAll();
            }, { crossOrigin: 'anonymous' }
          );
        });
      });
  }
  
  // === Common elements ===
  const pos_X = document.getElementById('pos_X');
  const pos_Y = document.getElementById('pos_Y');

  // 🟩 New: size inputs
  const size_1 = document.getElementById("size_1");

  const inputFile = document.getElementById('add_image');
  const controller = document.getElementById('controller');

  let currentFile = null;
  let firstImageData = null;
  let originalSize1 = { width: 0, height: 0 };
  let imageControls = []; // store link between image and its controls

  inputFile.addEventListener('change', () => {
    const files = inputFile.files;

    for (const file of files) {
      const readerAdd = new FileReader();

      readerAdd.onload = () => {
        const imgData = readerAdd.result;

        fabric.Image.fromURL(imgData, (img) => {
          currentFile = img;
          img.fileName = file.name;

          // Save original size
          originalSize1.width = img.width;
          originalSize1.height = img.height;

          img.set({
            originX: 'center',
            originY: 'center',
            objectId: uid(),
            left: canvas.getWidth(),
            top: canvas.getHeight(),
            selectable: true,
            evented: true,
            isUserLayer: true,
            lockRotation: true,
            scaleX: 1,
            scaleY: 1,
            angle: 0
          });
          
          img.setCoords();
          canvas.add(img);
          canvas.requestRenderAll();

          // Attach to existing or new controls
          linkImageControls(img);
        });
      };

      readerAdd.readAsDataURL(file);
    }

    // allow reselection of same image
    inputFile.value = "";
  });

  function linkImageControls(img) {
    let controlGroup;

    //If it's the first image, use the default inputs already in the DOM
    if (imageControls.length === 0) {
      controlGroup = {
        wrapper: controller,
        x: document.getElementById('pos_X'),
        y: document.getElementById('pos_Y'),
        size: document.getElementById('size_1'),
        removeBtn: document.getElementById('remove_first'),
        rotateBtn: document.getElementById('remove_rotate_first'),
        isDynamic: false,
      };
    
      // show delete button once an image exists
      controlGroup.removeBtn.classList.remove('d-none');
      controlGroup.rotateBtn.classList.remove('d-none');
    
      controlGroup.removeBtn.onclick = () => {
        canvas.remove(img);
      
        // reset inputs
        controlGroup.x.value = '';
        controlGroup.y.value = '';
        controlGroup.size.value = '';
      
        controlGroup.removeBtn.classList.add('d-none');
        controlGroup.rotateBtn.classList.add('d-none')
      
        imageControls = imageControls.filter(c => c !== controlGroup);
        canvas.requestRenderAll();

        document.querySelector('.textControls').classList.add('d-none')
      };

      controlGroup.rotateBtn?.addEventListener('click', () => {
        canvas.setActiveObject(img);
        img.rotate((img.angle || 0) + 90);
        img.setCoords();
        canvas.requestRenderAll();
      });
    } else {
      //For other images, create new inputs dynamically
      const wrapper = document.createElement('div');
      wrapper.classList.add('d-flex', 'flex-wrap', 'gap-2', 'align-items-center', 'justify-content-center');

      wrapper.innerHTML = `
        <label>X:</label>
        <input type="number" class="form-control w-auto pos_X" size="10">
        <label>Y:</label>
        <input type="number" class="form-control w-auto pos_Y" size="10">
        <label>Size:</label>
        <input type="number" class="form-control w-auto size" size="10">%
        <button class="btn btn-danger btn-sm remove-img">✖</button>
        <button type="button" class="btn btn-secondary rotate-img"><i class="fa-solid fa-rotate-right"></i></button>
      `;

      controller.parentNode.insertBefore(wrapper, controller.nextSibling);

      controlGroup = {
        wrapper,
        x: wrapper.querySelector('.pos_X'),
        y: wrapper.querySelector('.pos_Y'),
        size: wrapper.querySelector('.size'),
        removeBtn: wrapper.querySelector('.remove-img'),
        rotateBtn: wrapper.querySelector('.rotate-img'),
        isDynamic: true
      };

      //Delete this image + its controls
      controlGroup.removeBtn.addEventListener('click', () => {
        canvas.remove(img);
        wrapper.remove();
        imageControls = imageControls.filter(c => c !== controlGroup);
        canvas.requestRenderAll();
      });

      controlGroup.rotateBtn.onclick = (e) => {
        e.preventDefault();
        
        // store visual center BEFORE rotation
        const center = img.getCenterPoint();
        
        // rotate
        img.rotate((img.angle || 0) + 90);
        
        // restore visual center
        img.setPositionByOrigin(center, 'center', 'center');
        
        img.setCoords();
        canvas.requestRenderAll();
        
        // update inputs (logical position)
        controlGroup.x.value = Math.round(img.left);
        controlGroup.y.value = Math.round(img.top);
      };
    }

    //pour les premiers inputs static statics
    controller.dataset.objectId = img.objectId;

    //on assigne l'id au controller
    controlGroup.objectId = img.objectId;
    controlGroup.wrapper.dataset.objectId = img.objectId;

    // set initial values
    controlGroup.x.value = Math.round(img.left);
    controlGroup.y.value = Math.round(img.top);
    controlGroup.size.value = 100;

    // store link
    imageControls.push(controlGroup);

    // === Input to Image ===
    controlGroup.x.addEventListener('input', () => {
      img.set({ left: parseInt(controlGroup.x.value) || 0 });
      canvas.requestRenderAll();
    });

    controlGroup.y.addEventListener('input', () => {
      img.set({ top: parseInt(controlGroup.y.value) || 0 });
      canvas.requestRenderAll();
    });

    controlGroup.size.addEventListener('input', () => {
      const scale = (parseFloat(controlGroup.size.value) || 100) / 100;
      img.scaleX = scale;
      img.scaleY = scale;
      canvas.requestRenderAll();
    });

    controlGroup.wrapper.addEventListener('click', () => {
      canvas.setActiveObject(img);
      canvas.requestRenderAll();
    });

    // === Image to Input ===
    img.on('modified', () => {
      controlGroup.x.value = Math.round(img.left);
      controlGroup.y.value = Math.round(img.top);
      controlGroup.size.value = Math.round(img.scaleX * 100);
    });

    img.on('moving', () => {
      controlGroup.x.value = Math.round(img.left);
      controlGroup.y.value = Math.round(img.top);
    });
  }

  document.getElementById('remove_rotate_first').addEventListener('click', (e)=>{
    e.preventDefault()
  })

  document.getElementById('delete_image').addEventListener('mouseover', ()=>{
      document.getElementById('signalText').style.display = 'flex'
      document.getElementById('signalParagraphe').style.color = 'red'
  })

  document.getElementById('delete_image').addEventListener('mouseout', ()=>{
      document.getElementById('signalText').style.display = 'none'
  })

  document.getElementById('delete_image').addEventListener('click', (e) => {
    e.preventDefault();
    canvas.getObjects().forEach((o)=>{
        if(!o.isSlot && !o.isSlotImage){
            canvas.remove(o)
        }
    })

    // Remove all dynamically created control groups (but not the default)
    imageControls.forEach(ctrl => {
      if (ctrl.isDynamic && ctrl.wrapper) {
        ctrl.wrapper.remove();
      }
    });

    // Reset the array but keep the first one (the default input set)
    imageControls = imageControls.filter(c => !c.isDynamic);
    //Reset references and input values for the first image
    currentFile = null;
    pos_X.value = '';
    pos_Y.value = '';
    size_1.value = '';
        
    //Reset file inputs and background
    inputFile.value = ''; // allow reuploading same image
    upload.value = '';    // allow reuploading same background
    imageControls = []
    canvas.setBackgroundImage(null, canvas.renderAll.bind(canvas));

    document.querySelector('.textControls').classList.add('d-none')
    
    canvas.requestRenderAll();
  });

  canvas.on("mouse:over", function(e) {
    if (e.target && e.target.type === "image") {
      canvas.hoverCursor = "grab";
    }
  });
  
  canvas.on("mouse:out", function(e) {
    canvas.hoverCursor = "default";
  });

  canvas.on('selection:created', syncControls);
  canvas.on('selection:updated', syncControls);
  canvas.on('selection:cleared', clearControlHighlight);

  function syncControls(e) {
    const obj = e.selected?.[0];
    if (!obj || !obj.objectId) return;

    imageControls.forEach(c => {
      c.wrapper.classList.toggle(
        'control-active',
        c.objectId === obj.objectId
      );
    });

    // optional: scroll to controls
    //const active = imageControls.find(c => c.objectId === obj.objectId);
    //active?.wrapper.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function clearControlHighlight() {
    imageControls.forEach(c =>
      c.wrapper.classList.remove('control-active')
    );
  }

  const canvasTextChecker = canvas.getObjects().filter(obj => obj.isLayerText === true)
  const addTextToCanvas = document.getElementById('addTextToCanvas')
  addTextToCanvas.addEventListener('click', (e) => {
    e.preventDefault()

    const champText = new fabric.IText('Entrer un texte', {
      left: 700,
      top: 250,
      fontSize: 200,
      objectId: uid(),
      fill: 'black',
      originX: 'center',
      originY: 'center',
      selectable: true,
      hasControls: true,
      lockScalingFlip: true,
      isLayerText: true,
      lockRotation: true,
      isUserLayer: true,
    })

    canvas.add(champText)
    canvas.setActiveObject(champText)
    canvas.requestRenderAll()

    linkImageControls(champText)

    if(canvasTextChecker){
      document.querySelector('.textControls').classList.remove('d-none')
    }
  })

  const colorPicker = document.getElementById('textColorPicker');
  const alphaPicker = document.getElementById('textAlphaPicker');
  
  function hexToRgba(hex, alpha) {
    const r = parseInt(hex.substring(1, 3), 16);
    const g = parseInt(hex.substring(3, 5), 16);
    const b = parseInt(hex.substring(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }
  
  function applyTextColor() {
    const rgba = hexToRgba(colorPicker.value, alphaPicker.value);
  
    canvas.getObjects()
      .filter(obj => obj.isLayerText === true)
      .forEach(obj => {
        obj.set({ fill: rgba });
        obj.initDimensions();
      });
    
    canvas.requestRenderAll();
  }
  
  colorPicker.addEventListener('input', applyTextColor);
  alphaPicker.addEventListener('input', applyTextColor);

  const fontWeightSelect = document.getElementById('textFontWeight')
  fontWeightSelect.addEventListener('change', ()=>{
    canvas.getObjects()
    .filter(obj => obj.isLayerText === true)
    .forEach(obj => {
      obj.set({ fontWeight: Number(fontWeightSelect.value)})
    });

    canvas.requestRenderAll()
  })

  const fontSelect = document.getElementById('fontSelect')
  fontSelect.addEventListener('change', async () => {
    const option = fontSelect.selectedOptions[0];
    const fontName = option.value;
    const source = option.dataset.source;
    if (!fontName) return;
    //Load only if Google font
    if (source === 'google') {
      await loadGoogleFont(fontName);
    }
    applyFontToTextLayers(fontName);
  });

  function loadGoogleFont(fontFamily) {
    return new Promise((resolve, reject) => {
      if (document.fonts.check(`16px "${fontFamily}"`)) {
        resolve();
        return;
      }
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      const fontName = fontFamily.replace(/ /g, '+');
      link.href = `https://fonts.googleapis.com/css2?family=${fontName}:wght@100;200;300;400;500;600;700;800;900&display=swap`;
      link.onload = async () => {
        await document.fonts.load(`16px "${fontFamily}"`);
        resolve();
      };
      link.onerror = reject;
      document.head.appendChild(link);
    });
  }

  function applyFontToTextLayers(fontName) {
    canvas.getObjects()
      .filter(obj =>
        obj.isLayerText === true
      )
      .forEach(obj => {
        obj.set({
          fontFamily: fontName
        });
        obj.setCoords();
      });
    canvas.requestRenderAll();
  }

  window.addEventListener("resize", resizeCanvas);
  resizeCanvas();

  const saveTemplate = document.getElementById('saveTemplate');

  saveTemplate.addEventListener('click', async (e) => {
  e.preventDefault();

  if (document.getElementById('nom').value === '') {
    const element = document.getElementById('nom');
    window.scrollTo({ top: 0, behavior: 'smooth' });

    setTimeout(() => {
      document.getElementById('timedElement').style.display = 'block';
      element.style.border = '3px solid rgba(255, 0, 0, 0.5)';

      setTimeout(() => {
        document.getElementById('timedElement').style.display = 'none';
        element.style.border = '';
      }, 3000);
    }, 0);

    return;
  }

  const layers = [];
  const objects = canvas.getObjects().filter(obj => obj.isUserLayer);

  for (let i = 0; i < objects.length; i++) {
    const obj = objects[i];

    // 🔥 TEXT FIRST — MUST BE FIRST
    if (obj.isLayerText === true) {
      const imgData = await textToImage(obj);

      layers.push({
        image: imgData,
        x: Math.round(obj.left),
        y: Math.round(obj.top),
        width: Math.round(obj.getScaledWidth()),
        height: Math.round(obj.getScaledHeight()),
        index: i,
        image_name: 'text_layer.png'
      });

      continue;
    }

    // ✅ IMAGE LAYERS ONLY
    if (obj.type === 'image' && typeof obj.toDataURL === 'function') {
      layers.push({
        image: obj.toDataURL({ format: 'png' }),
        x: Math.round(obj.left),
        y: Math.round(obj.top),
        width: Math.round(obj.width * obj.scaleX),
        height: Math.round(obj.height * obj.scaleY),
        index: i,
        image_name: obj.fileName
      });
    }
  }

  let bg = selectedBackgroundImage || null;
  const nbposes = document.getElementById('nbposes').value

  fetch(`/saveTemplate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: document.getElementById('nom').value,
      format: currentTemplate,
      config_id: CONFIG_ID,
      background: bg,
      nbposes: nbposes,
      layers: layers
    })
  })
    .then(res => res.json())
    .then(data => {
      if (data.success && data.design_id) {
        DESIGN_ID = data.design_id;
        window.location.href = `/${CONFIG_ID}/editeur_templates/${data.design_id}`;
      } else {
        alert(data.error);
      }
    })
    .catch(err => console.error(err));
});

  function textToImage(obj) {
    return new Promise(resolve => {
      obj.clone(clone => {

        // Make sure Fabric updates transform data
        clone.setCoords();

        // TRUE bounding box (includes rotation, scale, etc.)
        const bounds = clone.getBoundingRect(true, true);

        const tempCanvas = new fabric.StaticCanvas(null, {
          width: Math.ceil(bounds.width),
          height: Math.ceil(bounds.height),
          objectCaching: false
        });

        // IMPORTANT: keep center logic
        clone.set({
          left: (bounds.width / 2)+2,
          top: (bounds.height / 2)+2,
          originX: 'center',
          originY: 'center',
          objectCaching: false
        });

        tempCanvas.add(clone);
        tempCanvas.renderAll();

        const dataURL = tempCanvas.toDataURL({
          format: 'png',
          multiplier: 1
        });

        tempCanvas.dispose();
        resolve(dataURL);
      });
    });
  } 

  //va nous permettre d'assigner un id au layers ajouté dans la canvas
  function uid() {
    return 'obj_' + Math.random().toString(36).slice(2, 9);
  }
})