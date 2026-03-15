/**
 * Tests for deck-based clustering
 */

import { describe, it, expect } from "@jest/globals";
import { positionNodes } from "../viz_utils.js";

describe("Deck-Based Clustering", () => {
  it("groups nodes from same deck closer together", () => {
    const nodes = [
      { id: "n1", deck: "Deck A", x: 0, y: 0, z: 0 },
      { id: "n2", deck: "Deck A", x: 10, y: 10, z: 10 },
      { id: "n3", deck: "Deck B", x: 100, y: 100, z: 100 },
      { id: "n4", deck: "Deck B", x: 110, y: 110, z: 110 },
    ];

    const positioned = positionNodes(nodes, {
      maxBounds: 250,
      deckClusterForce: 0.5,
      interDeckRepulsion: 100,
    });

    // Calculate distances within decks
    const deckADist = distance(positioned[0], positioned[1]);
    const deckBDist = distance(positioned[2], positioned[3]);
    const crossDeckDist = distance(positioned[0], positioned[2]);

    // Nodes in same deck should be closer than nodes in different decks
    expect(deckADist).toBeLessThan(crossDeckDist);
    expect(deckBDist).toBeLessThan(crossDeckDist);
  });

  it("positions different decks in different regions", () => {
    const nodes = [
      { id: "n1", deck: "日本語", x: 0, y: 0, z: 0 },
      { id: "n2", deck: "日本語", x: 10, y: 10, z: 10 },
      { id: "n3", deck: "English", x: 0, y: 0, z: 0 },
      { id: "n4", deck: "English", x: 10, y: 10, z: 10 },
    ];

    const positioned = positionNodes(nodes, {
      maxBounds: 250,
      deckClusterForce: 0.5,
      interDeckRepulsion: 100,
    });

    // Calculate deck centers
    const deckACenter = centroid([positioned[0], positioned[1]]);
    const deckBCenter = centroid([positioned[2], positioned[3]]);

    // Deck centers should be far apart
    const deckDistance = distance(deckACenter, deckBCenter);
    expect(deckDistance).toBeGreaterThan(50);
  });

  it("keeps all decks within bounds", () => {
    const nodes = Array(50)
      .fill(null)
      .map((_, i) => ({
        id: `n${i}`,
        deck: i % 2 === 0 ? "Deck A" : "Deck B",
        x: (Math.random() - 0.5) * 100,
        y: (Math.random() - 0.5) * 100,
        z: (Math.random() - 0.5) * 100,
      }));

    const positioned = positionNodes(nodes, { maxBounds: 250 });

    positioned.forEach((node) => {
      expect(Math.abs(node.x)).toBeLessThanOrEqual(250);
      expect(Math.abs(node.y)).toBeLessThanOrEqual(250);
      expect(Math.abs(node.z)).toBeLessThanOrEqual(250);
    });
  });

  it("handles multiple decks (3+)", () => {
    const nodes = Array(90)
      .fill(null)
      .map((_, i) => ({
        id: `n${i}`,
        deck: ["Deck A", "Deck B", "Deck C"][i % 3],
        x: (Math.random() - 0.5) * 100,
        y: (Math.random() - 0.5) * 100,
        z: (Math.random() - 0.5) * 100,
      }));

    const positioned = positionNodes(nodes, {
      maxBounds: 250,
      deckClusterForce: 0.5,
      interDeckRepulsion: 100,
    });

    // Group by deck
    const decks = {};
    positioned.forEach((node) => {
      if (!decks[node.deck]) decks[node.deck] = [];
      decks[node.deck].push(node);
    });

    // Calculate deck centers
    const centers = {};
    Object.keys(decks).forEach((deck) => {
      centers[deck] = centroid(decks[deck]);
    });

    // All deck centers should be far from each other
    const deckNames = Object.keys(centers);
    for (let i = 0; i < deckNames.length; i++) {
      for (let j = i + 1; j < deckNames.length; j++) {
        const dist = distance(centers[deckNames[i]], centers[deckNames[j]]);
        expect(dist).toBeGreaterThan(30);
      }
    }
  });
});

// Helper functions
function distance(a, b) {
  return Math.sqrt(
    Math.pow(b.x - a.x, 2) + Math.pow(b.y - a.y, 2) + Math.pow(b.z - a.z, 2),
  );
}

function centroid(nodes) {
  const sum = nodes.reduce(
    (acc, node) => ({
      x: acc.x + node.x,
      y: acc.y + node.y,
      z: acc.z + node.z,
    }),
    { x: 0, y: 0, z: 0 },
  );

  return {
    x: sum.x / nodes.length,
    y: sum.y / nodes.length,
    z: sum.z / nodes.length,
  };
}
