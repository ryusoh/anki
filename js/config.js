export const DATA_PATHS = {
  customStats: "/data/anki/custom_stats_data.json",
  reviewStats: "/data/anki/review_stats_data.json",
  graphData: "/graph/graph_data.json",
};

export const TABLE_GLASS_EFFECT = {
  enabled: true,
  excludeHeader: false,
  opacity: 0.75,
  responsiveOpacity: {
    desktop: 0.4,
    mobile: 0.4,
  },
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
      enabled: true,
      speed: 0.05,
      intensity: 0.1,
      width: 0.5,
      color: "rgba(255, 255, 255, 1)",
      fadeZone: 0.15,
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
      arcCount: 3,
      particlesEnabled: false,
      particleColors: null,
      particleSpeedMultiplier: 0.5,
    },
    ambientGlow: {
      innerOpacity: 0.15,
      outerOpacity: 0.05,
      pulseSpeed: 0.6,
      innerColor: "rgba(118, 183, 229, 1)",
      outerColor: "rgba(7, 18, 57, 1)",
    },
  },
};

export const GRAPH_BACKGROUND_IMAGE = {
  enabled: true,
};
