/**
 * Tests for deck color assignment
 */

import { describe, it, expect } from "@jest/globals";
import { assignDeckColor } from "../viz_utils.js";

describe("Deck Color Assignment", () => {
  it("assigns different colors to different decks", () => {
    const color1 = assignDeckColor("言語日語");
    const color2 = assignDeckColor("言語英語");
    expect(color1).not.toBe(color2);
  });

  it("assigns consistent color for same deck", () => {
    const color1 = assignDeckColor("言語日語");
    const color2 = assignDeckColor("言語日語");
    expect(color1).toBe(color2);
  });

  it("handles deck names with special characters", () => {
    const deck1 = "言語\x1f英語";
    const deck2 = "言語\x1f日語";
    const color1 = assignDeckColor(deck1);
    const color2 = assignDeckColor(deck2);
    expect(color1).not.toBe(color2);
  });

  it("returns valid hex color", () => {
    const color = assignDeckColor("Test Deck");
    expect(color).toMatch(/^#[0-9A-F]{6}$/i);
  });

  it("handles empty deck name", () => {
    const color = assignDeckColor("");
    expect(color).toBe("#888888");
  });

  it("handles null/undefined deck name", () => {
    expect(assignDeckColor(null)).toBe("#888888");
    expect(assignDeckColor(undefined)).toBe("#888888");
  });
});
