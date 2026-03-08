(function() {
  if (document.getElementById('glass-effect-style')) return;

  const style = document.createElement("style");
  style.id = "glass-effect-style";
  
  // We use pure CSS with background-attachment: fixed. 
  // This perfectly syncs the reflection sweep across all separate Anki WebViews natively!
  style.textContent = `
      /* Keyframe for the horizontal glass reflection sweep */
      @keyframes glassSweep {
          0% { background-position: -150vw 0, 0 0; }
          100% { background-position: 150vw 0, 0 0; }
      }

      html { 
          background-color: var(--canvas, var(--window-bg, #2d2d2d)) !important; 
          background-image: 
              /* 1. The sweeping glass reflection (horizontal bar) */
              linear-gradient(90deg, 
                  rgba(255,255,255,0) 0%, 
                  rgba(255,255,255,0) 45%, 
                  rgba(255,255,255,0.15) 48%, 
                  rgba(255,255,255,0.4) 50%, 
                  rgba(255,255,255,0.15) 52%, 
                  rgba(255,255,255,0) 55%,
                  rgba(255,255,255,0) 100%
              ),
              /* 2. The ambient blue glow from the top left */
              radial-gradient(circle at 0% 0%, rgba(118, 183, 229, 0.4) 0%, rgba(0,0,0,0) 70%) !important;
          
          /* The sweep size is stretched so it moves smoothly across the screen */
          background-size: 200vw 100vh, 100vw 100vh !important;
          
          /* Fixed attachment anchors the background to the Qt Window instead of the local WebView */
          background-attachment: fixed, fixed !important;
          background-repeat: no-repeat, no-repeat !important;
          
          /* 6 second continuous sweep */
          animation: glassSweep 6s infinite linear !important;
      }
      
      /* Light mode fallback tweaks */
      html:not(.nightMode) {
          background-color: var(--canvas, var(--window-bg, #f5f5f5)) !important;
          background-image: 
              linear-gradient(90deg, 
                  rgba(255,255,255,0) 0%, 
                  rgba(255,255,255,0) 45%, 
                  rgba(255,255,255,0.4) 48%, 
                  rgba(255,255,255,0.8) 50%, 
                  rgba(255,255,255,0.4) 52%, 
                  rgba(255,255,255,0) 55%,
                  rgba(255,255,255,0) 100%
              ),
              radial-gradient(circle at 0% 0%, rgba(118, 183, 229, 0.3) 0%, rgba(0,0,0,0) 70%) !important;
      }

      /* Make sure all body layers are fully transparent so the html background shines through */
      body, #app, main, .svelte-container, .deck-finished, .congrats { 
          background-color: transparent !important; 
          background-image: none !important;
      }
      
      /* Strip solid backgrounds from the toolbars so they look like one continuous window */
      #header, header, .toolbar, .nav, nav, 
      #bottom, .bottom, #bottom-bar,
      #toolbar, #bottombar, .top-toolbar, .bottom-toolbar {
          background-color: transparent !important;
          background-image: none !important;
          border: none !important;
          box-shadow: none !important;
      }
      
      /* Remove border on main DeckBrowser / Reviewer containers */
      #main, #qa {
          border: none !important;
          background-color: transparent !important;
      }
  `;
  document.head.appendChild(style);

  // Svelte pages aggressively wipe the body on load, but they rarely wipe the head.
  // We periodically ensure our style block survives any deep SPA re-renders.
  setInterval(() => {
      if (!document.getElementById('glass-effect-style')) {
          document.head.appendChild(style);
      }
      // Force Svelte body layers transparent via inline styles just in case CSS-in-JS overrides us
      const roots = document.querySelectorAll('body, body > *:not(script):not(style)');
      roots.forEach(el => {
          if (el.style) {
              el.style.setProperty('background-color', 'transparent', 'important');
              el.style.setProperty('background-image', 'none', 'important');
          }
      });
  }, 250);

})();