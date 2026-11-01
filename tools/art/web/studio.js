// midev Studio - Interactive Web Preview & Animation Engine
(function () {
  let state = {
    catalog: { assets: [], recipes: [] },
    activeCat: "all",
    activeAssetId: null,
    currentRecipe: null,
    meta: null,
    sheetImage: null,
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
  const categoryTabs = document.getElementById("categoryTabs");
  const projectSelect = document.getElementById("projectSelect");

  // Load Projects List into Header Dropdown
  async function loadProjects() {
    try {
      const res = await fetch("/api/projects");
      const data = await res.json();
      projectSelect.innerHTML = "";

      (data.projects || []).forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = `${p.title} (${p.recipes_count} rec)`;
        if (p.id === data.activeId) {
          opt.selected = true;
        }
        projectSelect.appendChild(opt);
      });
    } catch (e) {
      console.warn("[studio] Failed to load projects:", e);
    }
  }

  // Load Asset Catalog & Initialize
  async function loadCatalog() {
    try {
      const res = await fetch("/api/catalog");
      state.catalog = await res.json();

      if (state.catalog.palette) {
        document.getElementById("headerPalette").textContent = `Palette: ${state.catalog.palette}`;
      }

      renderAssetList();

      const defaultId = state.catalog.defaultAssetId || (state.catalog.assets[0] ? state.catalog.assets[0].id : null);
      if (defaultId) {
        selectAsset(defaultId);
      } else {
        renderPlaceholder("No assets in this project. Use 'midev new' or 'midev generate'.");
      }
    } catch (e) {
      console.error("[studio] Failed to load asset catalog:", e);
      renderPlaceholder("Failed to connect to Studio server");
    }
  }

  // Filter & Render Sidebar List
  function renderAssetList() {
    const filter = searchInput.value.toLowerCase().trim();
    recipeListEl.innerHTML = "";

    const filtered = (state.catalog.assets || []).filter((item) => {
      const matchesCat = state.activeCat === "all" || item.category === state.activeCat;
      const matchesSearch = !filter || item.name.toLowerCase().includes(filter) || item.recipe.toLowerCase().includes(filter);
      return matchesCat && matchesSearch;
    });

    if (filtered.length === 0) {
      const emptyLi = document.createElement("li");
      emptyLi.style.padding = "16px";
      emptyLi.style.color = "var(--text-muted)";
      emptyLi.style.fontSize = "12px";
      emptyLi.textContent = "No matching assets found";
      recipeListEl.appendChild(emptyLi);
      return;
    }

    filtered.forEach((item) => {
      const li = document.createElement("li");
      li.className = `recipe-item ${item.id === state.activeAssetId ? "active" : ""}`;

      const nameSpan = document.createElement("span");
      nameSpan.className = "item-title";
      nameSpan.textContent = item.name;

      const badge = document.createElement("span");
      badge.className = `item-badge badge-${item.category}`;
      badge.textContent = item.category === "backgrounds" ? "bg" : (item.category === "sprites" ? "sprite" : item.category);

      li.appendChild(nameSpan);
      li.appendChild(badge);

      li.onclick = () => selectAsset(item.id);
      recipeListEl.appendChild(li);
    });
  }

  // Select Asset and Load Data
  async function selectAsset(assetId) {
    state.activeAssetId = assetId;
    renderAssetList();

    try {
      const res = await fetch(`/api/asset?id=${encodeURIComponent(assetId)}`);
      const data = await res.json();
      state.meta = data.meta;
      state.currentRecipe = data.recipe || assetId;

      // Update Inspector details
      document.getElementById("inspRecipeName").textContent = data.name || assetId;
      const cat = assetId.includes("/") ? assetId.split("/")[0] : "sprites";
      document.getElementById("inspCategory").textContent = cat;
      document.getElementById("inspSourceRecipe").textContent = `${data.recipe}.py`;
      document.getElementById("inspFrameSize").textContent = `${data.meta?.frameWidth || "-"} x ${data.meta?.frameHeight || "-"}`;
      document.getElementById("inspOrigin").textContent = `${data.meta?.originX ?? "-"}, ${data.meta?.originY ?? "-"}`;

      // Update export download links
      const linksContainer = document.getElementById("exportLinks");
      linksContainer.innerHTML = `
        <a href="${data.imageUrl}" target="_blank"><span>PNG SpriteSheet</span><span>↗</span></a>
        <a href="/assets/${data.id}.tres" target="_blank"><span>Godot 4 .tres</span><span>↗</span></a>
        <a href="/assets/${data.id}_tp.json" target="_blank"><span>TexturePacker JSON</span><span>↗</span></a>
        <a href="/assets/${data.id}.json" target="_blank"><span>Native JSON</span><span>↗</span></a>
      `;

      // Populate animation selector
      animSelect.innerHTML = "";
      const anims = data.meta?.animations || {};
      const animNames = Object.keys(anims);

      if (animNames.length > 0) {
        animNames.forEach((an) => {
          const opt = document.createElement("option");
          opt.value = an;
          opt.textContent = an;
          animSelect.appendChild(opt);
        });
        state.currentAnimName = animNames[0];
        const a = anims[animNames[0]];
        state.fps = a?.fps || 10;
        fpsSlider.value = state.fps;
        fpsValEl.textContent = `${state.fps} fps`;
        document.getElementById("inspAnimFps").textContent = `${state.fps} fps`;
        document.getElementById("inspAnimFrames").textContent = a?.frames || 1;
        document.getElementById("inspAnimLoop").textContent = a?.loop ? "Yes" : "No";
      } else {
        state.currentAnimName = null;
        state.fps = 1;
      }
      state.currentFrame = 0;

      // Clean up previous image & load new one
      if (!data.imageUrl) {
        state.sheetImage = null;
        renderPlaceholder("No image generated yet. Click Rebuild.");
        return;
      }

      const img = new Image();
      img.onload = () => {
        state.sheetImage = img;
        document.getElementById("inspSheetSize").textContent = `${img.width} x ${img.height}`;
        renderFrameStrip();
        renderCanvas();
      };
      img.onerror = () => {
        state.sheetImage = null;
        console.error("Failed to load sprite sheet:", data.imageUrl);
        renderPlaceholder("Failed to load image from server.");
      };
      img.src = data.imageUrl + `?t=${Date.now()}`;
    } catch (e) {
      console.error("[studio] Failed to fetch asset data:", e);
      renderPlaceholder("Error fetching asset details");
    }
  }

  function setAnimation(name) {
    state.currentAnimName = name;
    state.currentFrame = 0;
    const anim = state.meta?.animations?.[name];
    if (anim) {
      state.fps = anim.fps || 10;
      fpsSlider.value = state.fps;
      fpsValEl.textContent = `${state.fps} fps`;
      document.getElementById("inspAnimFps").textContent = `${state.fps} fps`;
      document.getElementById("inspAnimFrames").textContent = anim.frames || 1;
      document.getElementById("inspAnimLoop").textContent = anim.loop ? "Yes" : "No";
    }
    renderFrameStrip();
    renderCanvas();
  }

  function renderFrameStrip() {
    frameStripEl.innerHTML = "";
    if (!state.sheetImage || !state.sheetImage.complete || state.sheetImage.naturalWidth === 0) return;
    if (!state.meta || !state.currentAnimName) return;

    const anim = state.meta.animations?.[state.currentAnimName];
    if (!anim) return;

    const fw = state.meta.frameWidth || state.sheetImage.width;
    const fh = state.meta.frameHeight || state.sheetImage.height;
    const row = anim.row || 0;
    const totalFrames = anim.frames || 1;

    for (let i = 0; i < totalFrames; i++) {
      const thumb = document.createElement("div");
      thumb.className = `frame-thumb ${i === state.currentFrame ? "active" : ""}`;

      const tCanvas = document.createElement("canvas");
      tCanvas.width = 40;
      tCanvas.height = 40;
      const tCtx = tCanvas.getContext("2d");
      tCtx.imageSmoothingEnabled = false;

      try {
        tCtx.drawImage(state.sheetImage, i * fw, row * fh, fw, fh, 0, 0, 40, 40);
      } catch (err) {
        // Safe catch
      }

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
    if (!state.sheetImage || !state.sheetImage.complete || state.sheetImage.naturalWidth === 0) return;
    if (!state.meta) return;

    const fw = state.meta.frameWidth || state.sheetImage.width;
    const fh = state.meta.frameHeight || state.sheetImage.height;
    const scale = state.scale;

    canvas.width = fw * scale;
    canvas.height = fh * scale;

    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    let srcX = 0;
    let srcY = 0;

    if (state.currentAnimName && state.meta.animations?.[state.currentAnimName]) {
      const anim = state.meta.animations[state.currentAnimName];
      srcX = state.currentFrame * fw;
      srcY = (anim.row || 0) * fh;
    }

    try {
      ctx.drawImage(state.sheetImage, srcX, srcY, fw, fh, 0, 0, fw * scale, fh * scale);
    } catch (err) {
      console.warn("Error drawing canvas slice:", err);
    }

    // Draw Origin Crosshair
    if (state.showOrigin && state.meta.originX !== undefined && state.meta.originY !== undefined) {
      const ox = state.meta.originX * scale;
      const oy = state.meta.originY * scale;

      ctx.strokeStyle = "rgba(0, 255, 204, 0.85)";
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

    // Draw Pixel Grid
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

  function renderPlaceholder(message) {
    canvas.width = 360;
    canvas.height = 200;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "rgba(22, 25, 38, 0.9)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = "rgba(43, 49, 76, 0.8)";
    ctx.strokeRect(1, 1, canvas.width - 2, canvas.height - 2);

    ctx.fillStyle = "#8c96b5";
    ctx.font = "13px monospace";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(message, canvas.width / 2, canvas.height / 2);
  }

  // Animation Loop
  function tick(timestamp) {
    if (!state.lastFrameTime) state.lastFrameTime = timestamp;
    const elapsed = timestamp - state.lastFrameTime;
    const interval = 1000 / state.fps;

    if (state.isPlaying && elapsed >= interval) {
      state.lastFrameTime = timestamp;
      if (state.meta && state.currentAnimName && state.meta.animations?.[state.currentAnimName]) {
        const anim = state.meta.animations[state.currentAnimName];
        const total = anim.frames || 1;
        if (total > 1) {
          state.currentFrame = (state.currentFrame + 1) % total;
          updateActiveThumb();
          renderCanvas();
        }
      }
    }

    requestAnimationFrame(tick);
  }

  // UI Event Listeners
  searchInput.oninput = renderAssetList;

  categoryTabs.querySelectorAll(".cat-pill").forEach((pill) => {
    pill.onclick = () => {
      categoryTabs.querySelectorAll(".cat-pill").forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      state.activeCat = pill.dataset.cat;
      renderAssetList();
    };
  });

  animSelect.onchange = (e) => setAnimation(e.target.value);

  playBtn.onclick = () => {
    state.isPlaying = !state.isPlaying;
    playBtn.textContent = state.isPlaying ? "❚❚ Pause" : "▶ Play";
  };

  prevFrameBtn.onclick = () => {
    if (!state.meta || !state.currentAnimName) return;
    state.isPlaying = false;
    playBtn.textContent = "▶ Play";
    const total = state.meta.animations?.[state.currentAnimName]?.frames || 1;
    state.currentFrame = (state.currentFrame - 1 + total) % total;
    updateActiveThumb();
    renderCanvas();
  };

  nextFrameBtn.onclick = () => {
    if (!state.meta || !state.currentAnimName) return;
    state.isPlaying = false;
    playBtn.textContent = "▶ Play";
    const total = state.meta.animations?.[state.currentAnimName]?.frames || 1;
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
    const target = state.activeAssetId || state.currentRecipe;
    if (!target) return;
    rebuildBtn.textContent = "⏳ Rebuilding...";
    try {
      const res = await fetch(`/api/build/${encodeURIComponent(target)}`, { method: "POST" });
      const data = await res.json();
      rebuildBtn.textContent = "✓ Built!";
      setTimeout(() => (rebuildBtn.textContent = "⚡ Rebuild"), 1200);
      selectAsset(state.activeAssetId);
    } catch (e) {
      rebuildBtn.textContent = "❌ Error";
      setTimeout(() => (rebuildBtn.textContent = "⚡ Rebuild"), 1500);
    }
  };

  projectSelect.onchange = async (e) => {
    const selected = e.target.value;
    try {
      await fetch(`/api/project/switch?project=${encodeURIComponent(selected)}`, { method: "POST" });
      state.activeAssetId = null;
      await loadCatalog();
    } catch (err) {
      console.error("[studio] Failed to switch project:", err);
    }
  };

  // Live Hot-Reload Listener (SSE)
  function initLiveWatcher() {
    try {
      const evtSource = new EventSource("/api/events");
      evtSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "project_switched") {
            loadProjects();
            state.activeAssetId = null;
            loadCatalog();
          } else if (data.type === "reload") {
            console.log(`[studio] Live change detected: ${data.recipe}`);
            loadCatalog().then(() => {
              if (state.activeAssetId) {
                selectAsset(state.activeAssetId);
              }
            });
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
  loadProjects();
  loadCatalog();
  if (!window.location.search.includes("nosse=1")) {
    initLiveWatcher();
  }
  requestAnimationFrame(tick);
})();
