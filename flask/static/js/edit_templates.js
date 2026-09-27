let selectedBackgroundImage = null
let deletedLayerIds = [];
let controlsInitialized = false;
let backgroundWasTouched = false;
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
                            isUserLayer: false,
                            selectable: false,
                            evented: false,
                            isFromDB: false,
                            layerId: null,
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
                          backgroundWasTouched = true;
                        
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
        isFromDB: false,
        layerId: null,
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
      backgroundWasTouched = true;
    
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
    enableRetinaScaling: false,
    preserveObjectStacking: true
  });

  // Canvas "logical" size (before CSS scaling)
  canvas.setWidth(3700);
  canvas.setHeight(2500);

  const formatSelect = document.getElementById("format");

  // Build initial format
  buildTemplate(formatSelect.value);
  
  // Update when changed
  formatSelect.addEventListener("change", () => {
      buildTemplate(e.target.value)
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
            isSlotRect: true,
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
              canvas.requestRenderAll();
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

          // Save original size
          originalSize1.width = img.width;
          originalSize1.height = img.height;

          img.set({
            left: 700,
            top: 250,
            originX: 'center',
            originY: 'center',
            objectId: uid(),
            selectable: true,
            evented: true,
            isUserLayer: true,
            scaleX: 1,
            scaleY: 1,
            isFromDB: false,
            layerId: null,
            lockRotation: true,
          });

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

  function linkImageControls(img, layerData = null) {
    let controlGroup;

    // === FIRST IMAGE ===
    if (layerData?.isFirst) {
      controlGroup = {
        wrapper: controller,
        x: document.getElementById('pos_X'),
        y: document.getElementById('pos_Y'),
        size: document.getElementById('size_1'),
        removeBtn: document.getElementById('remove_first'),
        rotateBtn: document.getElementById('remove_rotate_first'),
        layerId: img.layerId,
        img,
        isDynamic: false
      };

      controlGroup.removeBtn.classList.remove('d-none');
      controlGroup.rotateBtn.classList.remove('d-none');

      controlGroup.removeBtn.onclick = () => {
        canvas.remove(img);
        controlGroup.removeBtn.classList.add('d-none');
        controlGroup.rotateBtn.classList.add('d-none')

        if (img.layerId != null) {
          deletedLayerIds.push(img.layerId);
        }

        controlGroup.x.value = ""
        controlGroup.y.value = ""
        controlGroup.size.value = ""
      
        imageControls.splice(0, 1);
        canvas.requestRenderAll();
      };

      controlGroup.rotateBtn?.addEventListener('click', () => {
        canvas.setActiveObject(img);
        img.rotate((img.angle || 0) + 90);
        img.setCoords();
        canvas.requestRenderAll();
      });
    } 
    // === OTHER IMAGES ===
    else {
      const wrapper = document.createElement('div');
      wrapper.className = 'd-flex flex-wrap gap-2 align-items-center justify-content-center';

      wrapper.innerHTML = `
        <label>X:</label>
        <input type="number" class="form-control w-auto pos_X">
        <label>Y:</label>
        <input type="number" class="form-control w-auto pos_Y">
        <label>Size:</label>
        <input type="number" class="form-control w-auto size">%
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
        layerId: img.layerId,
        img,
        isDynamic: true
      };

      controlGroup.removeBtn.onclick = () => {
        canvas.remove(img);
        wrapper.remove();

        if (img.layerId != null) {
          deletedLayerIds.push(img.layerId);
        }
      
        imageControls.splice(imageControls.indexOf(controlGroup), 1);
        canvas.requestRenderAll();

        document.querySelector('.textControls').classList.add('d-none')
      };

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

    // === INITIAL VALUES (FROM DB) ===
    populateInputs(controlGroup, img, layerData);

    // === INPUT → IMAGE ===
    controlGroup.x.oninput = () => {
      img.set({ left: +controlGroup.x.value || 0 });
      canvas.requestRenderAll();
    };

    controlGroup.y.oninput = () => {
      img.set({ top: +controlGroup.y.value || 0 });
      canvas.requestRenderAll();
    };

    controlGroup.size.oninput = () => {
      const scale = (+controlGroup.size.value || 100) / 100;
      img.set({ scaleX: scale, scaleY: scale });
      img.setCoords();
      canvas.requestRenderAll();
    };

    controlGroup.wrapper.addEventListener('click', () => {
      canvas.setActiveObject(img);
      canvas.requestRenderAll();
    });

    // === IMAGE → INPUT (bind ONCE, immediately) ===
    img.on('moving', () => {
      controlGroup.x.value = Math.round(img.left);
      controlGroup.y.value = Math.round(img.top);
    });

    img.on('scaling', () => {
      controlGroup.size.value = Math.round(img.scaleX * 100);
    });

    imageControls.push(controlGroup);
  }

  document.getElementById('remove_first').addEventListener('click', (e)=>{
    e.preventDefault()
  })

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
        if(ctrl.layerId != null){
          deletedLayerIds.push(ctrl.layerId)
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
      backgroundWasTouched = true;

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
      fill: 'black',
      originX: 'center',
      originY: 'center',
      objectId: uid(),
      selectable: true,
      hasControls: true,
      lockScalingFlip: true,
      isUserLayer: true,
      lockRotation: true,
      isLayerText: true,
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
  
  if (MODE === "edit" && BACKGROUND_BASE64) {

    const cw = 3700;
    const ch = 2500;

    fabric.Image.fromURL(BACKGROUND_BASE64, img => {

      const iw = img.width;
      const ih = img.height;

      // Cover canvas without distortion
      const scale = Math.max(cw / iw, ch / ih);

      canvas.setBackgroundImage(
        img,
        canvas.renderAll.bind(canvas),
        {
          originX: 'center',
          originY: 'center',
          left: cw / 2,
          top: ch / 2,
          scaleX: scale,
          scaleY: scale,
          isFromDB: true,
          bgId: DESIGN_ID,
          IsBackGroundImg: true
        }
      );

    });
  }

  if (MODE === "edit") {
    //RESET EDITOR STATE
    //canvas.clear();
    imageControls.length = 0;

    // Remove dynamically created control groups (keep the first static one)
    document
      .querySelectorAll('.pos_X, .pos_Y, .size')
      .forEach(el => {
        const wrapper = el.closest('.d-flex');
        if (wrapper && wrapper !== controller) {
          wrapper.remove();
        }
      });
    
    // Reset first static inputs
    document.getElementById('pos_X').value = '';
    document.getElementById('pos_Y').value = '';
    document.getElementById('size_1').value = '';
    document.getElementById('remove_first').classList.add('d-none');

    LAYERS.forEach((layer, index) => {
      fabric.Image.fromURL(
        `data:image/png;base64,${layer.image}`,
        img => {
            img.set({
            left: layer.x,
            top: layer.y,
            originX: 'center',
            originY: 'center',
            objectId: uid(),
            scaleX: layer.size ? layer.size / 100 : 1,
            scaleY: layer.size ? layer.size / 100 : 1,
            isUserLayer: true,
            layerId: layer.id,
            hasControls: true,
            lockUniScaling: true,
            lockRotation: true,
            isFromDB: true,
          });

          canvas.add(img);
          canvas.bringToFront(img);
          canvas.requestRenderAll();

          //THIS IS WHAT YOU WERE MISSING
          linkImageControls(img, {
            layerId: layer.id,
            x: layer.x,
            y: layer.y,
            img: img,
            size: layer.size ?? 100,
            isFirst: index === 0
          });
          
          normalizeZOrder();
        }
      );
    });
  }

  const nbposes = document.getElementById('nbposes').value
  const editTemplate = document.getElementById('editTemplate')
  editTemplate.addEventListener('click', async () => {
    let backgroundData = undefined;
    
    if (backgroundWasTouched) {
      if (
        currentBackground &&
        typeof currentBackground.toDataURL === 'function'
      ) {
        try {
          backgroundData = currentBackground.toDataURL({ format: 'png' });
        } catch (e) {
          console.warn("Background export failed");
          backgroundData = null;
        }
      } else {
        backgroundData = null;
      }
    }
  
    const designPayload = {
      id: DESIGN_ID,
      name: document.getElementById('nom').value,
      nbposes: nbposes,
      format: currentTemplate
    };
  
    if (backgroundWasTouched) {
      designPayload.background = backgroundData;
    }
  
    //EXISTING IMAGE LAYERS (unchanged)
    const existingLayers = imageControls
      .filter(ctrl =>
        ctrl.layerId != null &&
        ctrl.img &&
        typeof ctrl.img.toDataURL === 'function'
      )
      .map(ctrl => ({
        id: ctrl.layerId,
        image: ctrl.img.toDataURL({ format: 'png' }),
        posX: Number(ctrl.x.value) || 0,
        posY: Number(ctrl.y.value) || 0
      }));
    
    // NEW LAYERS (IMAGES + TEXT FLATTENED)
    const newLayers = [];
    
    for (const obj of canvas.getObjects()) {
    
      if (!obj || obj.isSlotRect || obj.isSlotImage) continue;
    
      //NEW IMAGE
      if (
        obj.type === 'image' &&
        obj.layerId == null &&
        typeof obj.toDataURL === 'function'
      ) {
        newLayers.push({
          image: obj.toDataURL({ format: 'png' }),
          image_name: obj.fileName ?? null,
          posX: Math.round(obj.left),
          posY: Math.round(obj.top)
        });
      }
    
      //TEXT → IMAGE (THIS IS THE FIX)
      if (obj.isLayerText === true) {
        const imgData = await textToImage(obj);
      
        newLayers.push({
          image: imgData,
          image_name: 'text_layer.png',
          posX: Math.round(obj.left),
          posY: Math.round(obj.top)
        });
      }
    }
  
    fetch('/update_template', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        design: designPayload,
        existingLayers,
        newLayers,
        deletedLayers: deletedLayerIds
      })
    }
    .then(data => {
      if (data.success && data.design_id) {
        alert("Update effectué avec succés")
      }
    }))
  });

  window.addEventListener("resize", resizeCanvas);
  resizeCanvas();

  function normalizeZOrder() {
    const slotRects  = canvas.getObjects().filter(o => o.isSlotRect);
    const slotImages = canvas.getObjects().filter(o => o.isSlotImage);
    const userLayers = canvas.getObjects().filter(o => o.isUserLayer);
    
    //slot rectangles at the very bottom
    slotRects.forEach(o => canvas.sendToBack(o));
    
    //slot images ABOVE slot rects (but never above user layers)
    slotImages.forEach(o => {
      canvas.sendToBack(o);
      canvas.bringToFront(o)
    });
  
    // user layers ALWAYS on top (DB + new)
    userLayers.forEach(o => canvas.bringToFront(o));
  
    canvas.requestRenderAll();
  }

  function populateInputs(controlGroup, img, layerData) {
    console.log('populateInputs:', layerData);
    controlGroup.x.value = layerData?.x ?? Math.round(img.left);
    controlGroup.y.value = layerData?.y ?? Math.round(img.top);
    controlGroup.size.value =
      layerData?.size ?? Math.round(img.scaleX * 100);
  }

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