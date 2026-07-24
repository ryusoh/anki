(function () {
  // Prevent desktop zoom (Ctrl+wheel / trackpad pinch, Ctrl+Plus/Minus/0)
  document.addEventListener(
    "wheel",
    function (e) {
      if (e.ctrlKey || e.metaKey) e.preventDefault();
    },
    { passive: false },
  );
  document.addEventListener("keydown", function (e) {
    if (
      (e.ctrlKey || e.metaKey) &&
      (e.key === "+" || e.key === "-" || e.key === "=" || e.key === "0")
    ) {
      e.preventDefault();
    }
  });
  // Prevent Safari gesture zoom
  document.addEventListener("gesturestart", function (e) {
    e.preventDefault();
  });
  document.addEventListener("gesturechange", function (e) {
    e.preventDefault();
  });

  let lastScrollTop = 0;

  window.addEventListener("scroll", function () {
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;

    // If scrolling up and at the very top of the page
    if (scrollTop < lastScrollTop && scrollTop === 0) {
      // Prevent default scroll behavior
      window.scrollTo(0, 0);
    }
    lastScrollTop = scrollTop;
  });

  // For touch devices, to prevent overscroll bounce when scrolling up from the top
  // This might interfere with native pull-to-refresh if not handled carefully.
  // Given the user wants to prevent scrolling up, this is a necessary evil.
  /** @type {number} */
  let startY = 0;

  document.addEventListener("touchstart", function (e) {
    startY = e.touches[0].clientY;
  });

  document.addEventListener(
    "touchmove",
    function (e) {
      const currentY = e.touches[0].clientY;
      const deltaY = currentY - startY;

      // If trying to scroll page up (swiping finger up)
      if (deltaY < 0) {
        e.preventDefault(); // Prevent default touchmove behavior to disallow moving the page up
      }
      // If at the top and pulling down (deltaY > 0), allow default behavior (pull-to-refresh)
      // No 'else if' or 'else' needed here, as we only prevent specific cases.
    },
    { passive: false },
  ); // Use passive: false to allow preventDefault
})();
