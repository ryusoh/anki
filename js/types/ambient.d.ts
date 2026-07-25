/**
 * @typedef {Object} AmbientConfig
 * @property {boolean} [enabled]
 * @property {number} [minWidth]
 * @property {number} [maxParticles]
 * @property {number} [densityDivisor]
 * @property {{min: number, max: number}} [radius]
 * @property {{min: number, max: number}} [alpha]
 * @property {number} [speed]
 * @property {number} [zIndex]
 * @property {string} [blend]
 * @property {boolean} [respectReducedMotion]
 */

declare global {
  interface Window {
    AMBIENT_CONFIG?: AmbientConfig;
  }
}

export {};
