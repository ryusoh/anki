/**
 * Tests for 3D graph visualization
 */

import { describe, it, expect, beforeEach } from "@jest/globals";
import {
  stripHtml,
  assignDeckColor,
  positionNodes,
} from "../graph/viz_utils.js";

describe("HTML Stripping", () => {
  it("removes bold tags", () => {
    const input = "This is <b>bold</b> text";
    expect(stripHtml(input)).toBe("This is bold text");
  });

  it("removes italic tags", () => {
    const input = "<i>italic</i> text";
    expect(stripHtml(input)).toBe("italic text");
  });

  it("removes multiple tag types", () => {
    const input = "<b>bold</b> and <i>italic</i> and <u>underline</u>";
    expect(stripHtml(input)).toBe("bold and italic and underline");
  });

  it("removes Anki field separators", () => {
    const input = "Front::Back";
    expect(stripHtml(input)).toBe("Front Back");
  });

  it("handles Japanese text", () => {
    const input = "これがこの町で一番<b>高い</b>ビルです。";
    expect(stripHtml(input)).toContain("高い");
    expect(stripHtml(input)).not.toContain("<b>");
  });

  it("returns empty string for null/undefined", () => {
    expect(stripHtml(null)).toBe("");
    expect(stripHtml(undefined)).toBe("");
    expect(stripHtml("")).toBe("");
  });
});

describe("Deck Color Assignment", () => {
  const deckColors = {
    言語日語: "#FF6B6B",
    言語粵語: "#4ECDC4",
    言語英語: "#45B7D1",
    言語呉語: "#96CEB4",
    言語台語: "#FFEAA7",
    金融: "#DDA0DD",
  };

  it("assigns consistent color per deck", () => {
    const color1 = assignDeckColor("言語日語", deckColors);
    const color2 = assignDeckColor("言語日語", deckColors);
    expect(color1).toBe(color2);
  });

  it("assigns different colors to different decks", () => {
    const color1 = assignDeckColor("言語日語", deckColors);
    const color2 = assignDeckColor("言語粵語", deckColors);
    expect(color1).not.toBe(color2);
  });

  it("generates color for unknown decks", () => {
    const color = assignDeckColor("Unknown Deck", deckColors);
    expect(color).toMatch(/^#[0-9A-F]{6}$/i);
  });

  it("uses hash-based color for consistency", () => {
    const color1 = assignDeckColor("Test Deck", deckColors);
    const color2 = assignDeckColor("Test Deck", deckColors);
    expect(color1).toBe(color2);
  });
});

describe("Node Positioning", () => {
  it("keeps nodes within bounds", () => {
    const nodes = Array(100)
      .fill(null)
      .map((_, i) => ({
        id: `node${i}`,
        x: (Math.random() - 0.5) * 400,
        y: (Math.random() - 0.5) * 400,
        z: (Math.random() - 0.5) * 400,
      }));

    const positioned = positionNodes(nodes, { maxBounds: 250 });

    positioned.forEach((node) => {
      expect(node.x).toBeGreaterThanOrEqual(-250);
      expect(node.x).toBeLessThanOrEqual(250);
      expect(node.y).toBeGreaterThanOrEqual(-250);
      expect(node.y).toBeLessThanOrEqual(250);
      expect(node.z).toBeGreaterThanOrEqual(-250);
      expect(node.z).toBeLessThanOrEqual(250);
    });
  });

  it("applies center gravity to distant nodes", () => {
    const nodes = [
      {
        id: "far_node",
        x: 300,
        y: 300,
        z: 300,
      },
    ];

    const positioned = positionNodes(nodes, {
      maxBounds: 250,
      centerGravity: 0.01,
    });

    // Node should be pulled closer to center
    const dist = Math.sqrt(
      positioned[0].x ** 2 + positioned[0].y ** 2 + positioned[0].z ** 2,
    );
    expect(dist).toBeLessThan(Math.sqrt(300 ** 2 * 3));
  });
});
