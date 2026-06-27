/**
 * TDD Tests for positionNodes function
 * Run with: node --experimental-vm-modules --no-warnings node_modules/.bin/jest test_positioning.test.js
 */

import { describe, it, expect } from "@jest/globals";
import { positionNodes } from "../viz_utils.js";

describe("positionNodes - Basic Functionality", () => {
  it("returns same number of nodes as input", () => {
    const nodes = Array(100)
      .fill(null)
      .map((_, i) => ({
        id: `n${i}`,
        deck: "Test",
        x: 0,
        y: 0,
        z: 0,
      }));

    const positioned = positionNodes(nodes);

    expect(positioned.length).toBe(100);
  });

  it("keeps all nodes within bounds", () => {
    const nodes = Array(100)
      .fill(null)
      .map((_, i) => ({
        id: `n${i}`,
        deck: "Test",
        x: (Math.random() - 0.5) * 200,
        y: (Math.random() - 0.5) * 200,
        z: (Math.random() - 0.5) * 200,
      }));

    const positioned = positionNodes(nodes, { maxBounds: 250 });

    positioned.forEach((node) => {
      expect(Math.abs(node.x)).toBeLessThanOrEqual(250);
      expect(Math.abs(node.y)).toBeLessThanOrEqual(250);
      expect(Math.abs(node.z)).toBeLessThanOrEqual(250);
    });
  });

  it("preserves node properties", () => {
    const nodes = [{ id: "n1", deck: "Deck A", pagerank: 0.01, label: "Test" }];

    const positioned = positionNodes(nodes);

    expect(positioned[0].id).toBe("n1");
    expect(positioned[0].deck).toBe("Deck A");
    expect(positioned[0].pagerank).toBe(0.01);
    expect(positioned[0].label).toBe("Test");
  });
});

describe("positionNodes - Deck Clustering", () => {
  it("creates separate clusters for different decks", () => {
    const nodes = [
      // Deck A - 10 nodes
      ...Array(10)
        .fill(null)
        .map((_, i) => ({
          id: `a${i}`,
          deck: "Deck A",
          x: (Math.random() - 0.5) * 50,
          y: (Math.random() - 0.5) * 50,
          z: (Math.random() - 0.5) * 50,
        })),
      // Deck B - 10 nodes
      ...Array(10)
        .fill(null)
        .map((_, i) => ({
          id: `b${i}`,
          deck: "Deck B",
          x: (Math.random() - 0.5) * 50,
          y: (Math.random() - 0.5) * 50,
          z: (Math.random() - 0.5) * 50,
        })),
    ];

    const positioned = positionNodes(nodes, {
      maxBounds: 250,
      deckClusterForce: 0.5,
      interDeckRepulsion: 100,
      iterations: 100,
    });

    // Calculate cluster centers
    const deckA = positioned.filter((n) => n.deck === "Deck A");
    const deckB = positioned.filter((n) => n.deck === "Deck B");

    const centerA = {
      x: deckA.reduce((s, n) => s + n.x, 0) / deckA.length,
      y: deckA.reduce((s, n) => s + n.y, 0) / deckA.length,
      z: deckA.reduce((s, n) => s + n.z, 0) / deckA.length,
    };

    const centerB = {
      x: deckB.reduce((s, n) => s + n.x, 0) / deckB.length,
      y: deckB.reduce((s, n) => s + n.y, 0) / deckB.length,
      z: deckB.reduce((s, n) => s + n.z, 0) / deckB.length,
    };

    // Distance between centers
    const dist = Math.sqrt(
      Math.pow(centerA.x - centerB.x, 2) +
        Math.pow(centerA.y - centerB.y, 2) +
        Math.pow(centerA.z - centerB.z, 2),
    );

    // Centers should be far apart (> 50 units)
    expect(dist).toBeGreaterThan(50);
  });

  it("keeps same-deck nodes close together", () => {
    const nodes = Array(20)
      .fill(null)
      .map((_, i) => ({
        id: `n${i}`,
        deck: "Same Deck",
        x: (Math.random() - 0.5) * 100,
        y: (Math.random() - 0.5) * 100,
        z: (Math.random() - 0.5) * 100,
      }));

    const positioned = positionNodes(nodes, {
      deckClusterForce: 0.5,
      iterations: 100,
    });

    // Calculate average distance from center
    const center = {
      x: positioned.reduce((s, n) => s + n.x, 0) / positioned.length,
      y: positioned.reduce((s, n) => s + n.y, 0) / positioned.length,
      z: positioned.reduce((s, n) => s + n.z, 0) / positioned.length,
    };

    const avgDist =
      positioned.reduce((sum, n) => {
        return (
          sum +
          Math.sqrt(
            Math.pow(n.x - center.x, 2) +
              Math.pow(n.y - center.y, 2) +
              Math.pow(n.z - center.z, 2),
          )
        );
      }, 0) / positioned.length;

    // Average distance should be reasonable (< 100 units)
    expect(avgDist).toBeLessThan(100);
  });

  it("handles 3+ decks without overlap", () => {
    const nodes = [
      ...Array(30)
        .fill(null)
        .map((_, i) => ({
          id: `a${i}`,
          deck: "Deck A",
          x: (Math.random() - 0.5) * 50,
          y: (Math.random() - 0.5) * 50,
          z: (Math.random() - 0.5) * 50,
        })),
      ...Array(30)
        .fill(null)
        .map((_, i) => ({
          id: `b${i}`,
          deck: "Deck B",
          x: (Math.random() - 0.5) * 50,
          y: (Math.random() - 0.5) * 50,
          z: (Math.random() - 0.5) * 50,
        })),
      ...Array(30)
        .fill(null)
        .map((_, i) => ({
          id: `c${i}`,
          deck: "Deck C",
          x: (Math.random() - 0.5) * 50,
          y: (Math.random() - 0.5) * 50,
          z: (Math.random() - 0.5) * 50,
        })),
    ];

    const positioned = positionNodes(nodes, {
      maxBounds: 250,
      deckClusterForce: 0.5,
      interDeckRepulsion: 100,
      iterations: 150,
    });

    // Get cluster centers
    const getCenter = (deck) => {
      const deckNodes = positioned.filter((n) => n.deck === deck);
      return {
        x: deckNodes.reduce((s, n) => s + n.x, 0) / deckNodes.length,
        y: deckNodes.reduce((s, n) => s + n.y, 0) / deckNodes.length,
        z: deckNodes.reduce((s, n) => s + n.z, 0) / deckNodes.length,
      };
    };

    const centerA = getCenter("Deck A");
    const centerB = getCenter("Deck B");
    const centerC = getCenter("Deck C");

    // Distance helper
    const dist = (a, b) =>
      Math.sqrt(
        Math.pow(a.x - b.x, 2) +
          Math.pow(a.y - b.y, 2) +
          Math.pow(a.z - b.z, 2),
      );

    // All centers should be far apart
    expect(dist(centerA, centerB)).toBeGreaterThan(40);
    expect(dist(centerA, centerC)).toBeGreaterThan(40);
    expect(dist(centerB, centerC)).toBeGreaterThan(40);
  });
});

describe("positionNodes - Edge Cases", () => {
  it("handles empty node list", () => {
    const positioned = positionNodes([]);
    expect(positioned.length).toBe(0);
  });

  it("handles single node", () => {
    const nodes = [{ id: "n1", deck: "Test", x: 0, y: 0, z: 0 }];
    const positioned = positionNodes(nodes);
    expect(positioned.length).toBe(1);
    expect(positioned[0].x).toBeDefined();
  });

  it("handles nodes without deck property", () => {
    const nodes = [
      { id: "n1", x: 0, y: 0, z: 0 },
      { id: "n2", deck: null, x: 0, y: 0, z: 0 },
      { id: "n3", deck: "Test", x: 0, y: 0, z: 0 },
    ];

    const positioned = positionNodes(nodes);

    // Should not crash and should position all nodes
    expect(positioned.length).toBe(3);
    positioned.forEach((n) => {
      expect(n.x).toBeDefined();
      expect(n.y).toBeDefined();
      expect(n.z).toBeDefined();
    });
  });
});
