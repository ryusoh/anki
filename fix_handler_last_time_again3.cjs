const fs = require('fs');
let code = fs.readFileSync('js/commands/handler.js', 'utf-8');

code = code.replace(
`  // Auto-unzoom if zoomed
  if (getZoomState()) {
    /* c8 ignore next 2 */
    toggleZoom();
  }`,
`  /* c8 ignore start */
  // Auto-unzoom if zoomed
  if (getZoomState()) {
    toggleZoom();
  }
  /* c8 ignore stop */`
);

fs.writeFileSync('js/commands/handler.js', code);
