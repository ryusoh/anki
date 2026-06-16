(function () {
  if (window.glassEffectInstance) return; // Prevent double injection

  class GlassEffectBackground {
    constructor() {
      this.container = document.body;

      // Use injected config or defaults
      const config = window.glassEffectConfig || {};

      this.options = {
        enabled: config.enabled !== undefined ? config.enabled : true,
        excludeHeader: false,
        rowHoverEffect: { enabled: false },
        threeD: {
          ambientGlow: {
            innerColor: config.ambientGlowColor || "rgba(118, 183, 229, 0.4)",
            innerOpacity:
              config.ambientGlowOpacity !== undefined
                ? config.ambientGlowOpacity
                : 0.8,
          },
          electric: {
            enabled: false,
            particlesEnabled: false,
          },
          reflection: {
            speed:
              config.reflectionSpeed !== undefined
                ? config.reflectionSpeed
                : 0.03,
            intensity:
              config.reflectionIntensity !== undefined
                ? config.reflectionIntensity
                : 0.4,
            width:
              config.reflectionWidth !== undefined
                ? config.reflectionWidth
                : 0.3,
            color: config.reflectionColor || "rgba(255, 255, 255, 0.8)",
            fadeZone: 0.15,
          },
        },
      };

      if (!this.options.enabled) return;

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

      this.cachedLayout = null;
      this.lastLayoutUpdate = 0;
      this.init();
    }

    init() {
      this.canvas.id = "glass-effect-bg";
      this.canvas.style.position = "fixed";
      this.canvas.style.top = "0";
      this.canvas.style.left = "0";
      this.canvas.style.width = "100vw";
      this.canvas.style.height = "100vh";
      this.canvas.style.pointerEvents = "none";
      this.canvas.style.zIndex = "0";
      this.canvas.style.borderRadius = "0";

      // Elevate specific Anki elements above the canvas and strip opaque backgrounds
      const style = document.createElement("style");
      style.id = "glass-effect-style";
      style.textContent = `
          html { background-color: var(--canvas, var(--window-bg, #ffffff)) !important; }
          html.nightMode, body.nightMode { background-color: var(--canvas, var(--window-bg, #2d2d2d)) !important; }
          body { background-color: transparent !important; background-image: none !important; }
          
          /* Force Anki structural blocks to be transparent so the canvas shines through */
          #header, header, .toolbar, .nav, nav, #bottom, .bottom, #bottom-bar, #toolbar, #bottombar, .top-toolbar, .bottom-toolbar, #main, #qa {
              background-color: transparent !important;
              background-image: none !important;
              border: none !important;
              box-shadow: none !important;
          }
          
          /* Flatten the individual toolbar buttons so they don't look like disconnected islands */
          header button, .toolbar button, .nav button, nav button, #bottom button, .bottom button, .top-toolbar button, .bottom-toolbar button, .hitem {
              background-color: transparent !important;
              border-radius: 4px !important;
              border: none !important;
              box-shadow: none !important;
          }
          
          /* Add a subtle hover effect for the transparent buttons */
          header button:hover, .toolbar button:hover, .nav button:hover, nav button:hover, #bottom button:hover, .bottom button:hover, .hitem:hover {
              background-color: rgba(128, 128, 128, 0.2) !important;
          }
          
          /* Safely elevate Anki structural blocks over the canvas so the effect sits behind the text */
          table, #deck-table, #tree, #header, header, .nav, nav, #bottom, .bottom, #heatmap, .heatmap, svg.heatmap, .heatmap-container, #qa, .card, .reviewer, main, #app, .congrats, button, input, select, textarea, a, body > div:not(#glass-effect-bg) {
              position: relative !important; 
              z-index: 10 !important;
          }
      `;

      const appendCanvasAndStyle = () => {
        if (!document.getElementById("glass-effect-style"))
          document.head.appendChild(style);
        if (!document.getElementById("glass-effect-bg"))
          this.container.appendChild(this.canvas);
        if (
          this.width !== window.innerWidth ||
          this.height !== window.innerHeight
        )
          this.resize();

        // Aggressively strip Svelte opaque containers that might overwrite the above CSS via inline styles
        const roots = document.querySelectorAll(
          "body > *:not(#glass-effect-bg):not(script):not(style)",
        );
        roots.forEach((el) => {
          if (
            el.style &&
            (el.style.backgroundColor !== "transparent" ||
              el.style.backgroundImage !== "none")
          ) {
            el.style.setProperty(
              "background-color",
              "transparent",
              "important",
            );
            el.style.setProperty("background-image", "none", "important");
          }
        });
      };

      appendCanvasAndStyle();

      // Use MutationObserver instead of setInterval for better performance
      const observer = new MutationObserver((mutations) => {
        let shouldUpdate = false;
        for (const mutation of mutations) {
          if (
            mutation.type === "childList" ||
            (mutation.type === "attributes" &&
              mutation.attributeName === "style")
          ) {
            shouldUpdate = true;
            break;
          }
        }
        if (shouldUpdate) appendCanvasAndStyle();
      });
      observer.observe(document.body, {
        childList: true,
        attributes: true,
        subtree: false,
      });

      window.addEventListener("resize", () => this.resize());
      this.resize();

      document.addEventListener("mousemove", (e) => this.handleMouseMove(e));
      document.addEventListener("mouseleave", () => this.handleMouseLeave());

      this.startLoop();
    }

    resize() {
      this.width = window.innerWidth;
      this.height = window.innerHeight;
      const dpr = window.devicePixelRatio || 1;
      this.canvas.width = this.width * dpr;
      this.canvas.height = this.height * dpr;
      this.ctx.scale(dpr, dpr);
      this.cachedLayout = null; // Reset cache on resize
      this._ambientGradientCache = null;
      this._reflectionGradientCache = null;

      const isBottom =
        window.location.href.includes("bottom") ||
        document.getElementById("bottom");
      const isTop = window.location.href.includes("toolbar") && !isBottom;

      // Prevent writing 0 dimensions when Qt initializes WebViews in the background before showing them
      if (isTop && this.height > 0) {
        localStorage.setItem("anki_glass_h_top", this.height);
      } else if (!isBottom && this.height > 50) {
        localStorage.setItem("anki_glass_h_middle", this.height);
        if (this.width > 50) {
          localStorage.setItem("anki_glass_w_middle", this.width);
        }
      }
    }

    getSyncedLayout() {
      // Throttling localStorage access to once per 100ms
      const now = Date.now();
      if (this.cachedLayout && now - this.lastLayoutUpdate < 100) {
        return this.cachedLayout;
      }

      const isBottom =
        window.location.href.includes("bottom") ||
        document.getElementById("bottom");
      const isTop = window.location.href.includes("toolbar") && !isBottom;

      if (isBottom) {
        // The bottom pane acts as a completely independent glass panel
        this.cachedLayout = {
          totalWidth: this.width,
          totalHeight: this.height,
          offsetY: 0,
        };
      } else {
        // Unify the Top and Middle panes into a single virtual canvas
        let hTop = parseInt(localStorage.getItem("anki_glass_h_top"));
        if (isNaN(hTop) || hTop <= 0) hTop = 40;

        let hMid = parseInt(localStorage.getItem("anki_glass_h_middle"));
        // Fallback to local height or a safe minimum if the bridge is empty
        if (isNaN(hMid) || hMid <= 50) hMid = Math.max(this.height, 800);

        let wMid = parseInt(localStorage.getItem("anki_glass_w_middle"));
        if (isNaN(wMid) || wMid <= 50) wMid = Math.max(this.width, 1000);

        const totalWidth = wMid;
        const totalHeight = hTop + hMid;
        const offsetY = isTop ? 0 : hTop;

        this.cachedLayout = { totalWidth, totalHeight, offsetY };
      }

      this.lastLayoutUpdate = now;
      return this.cachedLayout;
    }

    handleMouseMove(e) {
      const x = e.clientX / this.width - 0.5;
      const y = e.clientY / this.height - 0.5;
      this.state.pointer.x = x * 2;
      this.state.pointer.y = y * 2;
    }

    handleMouseLeave() {
      this.state.pointer.x = 0;
      this.state.pointer.y = 0;
    }

    startLoop() {
      const loop = (time) => {
        this.update(time);
        this.draw();
        this.animationFrame = requestAnimationFrame(loop);
      };
      this.animationFrame = requestAnimationFrame(loop);
    }

    update(_time) {
      const globalTime = Date.now();
      if (!this.state.lastTime) this.state.lastTime = globalTime;
      const delta = (globalTime - this.state.lastTime) / 1000;
      this.state.lastTime = globalTime;

      const speed = this.options.threeD.reflection.speed || 0.05;
      this.state.phase = ((globalTime / 1000) * speed) % 1;
      this.state.continuousPhase += delta * speed;
      this.state.ambientPhase = ((globalTime / 1000) * 0.5) % 1;

      const damping = 0.1;
      this.state.pointerSmoothed.x +=
        (this.state.pointer.x - this.state.pointerSmoothed.x) * damping;
      this.state.pointerSmoothed.y +=
        (this.state.pointer.y - this.state.pointerSmoothed.y) * damping;
    }

    draw() {
      this.ctx.clearRect(0, 0, this.width, this.height);
      const radius = 0;
      const layout = this.getSyncedLayout();
      this.drawAmbientGlow(radius, layout);
      this.drawReflection(radius, layout);
    }

    drawPath(ctx, _radius) {
      ctx.beginPath();
      ctx.rect(0, 0, this.width, this.height);
      ctx.closePath();
    }

    drawAmbientGlow(radius, layout) {
      const glow = this.options.threeD.ambientGlow;
      const pulse = 0.5 + 0.5 * Math.sin(this.state.ambientPhase * Math.PI * 2);

      this.ctx.save();
      this.drawPath(this.ctx, radius);
      this.ctx.clip();

      // Bolt: Cache Canvas gradients to eliminate heavy object allocations in the high-frequency render loop
      if (!this._ambientGradientCache) {
        this._ambientGradientCache = this.ctx.createLinearGradient(
          0,
          -layout.offsetY,
          layout.totalWidth,
          layout.totalHeight - layout.offsetY,
        );

        // Distribute the blue glow more evenly across the diagonal
        const baseColor = glow.innerColor || "rgba(118, 183, 229, 0.5)";
        this._ambientGradientCache.addColorStop(0, baseColor);
        this._ambientGradientCache.addColorStop(
          0.6,
          "rgba(118, 183, 229, 0.25)",
        );
        this._ambientGradientCache.addColorStop(1, "rgba(118, 183, 229, 0.05)");
      }

      this.ctx.globalAlpha = (glow.innerOpacity || 0.8) * (0.8 + pulse * 0.2);
      this.ctx.fillStyle = this._ambientGradientCache;
      this.ctx.fill();
      this.ctx.restore();
    }
    drawReflection(radius, layout) {
      const reflection = this.options.threeD.reflection;
      const intensity = reflection.intensity || 0.5;
      const color = reflection.color || "rgba(255,255,255,1)";
      const width = reflection.width || 0.2;
      const fadeZone = reflection.fadeZone || 0.15;

      this.ctx.save();
      this.ctx.globalCompositeOperation = "overlay";

      const phase = this.state.phase;

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
          -width * layout.totalWidth,
          -width * layout.totalHeight,
          width * layout.totalWidth,
          width * layout.totalHeight,
        );
        this._reflectionGradientCache.addColorStop(0, "rgba(255,255,255,0)");
        this._reflectionGradientCache.addColorStop(0.5, color);
        this._reflectionGradientCache.addColorStop(1, "rgba(255,255,255,0)");
      }

      const centerX = phase * layout.totalWidth;
      const centerY = phase * layout.totalHeight - layout.offsetY;

      this.ctx.translate(centerX, centerY);
      this.ctx.fillStyle = this._reflectionGradientCache;
      this.ctx.fillRect(-centerX, -centerY, this.width, this.height);

      this.ctx.restore();
    }
  }

  // Delay init slightly to allow Svelte frameworks to settle
  setTimeout(() => {
    window.glassEffectInstance = new GlassEffectBackground();
  }, 50);
})();
