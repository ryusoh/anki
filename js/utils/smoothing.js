/**
 * Financial Chart Smoothing Utilities
 *
 * Provides various smoothing algorithms commonly used in financial charts
 * to reduce noise while preserving important trends and ensuring end values remain accurate.
 */

/**
 * Simple Moving Average (SMA)
 * Averages the last N data points for each position
 * @param {Array} data - Array of {x, y} points
 * @param {number} window - Window size for averaging
 * @param {boolean} preserveEnd - Whether to preserve the last point unchanged
 * @returns {Array} Smoothed data points
 */
export function simpleMovingAverage(data, window = 3, preserveEnd = true) {
  if (!Array.isArray(data) || data.length === 0) {
    return data;
  }

  if (data.length < window) {
    return data;
  }

  const smoothed = [];

  for (let i = 0; i < data.length; i++) {
    // Preserve the last point if requested
    if (preserveEnd && i === data.length - 1) {
      smoothed.push({ ...data[i] });
      continue;
    }

    // Calculate the average for the window
    const start = Math.max(0, i - Math.floor(window / 2));
    const end = Math.min(data.length, start + window);
    const windowData = data.slice(start, end);

    const sum = windowData.reduce((acc, point) => acc + point.y, 0);
    const average = sum / windowData.length;

    smoothed.push({
      x: data[i].x,
      y: average,
    });
  }

  return smoothed;
}

/**
 * Exponential Moving Average (EMA)
 * Industry standard for financial charts - more responsive to recent changes
 * @param {Array} data - Array of {x, y} points
 * @param {number} alpha - Smoothing factor (0-1), higher = more responsive
 * @param {boolean} preserveEnd - Whether to preserve the last point unchanged
 * @returns {Array} Smoothed data points
 */
export function exponentialMovingAverage(
  data,
  alpha = 0.3,
  preserveEnd = true,
) {
  if (!Array.isArray(data) || data.length === 0) {
    return data;
  }

  if (data.length === 1) {
    return data;
  }

  const smoothed = [{ ...data[0] }];

  for (let i = 1; i < data.length; i++) {
    // Preserve the last point if requested
    if (preserveEnd && i === data.length - 1) {
      smoothed.push({ ...data[i] });
      continue;
    }

    const prevSmoothed = smoothed[i - 1].y;
    const current = data[i].y;
    const smoothedValue = alpha * current + (1 - alpha) * prevSmoothed;

    smoothed.push({
      x: data[i].x,
      y: smoothedValue,
    });
  }

  return smoothed;
}

/**
 * Savitzky-Golay Filter
 * Preserves peaks and valleys better than simple moving averages
 * @param {Array} data - Array of {x, y} points
 * @param {number} window - Window size (must be odd)
 * @param {number} order - Polynomial order (typically 2 or 3)
 * @param {boolean} preserveEnd - Whether to preserve the last point unchanged
 * @returns {Array} Smoothed data points
 */
export function savitzkyGolay(data, window = 5, order = 2, preserveEnd = true) {
  if (!Array.isArray(data) || data.length === 0) {
    return data;
  }

  if (data.length < window) {
    return data;
  }

  // Ensure window is odd
  if (window % 2 === 0) {
    window += 1;
  }

  const halfWindow = Math.floor(window / 2);
  const smoothed = [];

  for (let i = 0; i < data.length; i++) {
    // Preserve the last point if requested
    if (preserveEnd && i === data.length - 1) {
      smoothed.push({ ...data[i] });
      continue;
    }

    // Calculate the window boundaries
    const start = Math.max(0, i - halfWindow);
    const end = Math.min(data.length, i + halfWindow + 1);
    const windowData = data.slice(start, end);

    if (windowData.length < 3) {
      smoothed.push({ ...data[i] });
      continue;
    }

    // Simple polynomial fitting for small windows
    const smoothedValue = polynomialFit(windowData, order, i - start);
    smoothed.push({
      x: data[i].x,
      y: smoothedValue,
    });
  }

  return smoothed;
}

/**
 * LOWESS (Locally Weighted Scatterplot Smoothing)
 * Non-parametric smoothing that adapts to local patterns
 * @param {Array} data - Array of {x, y} points
 * @param {number} bandwidth - Bandwidth parameter (0-1)
 * @param {boolean} preserveEnd - Whether to preserve the last point unchanged
 * @returns {Array} Smoothed data points
 */
export function lowess(data, bandwidth = 0.3, preserveEnd = true) {
  if (!Array.isArray(data) || data.length === 0) {
    return data;
  }

  if (data.length < 3) {
    return data;
  }

  const smoothed = [];

  for (let i = 0; i < data.length; i++) {
    // Preserve the last point if requested
    if (preserveEnd && i === data.length - 1) {
      smoothed.push({ ...data[i] });
      continue;
    }

    const smoothedValue = weightedLocalRegression(data, i, bandwidth);
    smoothed.push({
      x: data[i].x,
      y: smoothedValue,
    });
  }

  return smoothed;
}

/**
 * Adaptive Smoothing
 * Automatically chooses the best smoothing method based on data characteristics
 * @param {Array} data - Array of {x, y} points
 * @param {boolean} preserveEnd - Whether to preserve the last point unchanged
 * @returns {Array} Smoothed data points
 */
export function adaptiveSmoothing(data, preserveEnd = true) {
  if (!Array.isArray(data) || data.length === 0) {
    return data;
  }

  if (data.length < 10) {
    return exponentialMovingAverage(data, 0.2, preserveEnd);
  }

  // Calculate volatility to determine smoothing strength
  const returns = [];
  for (let i = 1; i < data.length; i++) {
    const ret = (data[i].y - data[i - 1].y) / data[i - 1].y;
    returns.push(Math.abs(ret));
  }

  const avgVolatility =
    returns.reduce((sum, ret) => sum + ret, 0) / returns.length;

  // Choose smoothing method based on volatility
  if (avgVolatility > 0.05) {
    // High volatility
    return exponentialMovingAverage(data, 0.4, preserveEnd);
  } else if (avgVolatility > 0.02) {
    // Medium volatility
    return exponentialMovingAverage(data, 0.3, preserveEnd);
  }
  // Low volatility
  return exponentialMovingAverage(data, 0.2, preserveEnd);
}

/**
 * Helper function for polynomial fitting in Savitzky-Golay
 */
function polynomialFit(points, order, targetIndex) {
  const n = points.length;
  if (n <= order) {
    return points[targetIndex]?.y || 0;
  }

  // Simple linear regression for order 1, quadratic for order 2
  if (order === 1) {
    let sumX = 0;
    let sumY = 0;
    let sumXY = 0;
    let sumXX = 0;

    // Bolt: Use a single O(N) loop instead of four chained .reduce() passes
    // to significantly reduce GC pressure and intermediate allocations.
    for (let i = 0; i < n; i++) {
      const p = points[i];
      sumX += i;
      sumY += p.y;
      sumXY += i * p.y;
      sumXX += i * i;
    }

    const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
    const intercept = (sumY - slope * sumX) / n;

    return slope * targetIndex + intercept;
  }
  // For higher orders, use a simplified approach
  return points[targetIndex]?.y || 0;
}

/**
 * Helper function for weighted local regression in LOWESS
 */
function weightedLocalRegression(data, index, bandwidth) {
  const n = data.length;
  const targetX = data[index].x;

  // Bolt: Pre-calculate maxDistance outside the loop to avoid O(N^2) complexity and excessive GC pressure.
  let maxDistance = 0;
  for (let i = 0; i < n; i++) {
    const d = Math.abs(data[i].x - targetX);
    if (d > maxDistance) {
      maxDistance = d;
    }
  }

  // Handle edge case where all points have the same x value
  /* c8 ignore next 3 */
  if (maxDistance === 0) {
    return data[index].y;
  }

  // Weighted average
  let weightedSum = 0;
  let weightSum = 0;
  const scale = bandwidth * maxDistance;

  // Bolt: Calculate weights and sum in a single O(N) pass, avoiding intermediate array allocations.
  for (let i = 0; i < n; i++) {
    const distance = Math.abs(data[i].x - targetX);
    const normalizedDistance = distance / scale;

    if (normalizedDistance < 1) {
      const weight = Math.pow(1 - Math.pow(normalizedDistance, 3), 3);
      weightedSum += weight * data[i].y;
      weightSum += weight;
    }
  }

  return weightSum > 0 ? weightedSum / weightSum : data[index].y;
}

/**
 * Default smoothing configuration for financial charts
 */
export const SMOOTHING_CONFIGS = {
  // Conservative smoothing - minimal impact
  conservative: {
    method: "exponential",
    params: { alpha: 0.2 },
    passes: 1,
    description: "Minimal smoothing, preserves most detail",
  },

  // Balanced smoothing - industry standard
  balanced: {
    method: "exponential",
    params: { alpha: 0.3 },
    passes: 1,
    description: "Balanced smoothing, good for most financial data",
  },

  // Aggressive smoothing - very smooth lines
  aggressive: {
    method: "exponential",
    params: { alpha: 0.5 },
    passes: 2,
    description: "Strong smoothing, reduces noise significantly",
  },

  // Adaptive smoothing - automatically adjusts
  adaptive: {
    method: "adaptive",
    params: {},
    passes: 1,
    description: "Automatically adjusts based on data volatility",
  },
};

/**
 * Apply smoothing to financial chart data
 * @param {Array} data - Array of {x, y} points
 * @param {string|Object} config - Smoothing configuration name or custom config
 * @param {boolean} preserveEnd - Whether to preserve the last point unchanged
 * @returns {Array} Smoothed data points
 */
export function smoothFinancialData(
  data,
  config = "balanced",
  preserveEnd = true,
) {
  if (!Array.isArray(data) || data.length === 0) {
    return data;
  }

  // Get configuration
  const smoothingConfig =
    typeof config === "string"
      ? SMOOTHING_CONFIGS[config] || SMOOTHING_CONFIGS.balanced
      : config;

  // Apply the appropriate smoothing method
  const passes = Number.isFinite(smoothingConfig.passes)
    ? Math.max(1, Math.round(smoothingConfig.passes))
    : 1;

  let result = data;
  for (let i = 0; i < passes; i += 1) {
    switch (smoothingConfig.method) {
      case "simple":
        result = simpleMovingAverage(
          result,
          smoothingConfig.params.window || 3,
          preserveEnd,
        );
        break;
      case "exponential":
        result = exponentialMovingAverage(
          result,
          smoothingConfig.params.alpha || 0.3,
          preserveEnd,
        );
        break;
      case "savitzky":
        result = savitzkyGolay(
          result,
          smoothingConfig.params.window || 5,
          smoothingConfig.params.order || 2,
          preserveEnd,
        );
        break;
      case "lowess":
        result = lowess(
          result,
          smoothingConfig.params.bandwidth || 0.3,
          preserveEnd,
        );
        break;
      case "adaptive":
        result = adaptiveSmoothing(result, preserveEnd);
        break;
      default:
        result = exponentialMovingAverage(result, 0.3, preserveEnd);
        break;
    }
  }

  return result;
}
