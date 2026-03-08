(function () {
  if (window.glassEffectInstance) return; // Prevent double injection

  class GlassEffectBackground {
    constructor() {
      this.canvas = document.createElement("canvas");
      this.ctx = this.canvas.getContext("2d");
      this.state = {
        phase: 0,
        continuousPhase: 0,
        ambientPhase: 0,
        lastTime: 0,
        energyParticles: [],
        pointer: { x: 0, y: 0 },
        pointerSmoothed: { x: 0, y: 0 },
      };

      this.options = {
        threeD: {
          ambientGlow: {
            innerColor: "rgba(118, 183, 229, 0.6)",
            innerOpacity: 0.8,
          },
          electric: {
            enabled: true,
            arcCount: 4,
            arcThickness: 1.5,
            streakSpeedMultiplier: 1,
            width: 0.15,
            colors: {
              primary: "rgba(118, 183, 229, 0.8)",
              secondary: "rgba(180, 220, 255, 0.5)",
              tertiary: "rgba(255, 255, 255, 0.3)",
            },
          },
          reflection: {
            speed: 0.03,
            intensity: 0.3,
            width: 0.3,
            color: "rgba(255,255,255,0.8)",
          },
        },
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
      // EXTREMELY IMPORTANT: Let clicks pass through to Anki UI!
      this.canvas.style.pointerEvents = "none";
      // Render above the background box but below elevated content
      this.canvas.style.zIndex = "0";

      // Elevate specific Anki elements and common add-ons (like Heatmap) above the canvas
      const style = document.createElement("style");
      style.textContent = `
              html { 
                  background-color: var(--canvas, var(--window-bg, #ffffff)) !important; 
              }
              html.nightMode, body.nightMode {
                  background-color: var(--canvas, var(--window-bg, #2d2d2d)) !important;
              }
              body { 
                  background-color: transparent !important; 
                  background-image: none !important;
              }
              
              /* Strip backgrounds from toolbars so the glass effect shows through */
              #header, header, .toolbar, .nav, nav, 
              #bottom, .bottom, #bottom-bar,
              #toolbar, #bottombar, .top-toolbar, .bottom-toolbar {
                  background-color: transparent !important;
                  background-image: none !important;
              }
              
              /* Elevate Anki's main content and common add-ons above the glass effect */
              table, #deck-table, #tree, 
              #header, header, .nav, nav, 
              #bottom, .bottom,
              #heatmap, .heatmap, svg.heatmap, .heatmap-container,
              #qa, .card, .reviewer,
              button, input, select, textarea, a {
                  position: relative !important;
                  z-index: 10 !important;
              }
          `;
      document.head.appendChild(style);

      document.body.appendChild(this.canvas);

      this.initParticles();

      window.addEventListener("resize", () => this.resize());
      this.resize();

      document.addEventListener("mousemove", (e) => this.handleMouseMove(e));
      document.addEventListener("mouseleave", () => this.handleMouseLeave());

      this.startLoop();
    }

    initParticles() {
      const electric = this.options.threeD.electric;
      const count = Math.max(12, (electric.arcCount || 3) * 8);
      this.state.energyParticles = Array.from({ length: count }, () => ({
        progress: Math.random(),
        speed: 0.2 + Math.random() * 0.5,
        size: 1.2 + Math.random() * 1.6,
        flickerOffset: Math.random() * Math.PI * 2,
        offset: (Math.random() - 0.5) * 10,
      }));
    }

    resize() {
      this.width = window.innerWidth;
      this.height = window.innerHeight;
      const dpr = window.devicePixelRatio || 1;
      this.canvas.width = this.width * dpr;
      this.canvas.height = this.height * dpr;
      this.ctx.scale(dpr, dpr);
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

    update(time) {
      // Use a global timer (Date.now()) so all separate webviews are perfectly synchronized in time
      const globalTime = Date.now();

      if (!this.state.lastTime) this.state.lastTime = globalTime;
      const delta = (globalTime - this.state.lastTime) / 1000;
      this.state.lastTime = globalTime;

      const speed = this.options.threeD.reflection.speed || 0.05;
      // Force phase based absolutely on time rather than accumulating delta to avoid drift across webviews
      this.state.phase = ((globalTime / 1000) * speed) % 1;
      this.state.continuousPhase += delta * speed;
      this.state.ambientPhase = ((globalTime / 1000) * 0.5) % 1;

      const damping = 0.1;
      this.state.pointerSmoothed.x +=
        (this.state.pointer.x - this.state.pointerSmoothed.x) * damping;
      this.state.pointerSmoothed.y +=
        (this.state.pointer.y - this.state.pointerSmoothed.y) * damping;

      this.state.energyParticles.forEach((p) => {
        p.progress = (p.progress + delta * p.speed * 0.5) % 1;
      });
    }

    draw() {
      this.ctx.clearRect(0, 0, this.width, this.height);
      const radius = 0; // Full bleed background, no rounded corners needed
      this.drawAmbientGlow(radius);
      this.drawReflection(radius);
    }

    getPointAtProgress(progress, radius) {
      progress = progress % 1;
      if (progress < 0) progress += 1;

      const w = this.width;
      const h = this.height;

      const perimeter = 2 * w + 2 * h;
      const dist = progress * perimeter;
      if (dist <= w) return { x: dist, y: 0 };
      if (dist <= w + h) return { x: w, y: dist - w };
      if (dist <= 2 * w + h) return { x: w - (dist - (w + h)), y: h };
      return { x: 0, y: h - (dist - (2 * w + h)) };
    }

    drawPath(ctx, radius) {
      ctx.beginPath();
      ctx.rect(0, 0, this.width, this.height);
      ctx.closePath();
    }

    drawAmbientGlow(radius) {
      const glow = this.options.threeD.ambientGlow;
      const pulse = 0.5 + 0.5 * Math.sin(this.state.ambientPhase * Math.PI * 2);

      this.ctx.save();
      this.drawPath(this.ctx, radius);
      this.ctx.clip();

      // Anchor the gradient to the absolute monitor space to unify the separate panes
      const winX = window.screenX || 0;
      const winY = window.screenY || 0;
      // Provide a fallback window size if screen width/height is unavailable
      const monitorW = window.screen?.width || 1920;
      const monitorH = window.screen?.height || 1080;

      const gradient = this.ctx.createLinearGradient(
        -winX,
        -winY,
        monitorW - winX,
        monitorH - winY,
      );
      gradient.addColorStop(0, glow.innerColor || "rgba(118, 183, 229, 0.2)");
      gradient.addColorStop(1, "rgba(0,0,0,0)");

      this.ctx.globalAlpha = (glow.innerOpacity || 0.15) * (0.8 + pulse * 0.2);
      this.ctx.fillStyle = gradient;
      this.ctx.fill();
      this.ctx.restore();
    }

    drawElectricTrails(radius) {
      const electric = this.options.threeD.electric;
      const palette = [
        electric.colors.primary,
        electric.colors.secondary,
        electric.colors.tertiary,
      ].filter(Boolean);

      this.ctx.save();
      this.ctx.globalCompositeOperation = "screen";
      this.ctx.lineCap = "round";
      this.ctx.lineWidth = electric.arcThickness || 1.5;

      const trailWidth = electric.width || 0.1;
      const segments = 30;

      palette.forEach((color, i) => {
        const offset =
          i / palette.length +
          this.state.continuousPhase * (electric.streakSpeedMultiplier || 1);
        const headProgress = offset % 1;

        this.ctx.shadowColor = color;
        this.ctx.shadowBlur = 5;

        for (let j = 0; j < segments; j++) {
          const segmentProgress = j / segments;
          const p1 = headProgress - segmentProgress * trailWidth;
          const p2 = headProgress - ((j + 1) / segments) * trailWidth;

          const point1 = this.getPointAtProgress(p1, radius);
          const point2 = this.getPointAtProgress(p2, radius);

          const opacity = Math.pow(1 - segmentProgress, 2);

          this.ctx.globalAlpha = opacity;
          this.ctx.strokeStyle = color;

          this.ctx.beginPath();
          this.ctx.moveTo(point1.x, point1.y);
          this.ctx.lineTo(point2.x, point2.y);
          this.ctx.stroke();
        }
      });

      this.ctx.restore();
    }

    drawParticles(radius) {
      const electric = this.options.threeD.electric;

      this.ctx.save();
      this.ctx.globalCompositeOperation = "screen";

      this.state.energyParticles.forEach((p) => {
        const pos = this.getPointAtProgress(p.progress, radius);
        const flicker =
          0.5 + 0.5 * Math.sin(this.state.phase * 10 + p.flickerOffset);

        this.ctx.fillStyle = electric.colors.primary;
        this.ctx.shadowColor = this.ctx.fillStyle;
        this.ctx.shadowBlur = 3 * flicker;

        this.ctx.beginPath();
        this.ctx.arc(pos.x, pos.y, p.size * flicker, 0, Math.PI * 2);
        this.ctx.fill();
      });

      this.ctx.restore();
    }

    drawReflection(radius) {
      const reflection = this.options.threeD.reflection;
      const intensity = reflection.intensity || 0.5;
      const color = reflection.color || "rgba(255,255,255,1)";
      const width = reflection.width || 0.2;
      const fadeZone = 0.15;

      this.ctx.save();
      this.ctx.globalCompositeOperation = "overlay";

      // Anchor the reflection gradient to absolute monitor space as well
      const winX = window.screenX || 0;
      const winY = window.screenY || 0;
      const monitorW = window.screen?.width || 1920;
      const monitorH = window.screen?.height || 1080;

      const gradient = this.ctx.createLinearGradient(
        -winX,
        -winY,
        monitorW - winX,
        monitorH - winY,
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

  // Initialize once the DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      window.glassEffectInstance = new GlassEffectBackground();
    });
  } else {
    window.glassEffectInstance = new GlassEffectBackground();
  }
})();
