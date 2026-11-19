import test, { describe } from "node:test";
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { JSDOM } from "jsdom";

const ROOT_DIR = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
);
const PAGES = ["index.html", "terminal/index.html", "graph/index.html"];
const ICON_UNICODE = {
  code: "f121",
  connectdevelop: "f20e",
  "chevron-right": "f054",
  filter: "f0b0",
  github: "f09b",
};
const normalizePath = (value) => value.replace(/\s+/g, " ").trim();

describe("inline navigation icons", () => {
  for (const page of PAGES) {
    test(`${page} uses original Font Awesome geometry without icon-font requests`, () => {
      const html = fs.readFileSync(path.join(ROOT_DIR, page), "utf8");
      const document = new JSDOM(html).window.document;
      assert.strictEqual(
        document.querySelector('link[href*="font-awesome"]'),
        null,
      );
      assert.strictEqual(
        document.querySelector('link[href*="fontawesome-webfont"]'),
        null,
      );
      assert.strictEqual(
        document.querySelector('script[src*="icon_font_ready"]'),
        null,
      );

      const icons = Array.from(document.querySelectorAll(".fa"));
      assert.ok(icons.length > 0);
      const fontSvg = fs.readFileSync(
        path.join(ROOT_DIR, "assets/vendor/fonts/fontawesome-webfont.svg"),
        "utf8",
      );

      for (const icon of icons) {
        assert.strictEqual(icon.tagName.toLowerCase(), "svg");
        const iconName = Array.from(icon.classList).find((name) =>
          name.startsWith("fa-"),
        );
        const name = iconName.slice(3);
        assert.strictEqual(icon.getAttribute("aria-hidden"), "true");
        assert.strictEqual(icon.getAttribute("focusable"), "false");
        assert.strictEqual(
          icon.querySelector("use").getAttribute("href"),
          `#icon-${name}`,
        );

        const symbol = document.getElementById(`icon-${name}`);
        assert.ok(symbol);
        const glyphTag = fontSvg.match(
          new RegExp(`<glyph[^>]*unicode="&#x${ICON_UNICODE[name]};"[^>]*>`),
        );
        assert.ok(glyphTag);
        const expectedPath = glyphTag[0].match(/\bd="([^"]+)"/)[1];
        assert.strictEqual(
          normalizePath(symbol.querySelector("path").getAttribute("d")),
          normalizePath(expectedPath),
        );
      }
    });
  }
});
