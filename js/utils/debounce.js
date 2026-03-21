/**
 * Debounce utility
 * Returns a function, that, as long as it continues to be invoked, will not
 * be triggered. The function will be called after it stops being called for
 * N milliseconds.
 *
 * @param {Function} func The function to debounce
 * @param {number} wait The delay in milliseconds
 * @returns {Function} The debounced function
 */
export function debounce(func, wait) {
  if (typeof func !== "function") {
    throw new TypeError("Expected a function");
  }

  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func.apply(this, args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}
