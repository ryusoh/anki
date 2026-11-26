# Background CPU Governor Config

- **enabled**: (true/false) Enable or disable WebView throttling when Anki is inactive.
- **pause_on_app_deactivate**: (true/false) Pause WebView animations automatically when Anki loses application focus.
- **pause_css_animations**: (true/false) Pause CSS animations and transitions while Anki is in the background.
- **pause_raf**: (true/false) Gate `requestAnimationFrame` callbacks while Anki is inactive and flush them when Anki regains focus.
- **warn_software_driver**: (true/false) Surface a status warning when QtWebEngine runs with GPU compositing disabled (`--disable-gpu-compositing` / software video driver).
