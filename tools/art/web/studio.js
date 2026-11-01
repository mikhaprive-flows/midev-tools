// midev Studio - Interactive Web Preview & Animation Engine
(function () {
  let state = {
    recipes: [],
    activeRecipe: null,
    meta: null,
    sheetImage: new Image(),
    currentAnimName: null,
    currentFrame: 0,
    isPlaying: true,
    fps: 10,
    scale: 4,
    showOrigin: true,
    showGrid: false,
    lastFrameTime: 0,
  };

  const canvas = document.getElementById("viewportCanvas");
  const ctx = canvas.getContext("2d");
  const recipeListEl = document.getElementById("recipeList");
  const searchInput = document.getElementById("searchInput");
  const animSelect = document.getElementById("animSelect");
  const playBtn = document.getElementById("playBtn");
  const prevFrameBtn = document.getElementById("prevFrameBtn");
  const nextFrameBtn = document.getElementById("nextFrameBtn");
  const fpsSlider = document.getElementById("fpsSlider");
  const fpsValEl = document.getElementById("fpsVal");
  const zoomSelect = document.getElementById("zoomSelect");
  const toggleOriginBtn = document.getElementById("toggleOrigin");
  const toggleGridBtn = document.getElementById("toggleGrid");
  const rebuildBtn = document.getElementById("rebuildBtn");
  const frameStripEl = document.getElementById("frameStrip");

  // Load recipes list
  async function loadRecipes() {
    try {
      const res = await fetch("/api/recipes");
      state.recipes = await res.json();
      renderRecipeList();
      if (state.recipes.length > 0 && !state.activeRecipe) {
        selectRecipe(state.recipes[0]);
      }
    } catch (e) {
      console.error("Failed to load recipes", e);
    }
  }

  function renderRecipeList() {
    const filter = searchInput.value.toLowerCase().trim();
    recipeListEl.innerHTML = "";

    state.recipes
      .filter((r) => r.toLowerCase().includes(filter))
      .forEach((r) => {
        const li = document.createElement("li");
        li.className = `recipe-item ${r === state.activeRecipe ? "active" : ""}`;
        li.textContent = r;
        li.onclick = () => selectRecipe(r);
        recipeListEl.appendChild(li);
      });
  }

  async function selectRecipe(name) {
    state.activeRecipe = name;
    renderRecipeList();
    document.getElementById("inspRecipeName").textContent = name;

    try {
      const res = await fetch(`/api/recipe/${name}`);
      const data = await res.json();
      state.meta = data.meta;

      // Update Inspector details
      document.getElementById("inspFrameSize").textContent = `${data.meta.frameWidth || "-"} x ${data.meta.frameHeight || "-"}`;
      document.getElementById("inspOrigin").textContent = `${data.meta.originX || 0}, ${data.meta.originY || 0}`;

      // Update export download links
      const linksContainer = document.getElementById("exportLinks");
      linksContainer.innerHTML = `
        <a href="${data.imageUrl}" target="_blank"><span>PNG SpriteSheet</span><span>↗</span></a>
        <a href="/assets/sprites/${name}.tres" target="_blank"><span>Godot 4 .tres</span><span>↗</span></a>
        <a href="/assets/sprites/${name}_tp.json" target="_blank"><span>TexturePacker JSON</span><span>↗</span></a>
        <a href="/assets/sprites/${name}.json" target="_blank"><span>Native JSON</span><span>↗</span></a>
      `;

      // Populate animation selector
      animSelect.innerHTML = "";
      const animNames = Object.keys(data.meta.animations || {});
      if (animNames.length > 0) {
        animNames.forEach((an) => {
          const opt = document.createElement("option");
          opt.value = an;
          opt.textContent = an;
          animSelect.appendChild(opt);
        });
        setAnimation(animNames[0]);
      } else {
        // Fallback for static single-frame assets
        state.currentAnimName = null;
        state.fps = 1;
      }

      // Load image
      state.sheetImage = new Image();
      state.sheetImage.onload = () => {
        document.getElementById("inspSheetSize").textContent = `${state.sheetImage.width} x ${state.sheetImage.height}`;
        renderFrameStrip();
        renderCanvas();
      };
      state.sheetImage.src = data.imageUrl + `?t=${Date.now()}`;
    } catch (e) {
      console.error("Failed to fetch recipe metadata", e);
    }
  }

  function setAnimation(name) {
    state.currentAnimName = name;
    state.currentFrame = 0;
    const anim = state.meta.animations[name];
    if (anim) {
      state.fps = anim.fps || 10;
      fpsSlider.value = state.fps;
      fpsValEl.textContent = `${state.fps} fps`;
      document.getElementById("inspAnimFps").textContent = `${state.fps} fps`;
      document.getElementById("inspAnimFrames").textContent = anim.frames;
      document.getElementById("inspAnimLoop").textContent = anim.loop ? "Yes" : "No";
    }
    renderFrameStrip();
    renderCanvas();
  }

  function renderFrameStrip() {
    frameStripEl.innerHTML = "";
    if (!state.meta || !state.currentAnimName) return;

    const anim = state.meta.animations[state.currentAnimName];
    if (!anim) return;

    const fw = state.meta.frameWidth;
    const fh = state.meta.frameHeight;
    const row = anim.row;

    for (let i = 0; i < anim.frames; i++) {
      const thumb = document.createElement("div");
      thumb.className = `frame-thumb ${i === state.currentFrame ? "active" : ""}`;

      const tCanvas = document.createElement("canvas");
      tCanvas.width = 40;
      tCanvas.height = 40;
      const tCtx = tCanvas.getContext("2d");
      tCtx.imageSmoothingEnabled = false;

      // Draw slice scaled into thumbnail
      tCtx.drawImage(state.sheetImage, i * fw, row * fh, fw, fh, 0, 0, 40, 40);

      const span = document.createElement("span");
      span.textContent = `#${i}`;

      thumb.appendChild(tCanvas);
      thumb.appendChild(span);

      thumb.onclick = () => {
        state.isPlaying = false;
        playBtn.textContent = "▶ Play";
        state.currentFrame = i;
        updateActiveThumb();
        renderCanvas();
      };

      frameStripEl.appendChild(thumb);
    }
  }

  function updateActiveThumb() {
    const thumbs = frameStripEl.children;
    for (let i = 0; i < thumbs.length; i++) {
      thumbs[i].className = `frame-thumb ${i === state.currentFrame ? "active" : ""}`;
    }
  }

  function renderCanvas() {
    if (!state.sheetImage.complete || !state.meta) return;

    const fw = state.meta.frameWidth || state.sheetImage.width;
    const fh = state.meta.frameHeight || state.sheetImage.height;
    const scale = state.scale;

    canvas.width = fw * scale;
    canvas.height = fh * scale;

    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    let srcX = 0;
    let srcY = 0;

    if (state.currentAnimName && state.meta.animations[state.currentAnimName]) {
      const anim = state.meta.animations[state.currentAnimName];
      srcX = state.currentFrame * fw;
      srcY = anim.row * fh;
    }

    // Draw frame
    ctx.drawImage(state.sheetImage, srcX, srcY, fw, fh, 0, 0, fw * scale, fh * scale);

    // Draw Origin Crosshair
    if (state.showOrigin && state.meta.originX !== undefined && state.meta.originY !== undefined) {
      const ox = state.meta.originX * scale;
      const oy = state.meta.originY * scale;

      ctx.strokeStyle = "rgba(0, 255, 204, 0.8)";
      ctx.lineWidth = 1;

      ctx.beginPath();
      ctx.moveTo(ox - 8, oy);
      ctx.lineTo(ox + 8, oy);
      ctx.moveTo(ox, oy - 8);
      ctx.lineTo(ox, oy + 8);
      ctx.stroke();

      ctx.fillStyle = "rgba(0, 255, 204, 0.9)";
      ctx.fillRect(ox - 1, oy - 1, 3, 3);
    }

    // Draw Grid
    if (state.showGrid) {
      ctx.strokeStyle = "rgba(255, 255, 255, 0.15)";
      ctx.lineWidth = 1;
      for (let x = 0; x <= fw; x++) {
        ctx.beginPath();
        ctx.moveTo(x * scale, 0);
        ctx.lineTo(x * scale, fh * scale);
        ctx.stroke();
      }
      for (let y = 0; y <= fh; y++) {
        ctx.beginPath();
        ctx.moveTo(0, y * scale);
        ctx.lineTo(fw * scale, y * scale);
        ctx.stroke();
      }
    }
  }

  // Animation Loop
  function tick(timestamp) {
    if (!state.lastFrameTime) state.lastFrameTime = timestamp;
    const elapsed = timestamp - state.lastFrameTime;
    const interval = 1000 / state.fps;

    if (state.isPlaying && elapsed >= interval) {
      state.lastFrameTime = timestamp;
      if (state.meta && state.currentAnimName && state.meta.animations[state.currentAnimName]) {
        const anim = state.meta.animations[state.currentAnimName];
        state.currentFrame = (state.currentFrame + 1) % anim.frames;
        updateActiveThumb();
        renderCanvas();
      }
    }

    requestAnimationFrame(tick);
  }

  // UI Event Listeners
  searchInput.oninput = renderRecipeList;

  animSelect.onchange = (e) => setAnimation(e.target.value);

  playBtn.onclick = () => {
    state.isPlaying = !state.isPlaying;
    playBtn.textContent = state.isPlaying ? "❚❚ Pause" : "▶ Play";
  };

  prevFrameBtn.onclick = () => {
    if (!state.meta || !state.currentAnimName) return;
    state.isPlaying = false;
    playBtn.textContent = "▶ Play";
    const total = state.meta.animations[state.currentAnimName].frames;
    state.currentFrame = (state.currentFrame - 1 + total) % total;
    updateActiveThumb();
    renderCanvas();
  };

  nextFrameBtn.onclick = () => {
    if (!state.meta || !state.currentAnimName) return;
    state.isPlaying = false;
    playBtn.textContent = "▶ Play";
    const total = state.meta.animations[state.currentAnimName].frames;
    state.currentFrame = (state.currentFrame + 1) % total;
    updateActiveThumb();
    renderCanvas();
  };

  fpsSlider.oninput = (e) => {
    state.fps = parseInt(e.target.value, 10);
    fpsValEl.textContent = `${state.fps} fps`;
    document.getElementById("inspAnimFps").textContent = `${state.fps} fps`;
  };

  zoomSelect.onchange = (e) => {
    state.scale = parseInt(e.target.value, 10);
    renderCanvas();
  };

  toggleOriginBtn.onclick = () => {
    state.showOrigin = !state.showOrigin;
    toggleOriginBtn.classList.toggle("btn-primary", state.showOrigin);
    renderCanvas();
  };

  toggleGridBtn.onclick = () => {
    state.showGrid = !state.showGrid;
    toggleGridBtn.classList.toggle("btn-primary", state.showGrid);
    renderCanvas();
  };

  rebuildBtn.onclick = async () => {
    if (!state.activeRecipe) return;
    rebuildBtn.textContent = "⏳ Rebuilding...";
    try {
      const res = await fetch(`/api/build/${state.activeRecipe}`, { method: "POST" });
      const data = await res.json();
      rebuildBtn.textContent = "✓ Built!";
      setTimeout(() => (rebuildBtn.textContent = "⚡ Rebuild"), 1200);
      selectRecipe(state.activeRecipe);
    } catch (e) {
      rebuildBtn.textContent = "❌ Error";
      setTimeout(() => (rebuildBtn.textContent = "⚡ Rebuild"), 1500);
    }
  };

  // Live Hot-Reload Listener (SSE)
  function initLiveWatcher() {
    try {
      const evtSource = new EventSource("/api/events");
      evtSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "reload") {
            console.log(`[studio] Live change detected: ${data.recipe}`);
            if (data.recipe === state.activeRecipe || !state.activeRecipe) {
              selectRecipe(state.activeRecipe);
            }
          }
        } catch (err) {}
      };
      evtSource.onerror = () => {
        console.warn("[studio] EventSource disconnected, retrying...");
      };
    } catch (e) {
      console.warn("[studio] EventSource not available", e);
    }
  }

  // Startup
  loadRecipes();
  initLiveWatcher();
  requestAnimationFrame(tick);
})();
