/**
 * Utility functions for graph visualization
 * Pure JavaScript - no dependencies
 */

/**
 * Remove HTML tags from text
 * @param {string} text - Text with possible HTML tags
 * @returns {string} - Clean text without HTML
 */
export function stripHtml(text) {
  if (!text) return "";

  let clean = text;
  let previous;

  // Run replacements until the string stops changing to prevent bypasses via nested tags
  // We avoid DOMParser here because it decodes HTML entities which could lead to mutation XSS
  // if later injected, and it also deletes legitimate text containing unclosed angle brackets.
  do {
    previous = clean;
    // Remove dangerous tags/attrs first
    clean = clean.replace(/<[^>]*?(?:on\w*|style|script|iframe)[^>]*?>/gi, "");

    // Remove remaining tags (CodeQL warning mitigated by this loop)
    // codeql[js/incomplete-sanitization] mitigated by loop; intended for display only
    clean = clean.replace(/<[^>]+>/g, "");
  } while (clean !== previous);

  // Remove Anki field separators
  clean = clean.replace(/::/g, " ");

  // Remove newlines
  clean = clean.replace(/\n/g, " ");

  // Clean whitespace and truncate
  clean = clean.split(/\s+/).join(" ").trim();
  return clean.substring(0, 60);
}

/**
 * Assign a consistent color to a deck
 * @param {string} deckName - Name of the deck
 * @param {Object} predefinedColors - Map of deck names to colors
 * @returns {string} - Hex color code
 */
export function assignDeckColor(deckName, predefinedColors = {}) {
  if (!deckName) return "#888888";

  // Clean deck name (remove unit separators and other control chars)
  const cleanDeckName = deckName.replace(/[\x00-\x1f]/g, "");

  // Check predefined colors first
  if (predefinedColors[cleanDeckName]) {
    return predefinedColors[cleanDeckName];
  }

  // Generate consistent color from deck name hash
  let hash = 0;
  for (let i = 0; i < cleanDeckName.length; i++) {
    hash = cleanDeckName.charCodeAt(i) + ((hash << 5) - hash);
  }

  // Use HSL for better color control - saturated, medium brightness
  const hue = hash % 360;
  const saturation = 70; // 70% saturation (vibrant)
  const lightness = 50; // 50% lightness (not too dark, not too light)

  // Convert HSL to hex
  const c = ((1 - Math.abs((2 * lightness) / 100 - 1)) * saturation) / 100;
  const x = c * (1 - Math.abs(((hue / 60) % 2) - 1));
  const m = lightness / 100 - c / 2;

  let r, g, b;
  if (hue < 60) {
    r = c;
    g = x;
    b = 0;
  } else if (hue < 120) {
    r = x;
    g = c;
    b = 0;
  } else if (hue < 180) {
    r = 0;
    g = c;
    b = x;
  } else if (hue < 240) {
    r = 0;
    g = x;
    b = c;
  } else if (hue < 300) {
    r = x;
    g = 0;
    b = c;
  } else {
    r = c;
    g = 0;
    b = x;
  }

  const R = Math.round((r + m) * 255);
  const G = Math.round((g + m) * 255);
  const B = Math.round((b + m) * 255);

  return `#${((1 << 24) + R * 65536 + G * 256 + B).toString(16).slice(1).toUpperCase()}`;
}

/**
 * Position nodes using force-directed layout with deck clustering
 * @param {Array} nodes - Array of node objects with deck property
 * @param {Object} options - Layout options
 * @returns {Array} - Positioned nodes
 */
export function positionNodes(nodes, options = {}) {
  if (!nodes || nodes.length === 0) return [];

  const {
    maxBounds = 250,
    repulsion = 20,
    damping = 0.9,
    iterations = 100,
    deckClusterForce = 0.2,
    interDeckRepulsion = 50,
  } = options;

  // Group nodes by deck
  const deckGroups = {};
  nodes.forEach((node, i) => {
    const deck = node.deck || "Unknown";
    if (!deckGroups[deck]) deckGroups[deck] = [];
    deckGroups[deck].push(i);
  });

  const decks = Object.keys(deckGroups);
  const numDecks = decks.length;

  // Assign initial positions - spread decks in circle
  const positions = nodes.map((node, i) => {
    const deck = node.deck || "Unknown";
    const deckIndex = decks.indexOf(deck);

    // Angle for this deck
    const deckAngle = numDecks > 1 ? (deckIndex / numDecks) * Math.PI * 2 : 0;

    // Radius based on number of decks
    const deckRadius = numDecks > 1 ? 80 : 0;

    // Add randomness within deck cluster
    return {
      x: Math.cos(deckAngle) * deckRadius + (Math.random() - 0.5) * 40,
      y: Math.sin(deckAngle) * deckRadius + (Math.random() - 0.5) * 40,
      z: (Math.random() - 0.5) * 30,
    };
  });

  const velocities = nodes.map(() => ({ x: 0, y: 0, z: 0 }));

  // Force-directed layout
  for (let iter = 0; iter < iterations; iter++) {
    for (let i = 0; i < positions.length; i++) {
      for (let j = i + 1; j < positions.length; j++) {
        const dx = positions[i].x - positions[j].x;
        const dy = positions[i].y - positions[j].y;
        const dz = positions[i].z - positions[j].z;
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz) || 1;

        const sameDeck = nodes[i].deck === nodes[j].deck;

        // Base repulsion between all nodes
        let force = repulsion / (dist * dist);

        // Extra repulsion for different decks (pushes clusters apart)
        if (!sameDeck) {
          force += interDeckRepulsion / (dist * dist);
        }

        // Apply repulsion
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        const fz = (dz / dist) * force;

        velocities[i].x += fx;
        velocities[i].y += fy;
        velocities[i].z += fz;
        velocities[j].x -= fx;
        velocities[j].y -= fy;
        velocities[j].z -= fz;

        // Attraction for same deck (keeps cluster together)
        if (sameDeck && deckClusterForce > 0) {
          const attraction = dist * deckClusterForce * 0.005;
          velocities[i].x -= dx * attraction;
          velocities[i].y -= dy * attraction;
          velocities[i].z -= dz * attraction;
          velocities[j].x += dx * attraction;
          velocities[j].y += dy * attraction;
          velocities[j].z += dz * attraction;
        }
      }

      // Gentle center gravity
      const distFromCenter = Math.sqrt(
        positions[i].x ** 2 + positions[i].y ** 2 + positions[i].z ** 2,
      );

      if (distFromCenter > 180) {
        velocities[i].x -= positions[i].x * 0.003;
        velocities[i].y -= positions[i].y * 0.003;
        velocities[i].z -= positions[i].z * 0.003;
      }
    }

    // Apply velocities
    for (let i = 0; i < positions.length; i++) {
      velocities[i].x *= damping;
      velocities[i].y *= damping;
      velocities[i].z *= damping;

      positions[i].x += velocities[i].x;
      positions[i].y += velocities[i].y;
      positions[i].z += velocities[i].z;

      // Hard bounds
      positions[i].x = Math.max(
        -maxBounds,
        Math.min(maxBounds, positions[i].x),
      );
      positions[i].y = Math.max(
        -maxBounds,
        Math.min(maxBounds, positions[i].y),
      );
      positions[i].z = Math.max(
        -maxBounds,
        Math.min(maxBounds, positions[i].z),
      );
    }
  }

  return nodes.map((node, i) => ({
    ...node,
    x: positions[i].x,
    y: positions[i].y,
    z: positions[i].z,
  }));
}

/**
 * Scale node size based on PageRank
 * @param {number} pagerank - PageRank score
 * @returns {number} - Scaled size
 */
export function scaleNodeSize(pagerank) {
  return Math.min(3, Math.max(0.5, pagerank * 100));
}
