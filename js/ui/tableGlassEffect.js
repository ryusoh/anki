import { PIE_CHART_GLASS_EFFECT } from "#js/config.js";

export class TableGlassEffect {
  constructor(containerSelector, options = {}) {
    this.container = document.querySelector(containerSelector);
    if (!this.container) {
      throw new Error(`Container not found: ${containerSelector}`);
    }
    // Expose instance for external control (e.g. zoom animations)
    this.container.glassEffect = this;

    // Merge defaults with provided options
    // If options has threeD, it overrides PIE_CHART_GLASS_EFFECT.threeD
    this.options = {
      ...PIE_CHART_GLASS_EFFECT,
      ...options,
      threeD: {
        ...PIE_CHART_GLASS_EFFECT.threeD,
        ...(options.threeD || {}),
      },
    };

    if (this.options.enabled === false) {
      return;
    }

    this.canvas = document.createElement("canvas");
    this.ctx = this.canvas.getContext("2d");
    this.animationFrame = null;
    this.state = {
      phase: 0,
      continuousPhase: 0,
      ambientPhase: 0,
      lastTime: 0,
      energyParticles: [],
      pointer: { x: 0, y: 0 },
      pointerSmoothed: { x: 0, y: 0 },
    };
    this.resizePaused = false;

    this.init();
  }

  pauseResize() {
    this.resizePaused = true;
  }

  resumeResize() {
    this.resizePaused = false;
    this.resize();
  }

  init() {
    this.canvas.style.left = "0";
    this.canvas.style.width = "100%";
    this.canvas.style.pointerEvents = "none"; // Let clicks pass through
    this.canvas.style.zIndex = "-1"; // Behind content
    this.canvas.style.display = "block";

    // Handle header exclusion
    this._headerHeight = 0;
    // Bolt: Call getComputedStyle once and cache the object to avoid
    // redundant synchronous style recalculations that block the main thread.
    this._computedStyle = window.getComputedStyle(this.container);
    const computedStyle = this._computedStyle;

    const computedRadius = parseInt(computedStyle.borderRadius, 10) || 8;
    this._borderRadius = computedRadius;
    if (this.options.excludeHeader) {
      // Bolt: Cache DOM queries lazily to avoid O(N) lookup overhead in high-frequency methods.
      this._thead = this._thead || this.container.querySelector("thead");
      const thead = this._thead;
      this._headerHeight = thead ? thead.offsetHeight : 0;
      this.canvas.style.top = `${this._headerHeight}px`;
      this.canvas.style.borderRadius = "0";
    } else {
      this.canvas.style.top = "0";
      this.canvas.style.borderRadius = `${computedRadius}px`;
    }

    // Ensure container is relative so canvas is positioned correctly
    if (computedStyle.position === "static") {
      this.container.style.position = "relative";
    }

    // Use sticky only when content actually overflows the container,
    // so the canvas stays pinned during scroll with zero lag.
    // Just checking overflow CSS is not enough — containers like .chart-card
    // have overflow:auto but content never exceeds the viewport.
    this._scrollable =
      /auto|scroll/.test(computedStyle.overflow + computedStyle.overflowY) &&
      this.container.scrollHeight > this.container.clientHeight + 1;

    if (this._scrollable) {
      this.canvas.style.position = "sticky";
      this.container.insertBefore(this.canvas, this.container.firstChild);
    } else {
      this.canvas.style.position = "absolute";
      this.container.appendChild(this.canvas);
    }

    // Find the table element to observe its full width
    // Bolt: Cache DOM queries lazily to avoid O(N) lookup overhead in high-frequency methods.
    this.table = this.table || this.container.querySelector("table");
    const target = this.table || this.container;

    // Observe size changes on the table (content) instead of just the container

    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(target);

    this.initParticles();
    this.resize();
    this.startLoop();

    // Mouse movement for parallax/interaction
    this.container.addEventListener("mouseenter", () => {
      const r = this.container.getBoundingClientRect();
      this.containerRect = {
        left: r.left + window.scrollX,
        top: r.top + window.scrollY,
        width: r.width,
        height: r.height,
      };
    });
    // Bolt: Throttle high-frequency mousemove events using requestAnimationFrame and a ticking lock
    this._ticking = false;
    this.container.addEventListener("mousemove", (e) => {
      if (!this._ticking) {
        window.requestAnimationFrame(() => {
          this.handleMouseMove(e);
          this._ticking = false;
        });
        this._ticking = true;
      }
    });
    this.container.addEventListener("mouseleave", () =>
      this.handleMouseLeave(),
    );
  }

  initParticles() {
    const electric = this.options.threeD?.electric || {};
    const count = Math.max(12, (electric.arcCount || 3) * 8);
    // Bolt: Use pre-allocated native array and native for loop instead of Array.from
    // to bypass dummy object creation and callback allocations inside hot paths.
    this.state.energyParticles = new Array(count);
    for (let i = 0; i < count; i++) {
      this.state.energyParticles[i] = {
        progress: Math.random(), // 0 to 1 along the path
        speed: 0.2 + Math.random() * 0.5,
        size: 1.2 + Math.random() * 1.6,
        flickerOffset: Math.random() * Math.PI * 2,
        offset: (Math.random() - 0.5) * 10, // Perpendicular offset
      };
    }
  }

  resize() {
    if (this.resizePaused) {
      return;
    }

    // Re-check header height on resize if needed
    let headerHeight = 0;
    if (this.options.excludeHeader) {
      this._thead = this._thead || this.container.querySelector("thead");
      const thead = this._thead;
      headerHeight = thead ? thead.offsetHeight : 0;
      this._headerHeight = headerHeight;
      this.canvas.style.top = `${headerHeight}px`;
    }

    // Re-evaluate whether content actually overflows and update positioning
    // Bolt: Cache getComputedStyle to avoid redundant synchronous style recalculations
    const containerStyle =
      this._computedStyle || window.getComputedStyle(this.container);
    const overflowStyle = containerStyle.overflow + containerStyle.overflowY;
    const nowScrollable =
      /auto|scroll/.test(overflowStyle) &&
      this.container.scrollHeight > this.container.clientHeight + 1;

    if (nowScrollable !== this._scrollable) {
      this._scrollable = nowScrollable;
      if (this._scrollable) {
        this.canvas.style.position = "sticky";
        // Move canvas to first child for sticky to work
        if (this.canvas !== this.container.firstChild) {
          this.container.insertBefore(this.canvas, this.container.firstChild);
        }
      } else {
        this.canvas.style.position = "absolute";
        this.canvas.style.marginBottom = "";
      }
    }

    // Use the table's full scroll width if available, otherwise container width
    // This ensures the canvas extends to cover all scrollable content
    const contentWidth = this.table
      ? this.table.scrollWidth
      : this.container.scrollWidth;
    // Add a small buffer to prevent pixel-perfect clipping at the very edge
    this.width = Math.max(this.container.clientWidth, contentWidth + 2);

    // Explicitly set style width to match the full content width
    this.canvas.style.width = `${this.width}px`;

    // Keep canvas at visible viewport size (avoids exceeding browser canvas limits)
    // Sticky positioning keeps it pinned during scroll with zero lag
    const visibleHeight = this.container.clientHeight - headerHeight;
    this.height = Math.max(1, visibleHeight);
    this.canvas.style.height = `${this.height}px`;
    // For sticky canvas, negative margin pulls content up so the canvas doesn't consume layout space
    if (this._scrollable) {
      this.canvas.style.marginBottom = `-${this.height}px`;
    }

    // Handle high DPI displays
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = this.width * dpr;
    this.canvas.height = this.height * dpr;
    this.ctx.scale(dpr, dpr);

    // Bolt: Invalidate cached ambient glow gradient since canvas dimensions have changed
    this._ambientGradientCache = null;
    this._reflectionGradientCache = null;
    this._hoverSpotlightGradientCache = null;
    this._hoverBorderGradientCache = null;

    this.containerRect = null; // Invalidate cached layout

    // Track rows for hover effect
    this.rows = [];
    this.rowMap = new WeakMap();
    if (this.options.rowHoverEffect?.enabled) {
      // Bolt: Cache DOM queries lazily to avoid O(N) lookup overhead in high-frequency methods.
      this._tbody = this._tbody || this.container.querySelector("tbody");
      const tbody = this._tbody;
      if (tbody) {
        this._trs = this._trs || tbody.querySelectorAll("tr");
        const rows = this._trs;

        // We need the canvas position to calculate relative row offsets accurately
        const canvasRect = this.canvas.getBoundingClientRect();

        // Bolt: Use native for loop and pre-allocate the array to avoid
        // dummy object creations and callback allocation garbage collection pressure
        this.rows = new Array(rows.length);
        for (let i = 0; i < rows.length; i++) {
          const row = rows[i];
          const rowRect = row.getBoundingClientRect();

          // Calculate top relative to the canvas itself
          // This handles all offset/header/padding logic implicitly because
          // we simply ask "where is the row relative to the canvas?"
          const relativeTop = rowRect.top - canvasRect.top;

          this.rows[i] = {
            top: relativeTop,
            height: rowRect.height,
            element: row,
          };
          this.rowMap.set(row, i);
        }
      }
    }
  }
  handleMouseMove(e) {
    if (!this.containerRect) {
      const r = this.container.getBoundingClientRect();
      this.containerRect = {
        left: r.left + window.scrollX,
        top: r.top + window.scrollY,
        width: r.width,
        height: r.height,
      };
    }
    const rect = this.containerRect;
    const x = (e.pageX - rect.left) / rect.width - 0.5;
    const y = (e.pageY - rect.top) / rect.height - 0.5;
    this.state.pointer.x = x * 2; // -1 to 1
    this.state.pointer.y = y * 2; // -1 to 1

    // Determine hovered row by finding actual element under cursor
    if (this.options.rowHoverEffect?.enabled) {
      // Bolt: Use e.target directly instead of the costly document.elementFromPoint
      // which causes layout thrashing and main thread blocking.
      const elementUnderMouse = e.target;
      if (elementUnderMouse) {
        // Find the closest table row
        const rowElement = elementUnderMouse.closest("tr");

        if (rowElement && this.container.contains(rowElement)) {
          // Bolt: Use WeakMap for O(1) constant-time lookup instead of O(N) array iteration
          const foundIndex = this.rowMap.get(rowElement);
          this.state.hoveredRowIndex =
            foundIndex !== undefined ? foundIndex : -1;
        } else {
          this.state.hoveredRowIndex = -1;
        }
      } else {
        this.state.hoveredRowIndex = -1;
      }
    }
  }

  handleMouseLeave() {
    this.state.pointer.x = 0;
    this.state.pointer.y = 0;
    this.state.hoveredRowIndex = -1;
    this.containerRect = null;
  }

  startLoop() {
    const loop = (time) => {
      this.update(time);
      this.draw();
      this.animationFrame = requestAnimationFrame(loop);
    };
    this.animationFrame = requestAnimationFrame(loop);
  }

  update(time) {
    if (!this.state.lastTime) {
      this.state.lastTime = time;
    }
    const delta = (time - this.state.lastTime) / 1000;
    this.state.lastTime = time;

    const speed = this.options.threeD?.reflection?.speed || 0.05;
    // Bolt: Replace slow modulo with subtraction in hot loop for better performance
    this.state.phase += delta * speed;
    if (this.state.phase >= 1) this.state.phase -= Math.floor(this.state.phase);

    this.state.continuousPhase += delta * speed;

    this.state.ambientPhase += delta * 0.5;
    if (this.state.ambientPhase >= 1)
      this.state.ambientPhase -= Math.floor(this.state.ambientPhase);

    // Smooth pointer
    const damping = 0.1;
    this.state.pointerSmoothed.x +=
      (this.state.pointer.x - this.state.pointerSmoothed.x) * damping;
    this.state.pointerSmoothed.y +=
      (this.state.pointer.y - this.state.pointerSmoothed.y) * damping;

    // Update particles
    const particles = this.state.energyParticles;
    for (let i = 0; i < particles.length; i++) {
      const p = particles[i];
      // Bolt: Replace slow modulo with subtraction in hot loop for better performance
      p.progress += delta * p.speed * 0.5;
      if (p.progress >= 1) p.progress -= Math.floor(p.progress);
    }
  }

  draw() {
    this.ctx.clearRect(0, 0, this.width, this.height);

    const radius = this.options.excludeHeader ? 0 : this._borderRadius || 8;

    // Draw effects
    this.drawAmbientGlow(radius);
    this.drawRowHoverEffect(); // New effect
    this.drawElectricTrails(radius);
    this.drawParticles(radius);
    this.drawReflection(radius);
  }

  drawRowHoverEffect() {
    if (
      !this.options.rowHoverEffect?.enabled ||
      this.state.hoveredRowIndex === -1 ||
      !this.rows
    ) {
      return;
    }

    const row = this.rows[this.state.hoveredRowIndex];
    if (!row) {
      return;
    }

    // Get the position of the row relative to the canvas
    // Bolt: Use pre-calculated row positions (row.top, row.height) instead of
    // getBoundingClientRect() and offsetHeight to prevent synchronous layout
    // thrashing during the requestAnimationFrame render loop.
    const rowTopRelativeToCanvas = row.top;
    const actualHeight = row.height;

    const settings = this.options.rowHoverEffect;

    this.ctx.save();
    // 'source-over' ensures the effect is drawn on top of the canvas content
    // We use transparency in the gradients to let the underlying content show through
    this.ctx.globalCompositeOperation = "source-over";

    // Calculate mouse X relative to canvas
    // pointer.x is -1 to 1. Convert back to pixels.
    const mouseX = ((this.state.pointer.x + 1) / 2) * this.width;
    const spotlightRadius = settings.spotlightRadius || 300;

    // Bolt: Cache radial gradients centered at (0, 0) to avoid re-instantiating objects on every 60fps frame.
    // We translate the canvas context to the target coordinates before drawing instead.
    if (!this._hoverSpotlightGradientCache) {
      this._hoverSpotlightGradientCache = this.ctx.createRadialGradient(
        0,
        0,
        0,
        0,
        0,
        spotlightRadius,
      );
      this._hoverSpotlightGradientCache.addColorStop(
        0,
        settings.color || "rgba(255, 255, 255, 0.05)",
      );
      this._hoverSpotlightGradientCache.addColorStop(1, "rgba(0, 0, 0, 0)");

      this._hoverBorderGradientCache = this.ctx.createRadialGradient(
        0,
        0,
        0,
        0,
        0,
        spotlightRadius * 0.8,
      );
      this._hoverBorderGradientCache.addColorStop(
        0,
        settings.borderColor || "rgba(255, 255, 255, 0.2)",
      );
      this._hoverBorderGradientCache.addColorStop(1, "rgba(0, 0, 0, 0)");
    }

    // Translate context to center of row hover spotlight
    this.ctx.translate(mouseX, rowTopRelativeToCanvas + actualHeight / 2);

    // 1. Spotlight Background
    this.ctx.fillStyle = this._hoverSpotlightGradientCache;
    this.ctx.fillRect(-mouseX, -actualHeight / 2, this.width, actualHeight);

    // 2. Border Reveal
    this.ctx.strokeStyle = this._hoverBorderGradientCache;
    this.ctx.lineWidth = 1;

    this.ctx.beginPath();
    this.ctx.moveTo(-mouseX, -actualHeight / 2);
    this.ctx.lineTo(this.width - mouseX, -actualHeight / 2);
    this.ctx.moveTo(-mouseX, actualHeight / 2);
    this.ctx.lineTo(this.width - mouseX, actualHeight / 2);
    this.ctx.stroke();

    this.ctx.restore();
  }

  // Helper to get point along rounded rectangle path
  // Helper to get point along rounded rectangle path
  getPointAtProgressZeroRadius(progress, out = { x: 0, y: 0 }) {
    const w = this.width;
    const h = this.height;
    const perimeter = 2 * w + 2 * h;
    const dist = progress * perimeter;
    if (dist <= w) {
      out.x = dist;
      out.y = 0;
      return out;
    }
    if (dist <= w + h) {
      out.x = w;
      out.y = dist - w;
      return out;
    }
    if (dist <= 2 * w + h) {
      out.x = w - (dist - (w + h));
      out.y = h;
      return out;
    }
    out.x = 0;
    out.y = h - (dist - (2 * w + h));
    return out;
  }

  getPointAtProgress(progress, radius, out = { x: 0, y: 0 }) {
    // Bolt: Replace slow modulo with subtraction in hot loop for better performance
    if (progress >= 1) progress -= Math.floor(progress);
    else if (progress < 0) progress += Math.ceil(-progress);

    if (radius === 0) {
      return this.getPointAtProgressZeroRadius(progress, out);
    }

    // Bolt: Inline mathematical calculations inside high-frequency
    // animation loops to eliminate Array.reduce and object generation GC pressure.
    const w = this.width;
    const h = this.height;
    const cornerLen = 0.5 * Math.PI * radius;
    const lineW = w - 2 * radius;
    const lineH = h - 2 * radius;
    const perimeter = 2 * lineW + 2 * lineH + 4 * cornerLen;

    let dist = progress * perimeter;

    if (dist <= lineW) {
      out.x = radius + dist;
      out.y = 0;
      return out;
    }
    dist -= lineW;

    if (dist <= cornerLen) {
      const angle = -Math.PI / 2 + (dist / cornerLen) * (Math.PI / 2);
      out.x = w - radius + Math.cos(angle) * radius;
      out.y = radius + Math.sin(angle) * radius;
      return out;
    }
    dist -= cornerLen;

    if (dist <= lineH) {
      out.x = w;
      out.y = radius + dist;
      return out;
    }
    dist -= lineH;

    if (dist <= cornerLen) {
      const angle = (dist / cornerLen) * (Math.PI / 2);
      out.x = w - radius + Math.cos(angle) * radius;
      out.y = h - radius + Math.sin(angle) * radius;
      return out;
    }
    dist -= cornerLen;

    if (dist <= lineW) {
      out.x = w - radius - dist;
      out.y = h;
      return out;
    }
    dist -= lineW;

    if (dist <= cornerLen) {
      const angle = Math.PI / 2 + (dist / cornerLen) * (Math.PI / 2);
      out.x = radius + Math.cos(angle) * radius;
      out.y = h - radius + Math.sin(angle) * radius;
      return out;
    }
    dist -= cornerLen;

    if (dist <= lineH) {
      out.x = 0;
      out.y = h - radius - dist;
      return out;
    }
    dist -= lineH;

    const angle = Math.PI + (dist / cornerLen) * (Math.PI / 2);
    out.x = radius + Math.cos(angle) * radius;
    out.y = radius + Math.sin(angle) * radius;
    return out;
  }

  // Better path follower that respects corners
  drawPath(ctx, radius) {
    ctx.beginPath();
    ctx.moveTo(radius, 0);
    ctx.lineTo(this.width - radius, 0);
    ctx.quadraticCurveTo(this.width, 0, this.width, radius);
    ctx.lineTo(this.width, this.height - radius);
    ctx.quadraticCurveTo(
      this.width,
      this.height,
      this.width - radius,
      this.height,
    );
    ctx.lineTo(radius, this.height);
    ctx.quadraticCurveTo(0, this.height, 0, this.height - radius);
    ctx.lineTo(0, radius);
    ctx.quadraticCurveTo(0, 0, radius, 0);
    ctx.closePath();
  }

  drawAmbientGlow(radius) {
    const glow = this.options.threeD?.ambientGlow || {};
    const pulse = 0.5 + 0.5 * Math.sin(this.state.ambientPhase * Math.PI * 2);

    this.ctx.save();
    this.drawPath(this.ctx, radius);
    this.ctx.clip();

    // Bolt: Cache Canvas gradients to eliminate heavy object allocations in the high-frequency render loop
    if (!this._ambientGradientCache) {
      this._ambientGradientCache = this.ctx.createLinearGradient(
        0,
        0,
        this.width,
        this.height,
      );
      this._ambientGradientCache.addColorStop(
        0,
        glow.innerColor || "rgba(118, 183, 229, 0.2)",
      );
      this._ambientGradientCache.addColorStop(1, "rgba(0,0,0,0)");
    }

    this.ctx.globalAlpha = (glow.innerOpacity || 0.15) * (0.8 + pulse * 0.2);
    this.ctx.fillStyle = this._ambientGradientCache;
    this.ctx.fill();
    this.ctx.restore();
  }

  drawElectricTrails(radius) {
    const electric = this.options.threeD?.electric || {};
    if (electric.enabled === false) {
      return;
    }

    // Bolt: Cache out objects to avoid creating object allocations in high
    // frequency animation loops, which puts heavy pressure on GC.
    this._p1 = this._p1 || { x: 0, y: 0 };
    this._p2 = this._p2 || { x: 0, y: 0 };

    if (!this._cachedActivePalette) {
      const colors = electric.colors || {};
      const rawPalette = [colors.primary, colors.secondary, colors.tertiary];
      let validPaletteCount = 0;
      for (let i = 0; i < rawPalette.length; i++) {
        if (rawPalette[i]) {
          validPaletteCount++;
        }
      }

      this._cachedActivePalette = rawPalette;
      this._cachedActivePaletteLength = validPaletteCount;

      if (validPaletteCount === 0) {
        this._cachedActivePalette = ["rgba(255, 255, 255, 0.4)"];
        this._cachedActivePaletteLength = 1;
      }
    }

    const activePalette = this._cachedActivePalette;
    const activePaletteLength = this._cachedActivePaletteLength;

    this.ctx.save();
    this.ctx.globalCompositeOperation = "screen"; // Softer than lighter
    this.ctx.lineCap = "round";
    this.ctx.lineWidth = electric.arcThickness || 1.5;

    const trailWidth = electric.width || 0.1;
    const segments = 30; // More segments for smoother gradient

    let paletteIdx = 0;
    for (let i = 0; i < activePalette.length; i++) {
      const color = activePalette[i];
      if (!color) {
        continue;
      }

      const offset =
        paletteIdx / activePaletteLength +
        this.state.continuousPhase * (electric.streakSpeedMultiplier || 1);
      // Bolt: Replace slow modulo with subtraction in hot loop for better performance
      let headProgress = offset;
      if (headProgress >= 1) headProgress -= Math.floor(headProgress);

      // Bolt: Hoist static canvas state assignments out of the inner render loop
      this.ctx.shadowColor = color;
      this.ctx.shadowBlur = 5;
      this.ctx.strokeStyle = color;

      const segmentStep = 1 / segments;
      const trailStep = trailWidth / segments;

      // Draw trail as segments
      for (let j = 0; j < segments; j++) {
        const segmentProgress = j * segmentStep; // 0 to 1
        const p1 = headProgress - j * trailStep;
        const p2 = headProgress - (j + 1) * trailStep;

        const point1 = this.getPointAtProgress(p1, radius, this._p1);
        const point2 = this.getPointAtProgress(p2, radius, this._p2);

        // Smooth fade out
        // Use a power curve for more elegant falloff
        const invProgress = 1 - segmentProgress;
        const opacity = invProgress * invProgress;

        this.ctx.globalAlpha = opacity;

        this.ctx.beginPath();
        this.ctx.moveTo(point1.x, point1.y);
        this.ctx.lineTo(point2.x, point2.y);
        this.ctx.stroke();
      }
      paletteIdx++;
    }

    this.ctx.restore();
  }

  drawParticles(radius) {
    const electric = this.options.threeD?.electric || {};
    if (electric.particlesEnabled === false) {
      return;
    }

    this.ctx.save();
    this.ctx.globalCompositeOperation = "screen";

    this._pParticle = this._pParticle || { x: 0, y: 0 };
    const particles = this.state.energyParticles;

    // Bolt: Hoist static canvas state assignments out of the inner render loop
    this.ctx.fillStyle = electric.colors?.primary || "rgba(255, 255, 255, 0.8)";
    this.ctx.shadowColor = this.ctx.fillStyle;

    for (let i = 0; i < particles.length; i++) {
      const p = particles[i];
      // Only draw path particles (those without 'life' property)
      if (p.life !== undefined) {
        continue;
      }

      const pos = this.getPointAtProgress(p.progress, radius, this._pParticle);

      // Add some jitter/offset
      const flicker =
        0.5 + 0.5 * Math.sin(this.state.phase * 10 + p.flickerOffset);

      this.ctx.shadowBlur = 3 * flicker; // Reduced blur

      this.ctx.beginPath();
      this.ctx.arc(pos.x, pos.y, p.size * flicker, 0, Math.PI * 2);
      this.ctx.fill();
    }

    this.ctx.restore();
  }

  drawReflection(radius) {
    const reflection = this.options.threeD?.reflection || {};
    const intensity = reflection.intensity || 0.5;
    const color = reflection.color || "rgba(255,255,255,1)";
    const width = reflection.width || 0.2;
    const fadeZone = reflection.fadeZone || 0.15; // Configurable fade zone

    this.ctx.save();
    this.ctx.globalCompositeOperation = "overlay";

    const phase = this.state.phase;

    // Calculate fade multiplier for smooth wrap
    // Fade out when approaching 1, fade in when starting from 0
    let fadeMultiplier = 1.0;
    if (phase > 1 - fadeZone) {
      fadeMultiplier = (1.0 - phase) / fadeZone;
    } else if (phase < fadeZone) {
      fadeMultiplier = phase / fadeZone;
    }

    this.ctx.globalAlpha = intensity * fadeMultiplier;

    this.drawPath(this.ctx, radius);
    this.ctx.clip();

    // Bolt: Cache Canvas gradients to eliminate heavy object allocations in the high-frequency render loop.
    // For moving gradients, we create them centered at (0, 0) and use ctx.translate() to position them,
    // avoiding the need to re-instantiate the gradient object on every frame.
    if (!this._reflectionGradientCache) {
      this._reflectionGradientCache = this.ctx.createLinearGradient(
        -width * this.width,
        -width * this.height,
        width * this.width,
        width * this.height,
      );
      this._reflectionGradientCache.addColorStop(0, "rgba(255,255,255,0)");
      this._reflectionGradientCache.addColorStop(0.5, color);
      this._reflectionGradientCache.addColorStop(1, "rgba(255,255,255,0)");
    }

    const centerX = phase * this.width;
    const centerY = phase * this.height;

    this.ctx.translate(centerX, centerY);
    this.ctx.fillStyle = this._reflectionGradientCache;
    this.ctx.fillRect(-centerX, -centerY, this.width, this.height);

    this.ctx.restore();
  }

  dispose() {
    if (this.animationFrame) {
      cancelAnimationFrame(this.animationFrame);
    }
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
    }
    if (this.canvas && this.canvas.parentNode) {
      this.canvas.parentNode.removeChild(this.canvas);
    }
  }
}
