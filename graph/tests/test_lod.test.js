/**
 * Tests for Frustum Culling and LOD system
 */

import { describe, it, expect, beforeEach } from "@jest/globals";

describe("FrustumCulling", () => {
  beforeEach(() => {
    // Mock THREE objects
    global.THREE = {
      Frustum: jest.fn().mockImplementation(() => ({
        containsPoint: jest.fn(),
      })),
      Vector3: jest.fn().mockImplementation((x, y, z) => ({ x, y, z })),
      Matrix4: jest.fn(),
    };
  });

  it("culls nodes outside camera view", () => {
    const { isVisibleInFrustum } = require("../../js/graph/lod_utils.js");

    const frustum = {
      containsPoint: jest
        .fn()
        .mockReturnValueOnce(false) // Outside
        .mockReturnValueOnce(true), // Inside
    };

    const node1 = { x: 1000, y: 1000, z: 1000 }; // Far outside
    const node2 = { x: 10, y: 10, z: 10 }; // Inside view

    expect(isVisibleInFrustum(node1, frustum)).toBe(false);
    expect(isVisibleInFrustum(node2, frustum)).toBe(true);
  });

  it("only processes visible nodes", () => {
    const { cullNodes } = require("../../js/graph/lod_utils.js");

    const nodes = Array(1000)
      .fill(null)
      .map((_, i) => ({
        id: `n${i}`,
        x: (Math.random() - 0.5) * 1000,
        y: (Math.random() - 0.5) * 1000,
        z: (Math.random() - 0.5) * 1000,
      }));

    const frustum = {
      containsPoint: jest.fn((point) => {
        // Simulate 10% visible
        return Math.random() < 0.1;
      }),
    };

    const visible = cullNodes(nodes, frustum);

    // Should have ~10% visible
    expect(visible.length).toBeLessThan(nodes.length);
    expect(visible.length).toBeGreaterThan(0);
  });

  it("handles empty node list", () => {
    const { cullNodes } = require("../../js/graph/lod_utils.js");

    const frustum = { containsPoint: jest.fn(() => true) };
    const visible = cullNodes([], frustum);

    expect(visible).toEqual([]);
  });

  // REGRESSION TEST: Ensure all nodes are visible when frustum is large enough
  it("shows all nodes when camera encompasses all positions", () => {
    const { filterNodesByLOD } = require("../../js/graph/lod_utils.js");

    // Create mock camera that sees everything
    const mockCamera = {
      position: { x: 0, y: 0, z: 500 },
      projectionMatrix: { elements: Array(16).fill(1) },
      matrixWorldInverse: { elements: Array(16).fill(1) },
    };

    const nodes = Array(1000)
      .fill(null)
      .map((_, i) => ({
        id: `n${i}`,
        x: (Math.random() - 0.5) * 200, // Within view
        y: (Math.random() - 0.5) * 200,
        z: (Math.random() - 0.5) * 200,
      }));

    const result = filterNodesByLOD(nodes, mockCamera);
    const total = result.high.length + result.medium.length + result.low.length;

    // REGRESSION: Should show MOST nodes (at least 90%)
    // This prevents the bug where all nodes were culled
    expect(total).toBeGreaterThan(nodes.length * 0.9);
  });
});

describe("LevelOfDetail", () => {
  it("selects LOD based on distance", () => {
    const { getLODLevel } = require("../../js/graph/lod_utils.js");

    // Close: Full detail
    expect(getLODLevel(50)).toBe("high");

    // Medium: Medium detail
    expect(getLODLevel(200)).toBe("medium");

    // Far: Low detail
    expect(getLODLevel(500)).toBe("low");

    // Very far: Hidden
    expect(getLODLevel(1000)).toBe("hidden");
  });

  it("uses appropriate geometry for each LOD", () => {
    const { getGeometryForLOD } = require("../../js/graph/lod_utils.js");

    // High: 16 segments
    expect(getGeometryForLOD("high").segments).toBe(16);

    // Medium: 8 segments
    expect(getGeometryForLOD("medium").segments).toBe(8);

    // Low: 4 segments (or sprite)
    expect(getGeometryForLOD("low").segments).toBe(4);
  });

  it("reduces draw calls for distant nodes", () => {
    const { getLODStats } = require("../../js/graph/lod_utils.js");

    const nodes = Array(10000)
      .fill(null)
      .map((_, i) => ({
        id: `n${i}`,
        x: (Math.random() - 0.5) * 1000,
        y: (Math.random() - 0.5) * 1000,
        z: (Math.random() - 0.5) * 1000,
      }));

    const cameraPos = { x: 0, y: 0, z: 500 };
    const stats = getLODStats(nodes, cameraPos);

    // Should have distribution across LOD levels
    expect(stats.high).toBeDefined();
    expect(stats.medium).toBeDefined();
    expect(stats.low).toBeDefined();
    expect(stats.hidden).toBeDefined();

    // Total should equal input
    expect(stats.high + stats.medium + stats.low + stats.hidden).toBe(10000);

    // Most should be medium/low (camera is at 500, nodes spread over 1000)
    expect(stats.medium + stats.low).toBeGreaterThan(stats.high);
  });
});

describe("ProgressiveLoading", () => {
  it("loads nodes in batches", () => {
    const { loadNodesInBatches } = require("../../js/graph/lod_utils.js");

    const nodes = Array(1000)
      .fill(null)
      .map((_, i) => ({
        id: `n${i}`,
        deck: i % 3 === 0 ? "A" : "B",
      }));

    const batches = loadNodesInBatches(nodes, 100);

    expect(batches.length).toBe(10);
    expect(batches[0].length).toBe(100);
    expect(batches[9].length).toBe(100);
  });

  it("prioritizes visible nodes", () => {
    const { prioritizeNodes } = require("../../js/graph/lod_utils.js");

    const nodes = Array(1000)
      .fill(null)
      .map((_, i) => ({
        id: `n${i}`,
        x: i * 10, // Spread out
        y: 0,
        z: 0,
        priority: i < 100 ? 1 : 0, // First 100 are high priority
      }));

    const cameraPos = { x: 0, y: 0, z: 0 };
    const prioritized = prioritizeNodes(nodes, cameraPos, 100);

    // High priority nodes should be first
    expect(prioritized.slice(0, 100).every((n) => n.priority === 1)).toBe(true);
  });

  it("groups nodes by deck for instancing", () => {
    const { groupByDeck } = require("../../js/graph/lod_utils.js");

    const nodes = [
      { id: "n1", deck: "Deck A" },
      { id: "n2", deck: "Deck B" },
      { id: "n3", deck: "Deck A" },
      { id: "n4", deck: "Deck B" },
      { id: "n5", deck: "Deck A" },
    ];

    const groups = groupByDeck(nodes);

    expect(groups["Deck A"].length).toBe(3);
    expect(groups["Deck B"].length).toBe(2);
  });
});
