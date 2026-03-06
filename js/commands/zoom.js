/**
 * Zoom module for Anki terminal
 * Expands/collapses the terminal to take over the chart area.
 * Uses GSAP for smooth animations.
 */
/* global gsap */

const ANIMATION_DURATION = 0.35;
const EASING = "power2.inOut";

let zoomed = false;

/**
 * Gets the elements needed for zoom transitions.
 * @returns {{terminal: Element, chart: Element, terminalOutput: Element} | null}
 */
function getZoomElements() {
  const terminal = document.getElementById("terminal");
  const chart = document.getElementById("runningAmountSection");
  const terminalOutput = document.getElementById("terminalOutput");

  if (!terminal || !terminalOutput) {
    return null;
  }

  return { terminal, chart, terminalOutput };
}

/**
 * Calculates the target height for the terminal-output when zoomed.
 * @param {Element} terminal
 * @param {Element} chart
 * @param {Element} terminalOutput
 * @returns {number}
 */
function calculateZoomedOutputHeight(terminal, chart, terminalOutput) {
  const terminalRect = terminal.getBoundingClientRect();
  const terminalOutputRect = terminalOutput.getBoundingClientRect();

  let targetBottom;

  if (chart && !chart.classList.contains("is-hidden")) {
    // Expand to the bottom of the chart section
    targetBottom = chart.getBoundingClientRect().bottom;
  } else {
    // Default expansion (~420px for typical chart height + gap)
    const simulatedAdditionalHeight = 420;
    targetBottom = terminalRect.bottom + simulatedAdditionalHeight;
  }

  const otherTerminalElements = terminalRect.height - terminalOutputRect.height;
  const newTerminalHeight = targetBottom - terminalRect.top;
  const newOutputHeight = newTerminalHeight - otherTerminalElements;

  return Math.max(newOutputHeight, terminalOutputRect.height);
}

/**
 * Animates terminal zoom-in (expand terminal, fade out chart).
 */
function animateZoomIn(terminal, chart, terminalOutput) {
  return new Promise((resolve) => {
    const targetHeight = calculateZoomedOutputHeight(
      terminal,
      chart,
      terminalOutput,
    );

    // Store original height for restoration
    terminalOutput.dataset.originalHeight =
      terminalOutput.getBoundingClientRect().height;

    const timeline = gsap.timeline({
      onComplete: () => {
        terminal.classList.add("terminal-zoomed");
        if (chart) {
          chart.classList.add("chart-zoomed-out");
        }
        resolve();
      },
    });

    // Fade out chart
    if (chart && !chart.classList.contains("is-hidden")) {
      timeline.to(
        chart,
        {
          opacity: 0,
          scale: 0.98,
          duration: ANIMATION_DURATION * 0.8,
          ease: EASING,
        },
        0,
      );
    }

    // Expand terminal output
    timeline.to(
      terminalOutput,
      {
        height: targetHeight,
        duration: ANIMATION_DURATION,
        ease: EASING,
      },
      0,
    );
  });
}

/**
 * Animates terminal zoom-out (collapse terminal, fade in chart).
 */
function animateZoomOut(terminal, chart, terminalOutput) {
  return new Promise((resolve) => {
    const originalHeight =
      parseFloat(terminalOutput.dataset.originalHeight) || 270;

    const timeline = gsap.timeline({
      onComplete: () => {
        terminal.classList.remove("terminal-zoomed");
        if (chart) {
          chart.classList.remove("chart-zoomed-out");
        }
        // Clear inline styles set by GSAP
        gsap.set(terminalOutput, { clearProps: "height" });
        if (chart) {
          gsap.set(chart, { clearProps: "opacity,scale" });
        }
        resolve();
      },
    });

    // Collapse terminal output
    timeline.to(
      terminalOutput,
      {
        height: originalHeight,
        duration: ANIMATION_DURATION,
        ease: EASING,
      },
      0,
    );

    // Fade in chart
    if (chart && !chart.classList.contains("is-hidden")) {
      timeline.to(
        chart,
        {
          opacity: 1,
          scale: 1,
          duration: ANIMATION_DURATION * 0.8,
          ease: EASING,
        },
        ANIMATION_DURATION * 0.3,
      );
    }
  });
}

/**
 * Toggles the terminal zoom state.
 * @returns {Promise<{zoomed: boolean, message: string}>}
 */
export async function toggleZoom() {
  const elements = getZoomElements();
  if (!elements) {
    return {
      zoomed,
      message: "Unable to toggle zoom: terminal elements not found.",
    };
  }

  const { terminal, chart, terminalOutput } = elements;

  if (zoomed) {
    await animateZoomOut(terminal, chart, terminalOutput);
    zoomed = false;
    return { zoomed: false, message: "Terminal zoomed out." };
  }

  await animateZoomIn(terminal, chart, terminalOutput);
  zoomed = true;
  return { zoomed: true, message: "Terminal zoomed in." };
}

/**
 * Returns the current zoom state.
 * @returns {boolean}
 */
export function getZoomState() {
  return zoomed;
}
