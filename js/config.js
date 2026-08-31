export const DATA_PATHS = {
  customStats: "/data/anki/custom_stats_data.json",
  reviewStats: "/data/anki/review_stats_data.json",
  graphData: "/graph/graph_data.json",
};

export const PIE_CHART_GLASS_EFFECT = {
  enabled: true,
  opacity: 0.75, // Default fallback; overridden via responsiveOpacity at runtime
  responsiveOpacity: {
    desktop: 0.4,
    mobile: 0.4,
  },
  // All border settings in one place
  borders: {
    // Slice separation borders (between pie slices)
    sliceWidth: 1, // Thinner, more delicate borders
    sliceColor: "rgba(0, 0, 0, 0.1)", // Subtle white borders like iOS
    // Outer/inner arc borders (for customArcBordersPlugin)
    arcWidth: 1.5, // Thinner arc borders
    arcColor: "rgba(0, 0, 0, 0.15)", // Very subtle white outline
    // Border style
    style: "solid", // Clean, crisp lines
  },
  // Enhanced liquid glass properties
  liquidGlass: {
    // Add subtle gradient overlay for depth
    gradientOverlay: true,
    gradientStart: "rgba(255, 255, 255, 0.3)", // Top highlight
    gradientEnd: "rgba(255, 255, 255, 0.02)", // Bottom subtle
    // Saturation boost for more vibrant liquid look
    saturationBoost: 1.4, // 40% more saturated colors
    // Optical distortion for glass refraction effect
    distortion: {
      enabled: true,
      strength: 2, // Barrel distortion coefficient (positive = barrel, negative = pincushion)
      type: "barrel", // 'barrel' for outward bulge effect
      smoothEdges: true, // Smooth distortion falloff at edges
      quality: "medium", // 'low', 'medium', 'high' - affects performance vs quality
      overlayColors: {
        inner: "rgba(0, 229, 255, 0.45)",
        middle: "rgba(38, 198, 218, 0.32)",
        outer: "rgba(77, 182, 172, 0.22)",
      },
      // Animation and movement settings
      animation: {
        speed: 0.002,
        movement: {
          hotspotRange: 1.2,
          colorBlockRange: 0.8,
          xFrequency: 1.3,
          yFrequency: 1.3,
        },
        colors: {
          shiftIntensity: 1,
          phaseOffset: 5,
        },
      },
    },
  },
  threeD: {
    enabled: true,
    depth: {
      desktop: 5,
      mobile: 5,
    },
    squash: 1,
    light: {
      azimuthDeg: -45,
      elevationDeg: 62,
    },
    sideOpacity: {
      top: 0.55,
      bottom: 0.18,
    },
    rimHighlight: {
      width: 1.4,
      opacity: 0.38,
    },
    topHighlight: {
      intensity: 0.45,
      radiusFraction: 0.82,
    },
    reflection: {
      speed: 0.1,
      width: 0.22,
      intensity: 0.52,
    },
    shadow: {
      scaleX: 1.12,
      scaleY: 0.46,
      offsetYPx: 16,
      blur: 34,
      opacity: 0.28,
    },
    parallax: {
      maxOffsetPx: 8,
      damping: 0.18,
    },
    electric: {
      intensity: 0.5,
      width: 0.15,
      colors: {
        primary: "rgba(250, 250, 250, 0.6)",
        secondary: "rgba(250, 250, 250, 0.4)",
        tertiary: "rgba(250, 250, 250, 0.2)",
        quaternary: "rgba(250, 250, 250, 0.1)",
      },
      arcCount: 3,
      arcThickness: 2.5,
      particlesEnabled: false,
      particleColors: null,
      streakSpeedMultiplier: 2.5,
      particleSpeedMultiplier: 0.5,
    },
    ambientGlow: {
      innerOpacity: 0.15,
      outerOpacity: 0.05,
      pulseSpeed: 0.6,
      innerColor: "rgba(118, 183, 229, 1)",
      outerColor: "rgba(7, 18, 57, 1)",
    },
    seamOffsetRad: 0,
  },
};

export const TABLE_GLASS_EFFECT = {
  enabled: true,
  excludeHeader: true,
  rowHoverEffect: {
    enabled: true,
    color: "rgba(255, 255, 255, 0.03)",
    borderColor: "rgba(255, 255, 255, 0.15)",
    spotlightRadius: 500,
  },
  chromaticAberration: {
    enabled: true,
    offset: 2,
    opacity: 0.5,
  },
  threeD: {
    ...PIE_CHART_GLASS_EFFECT.threeD,
    electric: {
      ...PIE_CHART_GLASS_EFFECT.threeD.electric,
      enabled: false,
      intensity: 0.1,
      width: 0.1,
      arcThickness: 1,
      streakSpeedMultiplier: 1,
      colors: {
        primary: "rgba(255, 255, 255, 0.4)",
        secondary: "rgba(255, 255, 255, 0.2)",
        tertiary: "rgba(255, 255, 255, 0.05)",
        quaternary: "rgba(255, 255, 255, 0.0)",
      },
    },
    reflection: {
      enabled: true,
      speed: 0.05,
      intensity: 0.1,
      width: 0.5,
      color: "rgba(255, 255, 255, 1)",
      fadeZone: 0.15,
    },
  },
};

export const GRAPH_BACKGROUND_IMAGE = {
  enabled: true,
};
