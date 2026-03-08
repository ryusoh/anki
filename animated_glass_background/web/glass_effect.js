(function() {
  if (window.glassEffectInstance) return; // Prevent double injection

  class GlassEffectBackground {
    constructor() {
      this.container = document.body;
      
      this.options = {
        enabled: true,
        excludeHeader: false,
        rowHoverEffect: { enabled: false },
        threeD: {
          ambientGlow: {
            innerColor: "rgba(118, 183, 229, 0.4)",
            innerOpacity: 0.8
          },
          electric: {
            enabled: false,
            particlesEnabled: false
          },
          reflection: {
            speed: 0.03,
            intensity: 0.4,
            width: 0.3,
            color: "rgba(255,255,255,0.8)",
            fadeZone: 0.15
          }
        }
      };

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
          
          /* Safely elevate Anki structural blocks over the canvas so the effect sits behind the text */
          table, #deck-table, #tree, #header, header, .nav, nav, #bottom, .bottom, #heatmap, .heatmap, svg.heatmap, .heatmap-container, #qa, .card, .reviewer, main, #app, .congrats, button, input, select, textarea, a, body > div:not(#glass-effect-bg) {
              position: relative !important; 
              z-index: 10 !important;
          }
      `;
      
      const appendCanvasAndStyle = () => {
          if (!document.getElementById("glass-effect-style")) document.head.appendChild(style);
          if (!document.getElementById("glass-effect-bg")) this.container.appendChild(this.canvas);
          if (this.width !== window.innerWidth || this.height !== window.innerHeight) this.resize();
          
          // Aggressively strip Svelte opaque containers that might overwrite the above CSS via inline styles
          const roots = document.querySelectorAll('body > *:not(#glass-effect-bg):not(script):not(style)');
          roots.forEach(el => {
              if (el.style) {
                  el.style.setProperty('background-color', 'transparent', 'important');
                  el.style.setProperty('background-image', 'none', 'important');
              }
          });
      };

      appendCanvasAndStyle();
      // Ensure Svelte doesn't destroy the canvas during hydration
      setInterval(appendCanvasAndStyle, 250);

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

        const isBottom = window.location.href.includes("bottom") || document.getElementById("bottom");
        const isTop = window.location.href.includes("toolbar") && !isBottom;

        if (isTop) {
            localStorage.setItem('anki_glass_h_top', this.height);
        } else if (!isBottom) {
            localStorage.setItem('anki_glass_h_middle', this.height);
            localStorage.setItem('anki_glass_w_middle', this.width);
        }
    }

    getSyncedLayout() {
        const isBottom = window.location.href.includes("bottom") || document.getElementById("bottom");
        const isTop = window.location.href.includes("toolbar") && !isBottom;

        if (isBottom) {
            // The bottom pane acts as a completely independent glass panel
            return { totalWidth: this.width, totalHeight: this.height, offsetY: 0 };
        }

        // Unify the Top and Middle panes into a single virtual canvas
        const hTop = parseInt(localStorage.getItem('anki_glass_h_top') || 40);
        const hMid = parseInt(localStorage.getItem('anki_glass_h_middle') || 800);
        const wMid = parseInt(localStorage.getItem('anki_glass_w_middle') || this.width);

        const totalWidth = wMid;
        const totalHeight = hTop + hMid;
        const offsetY = isTop ? 0 : hTop;

        return { totalWidth, totalHeight, offsetY };
    }

    handleMouseMove(e) {      const x = e.clientX / this.width - 0.5;
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

    update(time) {
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

    drawPath(ctx, radius) {
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

      const gradient = this.ctx.createLinearGradient(
        0,
        -layout.offsetY,
        layout.totalWidth,
        layout.totalHeight - layout.offsetY
      );
      gradient.addColorStop(0, glow.innerColor || "rgba(118, 183, 229, 0.4)");
      gradient.addColorStop(1, "rgba(0,0,0,0)");

      this.ctx.globalAlpha = (glow.innerOpacity || 0.8) * (0.8 + pulse * 0.2);
      this.ctx.fillStyle = gradient;
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

      const gradient = this.ctx.createLinearGradient(
        0,
        -layout.offsetY,
        layout.totalWidth,
        layout.totalHeight - layout.offsetY
      );

      const phase = this.state.phase;
      const start = phase - width;
      const end = phase + width;

      let fadeMultiplier = 1.0;
      if (phase > 1 - fadeZone) {
        fadeMultiplier = (1.0 - phase) / fadeZone;
      } else if (phase < fadeZone) {
        fadeMultiplier = phase / fadeZone;
      }

      this.ctx.globalAlpha = intensity * fadeMultiplier;

      gradient.addColorStop(Math.max(0, start), "rgba(255,255,255,0)");
      gradient.addColorStop(Math.max(0, Math.min(1, phase)), color);
      gradient.addColorStop(Math.min(1, end), "rgba(255,255,255,0)");

      this.ctx.fillStyle = gradient;
      this.drawPath(this.ctx, radius);
      this.ctx.fill();

      this.ctx.restore();
    }
  }

  // Delay init slightly to allow Svelte frameworks to settle
  setTimeout(() => {
      window.glassEffectInstance = new GlassEffectBackground();
  }, 50);

})();