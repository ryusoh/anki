(function () {
  if (typeof document === "undefined") {
    return;
  }
  const overlay = document.getElementById("terminalSweepOverlay");
  if (!overlay) {
    return;
  }
  const rootStyle = getComputedStyle(document.documentElement);
  const durationToken = rootStyle
    .getPropertyValue("--optic-sweep-duration")
    .trim();
  const duration = Number(durationToken.replace("s", "")) || 3;
  const refreshMs = Math.max(4000, (duration + 2) * 1000);

  const triggerSweep = () => {
    overlay.classList.remove("sweeping");
    void overlay.offsetWidth;
    overlay.classList.add("sweeping");
  };

  triggerSweep();
  setInterval(triggerSweep, refreshMs);
  window.addEventListener("focus", triggerSweep);
  window.addEventListener("click", triggerSweep);
})();
