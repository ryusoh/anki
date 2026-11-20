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
const CSS_FILES = ["css/base.css", "css/graph.css", "css/terminal/base.css"];
const ICON_UNICODE = {
  code: "f121",
  connectdevelop: "f20e",
  "chevron-right": "f054",
  filter: "f0b0",
  github: "f09b",
};

const readEmbeddedFont = (css) => {
  const match = css.match(
    /font-family:\s*["']AnkiIcons["'];[\s\S]*?url\((["'])data:font\/woff;base64,([^'"]+)\1\)\s*format\((["'])woff\3\)/,
  );
  assert.ok(match);
  return Buffer.from(match[2], "base64");
};

describe("embedded navigation icons", () => {
  for (const file of CSS_FILES) {
    test(`${file} embeds a small WOFF subset and all used glyphs`, () => {
      const css = fs.readFileSync(path.join(ROOT_DIR, file), "utf8");
      const font = readEmbeddedFont(css);

      assert.strictEqual(font.subarray(0, 4).toString("ascii"), "wOFF");
      assert.ok(font.length < 4096);
      for (const [name, unicode] of Object.entries(ICON_UNICODE)) {
        assert.match(
          css,
          new RegExp(
            `\\.fa-${name}::before\\s*\\{\\s*content:\\s*["']\\\\${unicode}["'];`,
          ),
        );
      }
    });
  }

  test("all stylesheets embed the identical subset", () => {
    const fonts = CSS_FILES.map((file) =>
      readEmbeddedFont(fs.readFileSync(path.join(ROOT_DIR, file), "utf8")),
    );
    assert.ok(fonts.every((font) => font.equals(fonts[0])));
  });

  for (const page of PAGES) {
    test(`${page} uses smoothed font glyphs without icon-font requests`, () => {
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
      assert.strictEqual(document.querySelector(".icon-sprite"), null);

      const icons = Array.from(document.querySelectorAll(".fa"));
      assert.ok(icons.length > 0);
      for (const icon of icons) {
        assert.strictEqual(icon.tagName.toLowerCase(), "i");
        assert.strictEqual(icon.getAttribute("aria-hidden"), "true");
        const iconName = Array.from(icon.classList).find((name) =>
          name.startsWith("fa-"),
        );
        assert.ok(
          Object.prototype.hasOwnProperty.call(ICON_UNICODE, iconName.slice(3)),
        );
      }
    });
  }
});
